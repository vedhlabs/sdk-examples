import asyncio
import os
import subprocess
import sys
from pathlib import Path

import pytest
from aga_strands import StrandsAdapter
from strands.types.exceptions import EventLoopException

from agent_quickstart import bedrock, workflows


def test_local_model_runs_through_a_real_strands_agent():
    agent = workflows.build_research_agent()
    result = asyncio.run(agent.invoke_async("Why keep a durable record?"))

    assert str(result).strip() == (
        "Local research complete: Why keep a durable record?"
    )
    assert result.metrics.accumulated_usage == {
        "inputTokens": 4,
        "outputTokens": 5,
        "totalTokens": 9,
    }


def test_agent_is_bound_as_one_opaque_operation():
    assert isinstance(workflows.strands_adapter, StrandsAdapter)
    assert workflows.research.manifest.durability_mode == "opaque"
    assert workflows.research.manifest.framework == "strands-agents"
    assert workflows.research._step._spec.operation_class == "agent"
    assert set(workflows.app._catalog.workflows) == {"investigate", "place_order"}


def test_factory_never_reuses_mutable_agent_state():
    assert workflows.build_research_agent() is not workflows.build_research_agent()


def test_optional_bedrock_factory_has_no_import_time_network_call(monkeypatch):
    created = {}

    class Model:
        def __init__(self, *, model_id, region_name):
            created["model_id"] = model_id
            created["region_name"] = region_name

    class Agent:
        def __init__(self, **kwargs):
            created["agent"] = kwargs

    monkeypatch.setattr(bedrock, "BedrockModel", Model)
    monkeypatch.setattr(bedrock, "Agent", Agent)
    monkeypatch.setenv("BEDROCK_MODEL_ID", "test-model")
    monkeypatch.setenv("BEDROCK_REGION", "eu-west-1")

    bedrock.build_bedrock_agent()

    assert created["model_id"] == "test-model"
    # Region is passed explicitly. A session default with no Anthropic access
    # is a permanent failure, and this example hit exactly that.
    assert created["region_name"] == "eu-west-1"
    assert created["agent"]["name"] == "bedrock-research"

    bedrock.build_bedrock_agent(model_id="pinned-model", region="ap-south-1")
    assert created["model_id"] == "pinned-model"
    assert created["region_name"] == "ap-south-1"


def test_bedrock_settings_prefer_explicit_region_then_aws_region_then_default(monkeypatch):
    for name in ("BEDROCK_MODEL_ID", "BEDROCK_REGION", "AWS_REGION", "AWS_DEFAULT_REGION"):
        monkeypatch.delenv(name, raising=False)
    assert bedrock.bedrock_settings() == (bedrock.DEFAULT_MODEL_ID, bedrock.DEFAULT_REGION)

    # AWS_DEFAULT_REGION is what most shells and CI images actually set; ignoring
    # it would send a correctly configured user to the wrong region.
    monkeypatch.setenv("AWS_DEFAULT_REGION", "eu-central-1")
    assert bedrock.bedrock_settings()[1] == "eu-central-1"

    monkeypatch.setenv("AWS_REGION", "us-west-2")
    assert bedrock.bedrock_settings()[1] == "us-west-2"

    monkeypatch.setenv("BEDROCK_REGION", "us-east-1")
    assert bedrock.bedrock_settings()[1] == "us-east-1"

    # The default is a single-geo `us.` profile, not a `global.` one: the Anthropic
    # use-case gate propagates per region, and global routing lands on whichever.
    assert bedrock.DEFAULT_MODEL_ID.startswith("us.")


def test_bedrock_pricer_uses_explicit_rates_and_rounds_cost_up(monkeypatch):
    monkeypatch.setenv(bedrock.INPUT_PRICE_ENV, "0.80")
    monkeypatch.setenv(bedrock.OUTPUT_PRICE_ENV, "4.00")

    price = bedrock.bedrock_pricer_from_env()

    assert price("model-is-pinned-by-the-adapter", 10, 5) == 28
    monkeypatch.setenv(bedrock.INPUT_PRICE_ENV, "0.0001")
    monkeypatch.setenv(bedrock.OUTPUT_PRICE_ENV, "0")
    assert bedrock.bedrock_pricer_from_env()("model", 1, 0) == 1


def test_bedrock_pricer_refuses_missing_or_invalid_rates(monkeypatch):
    monkeypatch.delenv(bedrock.INPUT_PRICE_ENV, raising=False)
    monkeypatch.setenv(bedrock.OUTPUT_PRICE_ENV, "4")
    with pytest.raises(RuntimeError, match=bedrock.INPUT_PRICE_ENV):
        bedrock.bedrock_pricer_from_env()

    monkeypatch.setenv(bedrock.INPUT_PRICE_ENV, "not-a-price")
    with pytest.raises(RuntimeError, match="non-negative decimal"):
        bedrock.bedrock_pricer_from_env()


def test_checkout_tool_reaches_app_effect_through_the_real_strands_loop():
    # The model asks for charge_card; Strands runs it on a to_thread worker; the
    # tool calls app.effect and must find the executing Step from that thread.
    # A fake client records the receipt the SDK proposes.
    import threading
    from unittest.mock import Mock

    from aga_runtime.protocol.wire import Effect, EffectClass, EffectState
    from aga_runtime.workflow._runtime import step_binding

    class Effects:
        def __init__(self):
            self.proposed, self.settled = [], []

        def propose(self, effect_id, operation_id, **kw):
            self.proposed.append({"id": effect_id, "operation_id": operation_id, **kw})
            return Effect(id=effect_id, state=EffectState.AUTHORIZED, generation=1), False

        def settle(self, effect_id, state, **kw):
            self.settled.append(state)
            return Effect(id=effect_id, state=state)

    client = Mock()
    client.effects = Effects()
    agent = workflows.build_checkout_agent()
    main_thread = threading.get_ident()
    with step_binding.bound(client, "run-1.strands.checkout.1", 3):
        result = asyncio.run(
            agent.invoke_async("Please charge order order-42 for 1200 cents.")
        )

    assert str(result).strip() == (
        "Checkout complete: charged 1200 minor units for order order-42."
    )
    assert len(client.effects.proposed) == 1
    receipt = client.effects.proposed[0]
    assert receipt["operation_id"] == "run-1.strands.checkout.1"
    assert receipt["effect_class"] is EffectClass.MUTATE
    assert receipt["idempotency_digest"]
    assert client.effects.settled[-1] is EffectState.COMMITTED
    assert threading.get_ident() == main_thread  # the test itself stayed put
    assert result.metrics.accumulated_usage["totalTokens"] == 46


def test_checkout_agent_is_bound_with_a_pricer_the_ceiling_can_use():
    assert workflows.checkout._step._spec.operation_class == "agent"
    assert workflows.local_price_micros("deterministic-checkout-v1", 12, 6) == 42
    assert set(workflows.app._catalog.workflows) == {"investigate", "place_order"}


def test_checkout_model_never_describes_a_failed_tool_as_complete():
    from unittest.mock import Mock

    from aga_runtime import errors
    from aga_runtime.workflow._runtime import step_binding

    client = Mock()
    client.effects.propose.side_effect = errors.CasConflict("stale fence")
    agent = workflows.build_checkout_agent()
    with step_binding.bound(client, "run-1.strands.checkout.1", 3):
        with pytest.raises(EventLoopException, match="checkout tool failed"):
            asyncio.run(agent.invoke_async("Please charge order order-42 for 1200 cents."))


def test_bedrock_workflow_registers_only_with_explicit_model_and_region():
    source = str(Path(__file__).resolve().parents[1] / "src")
    env = {**os.environ, "PYTHONPATH": source}
    env.pop("AGA_AGENT_BEDROCK", None)
    local = subprocess.run(
        [sys.executable, "-c", "from agent_quickstart import worker; "
         "print(sorted(worker.app._catalog.workflows))"],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "investigate_bedrock" not in local.stdout

    env["AGA_AGENT_BEDROCK"] = "1"
    env.pop("BEDROCK_MODEL_ID", None)
    env.pop("BEDROCK_REGION", None)
    missing = subprocess.run(
        [sys.executable, "-c", "import agent_quickstart.worker"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert missing.returncode != 0
    assert "Bedrock worker needs explicit configuration" in missing.stderr
    assert "BEDROCK_MODEL_ID" in missing.stderr
    assert bedrock.INPUT_PRICE_ENV in missing.stderr

    env["BEDROCK_MODEL_ID"] = "global.anthropic.claude-haiku-4-5-20251001-v1:0"
    env["BEDROCK_REGION"] = "ap-south-1"
    env[bedrock.INPUT_PRICE_ENV] = "1"
    env[bedrock.OUTPUT_PRICE_ENV] = "5"
    ready = subprocess.run(
        [sys.executable, "-c", "from agent_quickstart import worker; "
         "print(sorted(worker.app._catalog.workflows)); "
         "print(worker.bedrock_workflows.research_bedrock.manifest.model)"],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "investigate_bedrock" in ready.stdout
    assert env["BEDROCK_MODEL_ID"] in ready.stdout

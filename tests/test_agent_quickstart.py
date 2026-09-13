import asyncio

from aga_strands import StrandsAdapter

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
    assert set(workflows.app._catalog.workflows) == {"investigate"}


def test_factory_never_reuses_mutable_agent_state():
    assert workflows.build_research_agent() is not workflows.build_research_agent()


def test_optional_bedrock_factory_has_no_import_time_network_call(monkeypatch):
    created = {}

    class Model:
        def __init__(self, *, model_id):
            created["model_id"] = model_id

    class Agent:
        def __init__(self, **kwargs):
            created["agent"] = kwargs

    monkeypatch.setattr(bedrock, "BedrockModel", Model)
    monkeypatch.setattr(bedrock, "Agent", Agent)
    monkeypatch.setenv("BEDROCK_MODEL_ID", "test-model")

    bedrock.build_bedrock_agent()

    assert created["model_id"] == "test-model"
    assert created["agent"]["name"] == "bedrock-research"

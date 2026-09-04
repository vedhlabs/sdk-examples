from __future__ import annotations

import asyncio

import pytest

from agentic.adapter import SupportAdapterConfig, SupportAgentAdapter
from agentic.agent import ScriptedSupportAgent
from agentic.types import Resolution, Ticket


def test_scripted_agent_keeps_the_example_offline_and_typed():
    result = asyncio.run(
        ScriptedSupportAgent().run(
            Ticket("T-1", "customer-42", "Please share my order status")
        )
    )

    assert result == Resolution(
        ticket_id="T-1",
        category="order-status",
        summary="order shipped; tracking number ZX-42",
        proposed_action="reply-with-order-status",
        requires_approval=False,
    )


def test_adapter_configuration_is_immutable_and_identity_is_explicit():
    config = SupportAdapterConfig(identity="test.support/1", operation="test.run")
    adapter = SupportAgentAdapter(ScriptedSupportAgent(), config)

    assert adapter.name == "test.support/1"
    assert adapter.config.operation == "test.run"
    with pytest.raises(AttributeError):
        config.timeout = 5

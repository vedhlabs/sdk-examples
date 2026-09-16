"""A deterministic Strands model that asks for a tool — no cloud account needed.

Turn one requests ``charge_card``; turn two confirms with the tool's result. It
speaks the same event shape Bedrock streams, so Strands' real agent loop, tool
executor, and worker-thread hop all run exactly as they would in production.
"""

from __future__ import annotations

import json
import re
from collections.abc import AsyncGenerator
from typing import Any

from strands.models import Model

_ORDER = re.compile(r"order ([A-Za-z0-9][A-Za-z0-9._:-]*)")
_AMOUNT = re.compile(r"for (\d+) cents")


class LocalCheckoutModel(Model):
    """Deterministic two-turn model: one tool call, then a one-line answer."""

    def __init__(self) -> None:
        self.turns = 0

    def get_config(self) -> dict[str, Any]:
        return {"model_id": "deterministic-checkout-v1"}

    def update_config(self, **model_config: Any) -> None:
        if model_config:
            raise ValueError("LocalCheckoutModel has no configurable values")

    async def structured_output(self, *_args: Any, **_kwargs: Any) -> Any:
        raise NotImplementedError("the local example returns text")

    async def stream(
        self,
        messages: list[dict[str, Any]],
        *_args: Any,
        **_kwargs: Any,
    ) -> AsyncGenerator[dict[str, Any], None]:
        self.turns += 1
        yield {"messageStart": {"role": "assistant"}}
        if self.turns == 1:
            order_id, amount = _requested_order(messages)
            start = {"toolUse": {"toolUseId": "charge-1", "name": "charge_card"}}
            yield {"contentBlockStart": {"start": start}}
            arguments = json.dumps({"order_id": order_id, "amount": amount})
            yield {"contentBlockDelta": {"delta": {"toolUse": {"input": arguments}}}}
            yield {"contentBlockStop": {}}
            yield {"messageStop": {"stopReason": "tool_use"}}
            yield _usage(12, 6)
            return
        outcome = _latest_tool_result(messages)
        yield {"contentBlockStart": {"start": {}}}
        yield {"contentBlockDelta": {"delta": {"text": f"Checkout complete: {outcome}."}}}
        yield {"contentBlockStop": {}}
        yield {"messageStop": {"stopReason": "end_turn"}}
        yield _usage(20, 8)


def _usage(input_tokens: int, output_tokens: int) -> dict[str, Any]:
    return {
        "metadata": {
            "usage": {
                "inputTokens": input_tokens,
                "outputTokens": output_tokens,
                "totalTokens": input_tokens + output_tokens,
            },
            "metrics": {"latencyMs": 0},
        }
    }


def _requested_order(messages: list[dict[str, Any]]) -> tuple[str, int]:
    for message in reversed(messages):
        for block in reversed(message.get("content", [])):
            text = block.get("text") if isinstance(block, dict) else None
            if not isinstance(text, str):
                continue
            order, amount = _ORDER.search(text), _AMOUNT.search(text)
            if order and amount:
                return order.group(1), int(amount.group(1))
    return "example-order", 1200


def _latest_tool_result(messages: list[dict[str, Any]]) -> str:
    for message in reversed(messages):
        for block in reversed(message.get("content", [])):
            result = block.get("toolResult") if isinstance(block, dict) else None
            if isinstance(result, dict):
                for part in result.get("content", []):
                    if isinstance(part, dict) and isinstance(part.get("text"), str):
                        return part["text"]
    return "no tool result"

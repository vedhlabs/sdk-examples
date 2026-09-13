"""A deterministic Strands model for learning and tests—no cloud account needed."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

from strands.models import Model


class LocalResearchModel(Model):
    """Return one predictable answer through Strands' real Agent event loop."""

    def get_config(self) -> dict[str, Any]:
        return {"model_id": "deterministic-local-v1"}

    def update_config(self, **model_config: Any) -> None:
        if model_config:
            raise ValueError("LocalResearchModel has no configurable values")

    async def structured_output(self, *_args: Any, **_kwargs: Any) -> Any:
        raise NotImplementedError("the local example returns text")

    async def stream(
        self,
        messages: list[dict[str, Any]],
        *_args: Any,
        **_kwargs: Any,
    ) -> AsyncGenerator[dict[str, Any], None]:
        question = _latest_text(messages)
        answer = f"Local research complete: {question}"
        yield {"messageStart": {"role": "assistant"}}
        yield {"contentBlockStart": {"start": {}}}
        yield {"contentBlockDelta": {"delta": {"text": answer}}}
        yield {"contentBlockStop": {}}
        yield {"messageStop": {"stopReason": "end_turn"}}
        yield {
            "metadata": {
                "usage": {"inputTokens": 4, "outputTokens": 5, "totalTokens": 9},
                "metrics": {"latencyMs": 0},
            }
        }


def _latest_text(messages: list[dict[str, Any]]) -> str:
    for message in reversed(messages):
        for block in reversed(message.get("content", [])):
            if isinstance(block, dict) and isinstance(block.get("text"), str):
                return block["text"]
    return "no question supplied"

"""A long logical agent session split into small, durable Run generations."""

from __future__ import annotations

import time
from typing import Any

import aga_runtime as aga

from agent_pattern.app import app

RECENT_SUMMARY_LIMIT = 8


@app.step(operation_class=aga.OperationClass.MODEL)
def plan_turn(topic: str, turn: int) -> dict[str, Any]:
    """A deterministic stand-in for one complete model decision."""
    return {
        "turn": turn,
        "questions": [f"{topic}:documentation:{turn}", f"{topic}:incidents:{turn}"],
    }


@app.step(operation_class=aga.OperationClass.TOOL)
def search_documentation(query: str) -> dict[str, str]:
    time.sleep(0.05)
    return {"source": "documentation", "finding": f"documented answer for {query}"}


@app.step(operation_class=aga.OperationClass.TOOL)
def search_incidents(query: str) -> dict[str, str]:
    time.sleep(0.08)
    return {"source": "incidents", "finding": f"incident evidence for {query}"}


@app.step(operation_class=aga.OperationClass.MODEL)
def summarize_turn(turn: int, findings: list[dict[str, str]]) -> dict[str, Any]:
    return {"turn": turn, "sources": [finding["source"] for finding in findings]}


@app.workflow(
    name="agent_pattern.research_session",
    version="1",
    execution="async_distributed",
)
async def research_session(state: dict[str, Any]) -> dict[str, Any]:
    """Own the loop and continue before one physical Run grows without bound."""
    topic = _required_text(state, "topic")
    turn = _bounded_int(state, "turn", minimum=0, maximum=10_000)
    max_turns = _bounded_int(state, "max_turns", minimum=1, maximum=10_000)
    turns_per_generation = _bounded_int(
        state, "turns_per_generation", minimum=1, maximum=32
    )
    segment = _bounded_int(state, "segment", minimum=1, maximum=10_000)
    carried_summaries = state.get("recent_summaries", [])
    if not isinstance(carried_summaries, list):
        raise ValueError("recent_summaries must be a list")
    recent_summaries = list(carried_summaries[-RECENT_SUMMARY_LIMIT:])
    completed_here = 0

    while turn < max_turns:
        decision = await plan_turn(topic, turn + 1)
        documentation, incidents = await app.join(
            search_documentation(decision["questions"][0]),
            search_incidents(decision["questions"][1]),
        )
        recent_summaries.append(
            await summarize_turn(turn + 1, [documentation, incidents])
        )
        recent_summaries = recent_summaries[-RECENT_SUMMARY_LIMIT:]
        turn += 1
        completed_here += 1

        if turn < max_turns and completed_here >= turns_per_generation:
            app.continue_as_new(
                research_session,
                {
                    "topic": topic,
                    "turn": turn,
                    "max_turns": max_turns,
                    "turns_per_generation": turns_per_generation,
                    "segment": segment + 1,
                    "recent_summaries": recent_summaries,
                },
            )

    return {
        "topic": topic,
        "turns": turn,
        "segments": segment,
        "recent_summaries": recent_summaries,
    }


def _required_text(state: dict[str, Any], name: str) -> str:
    value = state.get(name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a nonempty string")
    return value


def _bounded_int(
    state: dict[str, Any], name: str, *, minimum: int, maximum: int
) -> int:
    value = state.get(name)
    if not isinstance(value, int) or isinstance(value, bool) or not minimum <= value <= maximum:
        raise ValueError(f"{name} must be an integer between {minimum} and {maximum}")
    return value

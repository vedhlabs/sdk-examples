"""A long-lived agent session driven by its ordered command mailbox."""

from __future__ import annotations

import time
from typing import Any

import aga_runtime as aga

from agent_pattern.app import app

RECENT_RESULT_LIMIT = 8


@app.step(operation_class=aga.OperationClass.AGENT)
def handle_command(command_id: str, kind: str, payload: Any) -> dict[str, Any]:
    """Stand in for one agent turn without hiding command identity."""
    if kind != "message":
        return {"command_id": command_id, "kind": kind, "status": "ignored"}
    if not isinstance(payload, dict) or not isinstance(payload.get("text"), str):
        raise ValueError("a message command requires a string payload.text")
    text = payload["text"].strip()
    if not text:
        raise ValueError("a message command requires nonempty payload.text")
    work_ms = payload.get("work_ms", 0)
    if isinstance(work_ms, bool) or not isinstance(work_ms, int) or not 0 <= work_ms <= 1_000:
        raise ValueError("message payload.work_ms must be an integer between 0 and 1000")
    if work_ms:
        time.sleep(work_ms / 1000)
    return {
        "command_id": command_id,
        "kind": kind,
        "status": "answered",
        "answer": f"Handled: {text}",
    }


@app.workflow(
    name="agent_pattern.command_session",
    version="1",
    execution="async_distributed",
)
async def command_session(state: dict[str, Any]) -> dict[str, Any]:
    """Receive ordered commands and continue before one Run grows too large."""
    handled = _bounded_int(state, "handled", minimum=0, maximum=100_000)
    generation = _bounded_int(state, "generation", minimum=1, maximum=100_000)
    commands_per_generation = _bounded_int(state, "commands_per_generation", minimum=1, maximum=32)
    command_timeout = _bounded_number(state, "command_timeout", minimum=0.1, maximum=86_400.0)
    carried = state.get("recent_results", [])
    if not isinstance(carried, list):
        raise ValueError("recent_results must be a list")
    recent_results = list(carried[-RECENT_RESULT_LIMIT:])
    handled_here = 0

    while True:
        command = await app.command(timeout=command_timeout)
        if command.kind == "stop":
            app.event(
                "agent.session.stopped",
                {"command_id": command.command_id, "revision": command.revision},
            )
            return {
                "handled": handled,
                "generations": generation,
                "recent_results": recent_results,
                "stop_revision": command.revision,
            }

        result = await handle_command(command.command_id, command.kind, command.payload)
        handled += 1
        handled_here += 1
        recent_results.append({"revision": command.revision, **result})
        recent_results = recent_results[-RECENT_RESULT_LIMIT:]
        app.event(
            "agent.command.completed",
            {
                "command_id": command.command_id,
                "kind": command.kind,
                "revision": command.revision,
            },
        )

        if handled_here >= commands_per_generation:
            app.continue_as_new(
                command_session,
                {
                    "handled": handled,
                    "generation": generation + 1,
                    "commands_per_generation": commands_per_generation,
                    "command_timeout": command_timeout,
                    "recent_results": recent_results,
                },
            )


def _bounded_int(state: dict[str, Any], name: str, *, minimum: int, maximum: int) -> int:
    value = state.get(name)
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise ValueError(f"{name} must be an integer between {minimum} and {maximum}")
    return value


def _bounded_number(state: dict[str, Any], name: str, *, minimum: float, maximum: float) -> float:
    value = state.get(name)
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"{name} must be a number between {minimum} and {maximum}")
    number = float(value)
    if not minimum <= number <= maximum:
        raise ValueError(f"{name} must be a number between {minimum} and {maximum}")
    return number

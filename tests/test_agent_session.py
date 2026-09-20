import asyncio

import pytest

from agent_pattern import session_workflow


def test_session_runs_parallel_tools_and_continues_with_committed_state(monkeypatch):
    calls = []

    async def plan(_topic, turn):
        return {"turn": turn, "questions": [f"docs-{turn}", f"incidents-{turn}"]}

    def docs(query):
        calls.append(("docs", query))
        return f"docs-handle-{query}"

    def incidents(query):
        calls.append(("incidents", query))
        return f"incidents-handle-{query}"

    async def join(*handles):
        calls.append(("join", handles))
        return [{"source": "documentation"}, {"source": "incidents"}]

    async def summarize(turn, _findings):
        return {"turn": turn, "sources": ["documentation", "incidents"]}

    class Continued(Exception):
        pass

    captured = {}

    def continue_as_new(workflow, state):
        captured.update({"workflow": workflow, "state": state})
        raise Continued

    monkeypatch.setattr(session_workflow, "plan_turn", plan)
    monkeypatch.setattr(session_workflow, "search_documentation", docs)
    monkeypatch.setattr(session_workflow, "search_incidents", incidents)
    monkeypatch.setattr(session_workflow, "summarize_turn", summarize)
    monkeypatch.setattr(session_workflow.app, "join", join)
    monkeypatch.setattr(session_workflow.app, "continue_as_new", continue_as_new)

    with pytest.raises(Continued):
        asyncio.run(session_workflow.research_session.__wrapped__({
            "topic": "durability",
            "turn": 0,
            "max_turns": 3,
            "turns_per_generation": 2,
            "segment": 1,
            "recent_summaries": [],
        }))

    assert captured["workflow"] is session_workflow.research_session
    assert captured["state"]["turn"] == 2
    assert captured["state"]["segment"] == 2
    assert len(captured["state"]["recent_summaries"]) == 2
    assert calls[0:3] == [
        ("docs", "docs-1"),
        ("incidents", "incidents-1"),
        ("join", ("docs-handle-docs-1", "incidents-handle-incidents-1")),
    ]


def test_session_state_is_bounded_and_explicit():
    with pytest.raises(ValueError, match="turns_per_generation"):
        asyncio.run(session_workflow.research_session.__wrapped__({
            "topic": "durability",
            "turn": 0,
            "max_turns": 3,
            "turns_per_generation": 0,
            "segment": 1,
            "recent_summaries": [],
        }))


def test_session_carries_only_the_eight_most_recent_summaries(monkeypatch):
    async def plan(_topic, turn):
        return {"turn": turn, "questions": ["docs", "incidents"]}

    async def join(*_handles):
        return [{"source": "documentation"}, {"source": "incidents"}]

    async def summarize(turn, _findings):
        return {"turn": turn, "sources": ["documentation", "incidents"]}

    monkeypatch.setattr(session_workflow, "plan_turn", plan)
    monkeypatch.setattr(session_workflow, "search_documentation", lambda _query: "docs")
    monkeypatch.setattr(session_workflow, "search_incidents", lambda _query: "incidents")
    monkeypatch.setattr(session_workflow, "summarize_turn", summarize)
    monkeypatch.setattr(session_workflow.app, "join", join)

    result = asyncio.run(session_workflow.research_session.__wrapped__({
        "topic": "durability",
        "turn": 0,
        "max_turns": 1,
        "turns_per_generation": 2,
        "segment": 1,
        "recent_summaries": [{"turn": turn} for turn in range(-9, 1)],
    }))

    assert len(result["recent_summaries"]) == session_workflow.RECENT_SUMMARY_LIMIT
    assert result["recent_summaries"][-1]["turn"] == 1

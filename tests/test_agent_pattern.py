import asyncio

import pytest

from agent_pattern import workflows


def test_model_proposal_must_match_the_declared_tool_allowlist():
    assert workflows.selected_tools(["watchlist_check", "identity_check"]) == (
        workflows.watchlist_check,
        workflows.identity_check,
    )
    for names in (
        [],
        ["identity_check"],
        ["identity_check", "identity_check"],
        ["identity_check", "delete_account"],
        ["identity_check", "watchlist_check", "delete_account"],
    ):
        with pytest.raises(ValueError, match="invalid tool set"):
            workflows.selected_tools(names)


def test_policy_block_never_requests_approval_or_effect(monkeypatch):
    calls = []

    async def propose(_case_id):
        return ["identity_check", "watchlist_check"]

    async def join(*_checks):
        return [{"passed": True}, {"passed": False}]

    async def policy(_checks):
        return {"allowed": False}

    def forbidden(*_args, **_kwargs):
        calls.append("unsafe boundary reached")
        raise AssertionError("blocked case must not reach approval or effect")

    monkeypatch.setattr(workflows, "propose_checks", propose)
    monkeypatch.setattr(workflows, "identity_check", lambda _case: object())
    monkeypatch.setattr(workflows, "watchlist_check", lambda _case: object())
    monkeypatch.setattr(workflows.app, "join", join)
    monkeypatch.setattr(workflows, "policy_check", policy)
    monkeypatch.setattr(workflows.app, "signal", forbidden)
    monkeypatch.setattr(workflows, "publish_decision", forbidden)

    result = asyncio.run(workflows.review_case.__wrapped__({"case_id": "case-1"}))

    assert result == {"case_id": "case-1", "status": "blocked"}
    assert calls == []


def test_parallel_tools_are_admitted_before_join(monkeypatch):
    calls = []

    async def propose(_case_id):
        return ["identity_check", "watchlist_check"]

    def identity(case):
        calls.append(("identity", case["case_id"]))
        return "identity-handle"

    def watchlist(case):
        calls.append(("watchlist", case["case_id"]))
        return "watchlist-handle"

    async def join(*handles):
        assert handles == ("identity-handle", "watchlist-handle")
        assert calls == [("identity", "case-2"), ("watchlist", "case-2")]
        return [{"passed": True}, {"passed": False}]

    async def policy(_checks):
        return {"allowed": False}

    monkeypatch.setattr(workflows, "propose_checks", propose)
    monkeypatch.setattr(workflows, "identity_check", identity)
    monkeypatch.setattr(workflows, "watchlist_check", watchlist)
    monkeypatch.setattr(workflows.app, "join", join)
    monkeypatch.setattr(workflows, "policy_check", policy)

    assert asyncio.run(workflows.review_case.__wrapped__({"case_id": "case-2"}))[
        "status"
    ] == "blocked"

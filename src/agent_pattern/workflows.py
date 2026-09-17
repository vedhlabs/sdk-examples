"""A bounded agent-like loop owned by Aga rather than a framework middleware.

The model proposal is deterministic here so the example runs without cloud
credentials. Replace that Step's body with a model call, not the ordering and
approval boundaries around it. The provider is a local SQLite-backed stand-in.
"""

from __future__ import annotations

import time

import aga_runtime as aga
from aga_runtime import errors

from agent_pattern import provider
from agent_pattern.app import app

ALLOWED_TOOLS = frozenset({"identity_check", "watchlist_check"})


@app.step(target=app.target, operation_class=aga.OperationClass.MODEL)
def propose_checks(case_id: str) -> list[str]:
    """Stand-in for one committed model decision, not an opaque Agent loop."""
    if not case_id:
        raise ValueError("case_id is required")
    return ["identity_check", "watchlist_check"]


@app.step(operation_class=aga.OperationClass.TOOL)
def identity_check(case: dict) -> dict:
    time.sleep(0.15)  # Make overlap visible in a local timeline.
    return {"name": "identity_check", "passed": not case.get("identity_mismatch", False)}


@app.step(operation_class=aga.OperationClass.TOOL)
def watchlist_check(case: dict) -> dict:
    time.sleep(0.2)
    return {"name": "watchlist_check", "passed": not case.get("watchlist_hit", False)}


@app.step()
def policy_check(results: list[dict]) -> dict:
    return {"allowed": all(result["passed"] for result in results)}


@app.step(operation_class=aga.OperationClass.TOOL, retry=aga.RetryPolicy(max_attempts=1))
def publish_decision(case_id: str, approval_gate_id: str) -> dict:
    """Only this Step may mutate the provider, under an Aga effect receipt."""
    key = f"case:{case_id}:decision:clear:v1"
    try:
        return app.effect(
            "publish-case-decision",
            lambda: provider.publish(case_id, "clear", key),
            idempotency_key=key,
            provider="example-case-provider",
            endpoint="POST /case-decisions",
            request={"case_id": case_id, "decision": "clear"},
            approval_gate=approval_gate_id,
        )
    except errors.EffectAlreadyApplied:
        receipt = provider.find(key)
        if receipt is None:
            raise  # Never guess that an ambiguous provider call did not apply.
        return receipt


def selected_tools(names: list[str]) -> tuple:
    """A model proposes; this allowlist decides what may actually run."""
    if len(names) != 2 or set(names) != ALLOWED_TOOLS or len(set(names)) != len(names):
        raise ValueError("model proposed an invalid tool set")
    tools = {"identity_check": identity_check, "watchlist_check": watchlist_check}
    return tuple(tools[name] for name in names)


@app.workflow(name="agent_pattern.review_case", version="1", execution="async_distributed")
async def review_case(case: dict) -> dict:
    case_id = case.get("case_id")
    if not isinstance(case_id, str) or not case_id:
        raise ValueError("case_id must be a nonempty string")

    chosen = selected_tools(await propose_checks(case_id))
    checks = await app.join(*(step(case) for step in chosen))
    policy = await policy_check(checks)
    if not policy["allowed"]:
        return {"case_id": case_id, "status": "blocked"}

    proposal = aga.Approval(
        "case_publish_approval",
        action="POST /case-decisions",
        provider="example-case-provider",
        arguments={"case_id": case_id, "decision": "clear"},
        mutating=True,
        risk="medium",
        reason="release the verified case decision",
        requester="agent-pattern",
        evidence={"identity_passed": True, "watchlist_passed": True},
        eligible_claims=("team:risk",),
    )
    try:
        gate = app.signal(proposal, timeout=float(case.get("approval_timeout", 120)))
        answer = await gate
    except aga.PermissionDenied:
        return {"case_id": case_id, "status": "not_approved"}
    if not answer.get("approved"):
        return {"case_id": case_id, "status": "not_approved"}

    receipt = await publish_decision(case_id, gate.id)
    return {"case_id": case_id, "status": "published", "receipt": receipt}

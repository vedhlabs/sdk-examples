"""Local durable stand-in for a separately owned case-decision provider."""

from example_support.store import stable_id, store

SCOPE = "agent-pattern.case-decision"


def publish(case_id: str, decision: str, idempotency_key: str) -> dict:
    return store.once(
        SCOPE,
        idempotency_key,
        lambda: {
            "receipt_id": stable_id("case", idempotency_key),
            "case_id": case_id,
            "decision": decision,
        },
    )


def find(idempotency_key: str) -> dict | None:
    receipt = store.effect(SCOPE, idempotency_key)
    return receipt if isinstance(receipt, dict) else None

from example_support.store import stable_id, store

CHARGE_SCOPE = "checkout.payments.charge"


def charge(customer_id: str, amount: int, idempotency_key: str) -> dict:
    return store.once(
        CHARGE_SCOPE,
        idempotency_key,
        lambda: {"id": stable_id("charge", idempotency_key), "amount": amount},
    )


def find_charge(idempotency_key: str) -> dict | None:
    """Reconcile an uncertain response without issuing a second charge."""
    receipt = store.effect(CHARGE_SCOPE, idempotency_key)
    return receipt if isinstance(receipt, dict) else None


def reimburse(charge_id: str, idempotency_key: str) -> dict:
    return store.once(
        "checkout.payments.reimburse",
        idempotency_key,
        lambda: {"refund_id": stable_id("refund", idempotency_key), "charge_id": charge_id},
    )

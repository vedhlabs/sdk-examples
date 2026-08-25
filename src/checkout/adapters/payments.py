from example_support.store import stable_id, store


def charge(customer_id: str, amount: int, idempotency_key: str) -> dict:
    return store.once(
        "checkout.payments.charge",
        idempotency_key,
        lambda: {"id": stable_id("charge", idempotency_key), "amount": amount},
    )


def reimburse(charge_id: str, idempotency_key: str) -> dict:
    return store.once(
        "checkout.payments.reimburse",
        idempotency_key,
        lambda: {"refund_id": stable_id("refund", idempotency_key), "charge_id": charge_id},
    )


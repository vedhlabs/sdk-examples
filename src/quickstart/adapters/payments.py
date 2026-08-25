from example_support.store import stable_id, store


def charge(customer_id: str, amount: int, idempotency_key: str) -> dict:
    return store.once(
        "quickstart.payments.charge",
        idempotency_key,
        lambda: {
            "charge_id": stable_id("ch", idempotency_key),
            "customer_id": customer_id,
            "amount": amount,
            "status": "captured",
        },
    )


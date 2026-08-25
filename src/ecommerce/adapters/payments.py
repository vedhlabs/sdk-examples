from example_support.store import stable_id, store


def charge(customer: str, amount: int, idempotency_key: str) -> dict:
    return store.once(
        "ecommerce.payments.charge",
        idempotency_key,
        lambda: {
            "charge_id": stable_id("ch", idempotency_key),
            "customer": customer,
            "amount": amount,
            "status": "captured",
        },
    )


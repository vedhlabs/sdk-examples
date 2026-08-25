from example_support.store import stable_id, store


def create(order: dict, idempotency_key: str) -> dict:
    return store.once(
        "checkout.shipping.create",
        idempotency_key,
        lambda: {
            "id": stable_id("shipment", idempotency_key),
            "tracking": stable_id("track", idempotency_key).upper(),
            "order_id": order["id"],
        },
    )


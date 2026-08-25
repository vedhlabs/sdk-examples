from example_support.store import stable_id, store


def create(order: dict, carrier: str, idempotency_key: str) -> dict:
    return store.once(
        "ecommerce.shipping.create",
        idempotency_key,
        lambda: {
            "shipment_id": stable_id("ship", idempotency_key),
            "tracking": stable_id(carrier, idempotency_key).upper(),
            "carrier": carrier,
            "order_id": order["id"],
        },
    )


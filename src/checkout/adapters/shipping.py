from example_support.store import stable_id, store

SHIPMENT_SCOPE = "checkout.shipping.create"


def create(order: dict, idempotency_key: str) -> dict:
    return store.once(
        SHIPMENT_SCOPE,
        idempotency_key,
        lambda: {
            "id": stable_id("shipment", idempotency_key),
            "tracking": stable_id("track", idempotency_key).upper(),
            "order_id": order["id"],
        },
    )


def find_shipment(idempotency_key: str) -> dict | None:
    """Reconcile an uncertain response without creating another shipment."""
    receipt = store.effect(SHIPMENT_SCOPE, idempotency_key)
    return receipt if isinstance(receipt, dict) else None

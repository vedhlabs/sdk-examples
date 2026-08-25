from example_support.store import stable_id, store


def reserve(order: dict, idempotency_key: str) -> dict:
    return store.once(
        "ecommerce.inventory.reserve",
        idempotency_key,
        lambda: {"ref": stable_id("stock", idempotency_key), "order_id": order["id"]},
    )


def release(reference: str) -> dict:
    key = f"release:{reference}"
    return store.once(
        "ecommerce.inventory.release",
        key,
        lambda: {"ref": reference, "released": True},
    )


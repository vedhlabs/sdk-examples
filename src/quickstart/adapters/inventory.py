from example_support.store import stable_id, store


def reserve(order: dict, idempotency_key: str) -> dict:
    return store.once(
        "quickstart.inventory.reserve",
        idempotency_key,
        lambda: {"reservation_id": stable_id("res", idempotency_key), "items": order["items"]},
    )


def release(reservation_id: str) -> dict:
    key = f"release:{reservation_id}"
    return store.once(
        "quickstart.inventory.release",
        key,
        lambda: {"reservation_id": reservation_id, "released": True},
    )


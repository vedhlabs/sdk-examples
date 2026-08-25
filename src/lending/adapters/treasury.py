from example_support.store import stable_id, store


def reserve(applicant_id: str, amount: int, idempotency_key: str) -> dict:
    return store.once(
        "lending.treasury.reserve",
        idempotency_key,
        lambda: {
            "reservation": stable_id("loan_res", idempotency_key),
            "applicant_id": applicant_id,
            "amount": amount,
        },
    )


def release(reservation: str) -> dict:
    key = f"release:{reservation}"
    return store.once(
        "lending.treasury.release",
        key,
        lambda: {"reservation": reservation, "released": True},
    )


def disburse(applicant_id: str, amount: int, idempotency_key: str) -> dict:
    return store.once(
        "lending.treasury.disburse",
        idempotency_key,
        lambda: {
            "txn_id": stable_id("txn", idempotency_key),
            "applicant_id": applicant_id,
            "amount": amount,
            "status": "posted",
        },
    )


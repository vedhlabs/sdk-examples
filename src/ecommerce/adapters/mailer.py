from example_support.store import stable_id, store


def send(to: str, subject: str, idempotency_key: str) -> dict:
    return store.once(
        "ecommerce.mailer.send",
        idempotency_key,
        lambda: {"message_id": stable_id("mail", idempotency_key), "to": to, "subject": subject},
    )


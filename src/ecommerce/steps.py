import ogha

from ecommerce.adapters import carriers, inventory, mailer, payments, shipping


@ogha.step(retry=ogha.RetryPolicy(max_attempts=3), timeout=15)
def validate_cart(order: dict) -> dict:
    if not order.get("items"):
        raise ValueError("empty cart")
    total = sum(int(item["price"]) * int(item["qty"]) for item in order["items"])
    return {"total": total}


@ogha.step(retry=ogha.RetryPolicy(max_attempts=3), timeout=15)
def price_shipping(order: dict, carrier: str) -> dict:
    return {"carrier": carrier, "price": carriers.quote(order=order, carrier=carrier)}


@ogha.step(
    retry=ogha.RetryPolicy(max_attempts=4),
    timeout=20,
    compensate_with="release_stock",
)
def reserve_stock(order: dict) -> dict:
    return inventory.reserve(order, idempotency_key=f"order:{order['id']}:stock")


@ogha.step
def release_stock(reservation: dict) -> dict:
    return inventory.release(reservation["ref"])


@ogha.step(retry=ogha.RetryPolicy(max_attempts=5), pivot=True, timeout=30)
def charge_card(order: dict, amount: int) -> dict:
    return payments.charge(
        customer=order["customer_id"],
        amount=amount,
        idempotency_key=f"order:{order['id']}:charge",
    )


@ogha.step(retry=ogha.RetryPolicy(max_attempts=5), timeout=30)
def create_shipment(order: dict, carrier: str) -> dict:
    return shipping.create(
        order=order,
        carrier=carrier,
        idempotency_key=f"order:{order['id']}:shipment",
    )


@ogha.step(retry=ogha.RetryPolicy(max_attempts=5), timeout=20)
def send_email(order: dict, subject: str) -> dict:
    return mailer.send(
        to=order["email"],
        subject=subject,
        idempotency_key=f"order:{order['id']}:email:{subject}",
    )


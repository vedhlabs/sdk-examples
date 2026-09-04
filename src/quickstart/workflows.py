import aga_runtime as aga

from quickstart.adapters import inventory, mailer, payments
from quickstart.app import app


@app.step(timeout=10)
def validate_order(order: dict) -> dict:
    if not order.get("items"):
        raise ValueError("order must contain at least one item")
    total = sum(int(item["price"]) * int(item["qty"]) for item in order["items"])
    return {"total": total}


@app.step(
    retry=aga.RetryPolicy(max_attempts=4),
    timeout=20,
    compensate_with="release_inventory",
)
def reserve_inventory(order: dict) -> dict:
    return inventory.reserve(order, idempotency_key=f"order:{order['id']}:inventory")


@app.step()
def release_inventory(reservation: dict) -> dict:
    return inventory.release(reservation["reservation_id"])


@app.step(retry=aga.RetryPolicy(max_attempts=5), timeout=30, pivot=True)
def charge_customer(order: dict, amount: int) -> dict:
    return payments.charge(
        customer_id=order["customer_id"],
        amount=amount,
        idempotency_key=f"order:{order['id']}:charge",
    )


@app.step(retry=aga.RetryPolicy(max_attempts=3), timeout=15)
def send_receipt(order: dict, charge: dict) -> dict:
    return mailer.send(
        to=order["email"],
        subject=f"Receipt for {charge['charge_id']}",
        idempotency_key=f"order:{order['id']}:receipt",
    )


@app.workflow(
    name="quickstart.checkout",
    version="1",
    execution="async",
)
async def checkout(order: dict) -> dict:
    validated = await validate_order(order)
    reservation = await reserve_inventory(order)
    charge = await charge_customer(order, validated["total"])
    receipt = await send_receipt(order, charge)
    aga.event("CheckoutCompleted", {"order_id": order["id"], "charge": charge["charge_id"]})
    return {
        "order_id": order["id"],
        "total": validated["total"],
        "reservation_id": reservation["reservation_id"],
        "charge_id": charge["charge_id"],
        "receipt_id": receipt["message_id"],
    }

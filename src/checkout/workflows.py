import ogha

from checkout.adapters import payments, shipping
from checkout.app import app


@app.step(
    retry=ogha.RetryPolicy(max_attempts=5),
    timeout=30,
    pivot=True,
)
def charge_order(order: dict) -> dict:
    return payments.charge(
        customer_id=order["customer_id"],
        amount=order["total"],
        idempotency_key=f"order:{order['id']}:charge",
    )


@app.step(retry=ogha.RetryPolicy(max_attempts=5), timeout=30)
def create_shipment(order: dict) -> dict:
    return shipping.create(order=order, idempotency_key=f"order:{order['id']}:shipment")


@app.workflow(name="checkout", version="1")
async def checkout(order: dict) -> dict:
    charge = await charge_order(order)
    shipment = await create_shipment(order)
    return {
        "order_id": order["id"],
        "charge_id": charge["id"],
        "tracking": shipment["tracking"],
    }

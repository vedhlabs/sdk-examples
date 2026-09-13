import aga_runtime as aga
from aga_runtime import errors

from checkout.adapters import payments, shipping
from checkout.app import app


@app.step(
    retry=aga.RetryPolicy(max_attempts=5),
    timeout=30,
    attempt_timeout=10,
    pivot=True,
)
def charge_order(order: dict) -> dict:
    key = f"order:{order['id']}:charge"
    try:
        return app.effect(
            "charge",
            lambda: payments.charge(
                customer_id=order["customer_id"],
                amount=order["total"],
                idempotency_key=key,
            ),
            idempotency_key=key,
            provider="payments",
            endpoint="charge",
            request={"order_id": order["id"], "amount": order["total"]},
        )
    except errors.EffectAlreadyApplied:
        receipt = payments.find_charge(key)
        if receipt is None:
            raise
        return receipt


@app.step(retry=aga.RetryPolicy(max_attempts=5), timeout=30, attempt_timeout=10)
def create_shipment(order: dict) -> dict:
    key = f"order:{order['id']}:shipment"
    try:
        return app.effect(
            "create-shipment",
            lambda: shipping.create(order=order, idempotency_key=key),
            idempotency_key=key,
            provider="shipping",
            endpoint="create",
            request=order,
        )
    except errors.EffectAlreadyApplied:
        receipt = shipping.find_shipment(key)
        if receipt is None:
            raise
        return receipt


@app.workflow(name="checkout", version="1")
async def checkout(order: dict) -> dict:
    charge = await charge_order(order)
    shipment = await create_shipment(order)
    return {
        "order_id": order["id"],
        "charge_id": charge["id"],
        "tracking": shipment["tracking"],
    }

import aga_runtime as aga

from checkout.adapters import payments
from checkout.app import app


@app.step(retry=aga.RetryPolicy(max_attempts=4), timeout=30)
def refund_charge(charge: dict) -> dict:
    return payments.reimburse(
        charge_id=charge["id"],
        idempotency_key=f"charge:{charge['id']}:refund",
    )

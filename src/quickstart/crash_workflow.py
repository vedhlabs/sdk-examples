import os
import time
from pathlib import Path

import ogha

from quickstart.adapters import inventory
from quickstart.app import app


@app.step(retry=ogha.RetryPolicy(max_attempts=5), timeout=20)
def reserve_for_crash_demo(order: dict) -> dict:
    return inventory.reserve(order, idempotency_key=f"order:{order['id']}:crash-demo")


@app.step(retry=ogha.RetryPolicy(max_attempts=5), timeout=30)
def fulfill_slowly(order: dict) -> dict:
    """Leave visible evidence around a hard kill.

    `START` may appear twice because a process can die after an external write but
    before Ogha records the step result. The final shipment effect uses a stable
    key in a real provider. This audit file intentionally makes the uncertainty
    observable for the tutorial.
    """
    path = Path(os.getenv("OGHA_CRASH_AUDIT", "audit.log"))
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"START {order['id']} pid={os.getpid()}\n")
        handle.flush()
    time.sleep(float(os.getenv("OGHA_CRASH_STEP_SECONDS", "8")))
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"DONE {order['id']} pid={os.getpid()}\n")
    return {"order_id": order["id"], "fulfilled": True}


@app.workflow(name="quickstart.crash-recovery")
async def crash_recovery(order: dict) -> dict:
    reservation = await reserve_for_crash_demo(order)
    fulfillment = await fulfill_slowly(order)
    return {**fulfillment, "reservation_id": reservation["reservation_id"]}

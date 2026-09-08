from __future__ import annotations

import sys
from typing import TypedDict

import aga_runtime as aga

from ecommerce.adapters import inventory, payments, shipping

app = aga.App("checkout", concurrency=8)


class RiskRequest(TypedDict):
    order_id: str
    total: int


# A Remote is a typed service declaration. Its implementation runs elsewhere.
@app.remote("risk", name="score", timeout=10)
def score_risk(request: RiskRequest) -> dict:
    raise NotImplementedError("Aga routes Remote declarations to their service")


@app.step()
def release_stock(reservation: dict) -> dict:
    return inventory.release(reservation["ref"])


@app.step(
    retry=aga.RetryPolicy(max_attempts=4),
    timeout=20,
    compensate_with=release_stock,
)
def reserve_stock(order: dict) -> dict:
    return inventory.reserve(
        order,
        idempotency_key=f"order:{order['id']}:stock",
    )


@app.step(retry=aga.RetryPolicy(max_attempts=3), timeout=10)
def quote_shipping(order: dict, carrier: str) -> dict:
    price = {"ups": 12, "fedex": 15, "dhl": 18}[carrier]
    return {"carrier": carrier, "price": price}


@app.step(retry=aga.RetryPolicy(max_attempts=5), timeout=30, pivot=True)
def charge_order(order: dict, total: int) -> dict:
    return payments.charge(
        customer=order["customer_id"],
        amount=total,
        idempotency_key=f"order:{order['id']}:charge",
    )


@app.step(retry=aga.RetryPolicy(max_attempts=5), timeout=30)
def create_shipment(order: dict, carrier: str) -> dict:
    return shipping.create(
        order,
        carrier,
        idempotency_key=f"order:{order['id']}:shipment",
    )


@app.workflow(name="checkout.audit", version="1")
async def audit_order(result: dict) -> dict:
    app.event("OrderAudited", result)
    return {"audited": result["order_id"]}


@app.workflow(
    name="checkout",
    version="1",
    execution="async_distributed",
)
async def checkout(order: dict) -> dict:
    quotes = {
        carrier: quote_shipping.options(name=f"quote-{carrier}")(order, carrier)
        for carrier in ("ups", "fedex", "dhl")
    }
    received = await app.join(*quotes.values(), count=2)
    winners = {quote["carrier"] for quote in received}
    for carrier, handle in quotes.items():
        if carrier not in winners:
            app.cancel(handle, reason="shipping quorum reached")

    best = min(received, key=lambda quote: quote["price"])
    total = int(order["total"]) + best["price"]

    if total > 5_000:
        risk = await score_risk({"order_id": order["id"], "total": total})
        approval = await app.signal(
            aga.Approval("fraud_review", evidence=risk),
            timeout=120,
        )
        if not approval["approved"]:
            raise PermissionError("fraud review denied the order")

    await reserve_stock(order)
    charge = await charge_order(order, total)
    shipment = await create_shipment(order, best["carrier"])

    if order.get("wait_for_pickup"):
        await app.signal("carrier_pickup", timeout=3 * 86_400)

    result = {
        "order_id": order["id"],
        "charge_id": charge["charge_id"],
        "tracking": shipment["tracking"],
    }
    app.event("CheckoutCompleted", result)

    # This child is intentionally independent of checkout completion.
    app.start(
        audit_order.options(
            run_id=f"audit-{order['id']}",
            detached=True,
        ),
        result,
    )

    await app.sleep(1)
    return result


@app.step(timeout=30)
def reconcile_day(day: str, occurrence: str) -> dict:
    return {"day": day, "occurrence": occurrence, "status": "balanced"}


@app.schedule(
    "0 6 * * *",
    schedule_id="checkout.daily-reconciliation",
    input={"day": "previous"},
    overlap=aga.OVERLAP_SKIP,
    revision=1,
)
@app.workflow(name="checkout.daily-reconciliation", version="1")
async def daily_reconciliation(request: dict) -> dict:
    occurrence = app.info().scheduled_time
    assert occurrence is not None
    return await reconcile_day(request["day"], occurrence.isoformat())


def main() -> None:
    if "--worker" in sys.argv:
        app.serve()
        return

    order = {
        "id": "ORDER-42",
        "customer_id": "CUS-7",
        "total": 200,
        "wait_for_pickup": False,
    }
    run = app.start(
        checkout.options(
            run_id=order["id"],
            resource=aga.ResourceRef("order", order["id"]),
        ),
        order,
    )
    print(run.result())


if __name__ == "__main__":
    main()

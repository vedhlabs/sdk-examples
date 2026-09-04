import ogha

from ecommerce.app import app
from ecommerce.steps import (
    charge_card,
    create_shipment,
    price_shipping,
    reserve_stock,
    send_email,
    validate_cart,
)


@app.workflow(
    name="ecommerce.checkout",
    version="1",
    execution="async_distributed",
)
async def checkout(order: dict) -> dict:
    ogha.event("OrderReceived", {"id": order["id"]})

    cart = await validate_cart(order)

    quotes = {
        carrier: price_shipping.options(name=f"quote-{carrier}")(order, carrier)
        for carrier in ("ups", "fedex", "dhl")
    }
    received = await ogha.quorum(2, *quotes.values())
    winning_carriers = {quote["carrier"] for quote in received}
    for carrier, handle in quotes.items():
        if carrier not in winning_carriers:
            # Reissue the same cancellation during replay as well. A loser is
            # terminal after the first pass, but still belongs to this scope;
            # calling cancel again is idempotent and releases that ownership.
            ogha.cancel(handle, reason="two quotes already received")
    best = min(received, key=lambda quote: quote["price"])
    total = cart["total"] + best["price"]
    ogha.event("ShippingPriced", {"carrier": best["carrier"], "price": best["price"]})

    if total > 5_000:
        try:
            review = await ogha.approval("fraud_review", {"total": total}, timeout=120)
        except ogha.PermissionDenied:
            return {"status": "rejected", "reason": "not reviewed in time"}
        if not review.get("approved"):
            return {"status": "rejected", "reason": "reviewer denied the order"}

    await reserve_stock(order)
    charge = await charge_card(order, total)
    ogha.event("Paid", {"charge": charge["charge_id"], "amount": total})

    shipment = await create_shipment(order, best["carrier"])
    pickup = await ogha.signal("carrier_pickup", timeout=3 * 86_400)

    await send_email(order, f"Shipped - {shipment['tracking']}")
    ogha.event("Shipped", {"tracking": shipment["tracking"], "pickup": pickup})
    await ogha.sleep(1)
    await send_email(order, "How was your order?")

    return {
        "status": "shipped",
        "order": order["id"],
        "total": total,
        "tracking": shipment["tracking"],
        "charge_id": charge["charge_id"],
    }

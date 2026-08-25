import ogha
from ogha import Quorum

from ecommerce.steps import (
    charge_card,
    create_shipment,
    price_shipping,
    reserve_stock,
    send_email,
    validate_cart,
)


@ogha.workflow(
    name="ecommerce.checkout",
    version="1",
    execution="async_distributed",
    target="python://ecommerce",
)
async def checkout(ctx, order: dict) -> dict:
    ctx.emit("OrderReceived", {"id": order["id"]})

    cart = await ctx.call(validate_cart, order)

    quotes = [
        ctx.call(price_shipping, order, carrier, name=f"quote-{carrier}")
        for carrier in ("ups", "fedex", "dhl")
    ]
    received = await ctx.join(*quotes, until=Quorum(2))
    for handle in quotes:
        if not handle.settled:
            ctx.cancel(handle, reason="two quotes already received")
    best = min(received, key=lambda quote: quote["price"])
    total = cart["total"] + best["price"]
    ctx.emit("ShippingPriced", {"carrier": best["carrier"], "price": best["price"]})

    if total > 5_000:
        try:
            review = await ctx.gate("fraud_review", {"total": total}, timeout=120)
        except ogha.PermissionDenied:
            return {"status": "rejected", "reason": "not reviewed in time"}
        if not review.get("approved"):
            return {"status": "rejected", "reason": "reviewer denied the order"}

    await ctx.call(reserve_stock, order)
    charge = await ctx.call(charge_card, order, total)
    ctx.emit("Paid", {"charge": charge["charge_id"], "amount": total})

    shipment = await ctx.call(create_shipment, order, best["carrier"])
    pickup = await ctx.wait("carrier_pickup", timeout=3 * 86_400)

    await ctx.call(send_email, order, f"Shipped - {shipment['tracking']}")
    ctx.emit("Shipped", {"tracking": shipment["tracking"], "pickup": pickup})
    ctx.sleep(1)
    await ctx.call(send_email, order, "How was your order?")

    return {
        "status": "shipped",
        "order": order["id"],
        "total": total,
        "tracking": shipment["tracking"],
        "charge_id": charge["charge_id"],
    }


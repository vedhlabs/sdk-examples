import time

import ogha


@ogha.step
def normalize_request(request: dict) -> dict:
    return {"customer": request["customer"].strip().lower(), "amount": int(request["amount"])}


@ogha.step(name="risk.score", retry=ogha.RetryPolicy(max_attempts=3), timeout=10)
def risk_score(request: dict) -> dict:
    score = 25 if request["amount"] < 1_000 else 70
    return {"score": score, "band": "low" if score < 50 else "high"}


@ogha.step
def quote_provider(request: dict, provider: str) -> dict:
    latency = {"fast": 0.04, "slow": 0.25}[provider]
    time.sleep(latency)
    return {"provider": provider, "price": request["amount"] + (5 if provider == "fast" else 3)}


@ogha.step
def create_child_record(request: dict) -> dict:
    return {"child_record": f"record:{request['customer']}"}


@ogha.workflow(name="primitives.child", target="python://primitives")
async def child_workflow(ctx, request: dict) -> dict:
    return await ctx.call(create_child_record, request)


@ogha.workflow(
    name="primitives.tour",
    version="1",
    execution="async_distributed",
    target="python://primitives",
)
async def methods_tour(ctx, request: dict) -> dict:
    normalized = await ctx.call(normalize_request, request)
    risk = await ctx.rpc("primitives", "risk.score", normalized, timeout=10)

    child = ctx.spawn(
        "primitives.child",
        normalized,
        target="python://primitives",
    )
    quotes = [
        ctx.call(quote_provider, normalized, provider, name=f"quote-{provider}")
        for provider in ("fast", "slow")
    ]
    first_quote = await ctx.join(*quotes, until=ogha.ANY)
    for handle in quotes:
        if not handle.settled:
            ctx.cancel(handle, reason="first quote already selected")
    child_result = await ctx.join(child)

    ctx.sleep(1)
    signal = await ctx.wait("external_signal", timeout=60)
    approval = await ctx.gate(
        "manual_approval",
        {"risk": risk, "quote": first_quote},
        timeout=60,
    )
    ctx.emit("TourCompleted", {"approved_by": approval["reviewer"]})
    return {
        "normalized": normalized,
        "risk": risk,
        "quote": first_quote,
        "child": child_result,
        "signal": signal,
        "approval": approval,
    }


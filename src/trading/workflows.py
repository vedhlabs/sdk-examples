from decimal import Decimal

import ogha

from trading.steps import (
    calculate_plan,
    cancel_open_order,
    check_fill,
    get_account,
    get_positions,
    market_clock,
    model_target_weights,
    place_order,
    pretrade_risk,
    reconcile,
    record_run,
    replace_order,
)

APPROVAL_TURNOVER_PCT = Decimal("10")


async def work_orders(ctx, orders: list[dict], run_tag: str, rounds: int = 3) -> dict:
    placed = []
    for order in orders:
        client_id = f"{run_tag}-{order['side']}-{order['symbol']}"
        reference = await ctx.call(
            place_order,
            order,
            client_id,
            name=f"place-{order['side']}-{order['symbol']}",
        )
        placed.append({"order": order, "ref": reference, "state": "open"})

    for round_number in range(rounds):
        for pending in placed:
            if pending["state"] != "open":
                continue
            state = await ctx.call(
                check_fill,
                pending["ref"],
                name=f"check-{pending['order']['symbol']}-{round_number}",
            )
            if state["status"] in ("filled", "canceled", "expired"):
                pending["state"] = state["status"]

        if all(pending["state"] != "open" for pending in placed):
            break

        if round_number == rounds // 2 - 1:
            for pending in placed:
                if pending["state"] == "open":
                    price = Decimal(pending["order"]["limit_price"])
                    factor = (
                        Decimal("1.002")
                        if pending["order"]["side"] == "buy"
                        else Decimal("0.998")
                    )
                    new_limit = str((price * factor).quantize(Decimal("0.01")))
                    pending["ref"] = await ctx.call(
                        replace_order,
                        pending["ref"],
                        new_limit,
                        name=f"replace-{pending['order']['symbol']}",
                    )
        ctx.sleep(1)

    for pending in placed:
        if pending["state"] == "open":
            await ctx.call(
                cancel_open_order,
                pending["ref"],
                name=f"cancel-{pending['order']['symbol']}",
            )
    return {"filled": sum(row["state"] == "filled" for row in placed), "orders": len(placed)}


@ogha.workflow(
    name="trading.rebalance",
    version="1",
    execution="async_distributed",
    target="python://trading",
)
async def trading_rebalance(ctx, request: dict) -> dict:
    portfolio = request["portfolio"]
    run_tag = request["run_id"]

    clock = await ctx.call(market_clock)
    if not clock["session_today"]:
        return {"portfolio": portfolio, "action": "market_closed"}
    if not clock["is_open"]:
        ctx.emit("WaitingForOpen", clock)
        ctx.sleep(clock["seconds_to_open"])

    account_h = ctx.call(get_account)
    positions_h = ctx.call(get_positions)
    account, positions = await ctx.join(account_h, positions_h)
    targets = await ctx.call(model_target_weights, portfolio, positions, account)
    plan = await ctx.call(calculate_plan, targets, positions, account)
    await ctx.call(pretrade_risk, plan)

    if Decimal(plan["turnover_pct"]) > APPROVAL_TURNOVER_PCT:
        try:
            approval = await ctx.gate(
                "rebalance_approval",
                {"portfolio": portfolio, "turnover_pct": plan["turnover_pct"]},
                timeout=120,
            )
        except ogha.PermissionDenied:
            return {"portfolio": portfolio, "status": "rejected", "reason": "not reviewed"}
        if not approval.get("approved"):
            return {"portfolio": portfolio, "status": "rejected", "reason": "denied"}

    sells = await work_orders(ctx, plan["sells"], run_tag)
    buys = await work_orders(ctx, plan["buys"], run_tag)
    reconciled = await ctx.call(reconcile, targets, account["portfolio_value"])
    record = await ctx.call(
        record_run,
        portfolio,
        run_tag,
        {"sells": sells, "buys": buys},
        reconciled,
    )
    ctx.emit("RebalanceRecorded", {"record_id": record["record_id"]})
    return {
        "portfolio": portfolio,
        "status": "completed",
        "turnover_pct": plan["turnover_pct"],
        "reconciliation": reconciled,
        "record_id": record["record_id"],
    }


@ogha.scheduled(
    "0 12 * * 1-5",
    schedule_id="trading.rebalance-day",
    context={"portfolios": ["growth", "income"]},
    overlap=ogha.OVERLAP_SKIP,
    revision=1,
)
@ogha.workflow(name="trading.rebalance-day", version="1", target="python://trading")
async def rebalance_day(ctx, request: dict) -> dict:
    trade_date = ogha.scheduled_time(ctx).date().isoformat()
    children = [
        ctx.spawn(
            "trading.rebalance",
            {"portfolio": portfolio, "run_id": f"{trade_date}-{portfolio}"},
            run_id=f"{trade_date}-{portfolio}",
            target="python://trading",
        )
        for portfolio in request["portfolios"]
    ]
    return {"trade_date": trade_date, "run_ids": [child.id for child in children]}

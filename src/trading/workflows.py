from decimal import Decimal

import ogha

from trading.app import app
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


async def work_orders(orders: list[dict], run_tag: str, rounds: int = 3) -> dict:
    placed = []
    for order in orders:
        client_id = f"{run_tag}-{order['side']}-{order['symbol']}"
        reference = await place_order.options(
            name=f"place-{order['side']}-{order['symbol']}"
        )(
            order,
            client_id,
        )
        placed.append({"order": order, "ref": reference, "state": "open"})

    for round_number in range(rounds):
        for pending in placed:
            if pending["state"] != "open":
                continue
            state = await check_fill.options(
                name=f"check-{pending['order']['symbol']}-{round_number}"
            )(
                pending["ref"],
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
                    pending["ref"] = await replace_order.options(
                        name=f"replace-{pending['order']['symbol']}"
                    )(
                        pending["ref"],
                        new_limit,
                    )
        await ogha.sleep(1)

    for pending in placed:
        if pending["state"] == "open":
            await cancel_open_order.options(
                name=f"cancel-{pending['order']['symbol']}"
            )(
                pending["ref"],
            )
    return {"filled": sum(row["state"] == "filled" for row in placed), "orders": len(placed)}


@app.workflow(
    name="trading.rebalance",
    version="1",
    execution="async_distributed",
)
async def trading_rebalance(request: dict) -> dict:
    portfolio = request["portfolio"]
    run_tag = request["run_id"]

    clock = await market_clock()
    if not clock["session_today"]:
        return {"portfolio": portfolio, "action": "market_closed"}
    if not clock["is_open"]:
        ogha.event("WaitingForOpen", clock)
        await ogha.sleep(clock["seconds_to_open"])

    account_h = get_account()
    positions_h = get_positions()
    account, positions = await ogha.join(account_h, positions_h)
    targets = await model_target_weights(portfolio, positions, account)
    plan = await calculate_plan(targets, positions, account)
    await pretrade_risk(plan)

    if Decimal(plan["turnover_pct"]) > APPROVAL_TURNOVER_PCT:
        try:
            approval = await ogha.signal(
                ogha.Approval(
                    "rebalance_approval",
                    {"portfolio": portfolio, "turnover_pct": plan["turnover_pct"]},
                ),
                timeout=120,
            )
        except ogha.PermissionDenied:
            return {"portfolio": portfolio, "status": "rejected", "reason": "not reviewed"}
        if not approval.get("approved"):
            return {"portfolio": portfolio, "status": "rejected", "reason": "denied"}

    sells = await work_orders(plan["sells"], run_tag)
    buys = await work_orders(plan["buys"], run_tag)
    reconciled = await reconcile(targets, account["portfolio_value"])
    record = await record_run(
        portfolio,
        run_tag,
        {"sells": sells, "buys": buys},
        reconciled,
    )
    ogha.event("RebalanceRecorded", {"record_id": record["record_id"]})
    return {
        "portfolio": portfolio,
        "status": "completed",
        "turnover_pct": plan["turnover_pct"],
        "reconciliation": reconciled,
        "record_id": record["record_id"],
    }


@app.schedule(
    "0 12 * * 1-5",
    schedule_id="trading.rebalance-day",
    input={"portfolios": ["growth", "income"]},
    overlap=ogha.OVERLAP_SKIP,
    revision=1,
)
@app.workflow(name="trading.rebalance-day", version="1")
async def rebalance_day(request: dict) -> dict:
    scheduled_time = ogha.info().scheduled_time
    assert scheduled_time is not None
    trade_date = scheduled_time.date().isoformat()
    children = [
        trading_rebalance.options(
            run_id=f"{trade_date}-{portfolio}",
            detached=True,
        ).spawn(
            {"portfolio": portfolio, "run_id": f"{trade_date}-{portfolio}"},
        )
        for portfolio in request["portfolios"]
    ]
    return {"trade_date": trade_date, "run_ids": [child.id for child in children]}

"""PostgreSQL-backed schedule declarations for the trading example."""

import aga_runtime as aga

from trading.app import app
from trading.workflows import trading_rebalance


@app.schedule(
    "0 12 * * 1-5",
    schedule_id="trading.rebalance-day",
    input={"portfolios": ["growth", "income"]},
    overlap=aga.OVERLAP_SKIP,
    revision=1,
)
@app.workflow(name="trading.rebalance-day", version="1")
async def rebalance_day(request: dict) -> dict:
    scheduled_time = aga.info().scheduled_time
    assert scheduled_time is not None
    trade_date = scheduled_time.date().isoformat()
    children = [
        app.start(
            trading_rebalance.options(
                run_id=f"{trade_date}-{portfolio}",
                detached=True,
            ),
            {"portfolio": portfolio, "run_id": f"{trade_date}-{portfolio}"},
        )
        for portfolio in request["portfolios"]
    ]
    return {"trade_date": trade_date, "run_ids": [child.id for child in children]}

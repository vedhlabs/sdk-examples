from decimal import Decimal

import ogha

from trading import domain
from trading.adapters import books, broker_from_env, model

broker = broker_from_env()
MAX_ORDER_NOTIONAL = Decimal("50000")
RESTRICTED = {"GME"}


@ogha.step(retry=ogha.RetryPolicy(max_attempts=4), timeout=15)
def market_clock() -> dict:
    return broker.clock()


@ogha.step(retry=ogha.RetryPolicy(max_attempts=4), timeout=15)
def get_account() -> dict:
    return broker.account()


@ogha.step(retry=ogha.RetryPolicy(max_attempts=4), timeout=15)
def get_positions() -> list[dict]:
    return broker.positions()


@ogha.step(retry=ogha.RetryPolicy(max_attempts=2), timeout=60)
def model_target_weights(portfolio: str, positions: list[dict], account: dict) -> dict:
    return model.target_weights(portfolio, positions, account)


@ogha.step(timeout=15)
def calculate_plan(targets: dict, positions: list[dict], account: dict) -> dict:
    return domain.plan_orders(targets, positions, account)


@ogha.step(timeout=15)
def pretrade_risk(plan: dict) -> dict:
    for order in plan["sells"] + plan["buys"]:
        if order["symbol"] in RESTRICTED:
            raise ValueError(f"{order['symbol']} is restricted")
        if Decimal(order["notional"]) > MAX_ORDER_NOTIONAL:
            raise ValueError("order exceeds the notional limit")
    return {"ok": True}


@ogha.step(
    retry=ogha.RetryPolicy(max_attempts=5),
    timeout=45,
    compensate_with="cancel_open_order",
)
def place_order(order: dict, client_order_id: str) -> dict:
    existing = broker.find_order(client_order_id)
    return existing or broker.place(order, client_order_id)


@ogha.step(retry=ogha.RetryPolicy(max_attempts=3), timeout=15)
def check_fill(reference: dict) -> dict:
    return broker.order(reference["id"])


@ogha.step(retry=ogha.RetryPolicy(max_attempts=3), timeout=30)
def replace_order(reference: dict, new_limit: str) -> dict:
    return broker.replace(reference["id"], new_limit)


@ogha.step
def cancel_open_order(reference: dict) -> dict:
    broker.cancel(reference["id"])
    return {"canceled": reference["id"]}


@ogha.step(retry=ogha.RetryPolicy(max_attempts=3), timeout=15)
def reconcile(targets: dict, equity: str) -> dict:
    return domain.reconciliation(targets, broker.positions(), equity)


@ogha.step(pivot=True, timeout=15)
def record_run(
    portfolio: str,
    run_tag: str,
    executed: dict,
    reconciliation_result: dict,
) -> dict:
    return books.record(portfolio, run_tag, executed, reconciliation_result)


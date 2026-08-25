from decimal import ROUND_DOWN, Decimal

DRIFT_BAND = Decimal("0.02")


def plan_orders(targets: dict, positions: list[dict], account: dict) -> dict:
    equity = Decimal(account["portfolio_value"])
    held = {row["symbol"]: row for row in positions}
    orders: list[dict] = []
    drift: dict[str, str] = {}

    for symbol in sorted(set(held) | set(targets)):
        position = held.get(symbol)
        target = targets.get(symbol, {"weight": "0"})
        current_value = Decimal(position["market_value"]) if position else Decimal(0)
        target_weight = Decimal(target["weight"])
        current_weight = current_value / equity
        drift[symbol] = str((current_weight - target_weight) * 100)
        if abs(current_weight - target_weight) <= DRIFT_BAND:
            continue

        price = Decimal(position["current_price"] if position else target["reference_price"])
        delta = target_weight * equity - current_value
        qty = (abs(delta) / price).quantize(Decimal("0.000001"), ROUND_DOWN)
        if qty:
            orders.append(
                {
                    "symbol": symbol,
                    "side": "buy" if delta > 0 else "sell",
                    "qty": str(qty),
                    "limit_price": str(price),
                    "notional": str(qty * price),
                }
            )

    sells = [order for order in orders if order["side"] == "sell"]
    buys = [order for order in orders if order["side"] == "buy"]
    turnover = sum(Decimal(order["notional"]) for order in orders) / equity * 100
    return {"sells": sells, "buys": buys, "turnover_pct": str(turnover), "drift": drift}


def reconciliation(targets: dict, positions: list[dict], equity: str) -> dict:
    total = Decimal(equity)
    held = {row["symbol"]: Decimal(row["market_value"]) for row in positions}
    symbols = sorted(set(held) | set(targets))
    drift = {
        symbol: str(
            (
                held.get(symbol, Decimal(0)) / total
                - Decimal(targets.get(symbol, {"weight": "0"})["weight"])
            )
            * 100
        )
        for symbol in symbols
    }
    worst = max((abs(Decimal(value)) for value in drift.values()), default=Decimal(0))
    return {"post_drift_pct": drift, "within_band": worst <= DRIFT_BAND * 100}


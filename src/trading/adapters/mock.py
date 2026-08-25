from __future__ import annotations

from decimal import Decimal

from example_support.store import stable_id, store


class MockBroker:
    """Deterministic local broker that preserves orders across worker restarts."""

    _INITIAL_POSITIONS = [
        {"symbol": "AAPL", "market_value": "20000", "current_price": "200"},
        {"symbol": "MSFT", "market_value": "20000", "current_price": "400"},
    ]

    def clock(self) -> dict:
        return {"is_open": True, "session_today": True, "seconds_to_open": 0}

    def account(self) -> dict:
        return {"portfolio_value": "100000", "buying_power": "60000"}

    def positions(self) -> list[dict]:
        return store.get("trading.mock", "positions", self._INITIAL_POSITIONS)

    def find_order(self, client_order_id: str) -> dict | None:
        order_id = store.get("trading.mock.client-order", client_order_id)
        return store.get("trading.mock.order", order_id) if order_id else None

    def place(self, order: dict, client_order_id: str) -> dict:
        existing = self.find_order(client_order_id)
        if existing is not None:
            return existing
        order_id = stable_id("order", client_order_id)
        value = {
            **order,
            "id": order_id,
            "client_order_id": client_order_id,
            "status": "open",
            "checks": 0,
        }
        store.set("trading.mock.order", order_id, value)
        store.set("trading.mock.client-order", client_order_id, order_id)
        return value

    def order(self, order_id: str) -> dict:
        value = store.get("trading.mock.order", order_id)
        if value is None:
            raise KeyError(f"unknown mock order: {order_id}")
        if value["status"] != "open":
            return value
        value["checks"] += 1
        if value["checks"] >= 2:
            value["status"] = "filled"
            self._apply_fill(value)
        store.set("trading.mock.order", order_id, value)
        return value

    def replace(self, order_id: str, limit_price: str) -> dict:
        current = store.get("trading.mock.order", order_id)
        if current is None:
            raise KeyError(f"unknown mock order: {order_id}")
        if current["status"] == "filled":
            return current
        current["status"] = "replaced"
        store.set("trading.mock.order", order_id, current)
        replacement_id = stable_id("replacement", f"{order_id}:{limit_price}")
        replacement = {
            **current,
            "id": replacement_id,
            "limit_price": limit_price,
            "status": "open",
            "checks": 0,
            "replaces": order_id,
        }
        store.set("trading.mock.order", replacement_id, replacement)
        return replacement

    def cancel(self, order_id: str) -> None:
        value = store.get("trading.mock.order", order_id)
        if value is None or value["status"] == "filled":
            return
        value["status"] = "canceled"
        store.set("trading.mock.order", order_id, value)

    def _apply_fill(self, order: dict) -> None:
        positions = {row["symbol"]: row for row in self.positions()}
        symbol = order["symbol"]
        current = positions.get(
            symbol,
            {"symbol": symbol, "market_value": "0", "current_price": order["limit_price"]},
        )
        value = Decimal(current["market_value"])
        notional = Decimal(order["notional"])
        value = value + notional if order["side"] == "buy" else value - notional
        current["market_value"] = str(value)
        current["current_price"] = order["limit_price"]
        positions[symbol] = current
        store.set("trading.mock", "positions", [positions[key] for key in sorted(positions)])


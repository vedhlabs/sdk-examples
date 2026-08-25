from __future__ import annotations

import os
from datetime import datetime


class Alpaca:
    def __init__(self, key_id: str, secret: str) -> None:
        try:
            import httpx
        except ImportError as exc:
            raise RuntimeError(
                'Install the optional adapter with pip install -e ".[alpaca]"'
            ) from exc
        self.http = httpx.Client(
            base_url="https://paper-api.alpaca.markets",
            headers={"APCA-API-KEY-ID": key_id, "APCA-API-SECRET-KEY": secret},
            timeout=15,
        )

    @classmethod
    def from_env(cls) -> Alpaca:
        return cls(os.environ["ALPACA_KEY_ID"], os.environ["ALPACA_SECRET"])

    def _json(self, method: str, path: str, **kwargs):
        response = self.http.request(method, path, **kwargs)
        response.raise_for_status()
        return response.json() if response.content else None

    def clock(self) -> dict:
        value = self._json("GET", "/v2/clock")
        now = datetime.fromisoformat(value["timestamp"])
        next_open = datetime.fromisoformat(value["next_open"])
        value["session_today"] = value["is_open"] or next_open.date() == now.date()
        value["seconds_to_open"] = max(0, int((next_open - now).total_seconds()))
        return value

    def account(self) -> dict:
        return self._json("GET", "/v2/account")

    def positions(self) -> list[dict]:
        return self._json("GET", "/v2/positions")

    def find_order(self, client_order_id: str) -> dict | None:
        response = self.http.get(
            "/v2/orders:by_client_order_id",
            params={"client_order_id": client_order_id},
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()

    def place(self, order: dict, client_order_id: str) -> dict:
        return self._json(
            "POST",
            "/v2/orders",
            json={
                "symbol": order["symbol"],
                "qty": order["qty"],
                "side": order["side"],
                "type": "limit",
                "limit_price": order["limit_price"],
                "time_in_force": "day",
                "client_order_id": client_order_id,
            },
        )

    def order(self, order_id: str) -> dict:
        return self._json("GET", f"/v2/orders/{order_id}")

    def replace(self, order_id: str, limit_price: str) -> dict:
        response = self.http.patch(f"/v2/orders/{order_id}", json={"limit_price": limit_price})
        if response.status_code == 422:
            current = self.order(order_id)
            if current["status"] == "filled":
                return current
        response.raise_for_status()
        return response.json()

    def cancel(self, order_id: str) -> None:
        response = self.http.delete(f"/v2/orders/{order_id}")
        if response.status_code not in (204, 404, 422):
            response.raise_for_status()

from __future__ import annotations

import os
from typing import Protocol


class Broker(Protocol):
    def clock(self) -> dict: ...

    def account(self) -> dict: ...

    def positions(self) -> list[dict]: ...

    def find_order(self, client_order_id: str) -> dict | None: ...

    def place(self, order: dict, client_order_id: str) -> dict: ...

    def order(self, order_id: str) -> dict: ...

    def replace(self, order_id: str, limit_price: str) -> dict: ...

    def cancel(self, order_id: str) -> None: ...


def broker_from_env() -> Broker:
    name = os.getenv("TRADING_BROKER", "mock").lower()
    if name == "mock":
        from trading.adapters.mock import MockBroker

        return MockBroker()
    if name == "alpaca":
        from trading.adapters.alpaca import Alpaca

        return Alpaca.from_env()
    raise ValueError("TRADING_BROKER must be 'mock' or 'alpaca'")


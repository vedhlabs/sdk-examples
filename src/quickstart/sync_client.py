from __future__ import annotations

import argparse
import json
import uuid
from typing import Any

from quickstart.app import app
from quickstart.workflows import checkout


def example_order(amount: int, *, order_id: str | None = None) -> dict[str, Any]:
    """Build one self-contained order for the synchronous caller example."""
    return {
        "id": order_id or f"QS-SYNC-{uuid.uuid4().hex[:12]}",
        "customer_id": "CUS-SYNC-QUICKSTART",
        "email": "sync-buyer@example.com",
        "items": [{"sku": "starter-kit", "price": amount, "qty": 1}],
    }


def run_checkout_sync(
    order: dict[str, Any],
    *,
    timeout_s: float = 30,
    poll_s: float = 0.2,
) -> tuple[str, dict[str, Any]]:
    """Start a durable run and block this caller until that run is terminal.

    Waiting does not execute the workflow in this process and does not create a
    third Ogha execution mode. The worker still uses the workflow's declared
    async-sticky or async-distributed placement, and the run survives if this
    caller disconnects.
    """
    run = app.start(checkout.options(run_id=str(order["id"])), order)
    output = run.result(timeout=timeout_s, poll=poll_s)
    if not isinstance(output, dict):
        raise RuntimeError(f"run {run.id} returned a non-object result")
    return run.id, output


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Submit a durable checkout and synchronously wait for its result"
    )
    parser.add_argument("--amount", type=int, default=125)
    parser.add_argument("--timeout", type=float, default=30, help="caller wait timeout in seconds")
    args = parser.parse_args()

    order = example_order(args.amount)
    run_id, output = run_checkout_sync(order, timeout_s=args.timeout)
    print(f"completed {run_id}")
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

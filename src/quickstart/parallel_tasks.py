"""Compare caller waiting, sticky placement, and distributed task concurrency."""

import argparse
import json
import os
import time

import aga_runtime as aga

app = aga.App("parallel-tasks", concurrency=8)


def simulate_check(name: str, order_id: str) -> dict:
    started_ns = time.monotonic_ns()
    time.sleep(2)  # Simulated blocking service call, not a durable workflow wait.
    return {
        "check": name,
        "order_id": order_id,
        "worker_pid": os.getpid(),
        "started_ns": started_ns,
        "finished_ns": time.monotonic_ns(),
    }


@app.step()
def check_stock(order_id: str) -> dict:
    return simulate_check("stock", order_id)


@app.step()
def quote_shipping(order_id: str) -> dict:
    return simulate_check("shipping", order_id)


@app.workflow(execution="async")
async def sticky_checks(order_id: str) -> dict:
    # Both calls start before waiting; the local worker runs them concurrently.
    stock_task = check_stock(order_id)
    shipping_task = quote_shipping(order_id)
    stock, shipping = await app.join(stock_task, shipping_task)
    return {"stock": stock, "shipping": shipping}


@app.workflow(execution="async_distributed")
async def distributed_checks(order_id: str) -> dict:
    # Both operations are submitted before waiting; available workers run them.
    stock_task = check_stock(order_id)
    shipping_task = quote_shipping(order_id)
    stock, shipping = await app.join(stock_task, shipping_task)
    return {"stock": stock, "shipping": shipping}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker", action="store_true", help="Serve both workflows")
    parser.add_argument("--mode", choices=("sync", "async", "async_distributed"), default="sync")
    parser.add_argument("--order-id", default="ORDER-DEMO")
    parser.add_argument(
        "--wait", action="store_true", help="Also wait after asynchronous submission",
    )
    args = parser.parse_args()
    try:
        if args.worker:
            app.serve()
        else:
            workflow = distributed_checks if args.mode == "async_distributed" else sticky_checks
            run = app.start(workflow, args.order_id)
            print(f"Run ID: {run.id}", flush=True)
            if args.mode == "sync" or args.wait:
                print(json.dumps(run.result(timeout=60), indent=2))
    finally:
        app.close()


if __name__ == "__main__":
    main()

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

SMOKE_ID = uuid.uuid4().hex[:10]
os.environ.setdefault("OGHA_NAMESPACE", f"sdk-examples-smoke-{SMOKE_ID}")
os.environ.setdefault("OGHA_EXAMPLE_STATE", f".state/smoke-{SMOKE_ID}.sqlite3")
os.environ.setdefault("TRADING_BROKER", "mock")

import ogha  # noqa: E402

from ecommerce.client import connect as ecommerce_connect  # noqa: E402
from ecommerce.webhooks import carrier_pickup  # noqa: E402
from example_support.config import connect, decode_output  # noqa: E402
from example_support.promises import pending_promise  # noqa: E402
from lending.client import connect as lending_connect  # noqa: E402
from primitives.client import connect as primitives_connect  # noqa: E402
from trading.client import connect as trading_connect  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
WORKERS = (
    "quickstart.worker",
    "checkout.worker",
    "reports.worker",
    "ecommerce.worker",
    "lending.worker",
    "primitives.worker",
    "trading.worker",
)


def terminal(client: ogha.Client, run_id: str, timeout_s: float = 45) -> dict:
    run = client.result(run_id, timeout_s=timeout_s)
    if run.state is not ogha.RunState.COMPLETED:
        raise RuntimeError(f"{run_id} ended {run.state.name}: {run.error}")
    return decode_output(run.output)


def submit(client: ogha.Client, workflow: str, target: str, value, prefix: str) -> str:
    run_id = f"{prefix}-{SMOKE_ID}-{uuid.uuid4().hex[:6]}"
    client.submit(
        workflow,
        json.dumps(value).encode(),
        run_id=run_id,
        target=target,
    )
    return run_id


def run_checks() -> None:
    base = connect()
    base.hello()

    quickstart_id = submit(
        base,
        "quickstart.checkout",
        "python://quickstart",
        {
            "id": f"QS-{SMOKE_ID}",
            "customer_id": "smoke-customer",
            "email": "smoke@example.com",
            "items": [{"sku": "kit", "price": 125, "qty": 1}],
        },
        "quickstart",
    )
    assert terminal(base, quickstart_id)["total"] == 125

    checkout_id = submit(
        base,
        "checkout",
        "python://checkout",
        {"id": f"ORDER-{SMOKE_ID}", "customer_id": "smoke", "total": 149},
        "checkout",
    )
    assert terminal(base, checkout_id)["tracking"]

    ecommerce = ecommerce_connect()
    ecommerce_id = submit(
        ecommerce,
        "ecommerce.checkout",
        "python://ecommerce",
        {
            "id": f"EC-{SMOKE_ID}",
            "customer_id": "smoke",
            "email": "smoke@example.com",
            "items": [{"sku": "widget", "price": 200, "qty": 1}],
        },
        "ecommerce",
    )
    pending_promise(ecommerce, ecommerce_id, "carrier_pickup", timeout_s=20)
    carrier_pickup(ecommerce_id, {"tracking": "SMOKE-PICKUP"})
    assert terminal(ecommerce, ecommerce_id)["status"] == "shipped"

    lending = lending_connect()
    lending_id = submit(
        lending,
        "lending.application",
        "python://lending",
        {
            "applicant": {
                "id": f"LOAN-{SMOKE_ID}",
                "national_id": "TEST-SMOKE",
                "requested_score": 730,
            },
            "amount": 100_000,
        },
        "lending",
    )
    assert terminal(lending, lending_id)["status"] == "disbursed"

    primitives = primitives_connect()
    primitives_id = submit(
        primitives,
        "primitives.tour",
        "python://primitives",
        {"customer": " Smoke Customer ", "amount": 250},
        "primitives",
    )
    signal = pending_promise(primitives, primitives_id, "external_signal", timeout_s=20)
    primitives.resolve(signal.id, json.dumps({"message": "smoke signal"}).encode())
    gate = pending_promise(primitives, primitives_id, "manual_approval", timeout_s=20)
    primitives.resolve(gate.id, json.dumps({"approved": True, "reviewer": "smoke"}).encode())
    assert terminal(primitives, primitives_id)["risk"]["band"] == "low"

    trading = trading_connect()
    trading_id = submit(
        trading,
        "trading.rebalance",
        "python://trading",
        {"portfolio": "growth", "run_id": f"trade-{SMOKE_ID}"},
        "trading",
    )
    gate = pending_promise(trading, trading_id, "rebalance_approval", timeout_s=20)
    trading.resolve(gate.id, json.dumps({"approved": True, "reviewer": "smoke"}).encode())
    trading_result = terminal(trading, trading_id, timeout_s=60)
    assert trading_result["status"] == "completed"
    assert trading_result["reconciliation"]["within_band"] is True

    deadline = time.monotonic() + 10
    expected_schedules = {
        "quickstart.daily-report",
        "reports.daily-kpis",
        "trading.rebalance-day",
    }
    while time.monotonic() < deadline:
        page, _ = base.list_schedules(limit=50)
        if expected_schedules <= {schedule.id for schedule in page}:
            break
        time.sleep(0.2)
    else:
        raise RuntimeError("workers did not converge every documented schedule")


def main() -> None:
    processes: list[subprocess.Popen] = []
    logs: list[object] = []
    with tempfile.TemporaryDirectory(prefix="ogha-sdk-smoke-") as log_dir:
        try:
            for module in WORKERS:
                log = open(Path(log_dir) / f"{module}.log", "w+", encoding="utf-8")
                logs.append(log)
                processes.append(
                    subprocess.Popen(
                        [sys.executable, "-m", module],
                        cwd=ROOT,
                        env=os.environ.copy(),
                        stdout=log,
                        stderr=subprocess.STDOUT,
                    )
                )
            time.sleep(2)
            for module, process in zip(WORKERS, processes, strict=True):
                if process.poll() is not None:
                    raise RuntimeError(f"worker {module} exited with {process.returncode}")
            run_checks()
            print(f"smoke passed in namespace {os.environ['OGHA_NAMESPACE']}")
        except Exception:
            for module, process, log in zip(WORKERS, processes, logs, strict=True):
                log.flush()
                log.seek(0)
                output = log.read()
                if output:
                    print(f"\n--- {module} (pid={process.pid}) ---\n{output}", file=sys.stderr)
            raise
        finally:
            for process in processes:
                process.terminate()
            for process in processes:
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
            for log in logs:
                log.close()


if __name__ == "__main__":
    main()


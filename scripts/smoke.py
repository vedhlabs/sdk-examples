from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any

SMOKE_ID = uuid.uuid4().hex[:10]
os.environ.setdefault("OGHA_NAMESPACE", f"sdk-examples-smoke-{SMOKE_ID}")
os.environ.setdefault("OGHA_EXAMPLE_STATE", f".state/smoke-{SMOKE_ID}.sqlite3")
os.environ.setdefault("TRADING_BROKER", "mock")

import ogha  # noqa: E402

from agentic.app import app as agentic_app  # noqa: E402
from agentic.types import Ticket  # noqa: E402
from agentic.workflows import resolve_ticket  # noqa: E402
from checkout.app import app as checkout_app  # noqa: E402
from checkout.workflows import checkout as compact_checkout  # noqa: E402
from ecommerce.app import app as ecommerce_app  # noqa: E402
from ecommerce.webhooks import carrier_pickup  # noqa: E402
from ecommerce.workflow import checkout as ecommerce_checkout  # noqa: E402
from example_support.promises import pending_promise  # noqa: E402
from lending.app import app as lending_app  # noqa: E402
from lending.workflows import application as lending_application  # noqa: E402
from primitives.app import app as primitives_app  # noqa: E402
from primitives.methods import methods_tour  # noqa: E402
from quickstart.app import app as quickstart_app  # noqa: E402
from quickstart.sync_client import example_order, run_checkout_sync  # noqa: E402
from quickstart.workflows import checkout as quickstart_checkout  # noqa: E402
from trading.app import app as trading_app  # noqa: E402
from trading.workflows import trading_rebalance  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
WORKERS = (
    "agentic.worker",
    "quickstart.worker",
    "checkout.worker",
    "reports.worker",
    "ecommerce.worker",
    "lending.worker",
    "primitives.worker",
    "trading.worker",
)


def terminal(run: ogha.RunHandle[Any], timeout_s: float = 45) -> Any:
    return run.result(timeout=timeout_s)


def submit(
    app: ogha.App, workflow: Any, value: Any, prefix: str
) -> ogha.RunHandle[Any]:
    run_id = f"{prefix}-{SMOKE_ID}-{uuid.uuid4().hex[:6]}"
    return app.start(workflow.options(run_id=run_id), value)


def run_checks() -> None:
    base = quickstart_app.client
    base.hello()

    agentic = agentic_app.client
    agentic_run = submit(
        agentic_app,
        resolve_ticket,
        Ticket(
            id=f"AGENT-{SMOKE_ID}",
            customer_id="customer-42",
            message="Please refund this order",
            requested_refund=250,
        ),
        "agentic",
    )
    gate = pending_promise(agentic, agentic_run.id, "agent_action", timeout_s=20)
    agentic.resolve(gate.id, b'{"approved":true,"reviewer":"smoke"}')
    agentic_result = terminal(agentic_run)
    assert agentic_result.status == "approved"
    assert agentic_result.proposed_action == "refund:250"

    quickstart_run = submit(
        quickstart_app,
        quickstart_checkout,
        {
            "id": f"QS-{SMOKE_ID}",
            "customer_id": "smoke-customer",
            "email": "smoke@example.com",
            "items": [{"sku": "kit", "price": 125, "qty": 1}],
        },
        "quickstart",
    )
    assert terminal(quickstart_run)["total"] == 125

    sync_run_id, sync_result = run_checkout_sync(
        example_order(175, order_id=f"QS-SYNC-{SMOKE_ID}"),
        timeout_s=30,
    )
    assert sync_run_id == f"QS-SYNC-{SMOKE_ID}"
    assert sync_result["total"] == 175

    checkout_run = submit(
        checkout_app,
        compact_checkout,
        {"id": f"ORDER-{SMOKE_ID}", "customer_id": "smoke", "total": 149},
        "checkout",
    )
    assert terminal(checkout_run)["tracking"]

    ecommerce = ecommerce_app.client
    ecommerce_run = submit(
        ecommerce_app,
        ecommerce_checkout,
        {
            "id": f"EC-{SMOKE_ID}",
            "customer_id": "smoke",
            "email": "smoke@example.com",
            "items": [{"sku": "widget", "price": 200, "qty": 1}],
        },
        "ecommerce",
    )
    pending_promise(ecommerce, ecommerce_run.id, "carrier_pickup", timeout_s=20)
    carrier_pickup(ecommerce_run.id, {"tracking": "SMOKE-PICKUP"})
    assert terminal(ecommerce_run)["status"] == "shipped"

    lending_run = submit(
        lending_app,
        lending_application,
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
    assert terminal(lending_run)["status"] == "disbursed"

    primitives = primitives_app.client
    primitives_run = submit(
        primitives_app,
        methods_tour,
        {"customer": " Smoke Customer ", "amount": 250},
        "primitives",
    )
    signal = pending_promise(primitives, primitives_run.id, "external_signal", timeout_s=20)
    primitives.resolve(signal.id, b'{"message":"smoke signal"}')
    gate = pending_promise(primitives, primitives_run.id, "manual_approval", timeout_s=20)
    primitives.resolve(gate.id, b'{"approved":true,"reviewer":"smoke"}')
    assert terminal(primitives_run)["risk"]["band"] == "low"

    trading = trading_app.client
    trading_run = submit(
        trading_app,
        trading_rebalance,
        {"portfolio": "growth", "run_id": f"trade-{SMOKE_ID}"},
        "trading",
    )
    gate = pending_promise(trading, trading_run.id, "rebalance_approval", timeout_s=20)
    trading.resolve(gate.id, b'{"approved":true,"reviewer":"smoke"}')
    trading_result = terminal(trading_run, timeout_s=60)
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

    for command, expected_paused in (("pause", True), ("resume", False)):
        subprocess.run(
            [
                sys.executable,
                "-m",
                "quickstart.schedule_admin",
                command,
                "quickstart.daily-report",
            ],
            cwd=ROOT,
            env=os.environ.copy(),
            check=True,
            capture_output=True,
            text=True,
        )
        assert base.get_schedule("quickstart.daily-report").paused is expected_paused


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

"""Run five distinct KYC checks concurrently in one sticky workflow."""

from __future__ import annotations

import argparse
import json
import os
import random
import time
from collections.abc import Mapping

import aga_runtime as aga

app = aga.App("kyc-review", concurrency=8)


def perform_check(
    application: Mapping[str, object],
    check: str,
    outcome: Mapping[str, object],
) -> dict[str, object]:
    delay_seconds = random.uniform(2, 3)
    started_ns = time.monotonic_ns()
    time.sleep(delay_seconds)
    return {
        "application_id": application["application_id"],
        "check": check,
        **outcome,
        "delay_seconds": round(delay_seconds, 3),
        "worker_pid": os.getpid(),
        "started_ns": started_ns,
        "finished_ns": time.monotonic_ns(),
    }


@app.step()
def pan_verification(application: dict[str, object]) -> dict[str, object]:
    return perform_check(application, "PAN verification", {"status": "verified"})


@app.step()
def employment_check(application: dict[str, object]) -> dict[str, object]:
    return perform_check(application, "Employment check", {"status": "active"})


@app.step()
def bureau_pull(application: dict[str, object]) -> dict[str, object]:
    return perform_check(application, "Credit bureau pull", {"score": 762})


@app.step()
def sanctions_screening(application: dict[str, object]) -> dict[str, object]:
    return perform_check(application, "Sanctions screening", {"matches": 0})


@app.step()
def bank_account_verification(application: dict[str, object]) -> dict[str, object]:
    return perform_check(application, "Bank account verification", {"status": "verified"})


@app.workflow(execution="async")
async def kyc_review(application: dict[str, object]) -> dict[str, object]:
    pan = pan_verification(application)
    employment = employment_check(application)
    bureau = bureau_pull(application)
    sanctions = sanctions_screening(application)
    bank_account = bank_account_verification(application)

    checks = await app.join(pan, employment, bureau, sanctions, bank_account)
    return {
        "application_id": application["application_id"],
        "decision": "approved",
        "checks": checks,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker", action="store_true", help="Serve the KYC workflow")
    parser.add_argument("--application-id", default="KYC-DEMO")
    args = parser.parse_args()
    try:
        if args.worker:
            app.serve()
            return

        application = {
            "application_id": args.application_id,
            "applicant": "Demo Applicant",
            "pan": "DEMO1234X",
        }
        run = app.start(kyc_review, application)
        print(f"Run ID: {run.id}", flush=True)
        print(json.dumps(run.result(timeout=60), indent=2), flush=True)
    finally:
        app.close()


if __name__ == "__main__":
    main()

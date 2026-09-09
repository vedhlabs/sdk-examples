"""Five distinct demo checks for the Inside Aga execution walkthrough.

These are simulated providers, not identity or lending decisions. Run a worker
first, then submit from another terminal. Use the same AGA_URL and AGA_NAMESPACE.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from typing import TypedDict

import aga_runtime as aga

app = aga.App(
    "inside-execution",
    namespace=os.environ.get("AGA_NAMESPACE", "default"),
    concurrency=8,
)


class Applicant(TypedDict):
    applicant_id: str


class Check(TypedDict):
    applicant_id: str
    check: str
    result: str
    worker_pid: int
    started_ns: int
    finished_ns: int


def demo_provider(applicant: Applicant, check: str) -> Check:
    """Ordinary helper called inside a Step; no real external effect."""
    started = time.monotonic_ns()
    # Long enough to observe overlap despite separate distributed-task claims.
    # Capacity permits concurrency; it does not synchronize start times.
    time.sleep(1.2)
    return {
        "applicant_id": applicant["applicant_id"],
        "check": check,
        "result": "demo-ok",
        "worker_pid": os.getpid(),
        "started_ns": started,
        "finished_ns": time.monotonic_ns(),
    }


@app.step()
def verify_pan(applicant: Applicant) -> Check:
    return demo_provider(applicant, "verify_pan")


@app.step()
def check_employment(applicant: Applicant) -> Check:
    return demo_provider(applicant, "check_employment")


@app.step()
def pull_bureau(applicant: Applicant) -> Check:
    return demo_provider(applicant, "pull_bureau")


@app.step()
def screen_sanctions(applicant: Applicant) -> Check:
    return demo_provider(applicant, "screen_sanctions")


@app.step()
def verify_bank(applicant: Applicant) -> Check:
    return demo_provider(applicant, "verify_bank")


async def checks(applicant: Applicant, parallel: bool) -> list[Check]:
    """A replay-safe helper, not a sixth durable Step or a child workflow."""
    if parallel:
        pan = verify_pan(applicant)
        employment = check_employment(applicant)
        bureau = pull_bureau(applicant)
        sanctions = screen_sanctions(applicant)
        bank = verify_bank(applicant)
        return await app.join(pan, employment, bureau, sanctions, bank)

    results = []
    results.append(await verify_pan(applicant))
    results.append(await check_employment(applicant))
    results.append(await pull_bureau(applicant))
    results.append(await screen_sanctions(applicant))
    results.append(await verify_bank(applicant))
    return results


@app.workflow(name="inside.five_sticky", execution="async")
async def sticky(applicant: Applicant, parallel: bool = False) -> list[Check]:
    return await checks(applicant, parallel)


@app.workflow(name="inside.five_distributed", execution="async_distributed")
async def distributed(applicant: Applicant, parallel: bool = False) -> list[Check]:
    return await checks(applicant, parallel)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument(
        "--worker", action="store_true", help="Serve both workflows and all five Steps"
    )
    result.add_argument("--mode", choices=("sync", "async", "async-distributed"), default="sync")
    result.add_argument(
        "--parallel", action="store_true", help="Call all five Steps before joining"
    )
    result.add_argument("--wait", action="store_true", help="Also wait in an async caller mode")
    result.add_argument(
        "--run-id", help="Optional durable root ID; use a new ID for a new experiment"
    )
    result.add_argument("--applicant-id", default="DEMO-001", help="A synthetic resource ID")
    return result


def main() -> None:
    args = parser().parse_args()
    try:
        if args.worker:
            app.serve()
            return
        workflow = distributed if args.mode == "async-distributed" else sticky
        run = app.start(
            workflow.options(
                run_id=args.run_id,
                resource=aga.ResourceRef("applicant", args.applicant_id),
            ),
            Applicant(applicant_id=args.applicant_id),
            args.parallel,
        )
        print(f"Run ID: {run.id}", flush=True)
        if args.mode == "sync" or args.wait:
            print(json.dumps(run.result(timeout=60), indent=2), flush=True)
        else:
            print(
                "Submission acknowledged; inspect this Run in the selected Namespace.", flush=True
            )
    finally:
        app.close()


if __name__ == "__main__":
    main()

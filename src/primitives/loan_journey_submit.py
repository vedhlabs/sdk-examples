"""Run five loan workflows together and open their shared Case layout."""

from __future__ import annotations

import argparse
import os
import uuid
from urllib.parse import urlencode

import aga_runtime as aga

from primitives.app import app
from primitives.loan_journey import application, approval, disbursement, kyc, underwriting


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--loan-id", default=f"LOAN-{uuid.uuid4().hex[:12]}")
    parser.add_argument("--url", default=os.getenv("AGA_URL", "http://127.0.0.1:8080"))
    args = parser.parse_args()

    loan = {"loan_id": args.loan_id, "applicant": "Demo Applicant"}
    submission = uuid.uuid4().hex[:8]
    handles = []
    for slug, workflow in (
        ("application", application),
        ("kyc", kyc),
        ("underwriting", underwriting),
        ("approval", approval),
        ("disbursement", disbursement),
    ):
        handle = app.start(
            workflow.options(
                run_id=f"loan-journey-{submission}-{slug}",
                resource=aga.ResourceRef("loan", args.loan_id),
            ),
            loan,
        )
        handles.append((slug, handle))
        print(f"{slug}: {handle.id}", flush=True)

    for slug, handle in handles:
        handle.result(timeout=60)
        print(f"{slug}: completed", flush=True)

    query = urlencode({
        "q": f"resource:loan/{args.loan_id}",
        "namespace_id": os.getenv("AGA_NAMESPACE", "default"),
    })
    print(f"{args.url.rstrip('/')}/runs?{query}")


if __name__ == "__main__":
    main()

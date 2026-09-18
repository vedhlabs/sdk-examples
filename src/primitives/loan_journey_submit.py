"""Run five separate loan workflows and open their shared resource journey."""

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
        print(f"{slug}: {handle.id}", flush=True)
        handle.result(timeout=60)

    query = urlencode({
        "kind": "loan", "id": args.loan_id,
        "namespace_id": os.getenv("AGA_NAMESPACE", "default"),
    })
    print(f"{args.url.rstrip('/')}/resources?{query}")


if __name__ == "__main__":
    main()

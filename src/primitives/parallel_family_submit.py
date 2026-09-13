"""Submit the parallel parent-and-children workflow used by the UI demo."""

from __future__ import annotations

import argparse
import hashlib
import json
import uuid

import aga_runtime as aga

from primitives.app import app
from primitives.parallel_family import parallel_family_root


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--application-id", default=f"KYC-{uuid.uuid4().hex[:12]}")
    parser.add_argument("--wait", action="store_true")
    args = parser.parse_args()

    application = {
        "application_id": args.application_id,
        "applicant": "Demo Applicant",
    }
    configured = parallel_family_root.options(
        run_id=(
            "parallel-family-"
            f"{hashlib.sha256(args.application_id.encode()).hexdigest()[:24]}"
        ),
        resource=aga.ResourceRef("kyc_application", args.application_id),
    )
    run = app.start(configured, application)
    print(f"Run ID: {run.id}", flush=True)
    if args.wait:
        print(json.dumps(run.result(timeout=60), indent=2), flush=True)


if __name__ == "__main__":
    main()


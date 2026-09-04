import argparse
import json
import uuid

from lending.app import app
from lending.workflows import application


def main() -> None:
    parser = argparse.ArgumentParser(description="Submit a lending application")
    parser.add_argument("--amount", type=int, default=100_000)
    parser.add_argument("--score", type=int, default=720)
    parser.add_argument("--wait", action="store_true")
    args = parser.parse_args()

    application_id = f"loan-{uuid.uuid4().hex[:12]}"
    request = {
        "applicant": {
            "id": application_id,
            "national_id": "TEST-001",
            "requested_score": args.score,
        },
        "amount": args.amount,
    }
    run = app.start(application.options(run_id=application_id), request)
    print(run.id)
    if args.wait:
        print(json.dumps(run.result(timeout=30), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

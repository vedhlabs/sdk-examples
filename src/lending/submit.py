import argparse
import json
import uuid

from example_support.config import decode_output
from lending.client import connect


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
    client = connect()
    run = client.submit(
        "lending.application",
        json.dumps(request).encode(),
        run_id=application_id,
        target="python://lending",
    )
    print(run.run_id)
    if args.wait:
        terminal = client.result(run.run_id, timeout_s=30)
        print(json.dumps(decode_output(terminal.output), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()


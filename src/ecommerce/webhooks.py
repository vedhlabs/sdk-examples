import argparse
import json
from datetime import datetime, timezone

from ecommerce.client import connect
from example_support.promises import pending_promise


def carrier_pickup(run_id: str, payload: dict) -> None:
    client = connect()
    pending = pending_promise(client, run_id, "carrier_pickup")
    value = {**payload, "received_at": datetime.now(timezone.utc).isoformat()}
    client.resolve(pending.id, json.dumps(value).encode())


def review_fraud(run_id: str, approved: bool, reviewer: str) -> None:
    client = connect()
    pending = pending_promise(client, run_id, "fraud_review")
    client.resolve(
        pending.id,
        json.dumps({"approved": approved, "reviewer": reviewer}).encode(),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Resolve ecommerce waits and gates")
    commands = parser.add_subparsers(dest="command", required=True)
    ship = commands.add_parser("ship")
    ship.add_argument("run_id")
    ship.add_argument("--tracking", default="LOCAL-PICKUP")
    review = commands.add_parser("review")
    review.add_argument("run_id")
    review.add_argument("decision", choices=("approve", "deny"))
    review.add_argument("--reviewer", default="local-reviewer")
    args = parser.parse_args()

    if args.command == "ship":
        carrier_pickup(args.run_id, {"tracking": args.tracking})
    else:
        review_fraud(args.run_id, args.decision == "approve", args.reviewer)


if __name__ == "__main__":
    main()


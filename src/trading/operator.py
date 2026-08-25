import argparse
import json

from example_support.promises import pending_promise
from trading.client import connect


def review(run_id: str, approved: bool, reviewer: str) -> None:
    client = connect()
    gate = pending_promise(client, run_id, "rebalance_approval")
    client.resolve(
        gate.id,
        json.dumps({"approved": approved, "reviewer": reviewer}).encode(),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Resolve a portfolio rebalance gate")
    parser.add_argument("decision", choices=("approve", "deny"))
    parser.add_argument("run_id")
    parser.add_argument("--reviewer", default="local-pm")
    args = parser.parse_args()
    review(args.run_id, args.decision == "approve", args.reviewer)


if __name__ == "__main__":
    main()


import argparse
import json

from example_support.promises import pending_promise
from lending.client import connect


def decide(run_id: str, approved: bool, underwriter: str) -> None:
    client = connect()
    gate = pending_promise(client, run_id, "manual_underwriting")
    client.resolve(
        gate.id,
        json.dumps({"approved": approved, "by": underwriter}).encode(),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Resolve a manual underwriting gate")
    parser.add_argument("decision", choices=("approve", "deny"))
    parser.add_argument("run_id")
    parser.add_argument("--underwriter", default="local-underwriter")
    args = parser.parse_args()
    decide(args.run_id, args.decision == "approve", args.underwriter)


if __name__ == "__main__":
    main()


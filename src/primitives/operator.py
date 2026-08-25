import argparse
import json

from example_support.promises import pending_promise
from primitives.client import connect


def signal(run_id: str, message: str) -> None:
    client = connect()
    pending = pending_promise(client, run_id, "external_signal")
    client.resolve(pending.id, json.dumps({"message": message}).encode())


def approve(run_id: str, reviewer: str) -> None:
    client = connect()
    pending = pending_promise(client, run_id, "manual_approval")
    client.resolve(pending.id, json.dumps({"approved": True, "reviewer": reviewer}).encode())


def main() -> None:
    parser = argparse.ArgumentParser(description="Resolve the tour's external boundaries")
    commands = parser.add_subparsers(dest="command", required=True)
    send = commands.add_parser("signal")
    send.add_argument("run_id")
    send.add_argument("--message", default="provider callback received")
    review = commands.add_parser("approve")
    review.add_argument("run_id")
    review.add_argument("--reviewer", default="local-operator")
    args = parser.parse_args()
    if args.command == "signal":
        signal(args.run_id, args.message)
    else:
        approve(args.run_id, args.reviewer)


if __name__ == "__main__":
    main()


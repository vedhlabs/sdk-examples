from __future__ import annotations

import argparse
import json
import uuid

from agentic.types import Ticket
from agentic.workflows import resolve_ticket


def main() -> None:
    parser = argparse.ArgumentParser(description="Submit the opaque support-agent example")
    parser.add_argument("--ticket-id", default=f"ticket-{uuid.uuid4().hex[:8]}")
    parser.add_argument("--customer", default="customer-42")
    parser.add_argument("--message", default="Where is my order?")
    parser.add_argument("--refund", type=int, default=0)
    parser.add_argument("--wait", action="store_true")
    args = parser.parse_args()

    ticket = Ticket(args.ticket_id, args.customer, args.message, args.refund)
    run = resolve_ticket.options(run_id=args.ticket_id).start(ticket)
    print(json.dumps({"run_id": run.id, "state": "submitted"}, sort_keys=True))
    if args.wait:
        print(json.dumps(run.result(timeout=120).__dict__, sort_keys=True))


if __name__ == "__main__":
    main()

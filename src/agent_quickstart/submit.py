"""Submit an Agent Run; optionally keep this caller waiting for the answer."""

import argparse
import os
import uuid

from agent_quickstart.app import app
from agent_quickstart.workflows import investigate, place_order


def main() -> None:
    parser = argparse.ArgumentParser(description="Submit the Strands Agent workflow")
    parser.add_argument("question", nargs="?", default="What makes a workflow durable?")
    parser.add_argument(
        "--checkout",
        type=int,
        metavar="AMOUNT",
        help="instead of a research question, run the checkout agent, whose "
        "charge_card tool holds a durable receipt; AMOUNT is in minor units",
    )
    parser.add_argument(
        "--bedrock",
        action="store_true",
        help="submit the opt-in Bedrock research workflow; requires the Bedrock worker",
    )
    parser.add_argument(
        "--wait",
        action="store_true",
        help="wait in this caller; the workflow itself is unchanged",
    )
    parser.add_argument(
        "--order-id",
        help="stable business order ID for --checkout; generated when omitted",
    )
    args = parser.parse_args()

    if args.bedrock and args.checkout is not None:
        parser.error("--bedrock and --checkout are separate examples")
    if args.bedrock:
        if args.order_id:
            parser.error("--order-id requires --checkout")
        if os.environ.get("AGA_AGENT_BEDROCK") != "1":
            parser.error("set AGA_AGENT_BEDROCK=1 in both the worker and caller")
        from agent_quickstart.bedrock_workflows import investigate_bedrock

        run = app.start(investigate_bedrock, args.question)
    elif args.checkout is not None:
        order_id = args.order_id or f"order-{uuid.uuid4().hex}"
        run = app.start(place_order, order_id, args.checkout)
    else:
        if args.order_id:
            parser.error("--order-id requires --checkout")
        run = app.start(investigate, args.question)
    print(f"Run ID: {run.id}")
    if args.wait:
        print(run.result(timeout=120 if args.bedrock else 30))


if __name__ == "__main__":
    main()

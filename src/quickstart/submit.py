import argparse
import json
import uuid

from quickstart.sync_client import run_checkout_sync
from quickstart.workflows import checkout


def main() -> None:
    parser = argparse.ArgumentParser(description="Submit the quickstart checkout workflow")
    parser.add_argument("--amount", type=int, default=125)
    parser.add_argument(
        "--wait",
        action="store_true",
        help="block this caller for the result (client behavior, not an execution mode)",
    )
    args = parser.parse_args()

    order_id = f"QS-{uuid.uuid4().hex[:12]}"
    order = {
        "id": order_id,
        "customer_id": "CUS-QUICKSTART",
        "email": "buyer@example.com",
        "items": [{"sku": "starter-kit", "price": args.amount, "qty": 1}],
    }
    if args.wait:
        run_id, output = run_checkout_sync(order)
        print(run_id)
        print(json.dumps(output, indent=2, sort_keys=True))
        return

    run = checkout.options(run_id=order_id).start(order)
    print(run.id)


if __name__ == "__main__":
    main()

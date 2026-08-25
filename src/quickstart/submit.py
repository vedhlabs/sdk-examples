import argparse
import json
import uuid

from example_support.config import decode_output
from quickstart.client import connect


def main() -> None:
    parser = argparse.ArgumentParser(description="Submit the quickstart checkout workflow")
    parser.add_argument("--amount", type=int, default=125)
    parser.add_argument("--wait", action="store_true", help="wait for and print the result")
    args = parser.parse_args()

    order_id = f"QS-{uuid.uuid4().hex[:12]}"
    order = {
        "id": order_id,
        "customer_id": "CUS-QUICKSTART",
        "email": "buyer@example.com",
        "items": [{"sku": "starter-kit", "price": args.amount, "qty": 1}],
    }
    client = connect()
    run = client.submit(
        "quickstart.checkout",
        json.dumps(order).encode(),
        run_id=order_id,
        target="python://quickstart",
    )
    print(run.run_id)
    if args.wait:
        terminal = client.result(run.run_id, timeout_s=30)
        print(json.dumps(decode_output(terminal.output), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()


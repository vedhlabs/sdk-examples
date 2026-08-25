import argparse
import json
import uuid

from ecommerce.client import connect


def main() -> None:
    parser = argparse.ArgumentParser(description="Submit an ecommerce checkout")
    parser.add_argument("--amount", type=int, default=200)
    args = parser.parse_args()

    order = {
        "id": f"ORD-{uuid.uuid4().hex[:12]}",
        "customer_id": "CUS-1",
        "email": "buyer@example.com",
        "items": [{"sku": "widget", "price": args.amount, "qty": 1}],
    }
    run = connect().submit(
        "ecommerce.checkout",
        json.dumps(order).encode(),
        run_id=order["id"],
        target="python://ecommerce",
    )
    print(run.run_id)


if __name__ == "__main__":
    main()


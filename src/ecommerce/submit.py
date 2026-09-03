import argparse
import uuid

from ecommerce.app import app
from ecommerce.workflow import checkout


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
    run = app.start(checkout.options(run_id=order["id"]), order)
    print(run.id)


if __name__ == "__main__":
    main()

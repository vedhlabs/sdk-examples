import json
import uuid

from example_support.config import connect


def main() -> None:
    order_id = f"ORDER-{uuid.uuid4().hex[:12]}"
    order = {"id": order_id, "customer_id": "CUS-1", "total": 149}
    run = connect("checkout-dev").submit(
        "checkout",
        json.dumps(order).encode(),
        run_id=order_id,
        target="python://checkout",
    )
    print(run.run_id)


if __name__ == "__main__":
    main()


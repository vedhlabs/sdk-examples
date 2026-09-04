import uuid

from checkout.workflows import checkout


def main() -> None:
    order_id = f"ORDER-{uuid.uuid4().hex[:12]}"
    order = {"id": order_id, "customer_id": "CUS-1", "total": 149}
    run = checkout.options(run_id=order_id).start(order)
    print(run.id)


if __name__ == "__main__":
    main()

import argparse
import json
import uuid

from primitives.client import connect


def main() -> None:
    parser = argparse.ArgumentParser(description="Submit the nine-method tour")
    parser.add_argument("--amount", type=int, default=250)
    args = parser.parse_args()
    run_id = f"primitive-{uuid.uuid4().hex[:12]}"
    request = {"customer": " Example Customer ", "amount": args.amount}
    run = connect().submit(
        "primitives.tour",
        json.dumps(request).encode(),
        run_id=run_id,
        target="python://primitives",
    )
    print(run.run_id)


if __name__ == "__main__":
    main()


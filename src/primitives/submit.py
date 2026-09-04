import argparse
import uuid

from primitives.methods import methods_tour


def main() -> None:
    parser = argparse.ArgumentParser(description="Submit the nine-method tour")
    parser.add_argument("--amount", type=int, default=250)
    args = parser.parse_args()
    run_id = f"primitive-{uuid.uuid4().hex[:12]}"
    request = {"customer": " Example Customer ", "amount": args.amount}
    run = methods_tour.options(run_id=run_id).start(request)
    print(run.id)


if __name__ == "__main__":
    main()

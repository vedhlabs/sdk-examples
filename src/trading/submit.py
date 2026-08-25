import argparse
import json
from datetime import date

from trading.client import connect


def main() -> None:
    parser = argparse.ArgumentParser(description="Submit one portfolio rebalance")
    parser.add_argument("portfolio", choices=("growth", "income"))
    parser.add_argument("--date", default=date.today().isoformat())
    args = parser.parse_args()

    run_id = f"{args.date}-{args.portfolio}"
    run = connect().submit(
        "trading.rebalance",
        json.dumps({"portfolio": args.portfolio, "run_id": run_id}).encode(),
        run_id=run_id,
        target="python://trading",
    )
    print(run.run_id)


if __name__ == "__main__":
    main()


import argparse
from datetime import date

from trading.workflows import trading_rebalance


def main() -> None:
    parser = argparse.ArgumentParser(description="Submit one portfolio rebalance")
    parser.add_argument("portfolio", choices=("growth", "income"))
    parser.add_argument("--date", default=date.today().isoformat())
    args = parser.parse_args()

    run_id = f"{args.date}-{args.portfolio}"
    run = trading_rebalance.options(run_id=run_id).start(
        {"portfolio": args.portfolio, "run_id": run_id},
    )
    print(run.id)


if __name__ == "__main__":
    main()

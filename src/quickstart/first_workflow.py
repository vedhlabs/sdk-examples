import argparse

import aga_runtime as aga

app = aga.App("first-workflow")


@app.step()
def calculate_total(prices: list[int]) -> int:
    if not prices or any(price < 0 for price in prices):
        raise ValueError("Provide at least one price, with no negative amounts")
    return sum(prices)


@app.step()
def make_summary(total: int) -> str:
    return f"Order total: {total} cents"


@app.workflow()
async def checkout(prices: list[int]) -> str:
    total = await calculate_total(prices)
    return await make_summary(total)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run your first Aga workflow")
    parser.add_argument("--worker", action="store_true", help="Serve workflow runs")
    args = parser.parse_args()
    try:
        if args.worker:
            app.serve()
        else:
            run = app.start(checkout, [200, 150])
            print(f"Run ID: {run.id}", flush=True)
            print(run.result(timeout=30))
    finally:
        app.close()


if __name__ == "__main__":
    main()

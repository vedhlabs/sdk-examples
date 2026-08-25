import ogha

from trading import steps, workflows  # noqa: F401
from trading.client import connect


def main() -> None:
    ogha.Worker(
        connect(),
        target="python://trading",
        concurrency=16,
        service="trading",
    ).run()


if __name__ == "__main__":
    main()


import ogha

from lending import workflows  # noqa: F401
from lending.client import connect


def main() -> None:
    ogha.Worker(
        connect(),
        target="python://lending",
        concurrency=16,
        service="lending",
    ).run()


if __name__ == "__main__":
    main()


import ogha

from primitives import methods  # noqa: F401
from primitives.client import connect


def main() -> None:
    ogha.Worker(
        connect(),
        target="python://primitives",
        concurrency=8,
        service="primitives",
    ).run()


if __name__ == "__main__":
    main()


import ogha

from ecommerce import workflow  # noqa: F401
from ecommerce.client import connect


def main() -> None:
    ogha.Worker(
        connect(),
        target="python://ecommerce",
        concurrency=8,
        service="ecommerce",
    ).run()


if __name__ == "__main__":
    main()


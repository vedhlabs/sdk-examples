import ogha

from example_support.config import connect
from reports import workflows  # noqa: F401


def main() -> None:
    ogha.Worker(connect("reports-dev"), target="python://reports", service="reports").run()


if __name__ == "__main__":
    main()


import ogha

from checkout import workflows  # noqa: F401
from example_support.config import connect


def main() -> None:
    ogha.Worker(connect("checkout-dev"), target="python://checkout", service="checkout").run()


if __name__ == "__main__":
    main()


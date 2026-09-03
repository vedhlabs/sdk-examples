from ecommerce import workflow  # noqa: F401
from ecommerce.app import app


def main() -> None:
    app.serve()


if __name__ == "__main__":
    main()

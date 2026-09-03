from checkout import workflows  # noqa: F401
from checkout.app import app


def main() -> None:
    app.serve()


if __name__ == "__main__":
    main()

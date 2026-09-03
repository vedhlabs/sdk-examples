from lending import workflows  # noqa: F401
from lending.app import app


def main() -> None:
    app.serve()


if __name__ == "__main__":
    main()

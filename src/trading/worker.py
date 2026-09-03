from trading import steps, workflows  # noqa: F401
from trading.app import app


def main() -> None:
    app.serve()


if __name__ == "__main__":
    main()

from primitives import methods  # noqa: F401
from primitives.app import app


def main() -> None:
    app.serve()


if __name__ == "__main__":
    main()

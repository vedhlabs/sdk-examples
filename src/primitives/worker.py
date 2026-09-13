from primitives import family, methods, parallel_family  # noqa: F401
from primitives.app import app


def main() -> None:
    app.serve()


if __name__ == "__main__":
    main()

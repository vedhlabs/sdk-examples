from agentic import workflows  # noqa: F401
from agentic.app import app


def main() -> None:
    app.serve()


if __name__ == "__main__":
    main()

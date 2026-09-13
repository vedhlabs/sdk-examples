"""Serve the deterministic Agent workflow."""

from agent_quickstart import workflows as workflows  # noqa: F401
from agent_quickstart.app import app


def main() -> None:
    app.serve()


if __name__ == "__main__":
    main()

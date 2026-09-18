"""Serve the deterministic Agent workflow."""

import os

from agent_quickstart import workflows as workflows  # noqa: F401
from agent_quickstart.app import app

if os.environ.get("AGA_AGENT_BEDROCK") == "1":
    from agent_quickstart import bedrock_workflows as bedrock_workflows  # noqa: F401


def main() -> None:
    app.serve()


if __name__ == "__main__":
    main()

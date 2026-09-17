"""Run the example worker with ``python -m agent_pattern.worker``."""

from agent_pattern.app import app
from agent_pattern.workflows import review_case  # noqa: F401 - registers the Workflow


def main() -> None:
    try:
        app.serve()
    finally:
        app.close()


if __name__ == "__main__":
    main()

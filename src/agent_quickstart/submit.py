"""Submit an Agent Run; optionally keep this caller waiting for the answer."""

import argparse

from agent_quickstart.app import app
from agent_quickstart.workflows import investigate


def main() -> None:
    parser = argparse.ArgumentParser(description="Submit the Strands Agent workflow")
    parser.add_argument("question", nargs="?", default="What makes a workflow durable?")
    parser.add_argument(
        "--wait",
        action="store_true",
        help="wait in this caller; the workflow itself is unchanged",
    )
    args = parser.parse_args()

    run = app.start(investigate, args.question)
    print(f"Run ID: {run.id}")
    if args.wait:
        print(run.result(timeout=30))


if __name__ == "__main__":
    main()

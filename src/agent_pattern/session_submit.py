"""Submit the bounded logical-session example."""

import argparse
import uuid

from agent_pattern.app import app
from agent_pattern.session_workflow import research_session


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a continued Aga agent session")
    parser.add_argument("topic", nargs="?", default="durable agents")
    parser.add_argument("--turns", type=int, default=6)
    parser.add_argument("--turns-per-generation", type=int, default=2)
    parser.add_argument("--session-id", default=f"conversation-{uuid.uuid4().hex[:12]}")
    parser.add_argument("--wait", action="store_true")
    args = parser.parse_args()

    configured = research_session.options(
        run_id=f"agent-session-{uuid.uuid4().hex}",
        session_id=args.session_id,
    )
    handle = app.start(
        configured,
        {
            "topic": args.topic,
            "turn": 0,
            "max_turns": args.turns,
            "turns_per_generation": args.turns_per_generation,
            "segment": 1,
            "recent_summaries": [],
        },
    )
    print(f"Session: {args.session_id}")
    print(f"Initial Run: {handle.id}")
    if args.wait:
        print(handle.result(timeout=120))


if __name__ == "__main__":
    main()

"""Start the mailbox-driven session with ``python -m agent_pattern.mailbox_submit``."""

from __future__ import annotations

import argparse
import uuid

from agent_pattern.app import app
from agent_pattern.command_session import command_session


def main() -> None:
    parser = argparse.ArgumentParser(description="Start one mailbox-driven Aga agent session")
    parser.add_argument("--session-id", default=f"agent-{uuid.uuid4().hex[:12]}")
    parser.add_argument("--commands-per-generation", type=int, default=4)
    parser.add_argument("--command-timeout", type=float, default=3600)
    parser.add_argument("--wait", action="store_true")
    args = parser.parse_args()

    handle = app.start(
        command_session.options(
            run_id=f"agent-command-{uuid.uuid4().hex[:12]}",
            session_id=args.session_id,
        ),
        {
            "handled": 0,
            "generation": 1,
            "commands_per_generation": args.commands_per_generation,
            "command_timeout": args.command_timeout,
            "recent_results": [],
        },
    )
    print(f"Session: {args.session_id}")
    print(f"Initial Run: {handle.id}")
    if args.wait:
        print(handle.result(timeout=args.command_timeout + 30))


if __name__ == "__main__":
    main()

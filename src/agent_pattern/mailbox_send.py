"""Send a command with ``python -m agent_pattern.mailbox_send SESSION TEXT``."""

from __future__ import annotations

import argparse
import uuid

from agent_pattern.control_plane import ControlPlane


def main() -> None:
    parser = argparse.ArgumentParser(description="Send one revision-fenced session command")
    parser.add_argument("session_id")
    parser.add_argument("text", nargs="?", default="")
    parser.add_argument("--kind", choices=("message", "stop"), default="message")
    parser.add_argument("--command-id", default=f"cmd-{uuid.uuid4().hex[:12]}")
    args = parser.parse_args()
    if args.kind == "message" and not args.text.strip():
        parser.error("text is required for a message command")

    payload = {"text": args.text} if args.kind == "message" else None
    response = ControlPlane().send_command(
        args.session_id,
        command_id=args.command_id,
        kind=args.kind,
        payload=payload,
    )
    command = response["command"]
    print(
        f"Command {command['command_id']} is {command['state']} "
        f"at mailbox revision {command['revision']}"
    )


if __name__ == "__main__":
    main()

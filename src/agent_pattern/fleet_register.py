"""Register desired state with ``python -m agent_pattern.fleet_register``."""

from __future__ import annotations

import argparse
import os

from agent_pattern.control_plane import ControlPlane


def main() -> None:
    parser = argparse.ArgumentParser(description="Register desired state for the example agent")
    parser.add_argument("--replicas", type=int, default=1)
    parser.add_argument("--concurrency", type=int, default=4)
    args = parser.parse_args()
    release = os.getenv("AGA_RELEASE", "mailbox-example-v1")
    manifest = os.getenv("AGA_MANIFEST_DIGEST", "sha256:mailbox-example-v1")
    admin_key = os.getenv("AGA_ADMIN_KEY", os.getenv("AGA_API_KEY", ""))
    response = ControlPlane(api_key=admin_key).register_agent(
        agent_id="agent-pattern",
        display_name="Mailbox agent",
        target="python://agent-pattern",
        release=release,
        manifest_digest=manifest,
        desired_replicas=args.replicas,
        concurrency=args.concurrency,
    )
    agent = response["agent"]
    print(f"Agent {agent['agent_id']} desired state is revision {agent['revision']}")


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import json

from agentic.app import app
from example_support.promises import pending_promise


def main() -> None:
    parser = argparse.ArgumentParser(description="Resolve the agent action approval")
    parser.add_argument("run_id")
    parser.add_argument("decision", choices=("approve", "reject"))
    parser.add_argument("--reviewer", default="local-reviewer")
    args = parser.parse_args()

    gate = pending_promise(app.client, args.run_id, "agent_action", timeout_s=20)
    decision = {
        "approved": args.decision == "approve",
        "reviewer": args.reviewer,
    }
    app.client.resolve(gate.id, json.dumps(decision, sort_keys=True).encode())
    print(json.dumps({"promise_id": gate.id, **decision}, sort_keys=True))


if __name__ == "__main__":
    main()

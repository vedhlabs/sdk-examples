"""Opt-in local PostgreSQL smoke for parallel checks and approval-before-effect.

Set AGA_URL, AGA_NAMESPACE, AGA_API_KEY (worker) and AGA_APPROVER_KEY for an
isolated authenticated Aga server. It uses a temporary provider store and
makes no paid model call.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path


def launch_worker(output: object) -> subprocess.Popen[bytes]:
    return subprocess.Popen(
        [sys.executable, "-m", "agent_pattern.worker"],
        stdout=output,
        stderr=subprocess.STDOUT,
        env=os.environ.copy(),
    )


def stop_worker(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def main() -> None:
    required = ("AGA_URL", "AGA_NAMESPACE", "AGA_API_KEY", "AGA_APPROVER_KEY")
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        raise RuntimeError(f"set {', '.join(missing)} for an authenticated Aga server")

    with tempfile.TemporaryDirectory(prefix="aga-agent-pattern-") as temporary:
        os.environ["AGA_EXAMPLE_STATE"] = str(Path(temporary) / "provider.sqlite3")

        from aga_runtime import ApprovalOutcome
        from aga_runtime.client import Client

        from agent_pattern.app import app
        from agent_pattern.provider import SCOPE
        from agent_pattern.workflows import review_case
        from example_support.config import connect
        from example_support.promises import pending_promise
        from example_support.store import store

        client = connect()
        approver = Client(
            os.environ["AGA_URL"], namespace=os.environ["AGA_NAMESPACE"],
            api_key=os.environ["AGA_APPROVER_KEY"],
        )
        with tempfile.TemporaryFile(mode="w+") as output:
            process = launch_worker(output)
            try:
                case_id = f"clear-{uuid.uuid4().hex[:10]}"
                case = {"case_id": case_id}
                run_id = f"agent-case-{uuid.uuid4().hex[:12]}"
                approved = app.start(review_case.options(run_id=run_id), case)
                gate = pending_promise(client, approved.id, "case_publish_approval", timeout_s=30)
                key = f"case:{case_id}:decision:clear:v1"
                assert store.effect(SCOPE, key) is None, "provider mutated before approval"
                question = approver.gates.get(gate.id)
                approver.gates.decide(
                    question, ApprovalOutcome.APPROVED, command_id=f"{run_id}-approve"
                )
                approver.gates.decide(
                    question, ApprovalOutcome.APPROVED, command_id=f"{run_id}-approve"
                )
                result = approved.result(timeout=30)
                assert result["status"] == "published", result
                assert store.effect_calls(SCOPE, key) == 1

                blocked_id = f"blocked-{uuid.uuid4().hex[:10]}"
                blocked = app.start(
                    review_case,
                    {"case_id": blocked_id, "watchlist_hit": True},
                )
                assert blocked.result(timeout=30)["status"] == "blocked"
                assert store.effect(SCOPE, f"case:{blocked_id}:decision:clear:v1") is None

                denied_id = f"denied-{uuid.uuid4().hex[:10]}"
                denied = app.start(review_case, {"case_id": denied_id})
                denied_gate = pending_promise(
                    client, denied.id, "case_publish_approval", timeout_s=30
                )
                approver.gates.decide(
                    approver.gates.get(denied_gate.id), ApprovalOutcome.REJECTED,
                    command_id=f"{denied.id}-reject",
                )
                assert denied.result(timeout=30)["status"] == "not_approved"
                assert store.effect(SCOPE, f"case:{denied_id}:decision:clear:v1") is None

                expired_id = f"expired-{uuid.uuid4().hex[:10]}"
                expired = app.start(
                    review_case,
                    {"case_id": expired_id, "approval_timeout": 0.4},
                )
                assert expired.result(timeout=30)["status"] == "not_approved"
                assert store.effect(SCOPE, f"case:{expired_id}:decision:clear:v1") is None

                stop_worker(process)
                process = launch_worker(output)
                repeated = app.start(review_case.options(run_id=run_id), case)
                assert repeated.result(timeout=30) == result
                assert store.effect_calls(SCOPE, key) == 1
                print(
                    f"PASS namespace={os.environ['AGA_NAMESPACE']} approved={approved.id} "
                    f"blocked={blocked.id} denied={denied.id} expired={expired.id} "
                    "provider_calls=1"
                )
            except BaseException:
                output.seek(0)
                print(output.read(), file=sys.stderr)
                raise
            finally:
                stop_worker(process)
                app.close()
                approver.close()
                client.close()


if __name__ == "__main__":
    main()

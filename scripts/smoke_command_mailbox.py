"""Exercise mailbox delivery, worker restart, continuation, and fleet drift."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
import uuid


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


def wait_until(description: str, predicate, *, timeout: float = 30) -> object:
    deadline = time.monotonic() + timeout
    last = None
    while time.monotonic() < deadline:
        last = predicate()
        if last:
            return last
        time.sleep(0.1)
    raise TimeoutError(f"timed out waiting for {description}; last observation: {last!r}")


def main() -> None:
    os.environ.setdefault("AGA_RELEASE", "mailbox-example-v1")
    os.environ.setdefault("AGA_MANIFEST_DIGEST", "sha256:mailbox-example-v1")
    os.environ.setdefault("AGA_URL", "http://localhost:8080")

    from example_support.config import create_namespace

    if not os.getenv("AGA_NAMESPACE"):
        suffix = uuid.uuid4().hex[:8]
        os.environ["AGA_NAMESPACE"] = create_namespace(f"Command mailbox smoke {suffix}")

    from agent_pattern.app import app
    from agent_pattern.command_session import command_session
    from agent_pattern.control_plane import ControlPlane

    session_id = f"mailbox-{uuid.uuid4().hex[:12]}"
    operator = ControlPlane()
    admin = ControlPlane(api_key=os.getenv("AGA_ADMIN_KEY", os.getenv("AGA_API_KEY", "")))
    admin.register_agent(
        agent_id="agent-pattern",
        display_name="Mailbox agent",
        target="python://agent-pattern",
        release=os.environ["AGA_RELEASE"],
        manifest_digest=os.environ["AGA_MANIFEST_DIGEST"],
        desired_replicas=1,
        concurrency=4,
    )

    with tempfile.TemporaryFile(mode="w+") as output:
        process = launch_worker(output)
        try:
            handle = app.start(
                command_session.options(
                    run_id=f"mailbox-run-{uuid.uuid4().hex[:12]}",
                    session_id=session_id,
                ),
                {
                    "handled": 0,
                    "generation": 1,
                    "commands_per_generation": 1,
                    "command_timeout": 120,
                    "recent_results": [],
                },
            )

            def session_at_least(generation: int):
                sessions = operator.sessions(agent_id="agent-pattern")["sessions"]
                return next(
                    (
                        session
                        for session in sessions
                        if session["session_id"] == session_id
                        and session["generation"] >= generation
                    ),
                    None,
                )

            wait_until("first session generation", lambda: session_at_least(1))
            first = operator.send_command(
                session_id,
                command_id="message-1",
                kind="message",
                payload={"text": "first command"},
            )["command"]
            assert first["revision"] == 1
            wait_until("second session generation", lambda: session_at_least(2))

            # The second generation is parked in app.command. Submit while its
            # worker is absent; restart must replay this exact command rather than
            # dequeue a different one.
            time.sleep(0.25)
            stop_worker(process)
            second = operator.send_command(
                session_id,
                command_id="message-2",
                kind="message",
                payload={"text": "survive a worker restart"},
            )["command"]
            process = launch_worker(output)
            wait_until("third session generation", lambda: session_at_least(3))

            stop = operator.send_command(
                session_id,
                command_id="stop-3",
                kind="stop",
                payload=None,
            )["command"]
            result = handle.result(timeout=30)
            commands = operator.session_commands(session_id)["commands"]
            assert [item["revision"] for item in commands] == [1, 2, 3]
            assert all(item["state"] == "delivered" for item in commands)
            assert result["handled"] == 2 and result["generations"] == 3
            assert second["revision"] == 2 and stop["revision"] == 3

            fleet = admin.agents()["agents"]
            row = next(
                item
                for item in fleet
                if item["deployment"]["agent_id"] == "agent-pattern"
            )
            assert row["observed"]["replicas"] >= 1
            assert row["observed"]["release_drift"] == 0
            assert row["observed"]["manifest_drift"] == 0
            print(
                f"PASS namespace={os.environ['AGA_NAMESPACE']} session={session_id} "
                f"generations={result['generations']} commands={len(commands)}"
            )
        except BaseException:
            output.seek(0)
            print(output.read(), file=sys.stderr)
            raise
        finally:
            stop_worker(process)
            app.close()


if __name__ == "__main__":
    main()

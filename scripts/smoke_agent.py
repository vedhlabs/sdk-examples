"""Run both caller experiences through a real Aga server and local Strands model."""

import os
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@contextmanager
def worker(environment: dict[str, str]):
    with tempfile.TemporaryFile(mode="w+") as log:
        process = subprocess.Popen(
            [sys.executable, "-m", "agent_quickstart.worker"],
            cwd=ROOT,
            env=environment,
            stdout=log,
            stderr=subprocess.STDOUT,
        )
        try:
            yield process
        except BaseException:
            log.seek(0)
            print(log.read(), file=sys.stderr)
            raise
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


def main() -> None:
    os.environ.setdefault("AGA_URL", "http://127.0.0.1:8080")
    namespace = os.environ.get("AGA_AGENT_SMOKE_NAMESPACE", "default")
    os.environ["AGA_NAMESPACE"] = namespace
    from agent_quickstart.app import app
    from agent_quickstart.workflows import investigate

    try:
        with worker(os.environ.copy()):
            async_run = app.start(investigate, "Explain an asynchronous caller")
            assert async_run.id
            sync_answer = app.start(
                investigate, "Explain a synchronous caller"
            ).result(timeout=30)
            async_answer = async_run.result(timeout=30)
            assert sync_answer == "Local research complete: Explain a synchronous caller"
            assert async_answer == "Local research complete: Explain an asynchronous caller"
            print(f"Sync and async callers passed in Namespace {namespace}")
    finally:
        app.close()


if __name__ == "__main__":
    main()

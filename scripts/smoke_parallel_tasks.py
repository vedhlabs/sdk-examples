"""Verify SDK caller modes and actual same-worker task overlap."""

import json
import os
import subprocess
import sys
import uuid

from smoke_first_workflow import ROOT, worker


def main() -> None:
    namespace = f"parallel-tasks-smoke-{uuid.uuid4().hex[:10]}"
    os.environ["AGA_NAMESPACE"] = namespace
    os.environ.setdefault("AGA_URL", "http://127.0.0.1:8080")
    from quickstart.parallel_tasks import app, distributed_checks, sticky_checks

    try:
        with worker("quickstart.parallel_tasks", os.environ.copy()) as process:
            for name, workflow in (("sticky", sticky_checks), ("distributed", distributed_checks)):
                run = app.start(workflow, f"order-{name}")
                result = run.result(timeout=60)
                stock, shipping = result["stock"], result["shipping"]
                assert stock["worker_pid"] == shipping["worker_pid"] == process.pid
                assert stock["order_id"] == shipping["order_id"] == f"order-{name}"
                overlaps = max(stock["started_ns"], shipping["started_ns"]) < min(
                    stock["finished_ns"], shipping["finished_ns"],
                )
                assert overlaps, (name, result)
                print(f"{name}: {run.id}; overlap={overlaps}", flush=True)

            for mode in ("sync", "async", "async_distributed"):
                command = subprocess.run(
                    [sys.executable, "-m", "quickstart.parallel_tasks", "--mode", mode,
                     "--order-id", f"cli-{mode}"],
                    cwd=ROOT, env=os.environ.copy(), text=True, capture_output=True,
                    timeout=70, check=True,
                )
                lines = command.stdout.splitlines()
                assert lines[0].startswith("Run ID: "), command.stdout
                if mode == "sync":
                    result = json.loads("\n".join(lines[1:]))
                    assert result["stock"]["order_id"] == "cli-sync"
                else:
                    assert len(lines) == 1, command.stdout
                print(f"CLI {mode}: {lines[0]}", flush=True)

            # CLI --wait works independently of distributed placement.
            waited = subprocess.run(
                [sys.executable, "-m", "quickstart.parallel_tasks", "--mode",
                 "async_distributed", "--wait"],
                cwd=ROOT, env=os.environ.copy(), text=True, capture_output=True,
                timeout=70, check=True,
            )
            assert '"shipping"' in waited.stdout, waited.stdout
            print("CLI distributed --wait: result returned", flush=True)
    finally:
        app.close()
    print(f"Passed. Retained scope: default / {namespace}")


if __name__ == "__main__":
    main()

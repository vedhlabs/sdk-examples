"""Exercise both full SDK-guide files against a running tutorial server."""

import os
import subprocess
import sys
import tempfile
import uuid
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@contextmanager
def worker(module, env):
    with tempfile.TemporaryFile(mode="w+") as log:
        process = subprocess.Popen(
            [sys.executable, "-m", module, "--worker"],
            cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT,
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


def main():
    namespace = f"first-workflow-smoke-{uuid.uuid4().hex[:10]}"
    os.environ["AGA_NAMESPACE"] = namespace
    os.environ.setdefault("AGA_URL", "http://127.0.0.1:8080")
    from quickstart.first_workflow import app, checkout

    try:
        pending = app.start(checkout, [200, 150])
        assert not pending.done(), "No worker should exist in this new namespace"
        print(f"Submitted without a worker: {pending.id}", flush=True)
        with worker("quickstart.first_workflow", os.environ.copy()):
            assert pending.result(timeout=30) == "Order total: 350 cents"
            print("Pending run completed after worker startup", flush=True)
            command = subprocess.run(
                [sys.executable, "-m", "quickstart.first_workflow"],
                cwd=ROOT, env=os.environ.copy(), text=True, capture_output=True,
                timeout=40, check=True,
            )
            assert "Order total: 350 cents" in command.stdout
            print(command.stdout.strip(), flush=True)
            invalid = app.start(checkout, [-1])
            try:
                invalid.result(timeout=30)
            except Exception as error:
                assert "negative" in str(error), str(error)
            else:
                raise AssertionError("Negative prices must fail")
            print("Invalid input produced a workflow failure", flush=True)
    finally:
        app.close()

    with tempfile.TemporaryDirectory(prefix="aga-checkout-guide-") as temp:
        env = dict(os.environ, AGA_NAMESPACE=f"{namespace}-full")
        env["AGA_EXAMPLE_STATE"] = str(Path(temp) / "providers.sqlite3")
        with worker("quickstart.checkout_app", env):
            command = subprocess.run(
                [sys.executable, "-m", "quickstart.checkout_app"],
                cwd=ROOT, env=env, text=True, capture_output=True, timeout=70,
                check=True,
            )
            assert "ORDER-42" in command.stdout
            assert "tracking" in command.stdout
            assert "charge_id" in command.stdout
            print(f"Full checkout: {command.stdout.strip()}", flush=True)
    print(f"Both guide examples passed; scopes: {namespace}, {namespace}-full")


if __name__ == "__main__":
    main()

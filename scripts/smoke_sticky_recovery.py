"""Kill a worker after a committed concurrent prefix, then recover the same Run."""

import os
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

import aga_runtime as aga


def definitions(directory: Path):
    app = aga.App("sticky-recovery", concurrency=2, lease_ttl_ms=2000)

    @app.step()
    def prefix(number: int) -> int:
        with (directory / f"prefix-{number}").open("a") as log:
            log.write("executed\n")
        time.sleep(0.1)
        return number

    @app.step()
    def tail() -> str:
        (directory / "tail-started").touch()
        deadline = time.monotonic() + 45
        while not (directory / "release").exists():
            if time.monotonic() > deadline:
                raise TimeoutError("recovery driver did not release the tail")
            time.sleep(0.02)
        return "recovered"

    @app.workflow()
    async def workflow() -> str:
        values = await aga.join(prefix(1), prefix(2))
        # event flushes the completed prefix through the existing root fence.
        aga.event("prefix-complete", values)
        return await tail()

    return app, workflow


def launch(directory: Path, log):
    return subprocess.Popen(
        [sys.executable, __file__, "--worker", str(directory)],
        stdout=log, stderr=subprocess.STDOUT, env=os.environ.copy(),
    )


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "--worker":
        app, _ = definitions(Path(sys.argv[2]))
        try:
            app.serve()
        finally:
            app.close()
        return
    namespace = f"sticky-recovery-{uuid.uuid4().hex[:10]}"
    os.environ["AGA_NAMESPACE"] = namespace
    with tempfile.TemporaryDirectory(prefix="aga-recovery-") as temporary:
        directory = Path(temporary)
        with tempfile.TemporaryFile(mode="w+") as log:
            app, workflow = definitions(directory)
            process = launch(directory, log)
            try:
                run = app.start(workflow)
                deadline = time.monotonic() + 30
                while not (directory / "tail-started").exists():
                    assert process.poll() is None, "worker exited before checkpoint"
                    assert time.monotonic() < deadline, "worker never reached tail"
                    time.sleep(0.05)
                process.kill()
                process.wait(5)
                (directory / "release").touch()
                process = launch(directory, log)
                assert run.result(timeout=45) == "recovered"
                for number in (1, 2):
                    assert (directory / f"prefix-{number}").read_text() == "executed\n"
                print(f"Recovered {run.id}; concurrent prefix ran once; scope {namespace}")
            except BaseException:
                log.seek(0)
                print(log.read(), file=sys.stderr)
                raise
            finally:
                process.terminate()
                try:
                    process.wait(5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(5)
                app.close()


if __name__ == "__main__":
    main()

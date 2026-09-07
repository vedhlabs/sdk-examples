# Your first Aga workflow

This is the small example at the start of the [Python SDK guide](https://coding2fun.in/aga/python).
It adds two prices and returns a summary. It doesn't charge a card or contact
an external service; the point is to see a real workflow run through Aga.

Read the workflow from top to bottom: calculate the total, then make the summary.
The App connects to Aga, the step decorators mark work whose results can be saved,
and the workflow decorator marks the function that puts those steps in order.

Canonical source: [first_workflow.py](../src/quickstart/first_workflow.py).

```python
import argparse
import time

import aga_runtime as aga

app = aga.App("first-workflow")


@app.step()
def calculate_total(prices: list[int]) -> int:
    if not prices or any(price < 0 for price in prices):
        raise ValueError("Provide at least one price, with no negative amounts")
    time.sleep(2)
    return sum(prices)


@app.step()
def make_summary(total: int) -> str:
    time.sleep(1)
    return f"Order total: {total} cents"


@app.workflow()
async def checkout(prices: list[int]) -> str:
    total = await calculate_total(prices)
    return await make_summary(total)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run your first Aga workflow")
    parser.add_argument("--worker", action="store_true", help="Serve workflow runs")
    args = parser.parse_args()
    try:
        if args.worker:
            app.serve()
        else:
            run = app.start(checkout, [200, 150])
            print(f"Run ID: {run.id}", flush=True)
            print(run.result(timeout=30))
    finally:
        app.close()


if __name__ == "__main__":
    main()
```

### Install the example

The two-second and one-second pauses above only simulate slow service work.
They block inside these demo steps; use `aga.sleep` for a durable workflow wait
that releases worker capacity.

You'll need Python 3.11, Git, and Docker with Compose running. Check with
`python3.11 --version` before starting (or use your newer Python interpreter).
The commands below use macOS or Linux. On Windows, run them in WSL with Docker
Desktop's WSL integration enabled; these are not PowerShell commands.

```bash
git clone https://github.com/vedhlabs/sdk-examples.git
cd sdk-examples
python3.11 -m venv .venv
source .venv/bin/activate
python -m ensurepip --upgrade
python -m pip install --upgrade pip
python -m pip install -e .
docker compose -f compose.tutorial.yml up -d
```

Stay in the `sdk-examples` directory for the remaining commands. The virtual
environment keeps the example's Python packages separate from your other projects.
The install adds both the example modules and Aga SDK 0.4.1 or later in the 0.4 line.

This Compose file downloads Aga server 0.2.1 and starts PostgreSQL for it.
It doesn't build source or need a private-module token. Open
[http://127.0.0.1:8080](http://127.0.0.1:8080) and wait for the dashboard to load
before starting Python.

This is a **local-only** setup: authentication is disabled, the server port binds
to your computer's loopback address, and PostgreSQL is not exposed to the host.
It is not a production deployment recipe.

### Updating an existing example installation

From your `sdk-examples` checkout:

```bash
git pull --ff-only
source .venv/bin/activate
python -m ensurepip --upgrade
python -m pip install --upgrade -e .
docker compose -f compose.tutorial.yml pull
docker compose -f compose.tutorial.yml up -d
```

Stop old Python workers with Ctrl+C and restart them. The new SDK code only takes
effect after a worker restart. The server update preserves the database volume;
don't remove it if you want to keep workflow history.

### Terminal 1: start a worker

A worker is a Python process that runs the workflow's functions. Keep this
terminal open:

```bash
source .venv/bin/activate
export AGA_URL=http://127.0.0.1:8080
export AGA_NAMESPACE=first-workflow
python -m quickstart.first_workflow --worker
```

`app.serve()` connects this worker to Aga and makes its workflow available.
The process stays running; it is waiting for work, not stuck.

### Terminal 2: start an order

Open another terminal, go to the **same `sdk-examples` directory**, then run:

```bash
source .venv/bin/activate
export AGA_URL=http://127.0.0.1:8080
export AGA_NAMESPACE=first-workflow
python -m quickstart.first_workflow
```

The result should look like this; your run ID will be different:

```text
Run ID: <generated run ID>
Order total: 350 cents
```

In the dashboard, choose scope `default / first-workflow`, open **Runs**, and
select the printed ID. You should find a completed `checkout` with
`calculate_total` and `make_summary` results.

Run the submission command again to create another run. This example lets Aga
generate an ID each time. Later, use a stable business ID when repeated submissions
should refer to the same order.

### If you don't get a result

| What you see | What to check |
| :--- | :--- |
| `No module named pip` | Run `python -m ensurepip --upgrade`, then `python -m pip install -e .`. If `ensurepip` is unavailable and you have `uv`, use `uv pip install --python .venv/bin/python -e .`. |
| `No module named quickstart` | Activate this repository's virtual environment and run `python -m pip install -e .`. |
| Connection refused or no dashboard | Run `docker compose -f compose.tutorial.yml ps`, then `docker compose -f compose.tutorial.yml logs aga`. Docker must be running. |
| A run ID prints, then the caller times out | Keep Terminal 1 running. Both terminals must use the same URL, namespace, and source file. |
| No run in the dashboard | Select `default / first-workflow` and search for the printed ID. |
| Port 8080 is already in use | Start Compose with `AGA_TUTORIAL_PORT=8088 docker compose -f compose.tutorial.yml up -d`, then use port 8088 in both terminals and the browser. |

The caller waits up to 30 seconds in this example. A caller timeout doesn't cancel
the run: start the missing worker and inspect that original run in the dashboard.
Running the submission command again creates a different run.

To stop, press Ctrl+C in the worker terminal, then run
`docker compose -f compose.tutorial.yml down`. This keeps the database volume
and its run history. No database deletion is needed.


## What to try next

Try [two tasks and worker capacity](parallel-tasks.md) to compare caller waiting,
sticky placement and distributed overlap without creating child workflows.

Use [the longer checkout](../src/quickstart/checkout_app.py) to study parallel
quotes, approval, child workflows, and a schedule. It uses this repository's
local provider adapters. Its optional high-value branch also requires a separate
risk service; the default order does not take that branch.

With the tutorial server running, stop the first worker, then use
`python -m quickstart.checkout_app --worker` and
`python -m quickstart.checkout_app` in the two terminals. This starts an
engine-managed daily schedule as well as registering the workflow. For experiments,
keep this in the tutorial stack, not a production namespace.

The longer example uses fixed run ID `ORDER-42`; repeating its command refers
to the same run. Change the order ID for a new order or changed input.

The [crash-recovery walkthrough](quickstart.md#prove-crash-recovery) is a separate
exercise. The two-step introduction demonstrates submission and execution, not
every failure guarantee. Local work since the last saved checkpoint can repeat
after a crash. Real payments and other external changes need safe retry handling.

## Check this guide after an edit

With the tutorial server running and the virtual environment active:

```bash
python -m pip install -e ".[dev]"
make check
make smoke-first
```

`smoke-first` checks delayed worker startup, the small example's actual CLI,
invalid-input failure, and the full checkout's default path. It creates fresh
test namespaces and stops the workers it started. It does not delete run history
or exercise the optional external risk service.

When editing the blog checkout, also run `python scripts/check_sdk_guide.py
/path/to/coding2fun.github.io/src/pages/aga/python.md` to check both full code
samples against their source files before publishing.

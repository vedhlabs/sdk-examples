# Two checks, one workflow

A checkout needs stock availability and a shipping quote. Neither answer depends
on the other. Start both durable step calls, then join their Handles. These are
two tasks inside one Run, not two child workflows.

The runnable file is [parallel_tasks.py](../src/quickstart/parallel_tasks.py).
It uses SDK 0.4.2. Install the release and restart your Python worker:

```bash
python -m pip install --upgrade "aga-runtime==0.4.2"
```

Its two steps simulate service calls with two-second pauses; no external account
or API key is needed. The tutorial Compose file uses Aga server 0.2.1.

## What does `concurrency=8` mean?

`app = aga.App("parallel-tasks", concurrency=8)` gives this App's worker process
up to eight slots for claimed tasks. All workflow turns and independently
dispatched steps share that capacity. A separate worker-owned pool runs up to
eight sticky-local functions across those turns. Parents do not occupy that
pool while waiting, so even `concurrency=1` makes progress. Each turn admits at
most eight outstanding local calls before applying backpressure. The default is four.

This is not eight tasks per workflow, eight CPU cores, or a cluster-wide limit.
Two such worker processes provide up to sixteen configured claim slots together;
actual utilization depends on matching work and available resources. A caller
that only submits work does not start a worker pool. `app.serve()` starts it.
Durable suspension returns a slot after the active workflow turn finishes. A
blocking call inside a step keeps its execution slot occupied. A timed-out
blocking function may continue running, so this is not a hard limit on every
underlying thread or external request. Add separate resource limits where needed.

Call both steps before awaiting to allow concurrency in either placement.
Sticky runs execute them in the same worker process; distributed runs dispatch
them as separate leased tasks. There is no new task-spawn method to learn.
This is bounded thread-backed concurrency, not a guarantee of CPU parallelism.

## Run it

First complete [the installation and server setup](first-workflow.md#install-the-example).
Run these commands from `sdk-examples` with that virtual environment active.

Worker terminal:

```bash
source .venv/bin/activate
export AGA_URL=http://127.0.0.1:8080
export AGA_NAMESPACE=parallel-tasks
python -m quickstart.parallel_tasks --worker
```

In a second terminal, enter the same repository directory and activate the same
environment and namespace:

```bash
source .venv/bin/activate
export AGA_URL=http://127.0.0.1:8080
export AGA_NAMESPACE=parallel-tasks

# Sync: caller waits; independent sticky steps can overlap.
python -m quickstart.parallel_tasks --mode sync

# Async sticky: caller prints the Run ID and exits; the same steps can overlap.
python -m quickstart.parallel_tasks --mode async

# Async distributed: submit both checks for independent execution.
python -m quickstart.parallel_tasks --mode async_distributed
```

For the last two commands, inspect the result in the dashboard or add `--wait`
to the command to print it. Waiting does not change placement:

```bash
python -m quickstart.parallel_tasks --mode async_distributed --wait
```

Every submission generates a new Run ID. `--order-id` changes the business input;
this example does not use it as a submission idempotency key.

Open [the dashboard](http://127.0.0.1:8080), select `default / parallel-tasks`,
and find the printed Run ID. Both checks appear under the same Run. With one
worker, the returned `started_ns` / `finished_ns` intervals can show overlap.
These monotonic values are demo diagnostics: compare them only in this single
worker process, not across hosts or restarts, and never use them for workflow
decisions. Total Run time includes dispatch and persistence, not just the pauses.
Queue polling and load can still delay execution; this is not a guarantee of
immediate starts. Sticky calls execute on a bounded local pool; checkpoint writes
remain serialized on the workflow thread. Only committed results survive a crash;
uncommitted effects can repeat and must be safe to retry. Cancellation skips work
that has not started but cannot forcibly interrupt a running Python function.

To make work sequential, await the first step before calling the second.
To wait for all already-started work, use `await app.join(...)`; its full-join
results follow the input Handle order. Increasing `concurrency` alone does not
make a sequential workflow parallel. Unfinished owned work is joined before
the workflow completes; returning early is not a way to detach a task.

Stop this worker with Ctrl+C. To stop the tutorial server without deleting
history, run `docker compose -f compose.tutorial.yml down`.

## Verification

```bash
python -m pytest tests/test_parallel_tasks.py
python scripts/smoke_parallel_tasks.py
python scripts/smoke_sticky_recovery.py
```

The smoke check uses its own namespace and one worker process. It verifies
sticky and distributed overlap, all three CLI modes and final
outputs. It terminates only its own worker, leaving run history in place.
The recovery check kills its own worker after committing two concurrent results,
starts a replacement, and verifies that the committed prefix does not run again.

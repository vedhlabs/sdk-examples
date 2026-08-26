# Quickstart, synchronous waiting, crash recovery, and schedules

This guide backs the Python SDK page. It starts with one checkout and then exposes the two cases
that are easy to describe but important to see: a process dying in the middle of a step, and a cron
schedule that belongs to the engine rather than the worker.

## Mental model

```mermaid
sequenceDiagram
    participant S as submit.py
    participant E as Ogha engine
    participant W as worker.py
    participant P as local provider
    S->>E: submit quickstart.checkout
    E->>W: acquire durable task
    W->>P: reserve / charge with stable keys
    P-->>W: first result or same result on retry
    W->>E: checkpoint result
    E-->>S: terminal run
```

The engine remembers workflow progress. The provider remembers effect identity. Both are needed:
the engine cannot know whether a remote payment committed when a worker disappeared before
receiving its response.

## Run the basic workflow

```bash
docker compose up -d
python -m quickstart.worker
```

In another terminal:

```bash
python -m quickstart.sync_client
```

Expected result: one `quickstart.checkout` run reaches `COMPLETED`; its output contains the order,
reservation, charge, and receipt IDs. Re-run the command to create a new business order.

## Synchronous caller versus asynchronous submission

Ogha has two worker-placement modes: `async_sticky` and `async_distributed`. Synchronous waiting is
an independent client choice, not a third mode. The dedicated client makes that boundary visible:

```python
submitted = client.submit(
    "quickstart.checkout",
    json.dumps(order).encode(),
    run_id=order["id"],
    target="python://quickstart",
)
terminal = client.result(submitted.run_id, timeout_s=30)
```

The first call records the run and returns its ID. The second call waits for that same run to become
terminal. If the waiting process is killed, the engine and worker continue because neither the run
nor its lease belongs to the client connection.

```mermaid
sequenceDiagram
    participant C as sync_client.py
    participant E as Ogha engine
    participant W as async-sticky worker
    C->>E: submit(run_id)
    E-->>C: accepted run
    E->>W: execute root task
    loop client-side wait
        C->>E: status(run_id)
        E-->>C: running
    end
    W->>E: fulfill root task
    C->>E: status(run_id)
    E-->>C: completed output
```

Run both caller styles against the same worker:

```bash
python -m quickstart.submit       # returns the run ID immediately
python -m quickstart.sync_client  # waits and prints the decoded result
python -m quickstart.submit --wait  # compact equivalent of the second command
```

The synchronous helper also checks the terminal state. A failed or canceled workflow becomes an
application error instead of being mistaken for a successful empty response. Its timeout limits how
long this caller waits; it does not cancel the durable run.

Canonical files:

- [`src/quickstart/client.py`](../src/quickstart/client.py)
- [`src/quickstart/workflows.py`](../src/quickstart/workflows.py)
- [`src/quickstart/worker.py`](../src/quickstart/worker.py)
- [`src/quickstart/submit.py`](../src/quickstart/submit.py)
- [`src/quickstart/sync_client.py`](../src/quickstart/sync_client.py)

## Prove crash recovery

1. Stop the regular quickstart worker.
2. Start `python -m quickstart.crash_worker`.
3. Submit `quickstart.crash-recovery` with the short Python command below.
4. When `audit.log` contains `START`, kill the worker process with `kill -9`.
5. Start `python -m quickstart.crash_worker` again.

```bash
python - <<'PY'
import json, uuid
from quickstart.client import connect

run_id = f"crash-{uuid.uuid4().hex[:12]}"
order = {"id": run_id, "items": [{"sku": "demo", "price": 1, "qty": 1}]}
connect().submit(
    "quickstart.crash-recovery",
    json.dumps(order).encode(),
    run_id=run_id,
    target="python://quickstart",
)
print(run_id)
PY
```

`START` can appear twice. That is the honest failure window: the file write happened, but the
worker died before Ogha knew the step finished. A production provider operation must use the same
stable key on the retry. The inventory adapter in this example does exactly that.

Canonical files: [`crash_workflow.py`](../src/quickstart/crash_workflow.py) and
[`crash_worker.py`](../src/quickstart/crash_worker.py).

## Operate the schedule

Importing `quickstart.schedules` registers `quickstart.daily-report`. Worker startup converges that
declaration into the engine.

```bash
python -m quickstart.schedule_admin list
python -m quickstart.schedule_admin pause quickstart.daily-report
python -m quickstart.schedule_admin resume quickstart.daily-report
```

Every edit reads the current revision and writes `revision + 1`. That makes competing deployments
converge forward instead of overwriting a newer declaration with an older one.

## Common failures

- A run remains pending with no worker: the submit target and worker target differ.
- A schedule is absent: the module containing `@ogha.scheduled` was never imported by a worker.
- An effect appears twice: the external adapter did not implement a stable idempotency key.
- A workflow changes behavior after restart: it read time, randomness, environment, or network I/O
  in the workflow body instead of a recorded step.

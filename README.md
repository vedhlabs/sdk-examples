# Aga Python SDK examples

This repository is the runnable companion to the [Aga documentation](https://coding2fun.in/aga).
Every Python source file shown on the product, SDK, order, lending, and trading pages lives here as
working code. The examples use the real Aga SDK and engine. Local adapters simulate payment,
inventory, compliance, lending, and brokerage systems so no paid account or cloud credential is
required.

## Start here

Requirements: Python 3.10+, Docker with Compose, sibling `aga` and `sdk-python`
checkouts, and a `GITHUB_TOKEN` that can read the private Aga Go modules.

```bash
git clone https://github.com/vedhlabs/sdk-examples.git
cd sdk-examples
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ../sdk-python
python -m pip install -e ".[dev]" --no-deps
docker compose up -d
```

The Compose project builds the current sibling Aga engine locally. It does not
depend on an unpublished container tag.

Open [http://localhost:8080](http://localhost:8080) for the Aga dashboard. Then run the
quickstart in two terminals:

```bash
# terminal 1
python -m quickstart.worker

# terminal 2
python -m quickstart.sync_client
```

The `quickstart.app` object owns registration, the engine connection, and the worker lifecycle.
The synchronous caller uses
`app.start(checkout.options(run_id=order["id"]), order).result()` and
receives an ordinary Python value. The run still executes durably in the worker and survives if
the caller disconnects.

## The durable-promise mental model

Every durable function call immediately returns an awaitable handle. Aga stores the identified
operation and, after it commits a terminal result, replay reads that result instead of executing the
function again. In short: **call returns a promise; Aga stores the promise; recovery reuses its
committed value**.

That model explains the API, but it is not the whole distributed-systems contract. Work that never
committed may retry; task leases and fencing reject stale workers; durable waits need persisted
wake-up registration; and an external payment or email still needs provider idempotency or
reconciliation.

## Sync, Async, and Async Distributed

These are three user experiences over two independent choices:

| Experience | Example | What changes |
| :--- | :--- | :--- |
| **Sync** | `app.start(checkout.options(run_id=order["id"]), order).result()` | The caller waits for the typed result. |
| **Async** | `app.start(checkout.options(run_id=order["id"]), order)` | The caller receives a durable `Handle` immediately; `execution="async"` uses sticky placement. |
| **Async Distributed** | `app.start(distributed_checkout.options(run_id=order["id"]), order)` | The caller receives a `Handle`; `execution="async_distributed"` lets steps dispatch independently. |

Try the first two against the same quickstart workflow:

```bash
# Background/API submission: print the run ID and return immediately.
python -m quickstart.submit

# Request/response submission: block this process until the run is terminal.
python -m quickstart.sync_client

# The compact submitter supports the same waiting behavior as a flag.
python -m quickstart.submit --wait
```

All three commands submit the same durable `quickstart.checkout` workflow. “Synchronous” only means
the caller waits. Public workflow placement is `async` (the sticky default) or
`async_distributed`; there is no `execution="sync"` workflow mode. Ecommerce, lending,
primitives, and trading demonstrate distributed placement.

`app.start(workflow, ...)` is also the only way to create a child Run inside a workflow. The App
uses the active execution scope to distinguish a root from an owned child; an unfinished owned
child is joined automatically. Use immutable `workflow.options(detached=True)` only when that
child must outlive its parent.

> **Breaking SDK candidate.** These examples target the unpublished Python 0.4 candidate. It removes
> 0.3 aliases such as bare decorators, `.run()`, direct child Workflow calls, `.detach()`,
> `gather/race/quorum`, `approval()`, and `scheduled_time()`. Install the sibling SDK checkout as
> shown above. Do not mix 0.3 and 0.4 workers on a target with active Runs.

## Examples

| Guide                                     | Package               | What it demonstrates                                                                                    |
| :---------------------------------------- | :-------------------- | :------------------------------------------------------------------------------------------------------ |
| [Quickstart](docs/quickstart.md)          | `quickstart`          | sync waiting, async submit, workflow placement, crash recovery, schedules                               |
| [Checkout and reports](docs/checkout.md)  | `checkout`, `reports` | provider idempotency, compensation shape, engine cron                                                   |
| [Order workflow](docs/ecommerce.md)       | `ecommerce`           | fan-out, quorum, cancel, approval, webhook signal, sleep, event                                         |
| [Lending](docs/lending.md)                | `lending`             | composed stages, KYC, bureau quorum, approval, disbursement, detached child Runs                         |
| [Trading](docs/trading.md)                | `trading`             | scheduled rebalance, drift, risk, approval, order identity, reconciliation                              |
| [Compact App surface](docs/primitives.md) | `primitives`          | direct calls, remote calls, child workflows, join, sleep, signal, approval policy, event, cancel         |

Use `python -m <package>.<command> --help` for command options. All examples read:

- `AGA_URL`, default `http://localhost:8080`
- `AGA_NAMESPACE`, default `default`
- `AGA_EXAMPLE_STATE`, default `.state/examples.sqlite3`

## External effects and retries

Aga guarantees durable progress. A committed durable call result is reused during replay. It
cannot atomically combine its PostgreSQL commit with an
unrelated payment, email, treasury, or broker API. If a worker loses the response after the
provider accepted a request, that step can run again. Every effectful mock in this repository
therefore accepts a stable business idempotency key and returns the original result on retry.
Production adapters must use the same provider-side capability or an application-owned inbox,
outbox, or reconciliation design.

`client.apply_once(...)` is useful as an Aga-side admission marker. It is not, by itself, an
atomic exactly-once wrapper around a separate network request.

## Verification

```bash
make check       # lint, unit tests, source coverage checks
make smoke       # end-to-end runs against the local engine
```

`make smoke` starts temporary workers, submits representative workflows, resolves their pending
external waits, and checks terminal outputs. It does not reset PostgreSQL. Use
`docker compose down -v` only when you intentionally want a new local database.

## Optional Alpaca paper adapter

Trading uses a deterministic local broker by default. To use Alpaca paper trading:

```bash
python -m pip install -e ".[alpaca]"
export TRADING_BROKER=alpaca
export ALPACA_KEY_ID=...
export ALPACA_SECRET=...
python -m trading.worker
```

Paper trading still represents an external financial effect. Read [the trading guide](docs/trading.md)
before enabling it.

## Coverage contract

[docs/COVERAGE.md](docs/COVERAGE.md) maps every Aga documentation page to its canonical source
files. `tests/test_documentation_coverage.py` checks that every mapped path exists and contains no
placeholder bodies or ellipses.

## License

Apache License 2.0. See [LICENSE](LICENSE).

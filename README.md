# Ogha Python SDK examples

This repository is the runnable companion to the [Ogha documentation](https://coding2fun.in/ogha).
Every Python source file shown on the product, SDK, order, lending, and trading pages lives here as
working code. The examples use the real Ogha SDK and engine. Local adapters simulate payment,
inventory, compliance, lending, and brokerage systems so no paid account or cloud credential is
required.

## Start here

Requirements: Python 3.10+, Docker, and Docker Compose.

```bash
git clone https://github.com/vedhlabs/sdk-examples.git
cd sdk-examples
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
docker compose up -d
```

Open [http://localhost:8080](http://localhost:8080) for the Ogha dashboard. Then run the
quickstart in two terminals:

```bash
# terminal 1
python -m quickstart.worker

# terminal 2
python -m quickstart.submit --wait
```

The worker imports the workflow definitions, listens on `python://quickstart`, and executes work.
The submitter sends one JSON input to the engine and, with `--wait`, prints the terminal result.

## Examples

| Guide | Package | What it demonstrates |
| :--- | :--- | :--- |
| [Quickstart](docs/quickstart.md) | `quickstart` | steps, workflow, worker, submit, crash recovery, schedules |
| [Checkout and reports](docs/checkout.md) | `checkout`, `reports` | provider idempotency, compensation shape, engine cron |
| [Order workflow](docs/ecommerce.md) | `ecommerce` | fan-out, quorum, cancel, gate, webhook wait, sleep, emit |
| [Lending](docs/lending.md) | `lending` | composed stages, KYC, bureau quorum, approval, disbursement, spawn |
| [Trading](docs/trading.md) | `trading` | scheduled rebalance, drift, risk, approval, order identity, reconciliation |
| [Nine methods](docs/primitives.md) | `primitives` | `call`, `rpc`, `spawn`, `join`, `sleep`, `wait`, `gate`, `emit`, `cancel` |

Use `python -m <package>.<command> --help` for command options. All examples read:

- `OGHA_URL`, default `http://localhost:8080`
- `OGHA_NAMESPACE`, default `default`
- `OGHA_EXAMPLE_STATE`, default `.state/examples.sqlite3`

## External effects and retries

Ogha guarantees durable progress. It cannot atomically combine its PostgreSQL commit with an
unrelated payment, email, treasury, or broker API. If a worker loses the response after the
provider accepted a request, that step can run again. Every effectful mock in this repository
therefore accepts a stable business idempotency key and returns the original result on retry.
Production adapters must use the same provider-side capability or an application-owned inbox,
outbox, or reconciliation design.

`client.apply_once(...)` is useful as an Ogha-side admission marker. It is not, by itself, an
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

[docs/COVERAGE.md](docs/COVERAGE.md) maps every Ogha documentation page to its canonical source
files. `tests/test_documentation_coverage.py` checks that every mapped path exists and contains no
placeholder bodies or ellipses.

## License

Apache License 2.0. See [LICENSE](LICENSE).


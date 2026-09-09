# Five checks, one KYC workflow

A loan application needs several independent answers before it can move forward.
PAN verification does not need to wait for the credit bureau, and sanctions
screening does not need to wait for employment. Start all five durable calls,
then join their Handles once.

The runnable source is [kyc_parallel.py](../src/quickstart/kyc_parallel.py). It
uses five distinct `@app.step()` functions so the dashboard names the real
business boundaries:

1. `pan_verification`
2. `employment_check`
3. `bureau_pull`
4. `sanctions_screening`
5. `bank_account_verification`

Each Step waits for a random two to three seconds to simulate an external KYC
provider. That randomness affects only demo latency inside the durable Step; the
workflow makes no decision from it. Once a result commits, replay reuses it.

## Run it

Complete [the installation and server setup](first-workflow.md#install-the-example),
then use two terminals from the `sdk-examples` directory.

Worker terminal:

```bash
source .venv/bin/activate
export AGA_URL=http://127.0.0.1:8080
export AGA_NAMESPACE=default
python -m quickstart.kyc_parallel --worker
```

Caller terminal:

```bash
source .venv/bin/activate
export AGA_URL=http://127.0.0.1:8080
export AGA_NAMESPACE=default
python -m quickstart.kyc_parallel --application-id KYC-SYNC-5-CHECKS
```

This is the synchronous caller experience: `app.start(...)` creates the durable
Run, and `.result()` waits for its final value. The workflow declaration uses
`execution="async"` for sticky placement; there is no `execution="sync"` mode.

Inside the workflow, all five direct calls happen before one `app.join(...)`.
They are Steps in the same Run, not child workflows, so no spawn operation is
needed. `concurrency=8` leaves enough local execution capacity for all five.

Open [the dashboard](http://127.0.0.1:8080), select **Default**, and open the
printed Run ID. The operation list
shows all five names. Expand **Advanced diagnostics** to see their overlapping
waterfall bars and select any row to inspect its input and output.

The total Run duration includes dispatch and persistence. It should be near the
longest simulated check rather than the sum of all five, but this example does
not promise a latency SLA. Threads help blocking and I/O work overlap; they do
not guarantee CPU parallelism. Real KYC adapters must also define retry,
idempotency, privacy, and reconciliation behavior.

## Verify it

```bash
python -m pytest tests/test_kyc_parallel.py
make smoke-kyc
```

The smoke check creates an isolated Namespace, uses the local PostgreSQL server
and SDK candidate, and proves all five measured intervals overlap in one worker process. It
stops only its own temporary worker and preserves the completed Run for inspection.

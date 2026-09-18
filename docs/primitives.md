# The compact App surface, running together

`primitives.tour` deliberately exercises the ordinary App-owned workflow surface in one short run.
Application code uses durable function objects and control helpers directly.

| Method | Line of business meaning in this tour |
| :--- | :--- |
| `step(...)` | normalize input and request provider quotes as direct typed calls |
| `remote(...)` | invoke `risk.score` across a service boundary |
| `app.start(child_workflow, ...)` | eagerly start an owned child Run |
| `join(..., count=...)` | await all, the first, or a threshold of handles |
| `sleep` | park for one second without a worker |
| `signal` | await an external system callback |
| `app.signal(aga.Approval(...))` | require an operator decision that denies on silence |
| `event` | write a milestone to the run timeline |
| `cancel` | stop the quote that lost the race |

## Run it

```bash
# terminal 1
python -m primitives.worker

# terminal 2
RUN_ID=$(python -m primitives.submit --amount 250)
python -m primitives.operator signal "$RUN_ID"
python -m primitives.operator approve "$RUN_ID"
```

The App name `primitives` makes its worker listen on both `python://primitives` and
`rpc://primitives`. The typed `@app.remote("primitives", name="risk.score")` declaration routes to
the ordinary `@app.step(name="risk.score")` registered in that serving process.

```mermaid
sequenceDiagram
    participant W as workflow
    participant R as rpc://primitives
    participant C as child run
    participant O as outside operator
    W->>R: risk.score
    R-->>W: recorded score
    W->>C: app.start primitives.child
    W->>W: quote race, cancel loser, sleep
    W-->>O: pending external_signal
    O->>W: resolve signal
    W-->>O: pending manual_approval
    O->>W: approve
```

Canonical source: [`src/primitives/methods.py`](../src/primitives/methods.py).

## Trace one nested execution family

`primitives.family.root` records one typed `order` resource and demonstrates a
four-level execution family. The root performs four durable steps and its fifth
operation starts `loop`. That child performs three loop steps and its fourth
operation starts `fulfilment`. `fulfilment` performs four steps and its fifth
operation starts `finalize`, which performs three final steps. The resource is
declared once on the root and inherited automatically through every nested Run.

```bash
python -m primitives.family_submit --order-id ORDER-42 --wait
```

Open any Run in the dashboard to see the retained workflow tree. Select a workflow
to see its own ordered operations, inspect each operation's input and output, or
open the child directly from the exact spawn row. Breadcrumbs make every ancestor
reachable even when the family is deeply nested. Searching for
`resource:order/ORDER-42` finds the whole family without scanning input JSON.

Canonical source: [`src/primitives/family.py`](../src/primitives/family.py).

## See three child Workflows run together

`primitives.parallel-family.root` starts three owned children before it waits:
identity, employment, and financial checks. Each child also starts two distinct
Steps before joining them. The result is one parent, three direct children, and
six overlapping functions on the execution-family waterfall.

```bash
python -m primitives.parallel_family_submit --application-id KYC-PARALLEL-DEMO --wait
```

Open the printed root Run in **Missions**. The tree shows all three children at
the same depth. Switch the family view to **Timeline** to compare their real
start times and function durations. Selecting any operation opens its recorded
input and output without leaving the family.

Canonical source:
[`src/primitives/parallel_family.py`](../src/primitives/parallel_family.py).

## See five separate workflows for one loan

This local-only fixture starts application, KYC, underwriting, approval, and
disbursement as **five independent root Runs**, in sequence. Each root declares
the same `ResourceRef("loan", loan_id)`. Underwriting also starts one real owned
document-check child. The shared loan ID groups the roots for inspection; it
does not create a parent edge between them or enforce their business ordering.
The functions return illustrative values and do not contact a bureau, approval
service, or payment provider.

```bash
# terminal 1: keep the primitive worker running
python -m primitives.worker

# terminal 2: from the sdk-examples directory
python -m primitives.loan_journey_submit --loan-id LOAN-DEMO-42
```

The submitter prints the five Run IDs and a link to the resource Journey. Open
that link in the dashboard's selected Namespace. Click any of the five lanes
to inspect its steps; the document-check lane is indented beneath underwriting
because it has a recorded spawn edge. On a non-default local server, set
`AGA_URL` for both terminals; the submitter uses it in the printed link.

Canonical source: [`src/primitives/loan_journey.py`](../src/primitives/loan_journey.py)
and [`src/primitives/loan_journey_submit.py`](../src/primitives/loan_journey_submit.py).

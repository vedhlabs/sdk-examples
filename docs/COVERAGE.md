# Documentation coverage

The public docs and this repository have one ownership rule: prose may summarize, but runnable
Python lives here. Every real source-file label in the six Aga pages links to a file in this repo.

| Public page    | Runnable packages                     | Verification                                                                                |
| :------------- | :------------------------------------ | :------------------------------------------------------------------------------------------ |
| Product page   | `checkout`, `reports`                 | import tests, provider idempotency tests, schedule registration                             |
| Python SDK     | `quickstart`, `primitives`            | first_workflow.py and checkout_app.py are full-page examples; unit tests, source parity, live execution |
| Use-case index | all guides                            | path coverage test                                                                          |
| Order workflow | `ecommerce`                           | domain adapter tests and smoke with webhook resolution                                      |
| Lending        | `lending`                             | decision tests and smoke through automatic approval                                         |
| Trading        | `trading`                             | decimal math, mock broker identity, approval and reconciliation smoke                       |

[`coverage.json`](coverage.json) is the machine-readable contract. The docs build is separately
checked after links are updated so a renamed file cannot leave a plausible-looking dead example.

The quickstart’s `sync_client.py` is deliberately classified as a caller example. It uses
`app.start(workflow.options(...), ...).result()`: waiting is caller behavior and does not introduce
an `execution="sync"` workflow declaration. The asynchronous client uses the same `app.start(...)`
operation and receives a `Handle` immediately.

`parallel_tasks.py` demonstrates the same distinction plus two calls followed by
one join. SDK 0.4.1 supports actual sticky and distributed overlap in one worker
process. Its walkthrough uses the published package and checks both caller styles.

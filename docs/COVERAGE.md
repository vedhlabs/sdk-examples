# Documentation coverage

The public docs and this repository have one ownership rule: prose may summarize, but runnable
Python lives here. Every real source-file label in the six Ogha pages links to a file in this repo.

| Public page    | Runnable packages                     | Verification                                                                                |
| :------------- | :------------------------------------ | :------------------------------------------------------------------------------------------ |
| Product page   | `checkout`, `reports`                 | import tests, provider idempotency tests, schedule registration                             |
| Python SDK     | `quickstart`, `primitives`            | sync/async callers, compact controls, unit tests, and end-to-end smoke                     |
| Use-case index | all guides                            | path coverage test                                                                          |
| Order workflow | `ecommerce`                           | domain adapter tests and smoke with webhook resolution                                      |
| Lending        | `lending`                             | decision tests and smoke through automatic approval                                         |
| Trading        | `trading`                             | decimal math, mock broker identity, approval and reconciliation smoke                       |
| Future research | `agentic`                            | credential-free opaque-adapter experiment retained as regression evidence in the smoke       |

[`coverage.json`](coverage.json) is the machine-readable contract. The docs build is separately
checked after links are updated so a renamed file cannot leave a plausible-looking dead example.

The quickstart’s `sync_client.py` is deliberately classified as a caller example. It uses
`workflow.options(...).run(...)`: waiting is caller behavior and does not introduce an
`execution="sync"` workflow declaration. The asynchronous client uses `start(...)` and receives a
`RunHandle` immediately.

The deferred `agentic` research package is deliberately credential-free and explicitly opaque. Its outer operation's
committed result is reused; it does not claim that passive hooks make internal model or tool calls
replayable.

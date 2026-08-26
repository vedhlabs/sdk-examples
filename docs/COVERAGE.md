# Documentation coverage

The public docs and this repository have one ownership rule: prose may summarize, but runnable
Python lives here. Every real source-file label in the six Ogha pages links to a file in this repo.

| Public page | Runnable packages | Verification |
| :--- | :--- | :--- |
| Product page | `checkout`, `reports` | import tests, provider idempotency tests, schedule registration |
| Python SDK | `quickstart`, `primitives` | sync/async caller tests, unit tests, and end-to-end smoke |
| Use-case index | all guides | path coverage test |
| Order workflow | `ecommerce` | domain adapter tests and smoke with webhook resolution |
| Lending | `lending` | decision tests and smoke through automatic approval |
| Trading | `trading` | decimal math, mock broker identity, approval and reconciliation smoke |

[`coverage.json`](coverage.json) is the machine-readable contract. The docs build is separately
checked after links are updated so a renamed file cannot leave a plausible-looking dead example.

The quickstart’s `sync_client.py` is deliberately classified as a caller example. It uses
`Client.execute`, the SDK convenience for `submit` followed by `result`, and does not introduce an
`execution="sync"` workflow declaration.

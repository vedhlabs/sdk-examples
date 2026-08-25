# Compact checkout and scheduled report

These packages are the two short examples on the Ogha product page.

## Checkout

```bash
python -m checkout.worker
python -m checkout.submit
```

`checkout.charge_order` uses `order:<id>:charge` at the provider boundary and is the point of no
return in this intentionally small example. A shipping failure after capture becomes a visible
business exception handled by an explicit refund process; it is never silently described as if
the payment did not occur.

```mermaid
flowchart LR
    A[charge order with stable key] --> B[record charge]
    B --> C[create shipment]
    C --> D[record tracking]
```

Source: [`src/checkout/workflows.py`](../src/checkout/workflows.py),
[`src/checkout/steps.py`](../src/checkout/steps.py), and the
[`checkout adapters`](../src/checkout/adapters).

## Reports

```bash
python -m reports.worker
```

Worker startup creates `reports.daily-kpis`. The engine evaluates the five-field UTC cron and
creates deterministic occurrence run IDs even while workers are offline. The worker is needed to
execute an occurrence, not to remember that the occurrence exists.

Source: [`src/reports/workflows.py`](../src/reports/workflows.py).

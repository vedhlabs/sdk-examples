"""One App owns the pattern's Workflows, Steps, and worker lifecycle."""

import aga_runtime as aga

app = aga.App("agent-pattern", concurrency=4, lease_ttl_ms=2_000)

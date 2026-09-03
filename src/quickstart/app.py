from example_support.config import create_app

app = create_app(
    "quickstart",
    default_namespace="quickstart-dev",
    concurrency=8,
    lease_ttl_ms=8_000,
)

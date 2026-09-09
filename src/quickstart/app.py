from example_support.config import create_app

app = create_app(
    "quickstart",
    concurrency=8,
    lease_ttl_ms=8_000,
)

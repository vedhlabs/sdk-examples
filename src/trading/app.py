from example_support.config import create_app

app = create_app("trading", default_namespace="trading-dev", concurrency=16)

from example_support.config import create_app

app = create_app("primitives", default_namespace="primitives-dev", concurrency=8)

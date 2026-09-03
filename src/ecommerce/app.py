from example_support.config import create_app

app = create_app("ecommerce", default_namespace="ecommerce-dev", concurrency=8)

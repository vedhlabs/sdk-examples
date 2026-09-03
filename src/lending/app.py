from example_support.config import create_app

app = create_app("lending", default_namespace="lending-dev", concurrency=16)

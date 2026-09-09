from example_support.config import create_app

app = create_app("trading", concurrency=16)

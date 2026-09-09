from example_support.config import create_app

app = create_app("lending", concurrency=16)

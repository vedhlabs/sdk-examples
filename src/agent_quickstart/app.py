"""One Aga App owns this service's workflow, Agent Step, and worker."""

from aga_runtime.integrations.strands import StrandsAdapter

from example_support.config import create_app

app = create_app("agent-quickstart", concurrency=8)
strands_adapter = app.use(StrandsAdapter())

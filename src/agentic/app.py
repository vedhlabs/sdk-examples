from agentic.adapter import SupportAgentAdapter
from agentic.agent import ScriptedSupportAgent
from example_support.config import create_app

app = create_app(
    "agentic",
    default_namespace="agentic-dev",
    concurrency=4,
    lease_ttl_ms=8_000,
)

support = app.use(SupportAgentAdapter(ScriptedSupportAgent()))

"""Treat one complete Strands invocation as one opaque durable Aga operation."""

from strands import Agent

from agent_quickstart.app import app, strands_adapter
from agent_quickstart.local_model import LocalResearchModel


def build_research_agent() -> Agent:
    """Create fresh mutable conversation state for one Aga Step attempt."""
    return Agent(
        model=LocalResearchModel(),
        system_prompt="Answer the research question plainly.",
        callback_handler=None,
        name="local-research",
    )


research = strands_adapter.agent(
    "research",
    factory=build_research_agent,
    version="1",
    provider="local",
    model="deterministic-local-v1",
)


@app.workflow()
async def investigate(question: str) -> str:
    return await research(question)

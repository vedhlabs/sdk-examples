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


# ── A mutating tool, and cost the Namespace ceiling can see ──────────────────

from agent_quickstart.local_tool_model import LocalCheckoutModel  # noqa: E402
from agent_quickstart.tools import charge_card  # noqa: E402


def build_checkout_agent() -> Agent:
    """Fresh state per attempt, with one durable mutating tool."""
    return Agent(
        model=LocalCheckoutModel(),
        tools=[charge_card],
        system_prompt="When asked to charge, call charge_card once, then confirm.",
        callback_handler=None,
        name="local-checkout",
    )


def local_price_micros(model: str, input_tokens: int, output_tokens: int) -> int:
    """Turn the tokens Strands reports into micros for `max_cost_micros`.

    A stand-in rate. In production, price from the provider's published rates for
    `model` — the adapter deliberately ships no table, because a stale one
    under-reports, and an under-report is the one thing a spend ceiling cannot
    survive.
    """
    return input_tokens * 1 + output_tokens * 5


checkout = strands_adapter.agent(
    "checkout",
    factory=build_checkout_agent,
    version="1",
    provider="local",
    model="deterministic-checkout-v1",
    pricer=local_price_micros,
)


@app.workflow()
async def place_order(order_id: str, amount: int) -> str:
    return await checkout(f"Please charge order {order_id} for {amount} cents.")

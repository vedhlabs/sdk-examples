"""Opt-in Bedrock workflow, separate from the default cloud-free example."""

import os

from agent_quickstart.app import app, strands_adapter
from agent_quickstart.bedrock import (
    INPUT_PRICE_ENV,
    OUTPUT_PRICE_ENV,
    bedrock_pricer_from_env,
    bedrock_settings,
    build_bedrock_agent,
)

required = ("BEDROCK_MODEL_ID", "BEDROCK_REGION", INPUT_PRICE_ENV, OUTPUT_PRICE_ENV)
missing = [name for name in required if not os.environ.get(name)]
if missing:
    raise RuntimeError(
        "Bedrock worker needs explicit configuration: " + ", ".join(missing)
    )

model_id, region = bedrock_settings()
price_micros = bedrock_pricer_from_env()


def build_agent():
    """Keep the registered model and Region fixed for each fresh attempt."""
    return build_bedrock_agent(model_id=model_id, region=region)


research_bedrock = strands_adapter.agent(
    "research_bedrock",
    factory=build_agent,
    provider="bedrock",
    model=model_id,
    model_settings={"region": region},
    pricer=price_micros,
)


@app.workflow()
async def investigate_bedrock(question: str) -> str:
    return await research_bedrock(question)

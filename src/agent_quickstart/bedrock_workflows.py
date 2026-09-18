"""Opt-in Bedrock workflow, separate from the default cloud-free example."""

import os

from agent_quickstart.app import app, strands_adapter
from agent_quickstart.bedrock import bedrock_settings, build_bedrock_agent

if not os.environ.get("BEDROCK_MODEL_ID") or not os.environ.get("BEDROCK_REGION"):
    raise RuntimeError(
        "Bedrock worker and caller both need explicit BEDROCK_MODEL_ID and BEDROCK_REGION"
    )

model_id, region = bedrock_settings()


def build_agent():
    """Keep the registered model and Region fixed for each fresh attempt."""
    return build_bedrock_agent(model_id=model_id, region=region)


research_bedrock = strands_adapter.agent(
    "research_bedrock",
    factory=build_agent,
    provider="bedrock",
    model=model_id,
    model_settings={"region": region},
)


@app.workflow()
async def investigate_bedrock(question: str) -> str:
    return await research_bedrock(question)

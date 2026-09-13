"""Optional real-provider factory; importing it performs no network call."""

import os

from strands import Agent
from strands.models import BedrockModel


def build_bedrock_agent() -> Agent:
    """Build one fresh Bedrock-backed Agent for an Aga Step attempt."""
    model_id = os.environ["BEDROCK_MODEL_ID"]
    return Agent(
        model=BedrockModel(model_id=model_id),
        system_prompt="Answer the research question plainly and cite uncertainty.",
        callback_handler=None,
        name="bedrock-research",
    )

"""Optional real-provider factory; importing it performs no network call.

Two things this example learned the hard way, recorded so the next reader does
not repeat them:

- Bedrock is regional and Strands honours ``region_name``. A session whose default
  region has no Anthropic access fails permanently; pass the region explicitly.
- Anthropic models on Bedrock need the account's use-case form filed. Until then
  calls can fail with ``ResourceNotFoundException: Model use case details have not
  been submitted for this account``. Pick a profile supported by the caller's
  Region: Haiku 4.5 uses ``global.`` from Mumbai, which may route worldwide.
"""

import os

from strands import Agent
from strands.models import BedrockModel

#: Standalone factory default; the runnable workflow requires an explicit model.
DEFAULT_MODEL_ID = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
DEFAULT_REGION = "us-east-1"


def bedrock_settings() -> tuple[str, str]:
    """Resolve model and region from the environment, with explicit defaults."""
    return (
        os.environ.get("BEDROCK_MODEL_ID", DEFAULT_MODEL_ID),
        os.environ.get("BEDROCK_REGION")
        or os.environ.get("AWS_REGION")
        or os.environ.get("AWS_DEFAULT_REGION")
        or DEFAULT_REGION,
    )


def build_bedrock_agent(*, model_id: str | None = None, region: str | None = None) -> Agent:
    """Build one fresh Bedrock-backed Agent for an Aga Step attempt."""
    configured_model, configured_region = bedrock_settings()
    return Agent(
        model=BedrockModel(
            model_id=model_id or configured_model,
            region_name=region or configured_region,
        ),
        system_prompt="Answer the research question plainly and cite uncertainty.",
        callback_handler=None,
        name="bedrock-research",
    )

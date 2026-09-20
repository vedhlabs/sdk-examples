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
from collections.abc import Callable
from decimal import ROUND_CEILING, Decimal, InvalidOperation

from strands import Agent
from strands.models import BedrockModel

#: Standalone factory default; the runnable workflow requires an explicit model.
DEFAULT_MODEL_ID = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
DEFAULT_REGION = "us-east-1"
INPUT_PRICE_ENV = "BEDROCK_INPUT_USD_PER_MILLION_TOKENS"
OUTPUT_PRICE_ENV = "BEDROCK_OUTPUT_USD_PER_MILLION_TOKENS"


def bedrock_settings() -> tuple[str, str]:
    """Resolve model and region from the environment, with explicit defaults."""
    return (
        os.environ.get("BEDROCK_MODEL_ID", DEFAULT_MODEL_ID),
        os.environ.get("BEDROCK_REGION")
        or os.environ.get("AWS_REGION")
        or os.environ.get("AWS_DEFAULT_REGION")
        or DEFAULT_REGION,
    )


def bedrock_pricer_from_env() -> Callable[[str, int, int], int]:
    """Build explicit, model-pinned micro-USD accounting for this worker.

    AWS prices can change and differ by model and routing profile. Requiring the
    operator to supply the two current rates is safer than embedding a price list
    that silently grows stale. USD per million tokens is numerically equal to
    micro-USD per token, so the final total needs only conservative rounding.
    """
    input_rate = _usd_per_million(INPUT_PRICE_ENV)
    output_rate = _usd_per_million(OUTPUT_PRICE_ENV)

    def price_micros(_model_id: str, input_tokens: int, output_tokens: int) -> int:
        total = Decimal(input_tokens) * input_rate + Decimal(output_tokens) * output_rate
        return int(total.to_integral_value(rounding=ROUND_CEILING))

    return price_micros


def _usd_per_million(name: str) -> Decimal:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        raise RuntimeError(
            f"{name} is required so the Namespace cost ceiling does not treat "
            "paid Bedrock usage as free"
        )
    try:
        value = Decimal(raw)
    except InvalidOperation as exc:
        raise RuntimeError(f"{name} must be a non-negative decimal") from exc
    if not value.is_finite() or value < 0:
        raise RuntimeError(f"{name} must be a non-negative decimal")
    return value


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

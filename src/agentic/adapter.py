from __future__ import annotations

from dataclasses import dataclass

import ogha

from agentic.agent import SupportAgent
from agentic.types import Resolution, Ticket


@dataclass(frozen=True)
class SupportAdapterConfig:
    """Adapter-owned immutable configuration, independent of Ogha core."""

    identity: str = "example.support-agent/1"
    operation: str = "agentic.support.run"
    timeout: int = 120


DEFAULT_CONFIG = SupportAdapterConfig()


class SupportAgentAdapter:
    """Bind one existing agent as an explicitly opaque durable operation."""

    def __init__(
        self,
        agent: SupportAgent,
        config: SupportAdapterConfig = DEFAULT_CONFIG,
    ) -> None:
        self.agent = agent
        self.config = config
        self.name = config.identity

    def install(self, app: ogha.App) -> None:
        @app.opaque(
            adapter=self.name,
            name=self.config.operation,
            timeout=self.config.timeout,
        )
        async def run(ticket: Ticket) -> Resolution:
            return await self.agent.run(ticket)

        self.run = run

    def validate(self, app: ogha.App) -> None:
        if not self.name.strip() or self.name != self.name.strip():
            raise ValueError("agent adapter identity must be a stable non-empty string")
        if not getattr(self.agent, "name", ""):
            raise ValueError("agent requires a stable name")
        if not self.config.operation.strip():
            raise ValueError("agent operation name must not be empty")

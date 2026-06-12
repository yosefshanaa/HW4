"""Provider-agnostic LLM access — always through the Gatekeeper (FR-5.4).

Two layers on purpose: a dumb Transport (provider SDK adapter in
shared/transports.py, swappable per ADR-3) and the LlmClient that resolves model tiers from config and
routes every completion through ApiGatekeeper.execute, so token logging,
rate limits, retries, and the budget firewall apply to every consumer
(wiki generation, agents, experiments) with zero discipline required.

Constructing an LlmClient without a gatekeeper is a hard error — bypass
is structurally impossible, not just discouraged (tested in T059).
"""

from __future__ import annotations

from dataclasses import dataclass

from hw4.constants import ModelTier
from hw4.shared.config import Config
from hw4.shared.gatekeeper import ApiGatekeeper, CallResult

TRANSIENT_HTTP_STATUSES = frozenset({408, 409, 429, 500, 502, 503, 504, 529})


class GatekeeperRequiredError(RuntimeError):
    """LlmClient must be wired through a gatekeeper — no direct API access."""


@dataclass(frozen=True)
class LlmResponse:
    """One completion with its usage as reported by the provider API.

    Token counts come from API response metadata, NOT a local tokenizer —
    the token experiment's numbers must be the provider's ground truth.
    """

    text: str
    input_tokens: int
    output_tokens: int
    model: str


def is_transient_status(status_code: int) -> bool:
    """Retry policy: rate-limit/overload/server errors are transient."""
    return status_code in TRANSIENT_HTTP_STATUSES


class LlmClient:
    """Tiered completions, gated and ledger-logged end to end."""

    def __init__(self, config: Config, gatekeeper: ApiGatekeeper, transport):
        if gatekeeper is None:
            raise GatekeeperRequiredError("LlmClient requires an ApiGatekeeper (NFR-2)")
        self._models = {
            ModelTier.CHEAP: config.get("models.cheap"),
            ModelTier.STRONG: config.get("models.strong"),
        }
        self._max_tokens = int(config.get("llm.max_output_tokens"))
        self._gatekeeper = gatekeeper
        self._transport = transport

    def model_for(self, tier: ModelTier) -> str:
        """Resolve a tier to its configured model id (ADR-3)."""
        return self._models[tier]

    def complete(
        self,
        messages: list[dict],
        *,
        purpose_tag: str,
        tier: ModelTier = ModelTier.CHEAP,
        system: str = "",
        temperature: float = 0.0,
    ) -> LlmResponse:
        """One gated completion; returns text plus provider-reported usage."""
        model = self.model_for(tier)

        def call() -> CallResult:
            response = self._transport.send(
                model=model,
                messages=messages,
                system=system,
                temperature=temperature,
                max_tokens=self._max_tokens,
            )
            return CallResult(
                value=response,
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
            )

        return self._gatekeeper.execute(call, purpose_tag=purpose_tag, model=model)

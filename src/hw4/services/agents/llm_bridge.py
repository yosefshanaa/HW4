"""CrewAI LLM adapter — agent traffic cannot bypass the Gatekeeper (NFR-2).

CrewAI's default path (litellm) would talk to providers directly, which
is exactly the bypass FR-5.4 forbids. This BaseLLM subclass routes every
agent call through our LlmClient (which is constructable only WITH a
gatekeeper), tagging each call `agent.<role>.<purpose>` so per-role cost
is a ledger query.
"""

from __future__ import annotations

from crewai.llms.base_llm import BaseLLM

from hw4.constants import ModelTier
from hw4.shared.llm_client import LlmClient


class GatedCrewLLM(BaseLLM):
    """The only LLM object agents are ever given."""

    def __init__(self, client: LlmClient, role: str, tier: ModelTier = ModelTier.CHEAP):
        if not isinstance(client, LlmClient):
            raise TypeError("GatedCrewLLM requires the gated LlmClient (NFR-2)")
        super().__init__(model=client.model_for(tier))
        object.__setattr__(self, "_client", client)
        object.__setattr__(self, "_role", role)
        object.__setattr__(self, "_tier", tier)

    def call(self, messages, tools=None, callbacks=None, available_functions=None,
             from_task=None, from_agent=None, response_model=None):
        normalized = self._normalize(messages)
        response = self._client.complete(
            normalized,
            purpose_tag=f"agent.{self._role}",
            tier=self._tier,
        )
        return response.text

    @staticmethod
    def _normalize(messages) -> list[dict]:
        if isinstance(messages, str):
            return [{"role": "user", "content": messages}]
        return [
            {"role": str(m.get("role", "user")), "content": str(m.get("content", ""))}
            for m in messages
        ]

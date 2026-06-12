"""Provider transport adapters (ADR-3/ADR-7 — dumb, swappable, gated).

A transport is the ONLY code that touches a provider SDK. It owns two
jobs: send one completion, and map provider errors onto our
TransientApiError taxonomy so the Gatekeeper's retry policy stays
provider-agnostic. Token usage always comes from the provider's API
response metadata — never a local tokenizer (PLAN §4.4).

The active provider is config (`llm.provider`), like everything else.
"""

from __future__ import annotations

from hw4.shared.config import Config
from hw4.shared.gatekeeper import TransientApiError
from hw4.shared.llm_client import LlmResponse, is_transient_status


class AnthropicTransport:
    """Thin adapter over the Anthropic SDK (lazy import, no logic)."""

    def __init__(self, api_key: str):
        import anthropic  # local import: tests never need the real SDK wired

        self._client = anthropic.Anthropic(api_key=api_key)
        self._errors = anthropic

    def send(
        self, model: str, messages: list[dict], system: str, temperature: float, max_tokens: int
    ) -> LlmResponse:  # pragma: no cover - network path, exercised live only
        try:
            response = self._client.messages.create(
                model=model,
                system=system,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except self._errors.APIStatusError as exc:
            if is_transient_status(exc.status_code):
                raise TransientApiError(str(exc)) from exc
            raise
        except self._errors.APIConnectionError as exc:
            raise TransientApiError(str(exc)) from exc
        text = "".join(block.text for block in response.content if block.type == "text")
        return LlmResponse(
            text=text,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            model=model,
        )


class OpenAITransport:
    """Thin adapter over the OpenAI SDK (lazy import, no logic)."""

    def __init__(self, api_key: str):
        import openai  # local import, same rationale as above

        self._client = openai.OpenAI(api_key=api_key)
        self._errors = openai

    def send(
        self, model: str, messages: list[dict], system: str, temperature: float, max_tokens: int
    ) -> LlmResponse:  # pragma: no cover - network path, exercised live only
        chat = ([{"role": "system", "content": system}] if system else []) + messages
        try:
            response = self._client.chat.completions.create(
                model=model,
                messages=chat,
                temperature=temperature,
                max_completion_tokens=max_tokens,
            )
        except self._errors.APIStatusError as exc:
            if is_transient_status(exc.status_code):
                raise TransientApiError(str(exc)) from exc
            raise
        except self._errors.APIConnectionError as exc:
            raise TransientApiError(str(exc)) from exc
        return LlmResponse(
            text=response.choices[0].message.content or "",
            input_tokens=response.usage.prompt_tokens,
            output_tokens=response.usage.completion_tokens,
            model=model,
        )


PROVIDERS = {
    "anthropic": AnthropicTransport,
    "openai": OpenAITransport,
}


def make_transport(config: Config):
    """Build the configured provider's transport; key name is config too."""
    provider = str(config.get("llm.provider"))
    if provider not in PROVIDERS:
        raise ValueError(f"unknown llm.provider {provider!r}; known: {sorted(PROVIDERS)}")
    api_key = config.get_secret(str(config.get("llm.api_key_env")))
    return PROVIDERS[provider](api_key=api_key)

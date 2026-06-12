"""Tests for hw4.shared.llm_client — tiering, gating, usage propagation."""

import pytest

from hw4.constants import ModelTier
from hw4.shared.config import Config
from hw4.shared.gatekeeper import TransientApiError
from hw4.shared.llm_client import (
    GatekeeperRequiredError,
    LlmClient,
    LlmResponse,
    is_transient_status,
)

from .test_config import write_config_dir
from .test_gatekeeper import FakeClock, make_gatekeeper


class FakeTransport:
    """Scripted transport: returns queued responses or raises queued errors."""

    def __init__(self, script):
        self.script = list(script)
        self.calls = []

    def send(self, model, messages, system, temperature, max_tokens):
        self.calls.append(
            {"model": model, "messages": messages, "system": system, "max_tokens": max_tokens}
        )
        item = self.script.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def make_client(tmp_path, script):
    setup = {
        "version": "1.00",
        "paths": {"results": "results"},
        "models": {"cheap": "model-cheap", "strong": "model-strong"},
        "llm": {"max_output_tokens": 256, "api_key_env": "ANTHROPIC_API_KEY"},
        "pricing_per_mtok": {"model-cheap": {"input": 1.0, "output": 1.0}},
        "budget": {"max_usd": 10.0, "warn_usd": 10.0},
    }
    gate, ledger, _ = make_gatekeeper(tmp_path, max_usd=10.0)
    cfg = Config(write_config_dir(tmp_path / "cfg2", setup=setup), environ={})
    transport = FakeTransport(script)
    return LlmClient(cfg, gate, transport), transport, ledger


def response(text="hi", tokens=(100, 20), model="model-cheap"):
    return LlmResponse(text=text, input_tokens=tokens[0], output_tokens=tokens[1], model=model)


class TestConstruction:
    def test_gatekeeper_is_mandatory(self, tmp_path):
        setup = {
            "version": "1.00",
            "paths": {},
            "models": {"cheap": "a", "strong": "b"},
            "llm": {"max_output_tokens": 1, "api_key_env": "K"},
        }
        cfg = Config(write_config_dir(tmp_path / "cfg", setup=setup), environ={})
        with pytest.raises(GatekeeperRequiredError):
            LlmClient(cfg, None, FakeTransport([]))


class TestTiering:
    def test_tier_resolves_model_from_config(self, tmp_path):
        client, _, _ = make_client(tmp_path, [response()])
        assert client.model_for(ModelTier.CHEAP) == "model-cheap"
        assert client.model_for(ModelTier.STRONG) == "model-strong"

    def test_strong_tier_used_in_request(self, tmp_path):
        client, transport, _ = make_client(tmp_path, [response(model="model-strong")])
        client.complete([{"role": "user", "content": "q"}], purpose_tag="t", tier=ModelTier.STRONG)
        assert transport.calls[0]["model"] == "model-strong"


class TestCompletion:
    def test_returns_response_with_usage(self, tmp_path):
        client, _, _ = make_client(tmp_path, [response(text="answer", tokens=(7, 3))])
        result = client.complete([{"role": "user", "content": "q"}], purpose_tag="ask")
        assert result.text == "answer"
        assert (result.input_tokens, result.output_tokens) == (7, 3)

    def test_usage_lands_in_ledger_via_gatekeeper(self, tmp_path):
        client, _, ledger = make_client(tmp_path, [response(tokens=(11, 4))])
        client.complete([{"role": "user", "content": "q"}], purpose_tag="experiment.B.q2")
        entry = ledger.entries()[0]
        assert entry.purpose_tag == "experiment.B.q2"
        assert (entry.input_tokens, entry.output_tokens) == (11, 4)
        assert entry.model == "model-cheap"

    def test_max_tokens_comes_from_config(self, tmp_path):
        client, transport, _ = make_client(tmp_path, [response()])
        client.complete([{"role": "user", "content": "q"}], purpose_tag="t")
        assert transport.calls[0]["max_tokens"] == 256

    def test_transient_error_retried_by_gatekeeper(self, tmp_path):
        client, _, ledger = make_client(
            tmp_path, [TransientApiError("429"), response(text="recovered")]
        )
        result = client.complete([{"role": "user", "content": "q"}], purpose_tag="t")
        assert result.text == "recovered"
        assert ledger.entries()[0].status == "retry_ok"


class TestTransientClassification:
    def test_known_transient_statuses(self):
        for code in (429, 500, 503, 529):
            assert is_transient_status(code)

    def test_client_errors_are_not_transient(self):
        for code in (400, 401, 403, 404):
            assert not is_transient_status(code)


class TestFakeClockReuse:
    def test_fake_clock_importable(self):
        """Guard: gatekeeper test utilities stay reusable across test modules."""
        clock = FakeClock()
        before = clock()
        clock.sleep(5)
        assert clock() == before + 5

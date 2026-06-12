"""Tests for hw4.sdk.sdk — wiring, lazy singletons, injection, stubs."""

from pathlib import Path

import pytest

from hw4.constants import ModelTier
from hw4.sdk.sdk import Hw4Sdk, ServiceNotReadyError
from hw4.shared.config import Config

from .test_config import write_config_dir
from .test_llm_client import FakeTransport, response

SETUP = {
    "version": "1.00",
    "paths": {"results": "results"},
    "models": {"cheap": "model-cheap", "strong": "model-strong"},
    "llm": {"max_output_tokens": 64, "api_key_env": "ANTHROPIC_API_KEY"},
    "pricing_per_mtok": {"model-cheap": {"input": 1.0, "output": 1.0}},
    "budget": {"max_usd": 10.0, "warn_usd": 10.0},
}


def make_sdk(tmp_path, *, transport=None, run_id="run-test"):
    write_config_dir(tmp_path / "config", setup=SETUP)
    return Hw4Sdk(
        config_dir="config", environ={}, base_dir=tmp_path, transport=transport, run_id=run_id
    )


class TestWiring:
    def test_builds_config_from_config_dir(self, tmp_path):
        sdk = make_sdk(tmp_path)
        assert sdk.config.get("models.cheap") == "model-cheap"

    def test_accepts_prebuilt_config(self, tmp_path):
        cfg = Config(write_config_dir(tmp_path / "cfg", setup=SETUP), environ={})
        sdk = Hw4Sdk(cfg, base_dir=tmp_path)
        assert sdk.config is cfg

    def test_ledger_lives_under_results_dir(self, tmp_path):
        sdk = make_sdk(tmp_path)
        assert sdk.ledger is not None  # touching the property creates the dir
        assert (tmp_path / "results").is_dir()

    def test_shared_singletons(self, tmp_path):
        sdk = make_sdk(tmp_path)
        assert sdk.ledger is sdk.ledger
        assert sdk.gatekeeper is sdk.gatekeeper

    def test_run_id_generated_when_not_injected(self, tmp_path):
        write_config_dir(tmp_path / "config", setup=SETUP)
        sdk = Hw4Sdk(config_dir="config", environ={}, base_dir=tmp_path)
        assert sdk.run_id.startswith("run-")


class TestLlmWiring:
    def test_injected_transport_is_used(self, tmp_path):
        transport = FakeTransport([response(text="via-fake")])
        sdk = make_sdk(tmp_path, transport=transport)
        result = sdk.llm.complete([{"role": "user", "content": "q"}], purpose_tag="t")
        assert result.text == "via-fake"

    def test_llm_calls_flow_into_sdk_ledger(self, tmp_path):
        sdk = make_sdk(tmp_path, transport=FakeTransport([response(tokens=(9, 2))]))
        sdk.llm.complete([{"role": "user", "content": "q"}], purpose_tag="sdk.t")
        entry = sdk.ledger.entries()[0]
        assert (entry.purpose_tag, entry.input_tokens) == ("sdk.t", 9)

    def test_strong_tier_reaches_transport(self, tmp_path):
        transport = FakeTransport([response(model="model-strong")])
        sdk = make_sdk(tmp_path, transport=transport)
        sdk.llm.complete([{"role": "user", "content": "q"}], purpose_tag="t", tier=ModelTier.STRONG)
        assert transport.calls[0]["model"] == "model-strong"

    def test_default_transport_needs_secret(self, tmp_path):
        sdk = make_sdk(tmp_path)  # environ={} -> no ANTHROPIC_API_KEY
        with pytest.raises(Exception, match="ANTHROPIC_API_KEY"):
            sdk.llm  # noqa: B018 - property access is the behaviour under test


class TestNotReadyStubs:
    @pytest.mark.parametrize(
        "invoke",
        [
            lambda sdk: sdk.run_experiment(),
            lambda sdk: sdk.report(),
        ],
    )
    def test_unwired_capability_raises_with_phase_pointer(self, tmp_path, invoke):
        sdk = make_sdk(tmp_path)
        with pytest.raises(ServiceNotReadyError, match="Phase"):
            invoke(sdk)


class TestBuildGraph:
    MINI_REPO = Path(__file__).resolve().parents[1] / "fixtures" / "mini_repo"

    def make_graph_sdk(self, tmp_path):
        setup = dict(SETUP)
        setup["paths"] = {"results": "results"}
        setup["graph"] = {
            "exclude_dirs": [".git", "__pycache__"],
            "doc_suffixes": [".md"],
            "max_mentions_per_doc": 50,
        }
        setup["metrics"] = {"relations": ["imports", "calls"], "top_k_bottlenecks": 5}
        write_config_dir(tmp_path / "config", setup=setup)
        return Hw4Sdk(config_dir="config", environ={}, base_dir=tmp_path)

    def test_builds_iteration_zero_with_metrics(self, tmp_path):
        sdk = self.make_graph_sdk(tmp_path)
        record = sdk.build_graph(self.MINI_REPO)
        assert record.iteration == 0
        assert record.graph_path.exists()
        assert (record.graph_path.parent / "metrics.json").exists()

    def test_next_call_auto_increments_iteration(self, tmp_path):
        sdk = self.make_graph_sdk(tmp_path)
        sdk.build_graph(self.MINI_REPO)
        assert sdk.build_graph(self.MINI_REPO).iteration == 1

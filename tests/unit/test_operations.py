"""Integration tests for sdk operations — vault build + ask on mini_repo."""

from pathlib import Path

import pytest

from hw4.sdk.errors import ServiceNotReadyError
from hw4.sdk.sdk import Hw4Sdk
from hw4.services.retrieval import NoRetrievalMatchError

from .test_config import write_config_dir
from .test_llm_client import FakeTransport, response

MINI_REPO = Path(__file__).resolve().parents[1] / "fixtures" / "mini_repo"
PROSE = "SUMMARY: short generated summary.\nOPEN QUESTIONS:\n- open?\n"

FULL_SETUP = {
    "version": "1.00",
    "paths": {"results": "results", "vault": "vault", "workspace": "ws", "data": "data"},
    "models": {"cheap": "model-cheap", "strong": "model-strong"},
    "llm": {"max_output_tokens": 256, "api_key_env": "ANTHROPIC_API_KEY"},
    "pricing_per_mtok": {"model-cheap": {"input": 1.0, "output": 1.0}},
    "budget": {"max_usd": 10.0, "warn_usd": 10.0},
    "graph": {"exclude_dirs": [".git", "__pycache__"], "doc_suffixes": [".md"],
              "max_mentions_per_doc": 50},
    "metrics": {"relations": ["imports", "calls"], "top_k_bottlenecks": 5},
    "retrieval": {"k_pages": 2, "ego_radius": 2, "max_nodes": 40,
                  "max_seeds": 3, "context_token_cap": 12000},
    "vault": {"project": "proj-x", "domains": ["python"], "top_hub_pages": 3,
              "wiki_page_max_lines": 40, "index_max_entries_per_section": 8,
              "min_community_size": 3},
}


FAST_RATE_LIMITS = {
    "rate_limits": {
        "version": "1.00",
        "services": {
            "default": {
                # generous: these tests use a REAL clock/sleeper via Hw4Sdk —
                # a small rpm here would make the gatekeeper sleep for real
                "requests_per_minute": 100000,
                "requests_per_hour": 100000,
                "concurrent_max": 5,
                "retry_after_seconds": 0,
                "max_retries": 1,
                "queue_depth_max": 50,
            }
        },
    }
}


def make_sdk(tmp_path, fill=None):
    write_config_dir(tmp_path / "config", setup=FULL_SETUP, rate_limits=FAST_RATE_LIMITS)
    transport = FakeTransport([], fill=fill or response(text=PROSE))
    sdk = Hw4Sdk(config_dir="config", environ={}, base_dir=tmp_path, transport=transport)
    sdk.build_graph(MINI_REPO)
    return sdk, transport


class TestBuildVault:
    def test_full_vault_build_from_latest_graph(self, tmp_path):
        sdk, _ = make_sdk(tmp_path)
        report = sdk.build_vault()
        assert report.iteration == 0
        assert report.pages, "wiki pages must be generated"
        index = report.index_path.read_text()
        assert "Hubs & bottlenecks" in index and "Communities" in index
        assert any("manifest" in p.name for p in report.raw_copies)

    def test_wiki_generation_ledgered(self, tmp_path):
        sdk, _ = make_sdk(tmp_path)
        sdk.build_vault()
        tags = [e.purpose_tag for e in sdk.ledger.entries()]
        assert any(tag.startswith("wiki.gen.") for tag in tags)


class TestAsk:
    def test_answer_carries_citation_material(self, tmp_path):
        sdk, transport = make_sdk(tmp_path)
        sdk.build_vault()
        transport.script.append(response(text="run() drives parse->summarize [app.engine]"))
        result = sdk.ask("what does the engine run pipeline do?")
        assert "run()" in result.answer
        assert result.matched_nodes
        assert any("engine" in f for f in result.source_files)
        assert sdk.ledger.entries()[-1].purpose_tag == "ask"

    def test_refuses_when_nothing_matches(self, tmp_path):
        sdk, _ = make_sdk(tmp_path)
        sdk.build_vault()
        with pytest.raises(NoRetrievalMatchError):
            sdk.ask("explain quantum blockchain consensus")

    def test_ask_without_graph_fails_loud(self, tmp_path):
        write_config_dir(tmp_path / "config", setup=FULL_SETUP)
        sdk = Hw4Sdk(config_dir="config", environ={}, base_dir=tmp_path,
                     transport=FakeTransport([]))
        with pytest.raises(FileNotFoundError, match="no graph iterations"):
            sdk.ask("anything about engine")

    def test_naive_mode_not_ready_yet(self, tmp_path):
        sdk, _ = make_sdk(tmp_path)
        with pytest.raises(ServiceNotReadyError, match="Phase 7"):
            sdk.ask("q", mode="naive")


class TestContextBudgetSanity:
    def test_typical_question_context_under_cap(self, tmp_path):
        """T208: the savings mechanism exists before we measure it."""
        sdk, _ = make_sdk(tmp_path)
        sdk.build_vault()
        result = sdk.ask("what does the engine run pipeline do?")
        cap = int(sdk.config.get("retrieval.context_token_cap"))
        assert 0 < result.context_token_estimate <= cap
        assert not result.truncated

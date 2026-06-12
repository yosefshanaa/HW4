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
    "llm": {"max_output_tokens": 256, "provider": "anthropic",
            "api_key_env": "ANTHROPIC_API_KEY"},
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
    "detectors": {
        "spof": {"min_mandatory_ratio": 0.3, "max_rank": 5},
        "god_node": {"degree_multiplier": 2.0, "percentile": 0.98,
                     "min_fan_out": 3, "min_communities": 2},
        "isolation": {"min_size": 1},
        "traceability": {"report_undocumented": False},
        "duplication": {"min_confidence": 0.5},
    },
    "repo": {"timeout_seconds": 60, "default_dirname": "target"},
    "experiment": {"repetitions": 1, "temperature": 0.0, "model_tier": "cheap",
                   "shuffle_seed": 42, "n_questions_min": 1,
                   "naive_context_token_cap": 16000, "assumed_output_tokens": 100},
    "loop": {"max_iterations": 3, "metric_improvement_threshold": 0.1,
             "step_timeout_seconds": 120},
    "fixloop": {"branch_prefix": "fix/", "max_edit_retries": 1,
                "test_command": ["python", "-m", "pytest", "-q", "tests"]},
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
        with pytest.raises(ServiceNotReadyError, match="experiment"):
            sdk.ask("q", mode="naive")


class TestAnalyze:
    def test_planted_defects_found_on_mini_repo(self, tmp_path):
        """T236: the fixture's answer key, end to end through the SDK."""
        from hw4.constants import FindingKind

        sdk, _ = make_sdk(tmp_path)
        findings = sdk.analyze()
        by_kind = {}
        for finding in findings:
            by_kind.setdefault(finding.kind, []).append(finding)
        gap_nodes = {n for f in by_kind[FindingKind.TRACE_GAP] for n in f.nodes}
        assert "missing:app.plugins" in gap_nodes  # the planted README lie
        island_nodes = {n for f in by_kind[FindingKind.ISOLATED] for n in f.nodes}
        assert {"orphan", "orphan.legacy"} <= island_nodes  # the planted orphan
        assert (tmp_path / "results" / "findings.json").exists()

    def test_findings_ranked_with_stable_ids(self, tmp_path):
        sdk, _ = make_sdk(tmp_path)
        findings = sdk.analyze()
        assert findings, "mini_repo must produce findings"
        assert [f.id for f in findings] == [f"F-{i:03d}" for i in range(1, len(findings) + 1)]


class TestFix:
    @staticmethod
    def with_target(tmp_path):
        import shutil

        sdk, _ = make_sdk(tmp_path)
        shutil.copytree(MINI_REPO, tmp_path / "ws" / "target")
        return sdk

    def test_unknown_finding_id_fails_loud(self, tmp_path):
        sdk = self.with_target(tmp_path)
        with pytest.raises(KeyError, match="F-999"):
            sdk.fix("F-999")

    def test_base_graph_always_freshly_extracted(self, tmp_path):
        """A stale iteration must never become the loop baseline."""
        sdk = self.with_target(tmp_path)
        before = len(list((tmp_path / "results" / "graphs").iterdir()))
        sdk.fix(auto=True)
        after = len(list((tmp_path / "results" / "graphs").iterdir()))
        assert after == before + 1  # fresh base built from the current tree

    def test_auto_mode_on_mini_repo_is_honest_no_safe_action(self, tmp_path):
        """mini_repo's findings (trace gap, island) are human-only or carry
        AMBIGUOUS links — the loop must refuse them all and say so."""
        sdk = self.with_target(tmp_path)
        report = sdk.fix(auto=True)
        assert report["stop_reason"] == "NO_SAFE_ACTION"
        assert report["iterations"] == []
        assert (tmp_path / "results" / "loop_log.json").exists()


class TestExperimentAndReport:
    DATASET = """\
version: "1.00"
questions:
  - id: Q-01
    tier: locate
    question: "where does the engine run pipeline live?"
    reference_answer: "app/engine.py"
    reference_files: [app/engine.py]
  - id: Q-02
    tier: path
    question: "how does run reach render?"
    reference_answer: "run -> render"
    reference_files: [app/engine.py, app/reports.py]
  - id: Q-03
    tier: impact
    question: "what breaks if utils clamp changes?"
    reference_answer: "engine and models"
    reference_files: [app/utils.py]
"""

    def make_experiment_sdk(self, tmp_path):
        import shutil

        sdk, transport = make_sdk(tmp_path)
        shutil.copytree(MINI_REPO, tmp_path / "ws" / "target")
        (tmp_path / "data").mkdir()
        (tmp_path / "data" / "questions.yaml").write_text(self.DATASET)
        sdk.build_vault()
        return sdk

    def test_full_ab_run_produces_comparison(self, tmp_path):
        sdk = self.make_experiment_sdk(tmp_path)
        result = sdk.run_experiment()
        assert "comparison" in result
        assert (tmp_path / "results" / "experiment" / "comparison.json").exists()
        tags = {e.purpose_tag for e in sdk.ledger.entries()}
        assert "experiment.A.Q-01" in tags and "experiment.B.Q-03" in tags

    def test_report_aggregates_all_artifacts(self, tmp_path):
        sdk = self.make_experiment_sdk(tmp_path)
        sdk.analyze()
        sdk.run_experiment()
        text = sdk.report().read_text()
        for heading in ("## Findings", "## Token experiment", "## Cost"):
            assert heading in text


class TestContextBudgetSanity:
    def test_typical_question_context_under_cap(self, tmp_path):
        """T208: the savings mechanism exists before we measure it."""
        sdk, _ = make_sdk(tmp_path)
        sdk.build_vault()
        result = sdk.ask("what does the engine run pipeline do?")
        cap = int(sdk.config.get("retrieval.context_token_cap"))
        assert 0 < result.context_token_estimate <= cap
        assert not result.truncated

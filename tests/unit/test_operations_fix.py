"""Integration tests for sdk fix loop, A/B experiment + report aggregation.

Split out of test_operations to keep each file within the 150-code-line limit
(guidelines §3.2/§6.1); reuses that suite's shared scaffolding (make_sdk,
MINI_REPO) — the same import pattern the other sibling suites already use.
"""

import shutil

from .test_operations import MINI_REPO, make_sdk


class TestFix:
    @staticmethod
    def with_target(tmp_path):
        sdk, _ = make_sdk(tmp_path)
        shutil.copytree(MINI_REPO, tmp_path / "ws" / "target")
        return sdk

    def test_unknown_finding_id_fails_loud(self, tmp_path):
        import pytest

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
        sdk, _ = make_sdk(tmp_path)
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

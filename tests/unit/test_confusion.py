"""Confusion-matrix evaluation tests — math + end-to-end on mini_repo (L07 §13.2)."""

from pathlib import Path

import pytest

from hw4.constants import FindingKind
from hw4.sdk.sdk import Hw4Sdk
from hw4.services.detectors.base import Finding
from hw4.services.evaluation import confusion

from .test_config import write_config_dir
from .test_operations import FAST_RATE_LIMITS, FULL_SETUP

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
MINI_REPO = FIXTURES / "mini_repo"
ANSWER_KEY = FIXTURES / "mini_repo_answer_key.json"


def finding(kind: FindingKind, *nodes: str) -> Finding:
    return Finding(id="", kind=kind, nodes=list(nodes), evidence_chain=[])


def candidate(target: str, kind: FindingKind, is_defect: bool) -> confusion.Candidate:
    return confusion.Candidate(target=target, kind=kind, is_defect=is_defect, rationale="")


class TestNodeMatching:
    def test_exact_and_child_prefix_match(self):
        assert confusion._node_matches("app.engine", "app.engine")
        assert confusion._node_matches("app.engine.run", "app.engine")

    def test_missing_prefix_resolves_to_claimed_symbol(self):
        assert confusion._node_matches("missing:app.plugins", "app.plugins")

    def test_unrelated_node_does_not_match(self):
        assert not confusion._node_matches("app.utils.mean", "app.engine")
        assert not confusion._node_matches("app.engineering", "app.engine")


class TestMatrixMath:
    def test_cells_and_metrics(self):
        candidates = [
            candidate("app.engine", FindingKind.GOD_NODE, True),
            candidate("orphan.legacy", FindingKind.ISOLATED, True),
            candidate("app.plugins", FindingKind.TRACE_GAP, True),
            candidate("conftest", FindingKind.ISOLATED, False),
            candidate("app.utils", FindingKind.GOD_NODE, False),
        ]
        findings = [
            finding(FindingKind.GOD_NODE, "app.engine.run"),
            finding(FindingKind.ISOLATED, "orphan.legacy"),
            finding(FindingKind.TRACE_GAP, "doc:README.md", "missing:app.plugins"),
            finding(FindingKind.ISOLATED, "conftest"),
        ]
        m = confusion.evaluate(findings, candidates)
        assert (m.tp, m.fp, m.fn, m.tn) == (3, 1, 0, 1)
        assert m.precision == pytest.approx(0.75)
        assert m.recall == pytest.approx(1.0)
        assert m.f1 == pytest.approx(0.857, abs=1e-3)
        assert m.accuracy == pytest.approx(0.8)

    def test_missed_defect_is_false_negative(self):
        candidates = [candidate("app.engine", FindingKind.GOD_NODE, True)]
        m = confusion.evaluate([], candidates)
        assert (m.tp, m.fp, m.fn, m.tn) == (0, 0, 1, 0)
        assert m.recall == 0.0

    def test_wrong_kind_does_not_satisfy_candidate(self):
        candidates = [candidate("app.engine", FindingKind.GOD_NODE, True)]
        findings = [finding(FindingKind.ISOLATED, "app.engine.run")]
        assert confusion.evaluate(findings, candidates).fn == 1

    def test_empty_matrix_metrics_are_zero(self):
        m = confusion.evaluate([], [])
        assert (m.precision, m.recall, m.f1, m.accuracy) == (0.0, 0.0, 0.0, 0.0)

    def test_to_dict_round_trips_outcomes(self):
        m = confusion.evaluate(
            [finding(FindingKind.GOD_NODE, "app.engine.run")],
            [candidate("app.engine", FindingKind.GOD_NODE, True)],
        )
        payload = m.to_dict()
        assert payload["cells"] == {"tp": 1, "fp": 0, "fn": 0, "tn": 0}
        assert payload["outcomes"][0]["cell"] == "TP"


class TestAnswerKey:
    def test_loads_planted_ground_truth(self):
        candidates = confusion.load_answer_key(ANSWER_KEY)
        kinds = {(c.target, c.kind) for c in candidates}
        assert ("app.engine", FindingKind.GOD_NODE) in kinds
        assert ("app.plugins", FindingKind.TRACE_GAP) in kinds
        assert sum(1 for c in candidates if c.is_defect) == 3


class TestEvaluateOp:
    def make_sdk(self, tmp_path):
        write_config_dir(tmp_path / "config", setup=FULL_SETUP, rate_limits=FAST_RATE_LIMITS)
        return Hw4Sdk(config_dir="config", environ={}, base_dir=tmp_path)

    def test_mini_repo_matrix_matches_answer_key(self, tmp_path):
        sdk = self.make_sdk(tmp_path)
        report = sdk.evaluate(MINI_REPO, ANSWER_KEY)
        m = report.matrix
        assert (m.tp, m.fp, m.fn, m.tn) == (3, 1, 0, 2)
        assert m.recall == pytest.approx(1.0)
        assert m.precision == pytest.approx(0.75)

    def test_only_false_positive_is_conftest(self, tmp_path):
        sdk = self.make_sdk(tmp_path)
        report = sdk.evaluate(MINI_REPO, ANSWER_KEY)
        fps = [o.candidate.target for o in report.matrix.outcomes if o.cell == "FP"]
        assert fps == ["conftest"]

    def test_writes_both_artifacts(self, tmp_path):
        sdk = self.make_sdk(tmp_path)
        report = sdk.evaluate(MINI_REPO, ANSWER_KEY)
        assert report.json_path.exists() and report.markdown_path.exists()
        assert "Precision" in report.markdown_path.read_text(encoding="utf-8")
        assert "confusion matrix:" in str(report)

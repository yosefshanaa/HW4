"""Tests for fixloop.loop — scripted collaborators, every exit path."""

import json

from hw4.constants import EdgeEvidence, FindingKind, FindingStatus, StopReason
from hw4.services.detectors.base import EvidenceLink, Finding
from hw4.services.fixloop.applier import ApplyResult
from hw4.services.fixloop.loop import FixLoop
from hw4.shared.config import Config

from .test_config import write_config_dir
from .test_graph_diff import make_graph, make_metrics


class FakeApplier:
    """Scripted apply/test results; records reverts."""

    def __init__(self, test_results):
        self.test_results = list(test_results)
        self.reverts = []
        self.applies = []

    def apply(self, fix_plan):
        self.applies.append(fix_plan.finding_id)
        return ApplyResult(f"fix/{fix_plan.finding_id}", "base-sha", ("app/big.py",))

    def run_tests(self):
        return self.test_results.pop(0)

    def revert(self, base_sha):
        self.reverts.append(base_sha)


def make_finding(fid="F-001"):
    return Finding(
        id=fid, kind=FindingKind.GOD_NODE, nodes=["big"],
        status=FindingStatus.VALIDATED,
        evidence_chain=[EvidenceLink("obs", "calls", EdgeEvidence.EXTRACTED, 0.9, "app/big.py")],
    )


def graph_builder(scores):
    """iteration -> (graph, metrics with scripted bottleneck score, hash)."""
    def build(iteration):
        graph = make_graph(["a", "b"], [("a", "b")], iteration=iteration)
        score = scores[min(iteration, len(scores) - 1)]
        return graph, make_metrics(score, iteration=iteration), f"hash-{iteration}-{score}"
    return build


def make_loop(tmp_path, applier, scores, max_iterations=3, budget=lambda: False):
    setup = {
        "version": "1.00", "paths": {"results": "results"},
        "loop": {"max_iterations": max_iterations, "metric_improvement_threshold": 0.1,
                 "step_timeout_seconds": 300},
    }
    cfg = Config(write_config_dir(tmp_path / "cfg", setup=setup), environ={})
    return FixLoop(cfg, applier, graph_builder(scores), tmp_path / "loop_log.json",
                   budget, covered_files={"app/big.py"})


class TestExitPaths:
    def test_good_fix_reaches_goal_metric(self, tmp_path):
        """T331: green tests + improved metric -> accepted + GOAL_METRIC_REACHED."""
        applier = FakeApplier(test_results=[True])
        finding = make_finding()
        loop = make_loop(tmp_path, applier, scores=[1.0, 0.5])
        report = loop.run([finding], base_iteration=0)
        assert report["stop_reason"] == StopReason.GOAL_METRIC_REACHED.value
        assert report["iterations"][0]["accepted"] is True
        assert finding.status is FindingStatus.FIXED
        assert not applier.reverts

    def test_bad_fix_reverts_and_blocks_then_no_safe_action(self, tmp_path):
        """T332: red tests -> revert -> blocked -> NO_SAFE_ACTION (nothing left)."""
        applier = FakeApplier(test_results=[False])
        finding = make_finding()
        loop = make_loop(tmp_path, applier, scores=[1.0, 1.0])
        report = loop.run([finding], base_iteration=0)
        assert report["stop_reason"] == StopReason.NO_SAFE_ACTION.value
        assert applier.reverts == ["base-sha"]
        assert finding.status is FindingStatus.BLOCKED

    def test_max_iterations_path(self, tmp_path):
        """T333: neutral green iterations exhaust the cap."""
        applier = FakeApplier(test_results=[True, True])
        findings = [make_finding("F-001"), make_finding("F-002"), make_finding("F-003")]
        loop = make_loop(tmp_path, applier, scores=[1.0, 1.0, 1.0], max_iterations=2)
        report = loop.run(findings, base_iteration=0)
        assert report["stop_reason"] == StopReason.MAX_ITERATIONS.value
        assert len(report["iterations"]) == 2

    def test_budget_stop(self, tmp_path):
        applier = FakeApplier(test_results=[True])
        loop = make_loop(tmp_path, applier, scores=[1.0, 1.0], budget=lambda: True)
        report = loop.run([make_finding()], base_iteration=0)
        assert report["stop_reason"] == StopReason.BUDGET_EXCEEDED.value

    def test_no_plannable_findings_is_honest_no_safe_action(self, tmp_path):
        unplannable = make_finding()
        unplannable.status = FindingStatus.HYPOTHESIS
        loop = make_loop(tmp_path, FakeApplier([]), scores=[1.0])
        report = loop.run([unplannable], base_iteration=0)
        assert report["stop_reason"] == StopReason.NO_SAFE_ACTION.value
        assert report["iterations"] == []


class TestLogDiscipline:
    def test_every_iteration_logged_with_graph_hashes(self, tmp_path):
        """T335: re-graph happens inside EVERY iteration and is recorded."""
        applier = FakeApplier(test_results=[True])
        loop = make_loop(tmp_path, applier, scores=[1.0, 0.5])
        loop.run([make_finding()], base_iteration=0)
        log = json.loads((tmp_path / "loop_log.json").read_text())
        entry = log["iterations"][0]
        assert entry["graph_hash_before"] == "hash-0-1.0"
        assert entry["graph_hash_after"] == "hash-1-0.5"
        assert entry["graph_hash_before"] != entry["graph_hash_after"]
        assert log["stop_reason"] == StopReason.GOAL_METRIC_REACHED.value

    def test_metric_deltas_recorded(self, tmp_path):
        applier = FakeApplier(test_results=[True])
        loop = make_loop(tmp_path, applier, scores=[1.0, 0.5])
        report = loop.run([make_finding()], base_iteration=0)
        deltas = report["iterations"][0]["metric_deltas"]
        assert deltas == {"bottleneck_before": 1.0, "bottleneck_after": 0.5,
                          "isolated_before": 0, "isolated_after": 0}

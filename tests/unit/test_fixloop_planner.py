"""Tests for fixloop.planner — strategies and the refusal doctrine."""

import pytest

from hw4.constants import EdgeEvidence, FindingKind, FindingStatus
from hw4.services.detectors.base import EvidenceLink, Finding
from hw4.services.fixloop.planner import (
    PlanRefusedError,
    covered_source_files,
    plan,
)
from hw4.services.graph_models import Graph


def make_finding(kind=FindingKind.GOD_NODE, status=FindingStatus.VALIDATED,
                 evidence=EdgeEvidence.EXTRACTED, source_file="src/big.py"):
    return Finding(
        id="F-001", kind=kind, nodes=["big"], status=status,
        evidence_chain=[EvidenceLink("obs", "calls", evidence, 0.9, source_file)],
    )


class TestPlan:
    def test_god_node_plan_structure(self):
        result = plan(make_finding(), covered_files={"src/big.py"})
        assert "extract" in result.strategy
        assert result.target_files == ("src/big.py",)
        assert result.needs_characterization is False
        assert any("test suite" in step for step in result.steps)
        assert any("rebuild the graph" in step for step in result.steps)

    def test_spof_gets_seam_strategy(self):
        result = plan(make_finding(kind=FindingKind.SPOF), covered_files={"src/big.py"})
        assert "seam" in result.strategy

    def test_uncovered_file_forces_characterization_first(self):
        result = plan(make_finding(), covered_files=set())
        assert result.needs_characterization
        assert "characterization" in result.steps[0]
        assert result.test_strategy == "characterization-first"


class TestRefusals:
    def test_hypothesis_refused(self):
        with pytest.raises(PlanRefusedError, match="validated"):
            plan(make_finding(status=FindingStatus.HYPOTHESIS), covered_files=set())

    def test_non_extracted_evidence_refused(self):
        with pytest.raises(PlanRefusedError, match="EXTRACTED"):
            plan(make_finding(evidence=EdgeEvidence.INFERRED), covered_files=set())

    @pytest.mark.parametrize("kind", [FindingKind.ISOLATED, FindingKind.DUPLICATION])
    def test_human_only_kinds_refused(self, kind):
        with pytest.raises(PlanRefusedError, match="human triage"):
            plan(make_finding(kind=kind), covered_files=set())

    def test_no_source_files_refused(self):
        with pytest.raises(PlanRefusedError, match="no source files"):
            plan(make_finding(source_file=""), covered_files=set())


class TestCoverageMap:
    def test_tested_by_edges_mark_files_covered(self):
        graph = Graph.from_dict({
            "version": "1.00",
            "nodes": [
                {"id": "app.engine", "type": "module", "label": "e",
                 "source_file": "app/engine.py"},
                {"id": "app.engine.run", "type": "function", "label": "run",
                 "source_file": "app/engine.py"},
                {"id": "app.loner", "type": "module", "label": "l",
                 "source_file": "app/loner.py"},
                {"id": "tests.test_engine", "type": "module", "label": "t",
                 "source_file": "tests/test_engine.py"},
            ],
            "edges": [
                {"src": "app.engine", "dst": "tests.test_engine",
                 "relation": "tested_by", "evidence": "EXTRACTED", "confidence": 1.0},
            ],
        })
        covered = covered_source_files(graph)
        assert "app/engine.py" in covered
        assert "app/loner.py" not in covered

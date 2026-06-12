"""Tests for the detector suite — planted defects + mandatory FP guards."""

import json

from hw4.constants import EdgeEvidence, FindingKind, FindingStatus
from hw4.services.detectors.base import EvidenceLink, Finding
from hw4.services.detectors.registry import dump_findings, run_all
from hw4.services.graph_metrics import compute
from hw4.services.graph_models import Graph
from hw4.shared.config import Config

from .test_config import write_config_dir
from .test_graph_metrics import planted_graph

DETECTOR_SETUP = {
    "version": "1.00",
    "paths": {"results": "results"},
    "metrics": {"relations": ["imports", "calls"], "top_k_bottlenecks": 5},
    "detectors": {
        "spof": {"min_mandatory_ratio": 0.3, "max_rank": 5},
        "god_node": {"degree_multiplier": 2.0, "min_fan_out": 3, "min_communities": 2},
        "isolation": {"min_size": 1},
        "traceability": {"report_undocumented": False},
        "duplication": {"min_confidence": 0.5},
    },
}


def make_config(tmp_path):
    return Config(write_config_dir(tmp_path / "cfg", setup=DETECTOR_SETUP), environ={})


def analyzed(tmp_path, graph=None):
    graph = graph or planted_graph()
    config = make_config(tmp_path)
    return run_all(graph, compute(graph, config), config), graph


def god_graph():
    """god fans out into three concerns; util has fan-in only (healthy)."""
    nodes = [{"id": n, "type": "module", "label": n}
             for n in ("god", "util", "a1", "a2", "a3", "b1", "b2", "b3", "c1")]

    def edge(src, dst):
        return {"src": src, "dst": dst, "relation": "calls",
                "evidence": "EXTRACTED", "confidence": 1.0}

    edges = [edge("god", dst) for dst in ("a1", "a2", "a3", "b1", "b2", "b3", "c1")]
    edges += [edge(src, "util") for src in ("a1", "a3", "b1", "c1")]
    edges += [edge("a1", "a2"), edge("a2", "a3"), edge("b1", "b2"), edge("b2", "b3")]
    return Graph.from_dict({"version": "1.00", "nodes": nodes, "edges": edges})


class TestFindingModel:
    def test_confidence_is_weakest_link(self):
        finding = Finding(
            id="F-001", kind=FindingKind.SPOF, nodes=["x"],
            evidence_chain=[
                EvidenceLink("a", "calls", EdgeEvidence.EXTRACTED, 0.9),
                EvidenceLink("b", "calls", EdgeEvidence.INFERRED, 0.4),
            ],
        )
        assert finding.confidence == 0.4
        assert not finding.uses_only_extracted

    def test_serialization_matches_schema(self, tmp_path):
        findings, _ = analyzed(tmp_path)
        path = dump_findings(findings, tmp_path / "findings.json", iteration=0)
        doc = json.loads(path.read_text())
        assert doc["version"] and doc["iteration"] == 0
        sample = doc["findings"][0]
        for key in ("id", "kind", "nodes", "evidence_chain", "confidence", "status"):
            assert key in sample
        assert sample["status"] == FindingStatus.HYPOTHESIS.value
        link = sample["evidence_chain"][0]
        assert set(link) == {"observation", "relation", "evidence", "confidence", "source_file"}


class TestSpof:
    def test_planted_mandatory_hub_flagged(self, tmp_path):
        findings, _ = analyzed(tmp_path)
        spofs = [f for f in findings if f.kind is FindingKind.SPOF]
        assert any(f.nodes == ["hub"] for f in spofs)

    def test_redundant_hub_not_flagged(self, tmp_path):
        """util is central by degree but every pair routes around it."""
        findings, _ = analyzed(tmp_path, graph=god_graph())
        spofs = [f for f in findings if f.kind is FindingKind.SPOF]
        assert not any("util" in f.nodes for f in spofs)


class TestGodNode:
    def test_planted_god_node_flagged_with_counter_check(self, tmp_path):
        findings, _ = analyzed(tmp_path, graph=god_graph())
        gods = [f for f in findings if f.kind is FindingKind.GOD_NODE]
        assert any(f.nodes == ["god"] for f in gods)
        evidence_text = " ".join(
            link.observation for f in gods for link in f.evidence_chain
        )
        assert "healthy-hub counter-check" in evidence_text

    def test_fan_in_utility_not_condemned(self, tmp_path):
        findings, _ = analyzed(tmp_path, graph=god_graph())
        gods = [f for f in findings if f.kind is FindingKind.GOD_NODE]
        assert not any("util" in f.nodes for f in gods)


class TestIsolation:
    def test_island_flagged_with_checklist_not_verdict(self, tmp_path):
        findings, _ = analyzed(tmp_path)
        isolated = [f for f in findings if f.kind is FindingKind.ISOLATED]
        assert len(isolated) == 1
        finding = isolated[0]
        assert set(finding.nodes) == {"o1", "o2"}
        assert len(finding.triage_checklist) == 4
        assert finding.status is FindingStatus.HYPOTHESIS
        assert not finding.uses_only_extracted  # AMBIGUOUS link blocks auto-fix


class TestTraceability:
    def test_missing_mention_becomes_trace_gap(self, tmp_path):
        raw = planted_graph().to_dict()
        raw["nodes"] += [
            {"id": "doc:README.md", "type": "doc", "label": "readme",
             "source_file": "README.md"},
            {"id": "missing:app.plugins", "type": "doc", "label": "unresolved"},
        ]
        raw["edges"].append({"src": "doc:README.md", "dst": "missing:app.plugins",
                             "relation": "mentions", "evidence": "AMBIGUOUS",
                             "confidence": 0.4})
        findings, _ = analyzed(tmp_path, graph=Graph.from_dict(raw))
        gaps = [f for f in findings if f.kind is FindingKind.TRACE_GAP]
        assert any("missing:app.plugins" in f.nodes for f in gaps)


class TestDuplication:
    def test_similarity_pair_is_hypothesis_with_checklist(self, tmp_path):
        raw = planted_graph().to_dict()
        raw["edges"].append({"src": "a1", "dst": "b1",
                             "relation": "semantically_similar_to",
                             "evidence": "INFERRED", "confidence": 0.8})
        findings, _ = analyzed(tmp_path, graph=Graph.from_dict(raw))
        dups = [f for f in findings if f.kind is FindingKind.DUPLICATION]
        assert len(dups) == 1
        assert "purpose" in dups[0].triage_checklist[0]
        assert "delete" not in dups[0].suggested_action


class TestRegistry:
    def test_ids_stable_and_ranked(self, tmp_path):
        findings, _ = analyzed(tmp_path)
        assert [f.id for f in findings] == [f"F-{i:03d}" for i in range(1, len(findings) + 1)]
        confidences_x_impact_ordering = [f.kind for f in findings]
        assert confidences_x_impact_ordering[0] is FindingKind.SPOF  # hub outranks island

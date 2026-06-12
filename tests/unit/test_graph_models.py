"""Tests for hw4.services.graph_models — contract validation at the boundary."""

import json

import pytest

from hw4.constants import EdgeEvidence
from hw4.services.graph_models import Graph, GraphValidationError
from hw4.shared.version import ConfigVersionError


def raw_graph(**overrides):
    base = {
        "version": "1.00",
        "iteration": 0,
        "backend": "ast_extractor",
        "nodes": [
            {"id": "m.a", "type": "module", "label": "a", "source_file": "a.py", "community": 0},
            {"id": "m.b", "type": "module", "label": "b", "source_file": "b.py", "community": 1},
            {"id": "d.readme", "type": "doc", "label": "README"},
        ],
        "edges": [
            {"src": "m.a", "dst": "m.b", "relation": "imports",
             "evidence": "EXTRACTED", "confidence": 1.0},
            {"src": "d.readme", "dst": "m.a", "relation": "mentions",
             "evidence": "INFERRED", "confidence": 0.7},
        ],
    }
    base.update(overrides)
    return base


class TestParsing:
    def test_round_trip_preserves_everything(self, tmp_path):
        graph = Graph.from_dict(raw_graph())
        path = graph.dump(tmp_path / "graphs" / "g.json")
        reloaded = Graph.load(path)
        assert reloaded.to_dict() == graph.to_dict()
        assert reloaded.backend == "ast_extractor"

    def test_dangling_edge_endpoint_is_an_error(self):
        bad = raw_graph(edges=[{"src": "m.a", "dst": "ghost", "relation": "calls",
                                "evidence": "EXTRACTED", "confidence": 1.0}])
        with pytest.raises(GraphValidationError, match="dangling"):
            Graph.from_dict(bad)

    def test_unknown_node_type_is_an_error(self):
        bad = raw_graph(nodes=[{"id": "x", "type": "banana", "label": "x"}])
        with pytest.raises(GraphValidationError, match="banana"):
            Graph.from_dict(bad)

    def test_version_mismatch_rejected(self):
        with pytest.raises(ConfigVersionError, match="graph.json"):
            Graph.from_dict(raw_graph(version="9.00"))

    def test_malformed_json_raises(self, tmp_path):
        path = tmp_path / "g.json"
        path.write_text("{not json")
        with pytest.raises(json.JSONDecodeError):
            Graph.load(path)

    def test_unknown_extra_fields_tolerated(self):
        raw = raw_graph()
        raw["nodes"][0]["surprise"] = "ok"
        raw["edges"][0]["weight"] = 3
        graph = Graph.from_dict(raw)
        assert graph.nodes["m.a"].label == "a"


class TestConservativeDefaults:
    def test_missing_evidence_degrades_to_ambiguous(self):
        raw = raw_graph()
        del raw["edges"][1]["evidence"]
        graph = Graph.from_dict(raw)
        assert graph.edges[1].evidence is EdgeEvidence.AMBIGUOUS

    def test_unknown_evidence_value_degrades_to_ambiguous(self):
        raw = raw_graph()
        raw["edges"][0]["evidence"] = "TRUST_ME"
        assert Graph.from_dict(raw).edges[0].evidence is EdgeEvidence.AMBIGUOUS

    def test_unknown_relation_preserved_verbatim(self):
        raw = raw_graph()
        raw["edges"][0]["relation"] = "summons"
        assert Graph.from_dict(raw).edges[0].relation == "summons"

    def test_evidence_serialized_as_string_value(self):
        dumped = Graph.from_dict(raw_graph()).to_dict()
        assert dumped["edges"][0]["evidence"] in {"EXTRACTED", "INFERRED", "AMBIGUOUS"}

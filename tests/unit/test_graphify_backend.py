"""Graphify ingestion backend tests — node-link normalization + CLI path (ADR-4)."""

import json
import sys
from pathlib import Path

import pytest

from hw4.constants import EdgeEvidence
from hw4.services.extractor import graphify
from hw4.services.graph_models import GraphValidationError
from hw4.services.graph_runner import GraphRunner
from hw4.shared.config import Config

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "graphify_sample"
CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"


def cfg(environ=None):
    return Config(CONFIG_DIR, environ=environ or {})


class TestNormalize:
    def test_ingests_nodelink_graph(self):
        graph = graphify.extract(FIXTURE, cfg(), iteration=3)
        assert graph.backend == graphify.BACKEND_ID
        assert graph.iteration == 3
        assert set(graph.nodes) == {"app.engine", "app.engine.run", "app.utils", "doc:README.md"}

    def test_node_types_explicit_and_filetype_fallback(self):
        graph = graphify.extract(FIXTURE, cfg())
        assert graph.nodes["app.engine.run"].type == "function"  # explicit fine type
        assert graph.nodes["app.engine"].type == "module"
        assert graph.nodes["doc:README.md"].type == "doc"  # file_type=document fallback

    def test_edges_carry_evidence_and_confidence(self):
        graph = graphify.extract(FIXTURE, cfg())
        by_rel = {e.relation: e for e in graph.edges}
        assert by_rel["imports"].evidence is EdgeEvidence.EXTRACTED
        assert by_rel["imports"].confidence == 1.0
        mentions = by_rel["mentions"]
        assert mentions.evidence is EdgeEvidence.INFERRED
        assert mentions.confidence == pytest.approx(0.66)


class TestNodeAndEdgeMapping:
    def test_unmappable_node_type_raises(self):
        with pytest.raises(graphify.GraphifySchemaError):
            graphify._node({"id": "x", "file_type": "spreadsheet"})

    def test_unknown_evidence_degrades_to_ambiguous(self, tmp_path):
        raw = {
            "nodes": [
                {"id": "a", "type": "module", "source_file": "a.py"},
                {"id": "b", "type": "module", "source_file": "b.py"},
            ],
            "links": [{"source": "a", "target": "b", "relation": "calls", "confidence": "MAYBE"}],
        }
        (tmp_path / "graph.json").write_text(json.dumps(raw), encoding="utf-8")
        graph = graphify.extract(tmp_path, cfg())
        assert graph.edges[0].evidence is EdgeEvidence.AMBIGUOUS

    def test_dangling_edge_fails_at_the_boundary(self, tmp_path):
        raw = {
            "nodes": [{"id": "a", "type": "module"}],
            "links": [{"source": "a", "target": "ghost", "relation": "calls", "confidence": "EXTRACTED"}],
        }
        (tmp_path / "graph.json").write_text(json.dumps(raw), encoding="utf-8")
        with pytest.raises(GraphValidationError):
            graphify.extract(tmp_path, cfg())


class TestResolution:
    def test_missing_graph_json_without_command_errors(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="no graph.json"):
            graphify.extract(tmp_path, cfg())

    def test_runs_configured_command_to_produce_graph_json(self, tmp_path):
        script = "import shutil, sys; shutil.copy(sys.argv[1], 'graph.json')"
        command = [sys.executable, "-c", script, str(FIXTURE / "graph.json")]
        environ = {"HW4__graph__graphify__command": json.dumps(command)}
        graph = graphify.extract(tmp_path, cfg(environ))
        assert "app.engine" in graph.nodes
        assert (tmp_path / "graph.json").exists()


class TestRunnerSelector:
    def test_backend_config_routes_to_graphify(self, tmp_path):
        environ = {
            "HW4__graph__backend": "graphify",
            "HW4__graph__graphify__graph_json": str(FIXTURE / "graph.json"),
        }
        runner = GraphRunner(cfg(environ), results_dir=tmp_path / "results")
        record = runner.build(FIXTURE, iteration=0)
        graph = runner.graph_path(0)
        assert record.nodes == 4
        assert json.loads(graph.read_text())["backend"] == graphify.BACKEND_ID

    def test_unknown_backend_rejected(self, tmp_path):
        runner = GraphRunner(cfg({"HW4__graph__backend": "neo4j"}), results_dir=tmp_path)
        with pytest.raises(ValueError, match="unknown graph.backend"):
            runner.build(FIXTURE, iteration=0)

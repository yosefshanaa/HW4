"""Tests for the AST extraction backend — mini_repo is the answer key."""

from pathlib import Path

import pytest

from hw4.constants import EdgeEvidence
from hw4.services.extractor import BACKEND_ID, extract
from hw4.shared.config import Config

from .test_config import write_config_dir

MINI_REPO = Path(__file__).resolve().parents[1] / "fixtures" / "mini_repo"


@pytest.fixture(scope="module")
def graph(tmp_path_factory):
    setup = {
        "version": "1.00",
        "paths": {"results": "results"},
        "graph": {
            "exclude_dirs": [".git", "__pycache__"],
            "doc_suffixes": [".md"],
            "max_mentions_per_doc": 50,
        },
    }
    cfg_dir = write_config_dir(tmp_path_factory.mktemp("cfg"), setup=setup)
    return extract(MINI_REPO, Config(cfg_dir, environ={}))


def edge_set(graph, relation):
    return {(e.src, e.dst) for e in graph.edges if e.relation == relation}


class TestNodes:
    def test_all_modules_present(self, graph):
        for module in ("app", "app.engine", "app.models", "app.utils", "orphan.legacy"):
            assert module in graph.nodes
            assert graph.nodes[module].type == "module"

    def test_functions_classes_and_methods(self, graph):
        assert graph.nodes["app.engine.run"].type == "function"
        assert graph.nodes["app.models.Sample"].type == "class"
        assert graph.nodes["app.models.Sample.bounded"].type == "function"

    def test_backend_stamped(self, graph):
        assert graph.backend == BACKEND_ID


class TestCodeEdges:
    def test_god_node_imports_every_sibling(self, graph):
        imports = edge_set(graph, "imports")
        for target in ("app.models", "app.reports", "app.utils"):
            assert ("app.engine", target) in imports

    def test_local_and_imported_calls_extracted(self, graph):
        calls = edge_set(graph, "calls")
        assert ("app.engine.run", "app.engine.parse") in calls  # local
        assert ("app.engine.run", "app.reports.render") in calls  # imported
        assert ("app.models.Sample.bounded", "app.utils.clamp") in calls

    def test_call_evidence_is_extracted_at_full_confidence(self, graph):
        edge = next(
            e for e in graph.edges
            if (e.src, e.dst) == ("app.engine.run", "app.engine.parse")
        )
        assert edge.evidence is EdgeEvidence.EXTRACTED and edge.confidence == 1.0

    def test_test_module_yields_tested_by(self, graph):
        assert ("app.engine", "tests.test_engine") in edge_set(graph, "tested_by")

    def test_containment_keeps_code_connected(self, graph):
        implements = edge_set(graph, "implements")
        assert ("app.engine", "app") in implements
        assert ("app.models.Sample.bounded", "app.models.Sample") in implements
        assert ("orphan.legacy", "orphan") in implements


class TestDocLayer:
    def test_readme_mentions_real_modules_as_inferred(self, graph):
        mention = next(
            e for e in graph.edges
            if e.relation == "mentions" and e.dst == "app.engine"
        )
        assert mention.evidence is EdgeEvidence.INFERRED

    def test_planted_lie_becomes_missing_node_with_ambiguous_edge(self, graph):
        assert "missing:app.plugins" in graph.nodes
        gap = next(e for e in graph.edges if e.dst == "missing:app.plugins")
        assert gap.evidence is EdgeEvidence.AMBIGUOUS
        assert gap.src.startswith("doc:")

    def test_rationale_nodes_attached_to_modules(self, graph):
        assert "rationale:app.engine.doc" in graph.nodes
        assert ("rationale:app.engine.doc", "app.engine") in edge_set(graph, "rationale_for")


class TestIsolationGroundTruth:
    def test_orphan_has_no_inbound_code_edges_from_app(self, graph):
        inbound = {
            e.src for e in graph.edges
            if e.dst.startswith("orphan") and e.relation in ("imports", "calls")
        }
        assert not inbound


class TestMentionResolution:
    def test_reexport_mention_resolves_to_defining_module(self, graph):
        from hw4.services.extractor.docs import _resolve

        ids = {"werkzeug", "werkzeug.serving", "werkzeug.serving.run_simple",
               "werkzeug.wrappers.Request"}
        resolved = _resolve("werkzeug.run_simple", ids, {"werkzeug"})
        assert resolved[0] == "werkzeug.serving.run_simple"
        assert resolved[1] is EdgeEvidence.INFERRED

    def test_external_dotted_names_ignored(self, graph):
        from hw4.services.extractor.docs import _resolve

        assert _resolve("docs.pytest.org", {"werkzeug.http"}, {"werkzeug"}) is None

    def test_ambiguous_reexport_refused(self, graph):
        from hw4.services.extractor.docs import _resolve

        ids = {"werkzeug.serving.run_simple", "werkzeug.test.run_simple"}
        assert _resolve("werkzeug.run_simple", ids, {"werkzeug"}) is None

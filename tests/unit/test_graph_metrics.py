"""Tests for hw4.services.graph_metrics — planted topology, known answers."""

import json

from hw4.services.graph_metrics import compute
from hw4.services.graph_models import Graph
from hw4.shared.config import Config

from .test_config import write_config_dir


def make_config(tmp_path):
    setup = {
        "version": "1.00",
        "paths": {"results": "results"},
        "metrics": {"relations": ["imports", "calls"], "top_k_bottlenecks": 5},
    }
    return Config(write_config_dir(tmp_path / "cfg", setup=setup), environ={})


def planted_graph():
    """Two 3-node communities joined ONLY through `hub`, plus an island."""
    nodes, edges = [], []

    def node(nid):
        nodes.append({"id": nid, "type": "module", "label": nid})

    def edge(src, dst, relation="calls"):
        edges.append({"src": src, "dst": dst, "relation": relation,
                      "evidence": "EXTRACTED", "confidence": 1.0})

    for nid in ("a1", "a2", "a3", "hub", "b1", "b2", "b3", "o1", "o2", "doc1"):
        node(nid)
    edge("a1", "a2"), edge("a2", "a3"), edge("a3", "hub"), edge("a1", "hub")
    edge("hub", "b1"), edge("b1", "b2"), edge("b2", "b3"), edge("hub", "b3")
    edge("o1", "o2")  # island
    edge("doc1", "hub", relation="mentions")  # non-dependency: must be ignored
    return Graph.from_dict({"version": "1.00", "nodes": nodes, "edges": edges})


class TestCompute:
    def test_hub_has_top_betweenness(self, tmp_path):
        metrics = compute(planted_graph(), make_config(tmp_path))
        top = max(metrics.betweenness, key=metrics.betweenness.get)
        assert top == "hub"

    def test_hub_is_the_top_bottleneck_with_high_mandatory_ratio(self, tmp_path):
        metrics = compute(planted_graph(), make_config(tmp_path))
        best = metrics.bottlenecks[0]
        assert best.node_id == "hub"
        assert best.rank == 1
        assert best.mandatory_path_ratio > 0.5  # removal splits a from b
        assert best.score > 0

    def test_rubric_reports_relation_profile_not_verdict(self, tmp_path):
        metrics = compute(planted_graph(), make_config(tmp_path))
        profile = metrics.bottlenecks[0].relation_profile
        assert profile["calls"] == 4
        assert profile["mentions"] == 1  # full relation context for the human

    def test_island_listed_as_isolated_component(self, tmp_path):
        metrics = compute(planted_graph(), make_config(tmp_path))
        assert ["o1", "o2"] in metrics.isolated_components

    def test_communities_found_on_both_sides(self, tmp_path):
        metrics = compute(planted_graph(), make_config(tmp_path))
        assert metrics.community_count >= 2
        assert metrics.community_of["a1"] != metrics.community_of["b1"]

    def test_bridge_through_hub_detected(self, tmp_path):
        metrics = compute(planted_graph(), make_config(tmp_path))
        flat = {tuple(b) for b in metrics.bridges}
        assert ("o1", "o2") in flat or ("o2", "o1") in flat

    def test_non_dependency_relations_excluded_from_degree(self, tmp_path):
        metrics = compute(planted_graph(), make_config(tmp_path))
        assert metrics.fan_in["hub"] == 2  # a3->hub, a1->hub; mentions ignored


class TestPersistence:
    def test_dump_round_trips_as_json(self, tmp_path):
        metrics = compute(planted_graph(), make_config(tmp_path))
        path = metrics.dump(tmp_path / "results" / "graphs" / "i00" / "metrics.json")
        doc = json.loads(path.read_text())
        assert doc["community_count"] >= 2
        assert doc["bottlenecks"][0]["node_id"] == "hub"

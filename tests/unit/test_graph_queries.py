"""Tests for hw4.services.graph_queries — caps and determinism matter most."""

import pytest

from hw4.constants import EdgeEvidence
from hw4.services.graph_models import Graph
from hw4.services.graph_queries import (
    edges_by_evidence,
    ego_subgraph,
    neighbors,
    nodes_by_type,
)


def chain_graph(n=6):
    """hub -> s1..s{n-1} star plus a chain s1->s2->s3 for radius tests."""
    nodes = [{"id": "hub", "type": "module", "label": "hub"}]
    edges = []
    for i in range(1, n):
        nodes.append({"id": f"s{i}", "type": "function", "label": f"s{i}"})
        edges.append({"src": "hub", "dst": f"s{i}", "relation": "calls",
                      "evidence": "EXTRACTED", "confidence": 1.0})
    nodes.append({"id": "far", "type": "doc", "label": "far"})
    edges.append({"src": "s1", "dst": "far", "relation": "mentions",
                  "evidence": "INFERRED", "confidence": 0.6})
    return Graph.from_dict({"version": "1.00", "nodes": nodes, "edges": edges})


class TestBasicQueries:
    def test_neighbors_bidirectional_sorted(self):
        graph = chain_graph(4)
        assert neighbors(graph, "s1") == ["far", "hub"]

    def test_nodes_by_type(self):
        graph = chain_graph(3)
        assert {n.id for n in nodes_by_type(graph, "doc")} == {"far"}

    def test_edges_by_evidence(self):
        graph = chain_graph(3)
        assert len(edges_by_evidence(graph, EdgeEvidence.INFERRED)) == 1


class TestEgoSubgraph:
    def test_radius_bounds_expansion(self):
        graph = chain_graph(4)
        ego1 = ego_subgraph(graph, "hub", radius=1, max_nodes=50)
        assert set(ego1.nodes) == {"hub", "s1", "s2", "s3"}  # 'far' is 2 hops out
        ego2 = ego_subgraph(graph, "hub", radius=2, max_nodes=50)
        assert "far" in ego2.nodes

    def test_cap_limits_node_count_deterministically(self):
        graph = chain_graph(6)
        capped = ego_subgraph(graph, "hub", radius=2, max_nodes=3)
        assert len(capped.nodes) == 3
        again = ego_subgraph(graph, "hub", radius=2, max_nodes=3)
        assert set(capped.nodes) == set(again.nodes)  # same cap -> same context

    def test_kept_edges_only_between_selected_nodes(self):
        graph = chain_graph(4)
        ego = ego_subgraph(graph, "s1", radius=1, max_nodes=50)
        for edge in ego.edges:
            assert edge.src in ego.nodes and edge.dst in ego.nodes

    def test_unknown_center_raises(self):
        with pytest.raises(KeyError, match="ghost"):
            ego_subgraph(chain_graph(3), "ghost", radius=1, max_nodes=10)

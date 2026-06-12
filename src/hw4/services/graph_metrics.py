"""Structural metrics over the dependency graph (FR-2.5, ADR-5, T149-T152).

Metrics are computed on the *dependency* relations only (config-driven,
default imports+calls) — containment and doc edges would drown the
signal. Everything here is deterministic math; the bottleneck rubric
(T150) emits structured evidence for a human/agent verdict, never the
verdict itself (Part-C: hub-vs-bottleneck is an adjudication, not a
threshold).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

import networkx as nx

from hw4.services.graph_models import Graph
from hw4.shared.config import Config


@dataclass(frozen=True)
class BottleneckEvidence:
    """Rubric output for one suspect node — evidence, not a verdict."""

    node_id: str
    betweenness: float
    rank: int
    mandatory_path_ratio: float
    fan_in: int
    fan_out: int
    relation_profile: dict[str, int]
    score: float


@dataclass
class Metrics:
    """One iteration's structural snapshot."""

    iteration: int
    relations_considered: list[str]
    fan_in: dict[str, int] = field(default_factory=dict)
    fan_out: dict[str, int] = field(default_factory=dict)
    betweenness: dict[str, float] = field(default_factory=dict)
    community_of: dict[str, int] = field(default_factory=dict)
    community_count: int = 0
    bridges: list[list[str]] = field(default_factory=list)
    isolated_components: list[list[str]] = field(default_factory=list)
    bottlenecks: list[BottleneckEvidence] = field(default_factory=list)

    def dump(self, path: Path | str) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        doc = asdict(self)
        path.write_text(json.dumps(doc, indent=1, sort_keys=True), encoding="utf-8")
        return path


def dependency_digraph(graph: Graph, relations: list[str]) -> nx.DiGraph:
    dig = nx.DiGraph()
    dig.add_nodes_from(graph.nodes)
    for edge in graph.edges:
        if edge.relation in relations:
            dig.add_edge(edge.src, edge.dst, relation=edge.relation)
    return dig


def compute(graph: Graph, config: Config) -> Metrics:
    relations = list(config.get("metrics.relations"))
    top_k = int(config.get("metrics.top_k_bottlenecks"))
    dig = dependency_digraph(graph, relations)
    undirected = dig.to_undirected()

    betweenness = nx.betweenness_centrality(dig)
    communities = list(nx.community.greedy_modularity_communities(undirected))
    community_of = {n: i for i, members in enumerate(communities) for n in members}
    components = sorted(nx.connected_components(undirected), key=len, reverse=True)

    metrics = Metrics(
        iteration=graph.iteration,
        relations_considered=relations,
        fan_in={n: dig.in_degree(n) for n in dig},
        fan_out={n: dig.out_degree(n) for n in dig},
        betweenness=betweenness,
        community_of=community_of,
        community_count=len(communities),
        bridges=sorted(sorted(pair) for pair in nx.bridges(undirected)),
        isolated_components=[sorted(c) for c in components[1:]],
    )
    metrics.bottlenecks = _bottleneck_rubric(graph, dig, undirected, betweenness, top_k)
    return metrics


def _bottleneck_rubric(graph, dig, undirected, betweenness, top_k) -> list[BottleneckEvidence]:
    ranked = sorted(betweenness.items(), key=lambda kv: -kv[1])[:top_k]
    max_b = ranked[0][1] if ranked and ranked[0][1] > 0 else 1.0
    evidence = []
    for rank, (node, value) in enumerate(ranked, start=1):
        if value <= 0:
            break
        ratio = _mandatory_path_ratio(undirected, node)
        profile: dict[str, int] = {}
        for edge in graph.edges:
            if node in (edge.src, edge.dst):
                profile[edge.relation] = profile.get(edge.relation, 0) + 1
        evidence.append(
            BottleneckEvidence(
                node_id=node,
                betweenness=round(value, 6),
                rank=rank,
                mandatory_path_ratio=round(ratio, 4),
                fan_in=dig.in_degree(node),
                fan_out=dig.out_degree(node),
                relation_profile=profile,
                score=round((value / max_b) * ratio, 4),
            )
        )
    return evidence


def _mandatory_path_ratio(undirected: nx.Graph, node: str) -> float:
    """Share of formerly-connected pairs that disconnect without `node`."""
    component = nx.node_connected_component(undirected, node)
    others = component - {node}
    size = len(others)
    pairs_before = size * (size - 1) / 2
    if pairs_before == 0:
        return 0.0
    remaining = undirected.subgraph(others)
    pairs_after = sum(
        len(c) * (len(c) - 1) / 2 for c in nx.connected_components(remaining)
    )
    return (pairs_before - pairs_after) / pairs_before

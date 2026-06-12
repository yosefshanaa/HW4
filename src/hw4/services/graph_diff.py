"""Iteration-to-iteration graph diff + verdict helper (FR-2.7, T153-T156).

The fix loop's claim "this refactor improved the architecture" is only
credible as a measured delta between immutable graph iterations. The
verdict thresholds come from config (loop.metric_improvement_threshold);
the primary goal metric is the top bottleneck score, secondary is the
isolated-component count.

Known limitation (T156, documented honestly): a bottleneck that is
merely *renamed* would appear as remove+add. We flag suspected renames —
removed/added node pairs whose neighbor sets are identical after the
swap — as `possible_renames` so the QA step treats such an "improvement"
with suspicion; we do not claim to fully solve rename detection.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from hw4.services.graph_metrics import Metrics
from hw4.services.graph_models import Graph
from hw4.shared.config import Config

IMPROVED = "improved"
REGRESSED = "regressed"
NEUTRAL = "neutral"


@dataclass(frozen=True)
class GraphDelta:
    """Structural change between two graph iterations."""

    iteration_before: int
    iteration_after: int
    nodes_added: list[str]
    nodes_removed: list[str]
    edges_added: list[tuple[str, str, str]]
    edges_removed: list[tuple[str, str, str]]
    top_bottleneck_before: float
    top_bottleneck_after: float
    isolated_before: int
    isolated_after: int
    community_before: int
    community_after: int
    possible_renames: list[tuple[str, str]] = field(default_factory=list)

    @property
    def bottleneck_improvement(self) -> float:
        """Relative reduction of the top bottleneck score (positive = better)."""
        if self.top_bottleneck_before <= 0:
            return 0.0
        return (self.top_bottleneck_before - self.top_bottleneck_after) / (
            self.top_bottleneck_before
        )


def diff(before: Graph, after: Graph, m_before: Metrics, m_after: Metrics) -> GraphDelta:
    before_edges = {(e.src, e.dst, e.relation) for e in before.edges}
    after_edges = {(e.src, e.dst, e.relation) for e in after.edges}
    nodes_added = sorted(set(after.nodes) - set(before.nodes))
    nodes_removed = sorted(set(before.nodes) - set(after.nodes))
    return GraphDelta(
        iteration_before=before.iteration,
        iteration_after=after.iteration,
        nodes_added=nodes_added,
        nodes_removed=nodes_removed,
        edges_added=sorted(after_edges - before_edges),
        edges_removed=sorted(before_edges - after_edges),
        top_bottleneck_before=_top_score(m_before),
        top_bottleneck_after=_top_score(m_after),
        isolated_before=len(m_before.isolated_components),
        isolated_after=len(m_after.isolated_components),
        community_before=m_before.community_count,
        community_after=m_after.community_count,
        possible_renames=_suspect_renames(before, after, nodes_removed, nodes_added),
    )


def judge(delta: GraphDelta, config: Config) -> str:
    """improved / regressed / neutral vs the configured threshold."""
    threshold = float(config.get("loop.metric_improvement_threshold"))
    primary = delta.bottleneck_improvement
    if primary >= threshold or (primary >= 0 and delta.isolated_after < delta.isolated_before):
        return IMPROVED
    if primary <= -threshold or delta.isolated_after > delta.isolated_before:
        return REGRESSED
    return NEUTRAL


def _top_score(metrics: Metrics) -> float:
    """Max bottleneck SCORE — the list is rank-ordered by betweenness, and
    a rank-1 node with mandatory ratio 0 scores 0 (live bug, 2026-06-12)."""
    return max((b.score for b in metrics.bottlenecks), default=0.0)


def _neighbor_sets(graph: Graph) -> dict[str, frozenset]:
    neighbors: dict[str, set] = {node: set() for node in graph.nodes}
    for edge in graph.edges:
        neighbors[edge.src].add(edge.dst)
        neighbors[edge.dst].add(edge.src)
    return {n: frozenset(adj) for n, adj in neighbors.items()}


def _suspect_renames(before, after, removed: list[str], added: list[str]):
    if not removed or not added:
        return []
    nb_before, nb_after = _neighbor_sets(before), _neighbor_sets(after)
    suspects = []
    for old in removed:
        old_neighbors = nb_before[old]
        for new in added:
            renamed = frozenset(new if n == old else n for n in old_neighbors)
            if nb_after[new] in (renamed - {new}, renamed):
                suspects.append((old, new))
    return suspects

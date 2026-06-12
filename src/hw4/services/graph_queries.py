"""Read-side convenience queries over a Graph (FR-2, FR-3.4 retrieval).

Split from graph_models to keep both under the 150-line gate and because
they evolve for different reasons: the contract is frozen, the queries
grow with retrieval needs. ego_subgraph is THE token lever — a bounded
neighborhood instead of a file dump is what Condition B sells (PLAN §2.4),
so its cap behavior is deterministic and tested.
"""

from __future__ import annotations

from collections import deque

from hw4.constants import EdgeEvidence
from hw4.services.graph_models import Edge, Graph, Node


def neighbors(graph: Graph, node_id: str) -> list[str]:
    """Adjacent node ids (both directions), sorted, deduplicated."""
    found = {e.dst for e in graph.edges if e.src == node_id}
    found |= {e.src for e in graph.edges if e.dst == node_id}
    found.discard(node_id)
    return sorted(found)


def nodes_by_type(graph: Graph, node_type: str) -> list[Node]:
    return [node for node in graph.nodes.values() if node.type == node_type]


def edges_by_evidence(graph: Graph, evidence: EdgeEvidence) -> list[Edge]:
    return [edge for edge in graph.edges if edge.evidence == evidence]


def ego_subgraph(graph: Graph, center: str, radius: int, max_nodes: int) -> Graph:
    """Bounded BFS neighborhood around `center`.

    Deterministic under the cap: nodes admitted breadth-first, sorted by
    id within each ring, so the same question always yields the same
    context (the experiment depends on this).
    """
    if center not in graph.nodes:
        raise KeyError(f"unknown node {center!r}")
    selected = {center}
    queue = deque([(center, 0)])
    while queue and len(selected) < max_nodes:
        node_id, depth = queue.popleft()
        if depth >= radius:
            continue
        for neighbor in neighbors(graph, node_id):
            if neighbor in selected:
                continue
            selected.add(neighbor)
            queue.append((neighbor, depth + 1))
            if len(selected) >= max_nodes:
                break
    kept_edges = [e for e in graph.edges if e.src in selected and e.dst in selected]
    return Graph(
        version=graph.version,
        iteration=graph.iteration,
        backend=graph.backend,
        nodes={node_id: graph.nodes[node_id] for node_id in sorted(selected)},
        edges=kept_edges,
    )

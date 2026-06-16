"""Render a graph.json into a PNG (graphify-style visualization).

Usage: python scripts/render_graph.py <graph.json> <out.png> "<title>"
Deterministic layout (seeded) so re-renders are stable. Nodes are coloured
by type so module/function/doc structure is readable at a glance.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx

COLORS = {
    "module": "#4C78A8",
    "function": "#54A24B",
    "class": "#E45756",
    "doc": "#F58518",
    "rationale": "#BAB0AC",
}


def _short(node_id: str) -> str:
    return node_id.split(".")[-1].removeprefix("missing:").removeprefix("doc:")


def render(graph_path: str, out_path: str, title: str) -> None:
    raw = json.loads(Path(graph_path).read_text(encoding="utf-8"))
    types = {node["id"]: node.get("type", "") for node in raw["nodes"]}
    graph = nx.DiGraph()
    graph.add_nodes_from(node["id"] for node in raw["nodes"])
    graph.add_edges_from((edge["src"], edge["dst"]) for edge in raw["edges"])
    pos = nx.spring_layout(graph, seed=7, k=0.9)
    colors = [COLORS.get(types.get(node, ""), "#CCCCCC") for node in graph.nodes]
    fig, ax = plt.subplots(figsize=(11, 8))
    nx.draw_networkx_edges(graph, pos, ax=ax, edge_color="#999999", arrows=True, alpha=0.6)
    nx.draw_networkx_nodes(graph, pos, ax=ax, node_color=colors, node_size=900, alpha=0.95)
    nx.draw_networkx_labels(
        graph, pos, ax=ax, labels={n: _short(n) for n in graph.nodes}, font_size=8
    )
    ax.set_title(title, fontsize=13)
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(out_path, dpi=140)
    print("wrote", out_path)


if __name__ == "__main__":
    render(sys.argv[1], sys.argv[2], sys.argv[3])

"""Convert a graph.json into a folder of linked Obsidian notes.

One note per code node (module/function/class); every dependency edge becomes
a `[[wikilink]]`, so Obsidian's graph view renders the code structure. Used to
visualize the buggy-python before/after graphs in the same style as the rest
of the vault. Deterministic, no LLM.

Usage: python scripts/graph_to_vault.py <graph.json> <vault_dir> <project>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

CODE_TYPES = {"module", "function", "class"}


def build(graph_path: str, vault_dir: str, project: str) -> None:
    raw = json.loads(Path(graph_path).read_text(encoding="utf-8"))
    keep = {node["id"]: node for node in raw["nodes"] if node.get("type") in CODE_TYPES}
    links: dict[str, list[str]] = {node_id: [] for node_id in keep}
    for edge in raw["edges"]:
        if edge["src"] in keep and edge["dst"] in keep:
            links[edge["src"]].append(f"[[{edge['dst']}]] ({edge['relation']})")
    out = Path(vault_dir) / "20_Projects" / project
    out.mkdir(parents=True, exist_ok=True)
    for node_id, node in keep.items():
        link_lines = [f"- {link}" for link in links[node_id]] or ["- (no outgoing edges)"]
        body = [
            f"---\ntype: {node['type']}\nstatus: generated\nproject: {project}\n---",
            f"# {node_id}",
            f"`{node['type']}` · `{node.get('source_file', '')}`",
            "",
            "## Links",
            *link_lines,
        ]
        (out / f"{node_id}.md").write_text("\n".join(body) + "\n", encoding="utf-8")
    print(f"wrote {len(keep)} notes -> {out}")


if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2], sys.argv[3])

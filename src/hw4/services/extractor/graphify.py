"""Graphify ingestion backend (ADR-4) — normalize a real graph.json.

Graphify (safishamsi/graphify, graphify.net) is the course's Tree-sitter
knowledge-graph tool. It emits graph.json in NetworkX *node-link* format;
this module adapts that genuine output into the PLAN §2.1 contract, so a
real Graphify run is a drop-in alternative to the in-repo AST backend
(which stays the default for reproducibility — see ADR-4). The work is
pure translation: `links` -> edges, `source`/`target` -> `src`/`dst`,
Graphify's `confidence` evidence class -> our `evidence` (+ its
`confidence_score` -> our confidence), `file_type` -> node type. All
validation stays at the single boundary (`Graph.from_dict`), so a
malformed Graphify graph fails loudly there, not downstream.
"""

from __future__ import annotations

import json
from pathlib import Path

from hw4.services.graph_models import NODE_TYPES, Graph
from hw4.shared.config import Config
from hw4.shared.process_runner import ProcessRunner
from hw4.shared.version import __version__

BACKEND_ID = f"graphify_adapter/{__version__}"
# Graphify's coarse modality -> our node type; fine types (function/class/
# module) pass through unchanged when Graphify already emits them.
_FILE_TYPE_TO_NODE = {
    "code": "module",
    "document": "doc",
    "paper": "doc",
    "image": "doc",
    "rationale": "rationale",
}


class GraphifySchemaError(ValueError):
    """A Graphify node carries a type we cannot map into our contract."""


def extract(root: Path | str, config: Config, iteration: int = 0) -> Graph:
    """Locate (optionally run) Graphify's graph.json and normalize it."""
    graph_json = _resolve(Path(root), config)
    raw = json.loads(graph_json.read_text(encoding="utf-8"))
    return Graph.from_dict(_normalize(raw, iteration))


def _resolve(root: Path, config: Config) -> Path:
    """Find the graph.json; run the configured Graphify command if absent."""
    configured = str(config.get("graph.graphify.graph_json", default=""))
    path = Path(configured) if configured else root / "graph.json"
    if path.exists():
        return path
    command = list(config.get("graph.graphify.command", default=[]))
    if not command:
        raise FileNotFoundError(
            f"graphify backend: no graph.json at {path} and no graph.graphify.command "
            "configured to produce one (install + run Graphify — see README)"
        )
    runner = ProcessRunner(timeout_seconds=float(config.get("repo.timeout_seconds")))
    runner.run_checked(command, cwd=root)
    if not path.exists():
        raise FileNotFoundError(f"graphify command ran but produced no {path}")
    return path


def _normalize(raw: dict, iteration: int) -> dict:
    return {
        "version": __version__,
        "iteration": iteration,
        "backend": BACKEND_ID,
        "nodes": [_node(item) for item in raw.get("nodes", [])],
        "edges": [_edge(item) for item in raw.get("links", raw.get("edges", []))],
    }


def _node(item: dict) -> dict:
    return {
        "id": item["id"],
        "type": _node_type(item),
        "label": item.get("label", item["id"]),
        "source_file": item.get("source_file", ""),
        "community": item.get("community", -1),
    }


def _node_type(item: dict) -> str:
    declared = item.get("type")
    if declared in NODE_TYPES:
        return declared
    file_type = item.get("file_type", "")
    if file_type in _FILE_TYPE_TO_NODE:
        return _FILE_TYPE_TO_NODE[file_type]
    raise GraphifySchemaError(
        f"node {item.get('id')!r}: cannot map type={declared!r} file_type={file_type!r}"
    )


def _edge(item: dict) -> dict:
    evidence = str(item.get("confidence", ""))
    score = item.get("confidence_score")
    confidence = float(score) if score is not None else (1.0 if evidence == "EXTRACTED" else 0.5)
    return {
        "src": item.get("source", item.get("src")),
        "dst": item.get("target", item.get("dst")),
        "relation": item.get("relation", ""),
        "evidence": evidence,
        "confidence": confidence,
    }

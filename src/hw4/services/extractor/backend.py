"""Assembly of the AST extraction backend (ADR-4) — emits a valid Graph.

The output passes graph_models validation by construction: every edge
endpoint is a node we created, every edge carries its evidence class.
Backend id + version are stamped into the artifact so a future real
Graphify run is distinguishable in every downstream report.
"""

from __future__ import annotations

from pathlib import Path

from hw4.services.extractor import calls, docs, python_ast
from hw4.services.graph_models import Edge, Graph, Node
from hw4.shared.config import Config
from hw4.shared.version import __version__

BACKEND_ID = f"ast_extractor/{__version__}"


def extract(root: Path | str, config: Config, iteration: int = 0) -> Graph:
    """Scan one repository tree into the PLAN §2.1 contract."""
    root = Path(root)
    exclude_dirs = set(config.get("graph.exclude_dirs"))
    doc_suffixes = tuple(config.get("graph.doc_suffixes"))
    max_mentions = int(config.get("graph.max_mentions_per_doc"))

    modules = python_ast.scan_modules(root, exclude_dirs)
    by_name = {mod.name: mod for mod in modules}

    nodes: list[Node] = []
    edges: list[Edge] = []
    for mod in modules:
        nodes.extend(python_ast.collect_definitions(mod))
    for mod in modules:  # bindings need all symbol tables filled first
        edges.extend(python_ast.import_edges(mod, by_name))
    unique_symbols = calls.unique_symbol_index(modules)
    for mod in modules:
        edges.extend(calls.call_edges(mod, by_name, unique_symbols))
    nodes.extend(_rationale_nodes(modules, root, edges))
    edges.extend(python_ast.containment_edges(nodes))

    code_ids = {node.id for node in nodes}
    top_packages = {mod.name.split(".")[0] for mod in modules}
    doc_files = docs.scan_docs(root, exclude_dirs, doc_suffixes)
    doc_nodes, doc_edges = docs.doc_nodes_and_edges(
        doc_files, code_ids, top_packages, max_mentions
    )
    nodes.extend(doc_nodes)
    edges.extend(doc_edges)

    graph = Graph(
        version=__version__,
        iteration=iteration,
        backend=BACKEND_ID,
        nodes={node.id: node for node in nodes},
        edges=edges,
    )
    return Graph.from_dict(graph.to_dict())  # self-validate before returning


def _rationale_nodes(modules, root: Path, edges: list[Edge]) -> list[Node]:
    nodes = []
    for mod in modules:
        for suffix, label in python_ast.rationale_items(mod, root):
            rid = f"rationale:{mod.name}.{suffix}"
            nodes.append(Node(id=rid, type="rationale", label=label, source_file=mod.path))
            edges.append(
                Edge(
                    src=rid,
                    dst=mod.name,
                    relation="rationale_for",
                    evidence=python_ast.EdgeEvidence.EXTRACTED,
                    confidence=1.0,
                )
            )
    return nodes

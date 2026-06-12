"""Deterministic Python-AST extraction — the EXTRACTED layer (T137, T139).

Evidence discipline (Part-C): everything here is read directly from
syntax, so edges are EXTRACTED at confidence 1.0 (0.9 for attribute
calls, where the object's identity is syntactic but not certain). The
single exception: a bare call name that resolves uniquely elsewhere in
the repo is INFERRED 0.6; non-unique candidates are skipped entirely
rather than guessed (silence over fabrication).

Containment is encoded as `implements` edges (function→module,
method→class, class→module) so no code node floats disconnected.
Imports from test modules become `tested_by` edges (module→test).
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path

from hw4.constants import EdgeEvidence
from hw4.services.graph_models import Edge, Node

RATIONALE_MARKERS = ("# TODO", "# FIXME", "# WHY", "# HACK")


@dataclass
class PyModule:
    """One parsed module with its symbol and import bindings."""

    name: str
    path: str
    tree: ast.Module
    symbols: dict[str, str] = field(default_factory=dict)  # local name -> node id
    bindings: dict[str, str] = field(default_factory=dict)  # imported name -> node id

    @property
    def is_test(self) -> bool:
        parts = Path(self.path).parts
        return any(p in ("tests", "test") for p in parts) or parts[-1].startswith("test_")


def module_name(rel_path: Path) -> str:
    parts = list(rel_path.with_suffix("").parts)
    if parts and parts[0] == "src":
        parts = parts[1:]
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts) or rel_path.stem


def scan_modules(root: Path, exclude_dirs: set[str]) -> list[PyModule]:
    modules = []
    for py in sorted(root.rglob("*.py")):
        rel = py.relative_to(root)
        if any(part in exclude_dirs for part in rel.parts):
            continue
        try:
            tree = ast.parse(py.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            continue  # unparseable file is a finding for humans, not a crash
        modules.append(PyModule(name=module_name(rel), path=rel.as_posix(), tree=tree))
    return modules


def collect_definitions(mod: PyModule) -> list[Node]:
    """Module/class/function nodes + local symbol table."""
    nodes = [Node(id=mod.name, type="module", label=mod.name, source_file=mod.path)]
    for item in mod.tree.body:
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
            fid = f"{mod.name}.{item.name}"
            nodes.append(Node(id=fid, type="function", label=item.name, source_file=mod.path))
            mod.symbols[item.name] = fid
        elif isinstance(item, ast.ClassDef):
            cid = f"{mod.name}.{item.name}"
            nodes.append(Node(id=cid, type="class", label=item.name, source_file=mod.path))
            mod.symbols[item.name] = cid
            for sub in item.body:
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    mid = f"{cid}.{sub.name}"
                    nodes.append(
                        Node(id=mid, type="function", label=sub.name, source_file=mod.path)
                    )
    return nodes


def containment_edges(nodes: list[Node]) -> list[Edge]:
    ids = {n.id for n in nodes}
    edges = []
    for node in nodes:
        if "." not in node.id:
            continue  # top-level package has no parent
        parent = node.id.rsplit(".", 1)[0]
        if parent in ids:
            edges.append(_edge(node.id, parent, "implements", EdgeEvidence.EXTRACTED, 1.0))
    return edges


def import_edges(mod: PyModule, by_name: dict[str, PyModule]) -> list[Edge]:
    """imports / tested_by edges + name bindings for call resolution."""
    edges = []
    for stmt in ast.walk(mod.tree):
        if isinstance(stmt, ast.Import):
            for alias in stmt.names:
                if alias.name in by_name:
                    edges.append(_import_edge(mod, alias.name))
                    mod.bindings[alias.asname or alias.name] = alias.name
        elif isinstance(stmt, ast.ImportFrom):
            target = _resolve_from(mod, stmt)
            if target in by_name:
                edges.append(_import_edge(mod, target))
                for alias in stmt.names:
                    symbol = by_name[target].symbols.get(alias.name)
                    mod.bindings[alias.asname or alias.name] = symbol or target
    return edges


def rationale_items(mod: PyModule, source_root: Path) -> list[tuple[str, str]]:
    """(rationale node id suffix, label) pairs: docstring + TODO digest."""
    items = []
    doc = ast.get_docstring(mod.tree)
    if doc:
        items.append(("doc", doc.strip().splitlines()[0][:120]))
    text = (source_root / mod.path).read_text(encoding="utf-8", errors="replace")
    todos = [ln.strip() for ln in text.splitlines() if any(m in ln for m in RATIONALE_MARKERS)]
    if todos:
        items.append(("todos", f"{len(todos)} marker comment(s); first: {todos[0][:100]}"))
    return items


def _resolve_from(mod: PyModule, stmt: ast.ImportFrom) -> str:
    if stmt.level == 0:
        return stmt.module or ""
    package_parts = mod.name.split(".")
    is_package = Path(mod.path).stem == "__init__"
    keep = len(package_parts) - (stmt.level - 1 if is_package else stmt.level)
    base = package_parts[: max(keep, 0)]
    return ".".join(base + ([stmt.module] if stmt.module else []))


def _import_edge(mod: PyModule, target: str) -> Edge:
    if mod.is_test:
        return _edge(target, mod.name, "tested_by", EdgeEvidence.EXTRACTED, 1.0)
    return _edge(mod.name, target, "imports", EdgeEvidence.EXTRACTED, 1.0)


def _edge(src: str, dst: str, relation: str, evidence: EdgeEvidence, conf: float) -> Edge:
    return Edge(src=src, dst=dst, relation=relation, evidence=evidence, confidence=conf)

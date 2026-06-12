"""Doc-layer extraction — mentions are inference, gaps are findings (T138).

Docs claim things about code; the claims may be false. Resolution:
exact node-id match -> INFERRED 0.8; unique suffix match -> INFERRED 0.6;
a dotted path that *looks* internal (starts with a known top-level
package) but resolves to nothing becomes a `missing:` placeholder node
plus an AMBIGUOUS 0.4 edge — that unresolved mention IS the
documented-but-nonexistent trace gap the traceability detector hunts
(mini_repo's planted `app.plugins` lie travels exactly this path).
"""

from __future__ import annotations

import re
from pathlib import Path

from hw4.constants import EdgeEvidence
from hw4.services.graph_models import Edge, Node

IDENTIFIER = re.compile(r"\b[A-Za-z_][\w]*(?:\.[A-Za-z_][\w]*)+\b")


def scan_docs(
    root: Path, exclude_dirs: set[str], suffixes: tuple[str, ...]
) -> list[tuple[str, str, str]]:
    """(doc node id, title, text) for every doc file in scope."""
    found = []
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if path.suffix not in suffixes or any(p in exclude_dirs for p in rel.parts):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        title = next(
            (ln.lstrip("# ").strip() for ln in text.splitlines() if ln.startswith("#")),
            rel.name,
        )
        found.append((f"doc:{rel.as_posix()}", title, text))
    return found


def doc_nodes_and_edges(
    docs: list[tuple[str, str, str]],
    code_ids: set[str],
    top_packages: set[str],
    max_mentions: int,
) -> tuple[list[Node], list[Edge]]:
    nodes, edges = [], []
    for doc_id, title, text in docs:
        source_file = doc_id.removeprefix("doc:")
        nodes.append(Node(id=doc_id, type="doc", label=title[:120], source_file=source_file))
        mentioned = _candidates(text)
        for candidate in mentioned[:max_mentions]:
            resolution = _resolve(candidate, code_ids, top_packages)
            if resolution is None:
                continue
            target, evidence, confidence = resolution
            if target.startswith("missing:"):
                nodes.append(
                    Node(
                        id=target,
                        type="doc",
                        label=f"{candidate} (unresolved mention)",
                        source_file=source_file,
                    )
                )
            edges.append(
                Edge(
                    src=doc_id,
                    dst=target,
                    relation="mentions",
                    evidence=evidence,
                    confidence=confidence,
                )
            )
    return nodes, _dedupe_edges(edges)


def _candidates(text: str) -> list[str]:
    ordered, seen = [], set()
    for match in IDENTIFIER.finditer(text):
        token = match.group(0)
        if token not in seen:
            seen.add(token)
            ordered.append(token)
    return ordered


def _resolve(candidate: str, code_ids: set[str], top_packages: set[str]):
    if candidate in code_ids:
        return candidate, EdgeEvidence.INFERRED, 0.8
    top, leaf = candidate.split(".")[0], candidate.split(".")[-1]
    if top not in top_packages:
        return None  # external-looking dotted path; not ours to claim
    full_hits = [cid for cid in code_ids if cid.endswith("." + candidate)]
    if len(full_hits) == 1:
        return full_hits[0], EdgeEvidence.INFERRED, 0.6
    if full_hits:
        return None  # several plausible targets — refuse to guess
    # re-export tier: docs cite `pkg.name` for symbols defined in pkg.sub.name
    reexports = [c for c in code_ids if c.startswith(top + ".") and c.endswith("." + leaf)]
    if len(reexports) == 1:
        return reexports[0], EdgeEvidence.INFERRED, 0.6
    if reexports:
        return None
    return f"missing:{candidate}", EdgeEvidence.AMBIGUOUS, 0.4


def _dedupe_edges(edges: list[Edge]) -> list[Edge]:
    seen, kept = set(), []
    for edge in edges:
        key = (edge.src, edge.dst)
        if key not in seen:
            seen.add(key)
            kept.append(edge)
    return kept

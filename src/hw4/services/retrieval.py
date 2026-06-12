"""Index-first focused retrieval — the token engine (FR-3.4, PLAN §2.4).

Condition B's entire claim lives here: answer from index + bounded
ego-subgraph + 2-3 short wiki pages instead of file dumps. Assembly is
position-aware (Part-B): critical instructions at the START, the
question at the END, evidence kept short in the middle.

The token estimate is a chars/4 heuristic — fine as a *budget guard*
(it only decides truncation); the experiment's measured numbers always
come from provider API metadata via the Gatekeeper ledger, never from
this estimate.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from hw4.services.graph_models import Graph
from hw4.services.graph_queries import ego_subgraph
from hw4.services.vault_builder import VaultBuilder
from hw4.shared.config import Config

WORD = re.compile(r"[a-z_][a-z0-9_]+")


class NoRetrievalMatchError(LookupError):
    """Question matched nothing in the graph — answering would be guessing."""


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


@dataclass(frozen=True)
class ContextBundle:
    """Everything retrieved for one question, ready for assembly."""

    question: str
    matched_nodes: list[str]
    index_text: str
    subgraph_text: str
    wiki_pages: list[tuple[str, str]]
    token_estimate: int
    truncated: bool = False
    source_files: list[str] = field(default_factory=list)

    def assemble(self, instructions: str) -> str:
        """Edge placement: instructions FIRST, question LAST (Part-B)."""
        middle = [self.index_text, self.subgraph_text]
        middle += [f"### wiki:{pid}\n{text}" for pid, text in self.wiki_pages]
        body = "\n\n".join(part for part in middle if part)
        return f"{instructions}\n\n{body}\n\nQUESTION: {self.question}"


class Retriever:
    """question -> matched seeds -> bounded subgraph + top wiki pages."""

    def __init__(self, config: Config, vault: VaultBuilder):
        self._radius = int(config.get("retrieval.ego_radius"))
        self._max_nodes = int(config.get("retrieval.max_nodes"))
        self._k_pages = int(config.get("retrieval.k_pages"))
        self._max_seeds = int(config.get("retrieval.max_seeds"))
        self._token_cap = int(config.get("retrieval.context_token_cap"))
        self._vault = vault

    def retrieve(self, question: str, graph: Graph) -> ContextBundle:
        seeds = self._match_nodes(question, graph)
        if not seeds:
            raise NoRetrievalMatchError(f"no graph node matches: {question!r}")
        merged = Graph(version=graph.version, iteration=graph.iteration)
        for seed in seeds:
            ego = ego_subgraph(graph, seed, self._radius, self._max_nodes)
            merged.nodes.update(ego.nodes)
        kept = [e for e in graph.edges if e.src in merged.nodes and e.dst in merged.nodes]
        index_text = self._read_index()
        pages = self._match_pages(question)
        bundle = ContextBundle(
            question=question,
            matched_nodes=seeds,
            index_text=index_text,
            subgraph_text=_serialize(merged, kept),
            wiki_pages=pages,
            token_estimate=0,
            source_files=sorted({n.source_file for n in merged.nodes.values() if n.source_file}),
        )
        return self._enforce_cap(bundle)

    def _match_nodes(self, question: str, graph: Graph) -> list[str]:
        terms = set(WORD.findall(question.lower()))
        scored = []
        for node in graph.nodes.values():
            parts = set(WORD.findall(node.id.lower())) | set(WORD.findall(node.label.lower()))
            overlap = len(terms & parts)
            if overlap:
                scored.append((-overlap, node.id))
        return [node_id for _, node_id in sorted(scored)[: self._max_seeds]]

    def _match_pages(self, question: str) -> list[tuple[str, str]]:
        terms = set(WORD.findall(question.lower()))
        scored = []
        for page in sorted(self._vault.wiki_dir.glob("*.md")):
            text = page.read_text(encoding="utf-8")
            overlap = len(terms & set(WORD.findall(text[:400].lower())))
            if overlap:
                scored.append((-overlap, page.stem, text))
        return [(stem, text) for _, stem, text in sorted(scored)[: self._k_pages]]

    def _read_index(self) -> str:
        path: Path = self._vault.index_path
        return path.read_text(encoding="utf-8") if path.exists() else ""

    def _enforce_cap(self, bundle: ContextBundle) -> ContextBundle:
        def estimate(b: ContextBundle) -> int:
            return estimate_tokens(b.assemble(""))

        truncated = False
        pages = list(bundle.wiki_pages)
        subgraph = bundle.subgraph_text
        while estimate(_with(bundle, pages, subgraph, 0, truncated)) > self._token_cap and pages:
            pages.pop()  # drop least-relevant page first
            truncated = True
        if estimate(_with(bundle, pages, subgraph, 0, truncated)) > self._token_cap:
            lines = subgraph.splitlines()
            subgraph = "\n".join(lines[: max(len(lines) // 2, 1)])
            truncated = True
        final = _with(bundle, pages, subgraph, 0, truncated)
        return _with(bundle, pages, subgraph, estimate(final), truncated)


def _with(bundle: ContextBundle, pages, subgraph, estimate, truncated) -> ContextBundle:
    return ContextBundle(
        question=bundle.question,
        matched_nodes=bundle.matched_nodes,
        index_text=bundle.index_text,
        subgraph_text=subgraph,
        wiki_pages=pages,
        token_estimate=estimate,
        truncated=truncated,
        source_files=bundle.source_files,
    )


def _serialize(graph: Graph, edges) -> str:
    lines = ["### focused subgraph"]
    for node in graph.nodes.values():
        lines.append(f"node {node.id} [{node.type}] {node.source_file}".rstrip())
    for edge in edges:
        lines.append(
            f"edge {edge.src} -{edge.relation}-> {edge.dst} ({edge.evidence.value})"
        )
    return "\n".join(lines)

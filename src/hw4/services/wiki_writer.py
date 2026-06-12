"""LLM wiki page generation (FR-3.3, T176-T179).

Division of labor is the whole design: the LLM writes ONLY the prose
that needs judgment (Summary, Open questions) via the cheap tier through
the Gatekeeper (purpose `wiki.gen.<page>`); everything checkable —
evidence rows, confidences, source files, wikilinks — is injected
programmatically from the graph, so a page can never cite an edge that
does not exist. Pages are short (config cap) because short pages
re-retrieve better (Part-B).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from hw4.constants import ModelTier
from hw4.services.graph_metrics import Metrics
from hw4.services.graph_models import Graph
from hw4.services.vault_builder import VaultBuilder, frontmatter
from hw4.shared.config import Config
from hw4.shared.llm_client import LlmClient

SYSTEM = (
    "You write one short wiki page for a code-analysis vault. Respond with "
    "exactly two sections: 'SUMMARY:' (max 3 sentences, plain prose) and "
    "'OPEN QUESTIONS:' (max 3 bullet lines starting with '- '). Use careful, "
    "qualified language; never assert beyond the evidence given."
)
EVIDENCE_ROWS_PER_PAGE = 6


@dataclass(frozen=True)
class PageSpec:
    """One planned wiki page."""

    page_id: str
    title: str
    kind: str  # "hub" | "community"
    node_ids: list[str]


def select_entities(graph: Graph, metrics: Metrics, config: Config) -> list[PageSpec]:
    """Top bottleneck hubs + every non-trivial community."""
    specs = []
    for evidence in metrics.bottlenecks[: int(config.get("vault.top_hub_pages"))]:
        node = graph.nodes[evidence.node_id]
        specs.append(PageSpec(
            page_id=node.id.replace(":", "-"),
            title=f"{node.label} — rank-{evidence.rank} dependency bottleneck",
            kind="hub",
            node_ids=[node.id],
        ))
    members_of: dict[int, list[str]] = {}
    for node_id, community in sorted(metrics.community_of.items()):
        members_of.setdefault(community, []).append(node_id)
    for community, members in members_of.items():
        if len(members) >= int(config.get("vault.min_community_size")):
            specs.append(PageSpec(
                page_id=f"community-{community}",
                title=f"community {community} — {len(members)} nodes cluster",
                kind="community",
                node_ids=members,
            ))
    return specs


class WikiWriter:
    """Render PageSpecs into wiki/ — gated LLM prose, programmatic facts."""

    def __init__(self, config: Config, llm: LlmClient, vault: VaultBuilder):
        self._max_lines = int(config.get("vault.wiki_page_max_lines"))
        self._project = str(config.get("vault.project"))
        self._llm = llm
        self._vault = vault

    def write_pages(self, graph: Graph, metrics: Metrics, config: Config) -> list[Path]:
        specs = select_entities(graph, metrics, config)
        known_ids = {spec.page_id for spec in specs}
        written = []
        for spec in specs:
            evidence = _evidence_rows(graph, spec)
            prose = self._generate_prose(spec, evidence)
            page = self._render(spec, evidence, prose, known_ids, graph, metrics)
            path = self._vault.wiki_dir / f"{spec.page_id}.md"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(page, encoding="utf-8")
            self._vault.append_log(f"wiki page {spec.page_id}", f"graph i{graph.iteration:02d}",
                                   "wiki_writer")
            written.append(path)
        return written

    def _generate_prose(self, spec: PageSpec, evidence: list[str]) -> tuple[str, list[str]]:
        prompt = (
            f"Page subject: {spec.title} (kind: {spec.kind})\n"
            f"Graph evidence:\n" + "\n".join(evidence) + "\nWrite the page sections now."
        )
        response = self._llm.complete(
            [{"role": "user", "content": prompt}],
            purpose_tag=f"wiki.gen.{spec.page_id}",
            tier=ModelTier.CHEAP,
            system=SYSTEM,
        )
        return _parse_prose(response.text)

    def _render(self, spec, evidence, prose, known_ids, graph, metrics) -> str:
        summary, questions = prose
        links = _related_links(spec, known_ids, graph, metrics)
        lines = [frontmatter("wiki", self._project, status="generated").rstrip("\n")]
        lines += [f"# {spec.title}", "", "## Summary", summary, "", "## Evidence"]
        lines += evidence
        lines += ["", "## Links"] + [f"- [[{link}]]" for link in links]
        lines += ["", "## Open questions"] + (questions or ["- none recorded"])
        return "\n".join(lines[: self._max_lines]) + "\n"


def _evidence_rows(graph: Graph, spec: PageSpec) -> list[str]:
    focus = set(spec.node_ids)
    rows = []
    for edge in graph.edges:
        if edge.src in focus or edge.dst in focus:
            node = graph.nodes[edge.src if edge.src in focus else edge.dst]
            rows.append(
                f"- {edge.src} —{edge.relation}→ {edge.dst} "
                f"({edge.evidence.value}, {edge.confidence:.2f}) · {node.source_file}"
            )
    rows.sort()
    return rows[:EVIDENCE_ROWS_PER_PAGE]


def _related_links(spec, known_ids, graph: Graph, metrics: Metrics) -> list[str]:
    links = set()
    if spec.kind == "hub":
        community = metrics.community_of.get(spec.node_ids[0])
        if community is not None and f"community-{community}" in known_ids:
            links.add(f"community-{community}")
    else:
        members = set(spec.node_ids)
        links |= {pid for pid in known_ids if pid != spec.page_id and pid in members}
    links.add("index")
    return sorted(links)


def _parse_prose(text: str) -> tuple[str, list[str]]:
    summary, questions, mode = [], [], None
    for line in text.splitlines():
        upper = line.strip().upper()
        if upper.startswith("SUMMARY"):
            mode = "s"
            remainder = line.split(":", 1)[-1].strip()
            if remainder:
                summary.append(remainder)
        elif upper.startswith("OPEN QUESTIONS"):
            mode = "q"
        elif mode == "s" and line.strip():
            summary.append(line.strip())
        elif mode == "q" and line.strip().startswith("-"):
            questions.append(line.strip())
    return " ".join(summary) or text.strip()[:300], questions[:3]

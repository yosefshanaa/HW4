"""Operation implementations behind the Hw4Sdk facade (§3.2 split).

sdk.py stays a thin wiring surface; the multi-step orchestration of
vault building and question answering lives here. Functions receive the
facade itself — they use only its public surface (config, llm,
results_dir, base_dir), so tests can drive them with fake transports.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from hw4.sdk.errors import ServiceNotReadyError
from hw4.services import graph_metrics
from hw4.services.detectors import registry
from hw4.services.graph_models import Graph
from hw4.services.graph_runner import GraphRunner
from hw4.services.retrieval import ContextBundle, Retriever
from hw4.services.vault_builder import VaultBuilder
from hw4.services.wiki_writer import WikiWriter, select_entities

ASK_INSTRUCTIONS = (
    "Answer the question at the end using ONLY the context below. "
    "Cite the node ids and source files your answer relies on. "
    "If the context is insufficient, say exactly that instead of guessing."
)


@dataclass(frozen=True)
class VaultBuildReport:
    """What one vault build produced."""

    iteration: int
    pages: list[Path]
    index_path: Path
    raw_copies: list[Path]


@dataclass(frozen=True)
class AskResult:
    """One graph-guided answer with its citation material."""

    answer: str
    matched_nodes: list[str]
    source_files: list[str]
    context_token_estimate: int
    truncated: bool


def latest_graph(sdk) -> Graph:
    runner = GraphRunner(sdk.config, results_dir=sdk.results_dir)
    latest = runner.latest_iteration()
    if latest is None:
        raise FileNotFoundError("no graph iterations built yet — run `hw4 graph` first")
    return Graph.load(runner.graph_path(latest))


def build_vault(sdk, graph_path: Path | str | None = None) -> VaultBuildReport:
    """Skeleton + raw snapshots + LLM wiki pages + regenerated index."""
    graph = Graph.load(graph_path) if graph_path else latest_graph(sdk)
    metrics = graph_metrics.compute(graph, sdk.config)
    vault = VaultBuilder(sdk.config, base_dir=sdk.base_dir)
    vault.build_skeleton()
    raw_copies = _snapshot_raw_inputs(sdk, vault, graph)
    writer = WikiWriter(sdk.config, sdk.llm, vault)
    pages = writer.write_pages(graph, metrics, sdk.config)
    index_path = vault.write_index(_index_sections(sdk, graph, metrics))
    vault.append_log(f"vault build for i{graph.iteration:02d}", "graph artifacts", "sdk")
    return VaultBuildReport(
        iteration=graph.iteration, pages=pages, index_path=index_path, raw_copies=raw_copies
    )


def analyze(sdk, graph_path: Path | str | None = None):
    """All detectors over one graph -> ranked findings + findings.json (FR-6)."""
    graph = Graph.load(graph_path) if graph_path else latest_graph(sdk)
    metrics = graph_metrics.compute(graph, sdk.config)
    findings = registry.run_all(graph, metrics, sdk.config)
    registry.dump_findings(findings, sdk.results_dir / "findings.json", graph.iteration)
    return findings


def ask(sdk, question: str, mode: str = "graph") -> AskResult:
    """Graph-guided answer with citations (FR-8.3); naive mode is Phase 7."""
    if mode != "graph":
        raise ServiceNotReadyError("naive mode is wired in Phase 7 (experiment baseline)")
    vault = VaultBuilder(sdk.config, base_dir=sdk.base_dir)
    bundle: ContextBundle = Retriever(sdk.config, vault).retrieve(question, latest_graph(sdk))
    response = sdk.llm.complete(
        [{"role": "user", "content": bundle.assemble(ASK_INSTRUCTIONS)}],
        purpose_tag="ask",
    )
    return AskResult(
        answer=response.text,
        matched_nodes=bundle.matched_nodes,
        source_files=bundle.source_files,
        context_token_estimate=bundle.token_estimate,
        truncated=bundle.truncated,
    )


def _index_sections(sdk, graph: Graph, metrics) -> dict[str, list[str]]:
    cap = int(sdk.config.get("vault.index_max_entries_per_section"))
    specs = select_entities(graph, metrics, sdk.config)
    hubs = [f"[[{s.page_id}]] — {s.title}" for s in specs if s.kind == "hub"]
    communities = [f"[[{s.page_id}]] — {s.title}" for s in specs if s.kind == "community"]
    return {
        "Start here": ["[[log]] — ingestion trail", "raw/ — unprocessed inputs"],
        "Hubs & bottlenecks": hubs[:cap],
        "Communities": communities[:cap],
    }


def _snapshot_raw_inputs(sdk, vault: VaultBuilder, graph: Graph) -> list[Path]:
    """raw/ keeps unprocessed inputs separate from distilled wiki (Part-B)."""
    copies = []
    iteration_dir = sdk.results_dir / "graphs" / f"i{graph.iteration:02d}"
    for name in ("manifest.json", "VALIDATION.md"):
        source = iteration_dir / name
        if source.exists():
            target = vault.raw_dir / f"i{graph.iteration:02d}-{name}"
            shutil.copyfile(source, target)
            copies.append(target)
    provenance = Path(sdk.base_dir) / "docs" / "TARGET_REPO.md"
    if provenance.exists():
        target = vault.raw_dir / "TARGET_REPO.md"
        shutil.copyfile(provenance, target)
        copies.append(target)
    return copies

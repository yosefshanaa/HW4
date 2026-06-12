"""Operation implementations behind the Hw4Sdk facade (§3.2 split).

sdk.py stays a thin wiring surface; the multi-step orchestration of
vault building and question answering lives here. Functions receive the
facade itself — they use only its public surface (config, llm,
results_dir, base_dir), so tests can drive them with fake transports.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path

from hw4.constants import FindingStatus
from hw4.sdk.errors import ServiceNotReadyError
from hw4.services import graph_metrics
from hw4.services.detectors import registry
from hw4.services.fixloop.applier import Applier
from hw4.services.fixloop.loop import FixLoop
from hw4.services.fixloop.planner import covered_source_files
from hw4.services.graph_models import Graph
from hw4.services.graph_runner import GraphRunner
from hw4.services.retrieval import ContextBundle, Retriever
from hw4.services.vault_builder import VaultBuilder
from hw4.services.wiki_writer import WikiWriter, select_entities
from hw4.shared.process_runner import ProcessRunner

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


def fix(sdk, finding_id: str = "", auto: bool = False) -> dict:
    """Test-guarded improvement loop over validated findings (FR-7).

    Human triage hands over via results/validated.json (id -> note);
    only findings listed there are eligible, matching FINDINGS.md.
    """
    runner = GraphRunner(sdk.config, results_dir=sdk.results_dir)
    base_iteration = runner.latest_iteration()
    if base_iteration is None:
        raise FileNotFoundError("no graph iterations built yet — run `hw4 graph` first")
    graph = Graph.load(runner.graph_path(base_iteration))
    metrics = graph_metrics.compute(graph, sdk.config)
    findings = registry.run_all(graph, metrics, sdk.config)
    validated = _load_validations(sdk)
    for finding in findings:
        if finding.id in validated:
            finding.status = FindingStatus.VALIDATED
    if not auto:
        findings = [f for f in findings if f.id == finding_id]
        if not findings:
            raise KeyError(f"finding {finding_id!r} not found in current analysis")
    repo = sdk.base_dir / sdk.config.path("workspace") / str(
        sdk.config.get("repo.default_dirname")
    )
    process_runner = ProcessRunner(
        timeout_seconds=float(sdk.config.get("loop.step_timeout_seconds"))
    )
    applier = Applier(sdk.config, sdk.llm, process_runner, repo)
    max_usd = float(sdk.config.get("budget.max_usd"))
    loop = FixLoop(
        sdk.config,
        applier,
        _graph_builder(sdk, runner, repo),
        sdk.results_dir / "loop_log.json",
        budget_exceeded=lambda: sdk.ledger.total_cost() >= max_usd,
        covered_files=covered_source_files(graph),
    )
    return loop.run(findings, base_iteration)


def _load_validations(sdk) -> dict:
    path = sdk.results_dir / "validated.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _graph_builder(sdk, runner: GraphRunner, repo):
    """iteration -> (graph, metrics, hash); reuses immutable artifacts."""
    import hashlib

    def build(iteration: int):
        path = runner.graph_path(iteration)
        if path.exists():
            graph = Graph.load(path)
            content_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        else:
            record = runner.build(repo, iteration)
            graph = Graph.load(record.graph_path)
            content_hash = record.content_hash
        metrics = graph_metrics.compute(graph, sdk.config)
        metrics.dump(path.parent / "metrics.json")
        return graph, metrics, content_hash

    return build


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

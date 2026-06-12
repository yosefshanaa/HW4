"""Fix-loop wiring behind the facade (§3.2 split from operations.py).

Human triage hands over via results/validated.json (id -> note); only
findings listed there are loop-eligible, mirroring FINDINGS.md.
"""

from __future__ import annotations

import hashlib
import json

from hw4.constants import FindingStatus
from hw4.services import graph_metrics
from hw4.services.detectors import registry
from hw4.services.fixloop.applier import Applier
from hw4.services.fixloop.loop import FixLoop
from hw4.services.fixloop.planner import covered_source_files
from hw4.services.graph_models import Graph
from hw4.services.graph_runner import GraphRunner
from hw4.shared.process_runner import ProcessRunner


def fix(sdk, finding_id: str = "", auto: bool = False) -> dict:
    """Test-guarded improvement loop over validated findings (FR-7).

    The base graph is ALWAYS freshly extracted from the current tree —
    basing on a stale iteration (e.g. one built from a previously
    reverted attempt) contaminated a live verdict on 2026-06-12.
    """
    repo = target_repo_path(sdk)
    runner = GraphRunner(sdk.config, results_dir=sdk.results_dir)
    latest = runner.latest_iteration()
    base_iteration = 0 if latest is None else latest + 1
    record = runner.build(repo, base_iteration)
    graph = Graph.load(record.graph_path)
    metrics = graph_metrics.compute(graph, sdk.config)
    metrics.dump(record.graph_path.parent / "metrics.json")
    findings = registry.run_all(graph, metrics, sdk.config)
    validated = _load_validations(sdk)
    for finding in findings:
        # signature match (kind + anchor node), never positional ids —
        # ids are stable within one graph, not across graphs
        if (finding.kind.value, finding.nodes[0]) in validated:
            finding.status = FindingStatus.VALIDATED
    if not auto:
        findings = [f for f in findings if f.id == finding_id]
        if not findings:
            raise KeyError(f"finding {finding_id!r} not found in current analysis")
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


def target_repo_path(sdk):
    return sdk.base_dir / sdk.config.path("workspace") / str(
        sdk.config.get("repo.default_dirname")
    )


def _load_validations(sdk) -> set[tuple[str, str]]:
    """(kind, anchor-node) signatures of human-validated findings."""
    path = sdk.results_dir / "validated.json"
    if not path.exists():
        return set()
    doc = json.loads(path.read_text(encoding="utf-8"))
    return {(v["kind"], v["anchor"]) for v in doc.get("validations", [])}


def _graph_builder(sdk, runner: GraphRunner, repo):
    """iteration -> (graph, metrics, hash); reuses immutable artifacts."""

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

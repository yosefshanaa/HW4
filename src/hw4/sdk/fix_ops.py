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
    """Test-guarded improvement loop over validated findings (FR-7)."""
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
    repo = target_repo_path(sdk)
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


def _load_validations(sdk) -> dict:
    path = sdk.results_dir / "validated.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


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

"""The test-guarded improvement loop (T330-T335, PLAN §3.3).

Pure orchestration over injected collaborators (applier, graph builder,
verdict judge, budget probe) — the loop itself contains no LLM call and
no git command, so its control flow is provable with fakes while the
real collaborators are proven in their own tests. Every iteration —
accepted or reverted — appends one loop_log.json entry; rejected
iterations keep their graph artifacts on disk as evidence (ADR-6).
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

from hw4.constants import FindingStatus, StopReason
from hw4.services.detectors.base import Finding
from hw4.services.fixloop import stop
from hw4.services.fixloop.planner import PlanRefusedError, plan
from hw4.services.graph_diff import IMPROVED, REGRESSED, diff, judge
from hw4.shared.config import Config

# build_graph(iteration) -> (graph, metrics, content_hash)
GraphBuilder = Callable[[int], tuple]


class FixLoop:
    """Iterate: plan -> apply -> test -> re-graph -> diff -> verdict -> log."""

    def __init__(
        self,
        config: Config,
        applier,
        build_graph: GraphBuilder,
        log_path: Path | str,
        budget_exceeded: Callable[[], bool],
        covered_files: set[str],
    ):
        self._config = config
        self._max_iterations = int(config.get("loop.max_iterations"))
        self._applier = applier
        self._build_graph = build_graph
        self._log_path = Path(log_path)
        self._budget_exceeded = budget_exceeded
        self._covered = covered_files

    def run(self, findings: list[Finding], base_iteration: int) -> dict:
        queue = self._actionable(findings)
        if not queue:
            return self._finish([], StopReason.NO_SAFE_ACTION, note="no plannable findings")
        graph, metrics, base_hash = self._build_graph(base_iteration)
        entries, reason = [], None
        iteration = base_iteration
        for index, (finding, fix_plan) in enumerate(queue):
            iteration += 1
            apply_result = self._applier.apply(fix_plan)
            tests_green = self._applier.run_tests()
            new_graph, new_metrics, new_hash = self._build_graph(iteration)
            delta = diff(graph, new_graph, metrics, new_metrics)
            verdict = judge(delta, self._config) if tests_green else REGRESSED
            outcome = stop.evaluate(stop.LoopState(
                iteration=iteration - base_iteration,
                max_iterations=self._max_iterations,
                tests_green=tests_green,
                verdict=verdict,
                budget_exceeded=self._budget_exceeded(),
                findings_remaining=len(queue) - index - 1,
            ))
            if outcome.accept:
                finding.status = (
                    FindingStatus.FIXED if verdict == IMPROVED else finding.status
                )
                graph, metrics = new_graph, new_metrics
            else:
                self._applier.revert(apply_result.base_sha)
                finding.status = FindingStatus.BLOCKED
            entries.append({
                "iteration": iteration,
                "finding_id": finding.id,
                "strategy": fix_plan.strategy,
                "files_changed": list(apply_result.files_changed),
                "characterization_test": apply_result.characterization_test,
                "tests_green": tests_green,
                "graph_hash_before": base_hash,
                "graph_hash_after": new_hash,
                "metric_deltas": {
                    "bottleneck_before": delta.top_bottleneck_before,
                    "bottleneck_after": delta.top_bottleneck_after,
                    "isolated_before": delta.isolated_before,
                    "isolated_after": delta.isolated_after,
                },
                "verdict": verdict,
                "accepted": outcome.accept,
                "stop_reason": outcome.reason.value if outcome.reason else None,
                "recorded_utc": datetime.now(timezone.utc).isoformat(),
            })
            base_hash = new_hash if outcome.accept else base_hash
            self._write_log(entries, outcome.reason)
            if outcome.stop:
                reason = outcome.reason
                break
        return self._finish(entries, reason or StopReason.MAX_ITERATIONS)

    def _actionable(self, findings: list[Finding]) -> list[tuple[Finding, object]]:
        queue = []
        for finding in findings:
            try:
                queue.append((finding, plan(finding, self._covered)))
            except PlanRefusedError:
                continue  # refusals are by design; they stay hypotheses
        return queue

    def _finish(self, entries: list[dict], reason: StopReason, note: str = "") -> dict:
        report = {
            "iterations": entries,
            "stop_reason": reason.value,
            "note": note,
            "log_path": str(self._log_path),
        }
        self._write_log(entries, reason, note)
        return report

    def _write_log(self, entries: list[dict], reason, note: str = "") -> None:
        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        self._log_path.write_text(json.dumps({
            "version": "1.00",
            "stop_reason": reason.value if reason else None,
            "note": note,
            "iterations": entries,
        }, indent=1, sort_keys=True), encoding="utf-8")

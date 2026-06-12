"""Validated Finding -> FixPlan (T321-T323).

The plan skeleton is deterministic (strategy per finding kind, safety
constraints as hard refusals); only the *edit content* is LLM work, and
that happens later in the applier. Refusal is a feature: a planner that
plans everything is how loops destroy codebases (PRD_fix_loop §1).
"""

from __future__ import annotations

from dataclasses import dataclass

from hw4.constants import FindingKind, FindingStatus
from hw4.services.detectors.base import Finding
from hw4.services.graph_models import Graph


class PlanRefusedError(RuntimeError):
    """This finding may not be auto-fixed; the reason says why."""


STRATEGIES = {
    FindingKind.GOD_NODE: (
        "extract a cohesive group of helpers into a new module",
        "fan_out and degree of the god node decrease; no public API change",
    ),
    FindingKind.SPOF: (
        "introduce an injectable seam in front of the bottleneck",
        "mandatory_path_ratio of the bottleneck decreases",
    ),
    FindingKind.TRACE_GAP: (
        "align documentation with code: fix the doc claim or implement it",
        "missing: placeholder node disappears from the next graph iteration",
    ),
}
HUMAN_ONLY = {FindingKind.ISOLATED, FindingKind.DUPLICATION}


@dataclass(frozen=True)
class FixPlan:
    """One bounded, revertable refactor intent."""

    finding_id: str
    strategy: str
    target_files: tuple[str, ...]
    steps: tuple[str, ...]
    expected_metric_delta: str
    test_strategy: str
    needs_characterization: bool


def covered_source_files(graph: Graph) -> set[str]:
    """Files whose modules have tested_by edges — the safety map (FR-7.5)."""
    tested_modules = {e.src for e in graph.edges if e.relation == "tested_by"}
    return {
        node.source_file
        for node in graph.nodes.values()
        if node.source_file and any(node.id.startswith(m) for m in tested_modules)
    }


def plan(finding: Finding, covered_files: set[str]) -> FixPlan:
    if finding.status is not FindingStatus.VALIDATED:
        raise PlanRefusedError(f"{finding.id}: only validated findings are plannable (FR-6.3)")
    if not finding.uses_only_extracted:
        raise PlanRefusedError(f"{finding.id}: evidence chain is not EXTRACTED end to end")
    if finding.kind in HUMAN_ONLY:
        raise PlanRefusedError(f"{finding.id}: {finding.kind.value} requires human triage")
    strategy, expected = STRATEGIES[finding.kind]
    target_files = tuple(sorted({
        link.source_file for link in finding.evidence_chain if link.source_file
    }))
    if not target_files:
        raise PlanRefusedError(f"{finding.id}: no source files in evidence chain")
    uncovered = [name for name in target_files if name not in covered_files]
    steps = (
        *((f"write characterization tests pinning {', '.join(uncovered)}",) if uncovered else ()),
        f"apply strategy: {strategy}",
        "run the full target test suite",
        "rebuild the graph and diff against the previous iteration",
    )
    return FixPlan(
        finding_id=finding.id,
        strategy=strategy,
        target_files=target_files,
        steps=steps,
        expected_metric_delta=expected,
        test_strategy="existing suite" if not uncovered else "characterization-first",
        needs_characterization=bool(uncovered),
    )

"""Detector registry — run all, rank, assign ids, persist (T235).

Ranking is confidence x impact (PRD_defect_detection §2): impact is the
finding's maximum node betweenness normalized to the graph's maximum,
floored so zero-centrality findings (doc gaps, islands) still order by
confidence instead of vanishing.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from hw4.services.detectors.base import Detector, Finding
from hw4.services.detectors.duplication import DuplicationDetector
from hw4.services.detectors.god_node import GodNodeDetector
from hw4.services.detectors.isolation import IsolationDetector
from hw4.services.detectors.spof import SpofDetector
from hw4.services.detectors.traceability import TraceabilityDetector
from hw4.services.graph_metrics import Metrics
from hw4.services.graph_models import Graph
from hw4.shared.config import Config
from hw4.shared.version import __version__

IMPACT_FLOOR = 0.05


def all_detectors() -> list[Detector]:
    return [
        SpofDetector(),
        GodNodeDetector(),
        IsolationDetector(),
        TraceabilityDetector(),
        DuplicationDetector(),
    ]


def run_all(graph: Graph, metrics: Metrics, config: Config) -> list[Finding]:
    """Every detector once, ranked, with stable F-NNN ids assigned."""
    findings: list[Finding] = []
    for detector in all_detectors():
        findings.extend(detector.detect(graph, metrics, config))
    max_betweenness = max(metrics.betweenness.values(), default=0.0) or 1.0

    def rank_key(finding: Finding) -> tuple:
        centrality = max((metrics.betweenness.get(n, 0.0) for n in finding.nodes), default=0.0)
        impact = max(centrality / max_betweenness, IMPACT_FLOOR)
        return (-finding.confidence * impact, finding.kind.value, finding.nodes[0])

    findings.sort(key=rank_key)
    for index, finding in enumerate(findings, start=1):
        finding.id = f"F-{index:03d}"
    return findings


def dump_findings(findings: list[Finding], path: Path | str, iteration: int) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = {
        "version": __version__,
        "iteration": iteration,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "findings": [finding.to_dict() for finding in findings],
    }
    path.write_text(json.dumps(doc, indent=1, sort_keys=True), encoding="utf-8")
    return path

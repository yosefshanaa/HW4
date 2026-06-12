"""Isolation detector — disconnected clusters need triage (T229-T230).

Part-C is explicit: isolation is a *finding*, not a diagnosis. Metrics
see only dependency relations, so before claiming isolation we (a) merge
dependency-isolated nodes into groups over ALL relations (an orphan
package plus its rationale notes is ONE island, not three), and (b) skip
any group that touches the main component through any relation at all —
"not dependency-connected" is a different claim than "isolated".
The topology fact is EXTRACTED; its meaning ships as a checklist.
"""

from __future__ import annotations

from collections import deque

from hw4.constants import EdgeEvidence, FindingKind
from hw4.services.detectors.base import Detector, EvidenceLink, Finding
from hw4.services.graph_metrics import Metrics
from hw4.services.graph_models import Graph
from hw4.shared.config import Config

TRIAGE_OPTIONS = [
    "intentional standalone (plugin/tool/example)",
    "deprecated or dead code",
    "extractor miss (dynamic import / reflection)",
    "semantic-only relation the graph cannot see",
]
CODE_TYPES = ("module", "class", "function")


class IsolationDetector(Detector):
    kind = FindingKind.ISOLATED

    def detect(self, graph: Graph, metrics: Metrics, config: Config) -> list[Finding]:
        min_size = int(config.get("detectors.isolation.min_size"))
        isolated = {n for component in metrics.isolated_components for n in component}
        if not isolated:
            return []
        main = set(graph.nodes) - isolated
        findings = []
        for group in _groups(graph, isolated):
            touches_main = any(
                (e.src in group and e.dst in main) or (e.dst in group and e.src in main)
                for e in graph.edges
            )
            if touches_main:
                continue
            code_nodes = sorted(
                n for n in group if n in graph.nodes and graph.nodes[n].type in CODE_TYPES
            )
            if len(code_nodes) < min_size:
                continue
            findings.append(self._finding(graph, group, code_nodes))
        return findings

    def _finding(self, graph: Graph, group: set[str], code_nodes: list[str]) -> Finding:
        anchor = graph.nodes[code_nodes[0]]
        chain = [
            EvidenceLink(
                observation=(
                    f"island of {len(group)} nodes (anchor {anchor.id}) has no edges of "
                    "any relation to the main component"
                ),
                relation="imports",
                evidence=EdgeEvidence.EXTRACTED,
                confidence=0.9,
                source_file=anchor.source_file,
            ),
            EvidenceLink(
                observation="meaning of the isolation is undetermined — requires triage",
                relation="imports",
                evidence=EdgeEvidence.AMBIGUOUS,
                confidence=0.5,
                source_file=anchor.source_file,
            ),
        ]
        return Finding(
            id="",
            kind=self.kind,
            nodes=sorted(group),
            evidence_chain=chain,
            suggested_action="human triage against the checklist before any action",
            triage_checklist=list(TRIAGE_OPTIONS),
        )


def _groups(graph: Graph, isolated: set[str]) -> list[set[str]]:
    """Connected components over ALL relations, restricted to isolated nodes."""
    adjacency: dict[str, set[str]] = {n: set() for n in isolated}
    for edge in graph.edges:
        if edge.src in isolated and edge.dst in isolated:
            adjacency[edge.src].add(edge.dst)
            adjacency[edge.dst].add(edge.src)
    groups, seen = [], set()
    for start in sorted(isolated):
        if start in seen:
            continue
        group, queue = {start}, deque([start])
        while queue:
            for neighbor in adjacency[queue.popleft()]:
                if neighbor not in group:
                    group.add(neighbor)
                    queue.append(neighbor)
        seen |= group
        groups.append(group)
    return groups

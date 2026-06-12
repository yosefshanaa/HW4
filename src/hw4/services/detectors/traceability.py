"""Traceability detector — documented-but-nonexistent claims (T231-T232).

The extractor turns each unresolvable doc mention into a `missing:`
placeholder with an AMBIGUOUS edge; this detector promotes those into
TRACE_GAP hypotheses. Inversely, code modules no doc ever mentions are
reported as undocumented (lower confidence — absence of evidence).
"""

from __future__ import annotations

from hw4.constants import EdgeEvidence, FindingKind
from hw4.services.detectors.base import Detector, EvidenceLink, Finding
from hw4.services.graph_metrics import Metrics
from hw4.services.graph_models import Graph
from hw4.shared.config import Config


class TraceabilityDetector(Detector):
    kind = FindingKind.TRACE_GAP

    def detect(self, graph: Graph, metrics: Metrics, config: Config) -> list[Finding]:
        findings = [
            self._gap_finding(graph, edge)
            for edge in graph.edges
            if edge.relation == "mentions" and edge.dst.startswith("missing:")
        ]
        if bool(config.get("detectors.traceability.report_undocumented")):
            findings.extend(self._undocumented_modules(graph))
        return findings

    def _gap_finding(self, graph: Graph, edge) -> Finding:
        doc = graph.nodes[edge.src]
        claimed = edge.dst.removeprefix("missing:")
        chain = [
            EvidenceLink(
                observation=f"{doc.source_file} documents {claimed!r}",
                relation="mentions",
                evidence=EdgeEvidence.EXTRACTED,
                confidence=0.9,
                source_file=doc.source_file,
            ),
            EvidenceLink(
                observation=f"{claimed!r} resolves to no code entity in the graph",
                relation="mentions",
                evidence=EdgeEvidence.AMBIGUOUS,
                confidence=0.4,
                source_file=doc.source_file,
            ),
        ]
        return Finding(
            id="",
            kind=self.kind,
            nodes=[edge.src, edge.dst],
            evidence_chain=chain,
            suggested_action=(
                f"verify {claimed!r} in source (constant/attribute/external?); if truly "
                "absent, fix the doc or implement the claim"
            ),
        )

    def _undocumented_modules(self, graph: Graph) -> list[Finding]:
        mentioned = {e.dst for e in graph.edges if e.relation == "mentions"}
        findings = []
        for node in graph.nodes.values():
            if node.type != "module" or node.id in mentioned:
                continue
            chain = [
                EvidenceLink(
                    observation=f"module {node.id} is mentioned by no doc page",
                    relation="mentions",
                    evidence=EdgeEvidence.INFERRED,
                    confidence=0.5,
                    source_file=node.source_file,
                )
            ]
            findings.append(
                Finding(
                    id="",
                    kind=self.kind,
                    nodes=[node.id],
                    evidence_chain=chain,
                    suggested_action="confirm whether the module is internal-only or doc debt",
                )
            )
        return findings

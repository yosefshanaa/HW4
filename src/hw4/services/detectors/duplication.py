"""Duplication detector — similarity pairs as hypotheses only (T233-T234).

Part-C example 3 verbatim: semantic similarity NEVER justifies deletion
by itself. Each pair ships a mandatory verification checklist; the AST
backend does not emit `semantically_similar_to` edges, so on our own
graphs this detector is naturally silent — it exists for backends that
do (real Graphify) and is fixture-tested.
"""

from __future__ import annotations

from hw4.constants import FindingKind
from hw4.services.detectors.base import Detector, EvidenceLink, Finding
from hw4.services.graph_metrics import Metrics
from hw4.services.graph_models import Graph
from hw4.shared.config import Config

VERIFY_CHECKLIST = [
    "compare actual purpose (names lie)",
    "compare call sites / usage contexts",
    "compare test coverage of both sides",
    "check for intentional fork (compat shims, vendoring)",
]


class DuplicationDetector(Detector):
    kind = FindingKind.DUPLICATION

    def detect(self, graph: Graph, metrics: Metrics, config: Config) -> list[Finding]:
        min_confidence = float(config.get("detectors.duplication.min_confidence"))
        findings = []
        for edge in graph.edges:
            if edge.relation != "semantically_similar_to":
                continue
            if edge.confidence < min_confidence:
                continue
            src = graph.nodes[edge.src]
            chain = [
                EvidenceLink(
                    observation=(
                        f"{edge.src} and {edge.dst} marked semantically similar "
                        f"(confidence {edge.confidence:.2f})"
                    ),
                    relation=edge.relation,
                    evidence=edge.evidence,
                    confidence=edge.confidence,
                    source_file=src.source_file,
                )
            ]
            findings.append(
                Finding(
                    id="",
                    kind=self.kind,
                    nodes=[edge.src, edge.dst],
                    evidence_chain=chain,
                    suggested_action=(
                        "complete the verification checklist; consolidation only "
                        "after purpose/usage/tests all confirm true duplication"
                    ),
                    triage_checklist=list(VERIFY_CHECKLIST),
                )
            )
        return findings

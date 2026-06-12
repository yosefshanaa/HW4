"""SPOF detector — mandatory-path bottlenecks (FR-6, T225-T226).

The Part-C distinction drives the whole rule: a node everyone *can*
route around is a healthy hub; a node everyone *must* route through is
a single point of failure. We therefore require BOTH high betweenness
rank AND a mandatory-path ratio above the configured floor — a redundant
hub has ratio ≈ 0 and is never flagged, no matter how central.
"""

from __future__ import annotations

from hw4.constants import EdgeEvidence, FindingKind
from hw4.services.detectors.base import Detector, EvidenceLink, Finding
from hw4.services.graph_metrics import Metrics
from hw4.services.graph_models import Graph
from hw4.shared.config import Config


class SpofDetector(Detector):
    kind = FindingKind.SPOF

    def detect(self, graph: Graph, metrics: Metrics, config: Config) -> list[Finding]:
        min_ratio = float(config.get("detectors.spof.min_mandatory_ratio"))
        max_rank = int(config.get("detectors.spof.max_rank"))
        findings = []
        for evidence in metrics.bottlenecks:
            if evidence.rank > max_rank or evidence.mandatory_path_ratio < min_ratio:
                continue
            node = graph.nodes[evidence.node_id]
            dominant = max(evidence.relation_profile, key=evidence.relation_profile.get)
            chain = [
                EvidenceLink(
                    observation=(
                        f"{node.id} holds betweenness rank {evidence.rank} "
                        f"(score {evidence.betweenness})"
                    ),
                    relation=dominant,
                    evidence=EdgeEvidence.EXTRACTED,
                    confidence=1.0,
                    source_file=node.source_file,
                ),
                EvidenceLink(
                    observation=(
                        f"removing {node.id} disconnects "
                        f"{evidence.mandatory_path_ratio:.0%} of previously connected "
                        f"pairs — paths through it are mandatory, not optional"
                    ),
                    relation=dominant,
                    evidence=EdgeEvidence.EXTRACTED,
                    confidence=round(min(0.95, 0.5 + evidence.mandatory_path_ratio / 2), 2),
                    source_file=node.source_file,
                ),
            ]
            findings.append(
                Finding(
                    id="",
                    kind=self.kind,
                    nodes=[node.id],
                    evidence_chain=chain,
                    suggested_action=(
                        "introduce an interface/seam so dependents do not all route "
                        f"through {node.label}; verify against source first"
                    ),
                )
            )
        return findings

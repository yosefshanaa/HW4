"""God-node detector — does-everything outliers (FR-6, T227-T228).

Adjudication theory (Part-C): a popular *utility* has high fan-IN and
one concern — that is healthy and must not be condemned. A god node has
high fan-OUT *across multiple communities* (it reaches into everyone
else's business). Both criteria are attached to the finding as evidence
so the healthy-hub counter-argument is visible to the human triager.
"""

from __future__ import annotations

from statistics import median

from hw4.constants import EdgeEvidence, FindingKind
from hw4.services.detectors.base import Detector, EvidenceLink, Finding
from hw4.services.graph_metrics import Metrics
from hw4.services.graph_models import Graph
from hw4.shared.config import Config


class GodNodeDetector(Detector):
    kind = FindingKind.GOD_NODE

    def detect(self, graph: Graph, metrics: Metrics, config: Config) -> list[Finding]:
        multiplier = float(config.get("detectors.god_node.degree_multiplier"))
        percentile = float(config.get("detectors.god_node.percentile"))
        min_fan_out = int(config.get("detectors.god_node.min_fan_out"))
        min_communities = int(config.get("detectors.god_node.min_communities"))
        degrees = sorted(
            metrics.fan_in[n] + metrics.fan_out[n]
            for n in metrics.fan_in
            if metrics.fan_in[n] + metrics.fan_out[n] > 0
        )
        if not degrees:
            return []
        # call graphs are dominated by degree-1 leaves: a median multiple
        # alone flags half the library, so an outlier must ALSO clear the
        # configured percentile of the nonzero-degree distribution
        cutoff = degrees[int(percentile * (len(degrees) - 1))]
        threshold = max(median(degrees) * multiplier, cutoff)
        findings = []
        for node_id in metrics.fan_out:
            fan_in, fan_out = metrics.fan_in[node_id], metrics.fan_out[node_id]
            if fan_out < min_fan_out or fan_in + fan_out <= threshold:
                continue
            touched = self._touched_communities(node_id, graph, metrics)
            if len(touched) < min_communities:
                continue  # cohesive within one concern — not condemned
            node = graph.nodes[node_id]
            chain = [
                EvidenceLink(
                    observation=(
                        f"{node_id} degree {fan_in + fan_out} exceeds "
                        f"{multiplier}x median ({threshold:.1f}); fan_out={fan_out}"
                    ),
                    relation="calls",
                    evidence=EdgeEvidence.EXTRACTED,
                    confidence=0.9,
                    source_file=node.source_file,
                ),
                EvidenceLink(
                    observation=(
                        f"outbound reach spans {len(touched)} communities — "
                        f"fan-OUT across concerns, unlike a fan-IN utility "
                        f"(healthy-hub counter-check: fan_in={fan_in})"
                    ),
                    relation="calls",
                    evidence=EdgeEvidence.EXTRACTED,
                    confidence=0.8,
                    source_file=node.source_file,
                ),
            ]
            findings.append(
                Finding(
                    id="",
                    kind=self.kind,
                    nodes=[node_id],
                    evidence_chain=chain,
                    suggested_action=(
                        f"split {node.label} by concern (one community per "
                        "responsibility); confirm concern-mixing in source first"
                    ),
                )
            )
        return findings

    @staticmethod
    def _touched_communities(node_id: str, graph: Graph, metrics: Metrics) -> set[int]:
        touched = set()
        for edge in graph.edges:
            if edge.src == node_id and edge.dst in metrics.community_of:
                touched.add(metrics.community_of[edge.dst])
        return touched

"""Detector ABC + Finding model with evidence chains (FR-6, T223-T224).

A Finding is a *falsifiable hypothesis*, never a verdict (Part-C). Its
confidence is the MINIMUM over the evidence chain — a chain is as strong
as its weakest link — and its status starts at `hypothesis`; only manual
source validation may promote it. The JSON shape here IS the
findings.json schema documented in PRD_defect_detection §2 (T098).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field

from hw4.constants import EdgeEvidence, FindingKind, FindingStatus
from hw4.services.graph_metrics import Metrics
from hw4.services.graph_models import Graph
from hw4.shared.config import Config


@dataclass(frozen=True)
class EvidenceLink:
    """One step of the Part-C inference pipeline, machine-readable."""

    observation: str
    relation: str
    evidence: EdgeEvidence
    confidence: float
    source_file: str = ""


@dataclass
class Finding:
    """One architectural hypothesis with its full evidence chain."""

    id: str
    kind: FindingKind
    nodes: list[str]
    evidence_chain: list[EvidenceLink]
    status: FindingStatus = FindingStatus.HYPOTHESIS
    suggested_action: str = ""
    triage_checklist: list[str] = field(default_factory=list)

    @property
    def confidence(self) -> float:
        """Weakest-link aggregation (Part-C): min over the chain."""
        if not self.evidence_chain:
            return 0.0
        return min(link.confidence for link in self.evidence_chain)

    @property
    def uses_only_extracted(self) -> bool:
        """Fix-loop eligibility gate: EXTRACTED evidence end to end."""
        return bool(self.evidence_chain) and all(
            link.evidence is EdgeEvidence.EXTRACTED for link in self.evidence_chain
        )

    def to_dict(self) -> dict:
        doc = asdict(self)
        doc["kind"] = self.kind.value
        doc["status"] = self.status.value
        doc["confidence"] = round(self.confidence, 4)
        for link in doc["evidence_chain"]:
            link["evidence"] = (
                link["evidence"].value
                if isinstance(link["evidence"], EdgeEvidence)
                else link["evidence"]
            )
        return doc


class Detector(ABC):
    """One architectural smell, one deterministic detection pass."""

    kind: FindingKind

    @abstractmethod
    def detect(self, graph: Graph, metrics: Metrics, config: Config) -> list[Finding]:
        """Return findings with placeholder ids; the registry assigns F-NNN."""

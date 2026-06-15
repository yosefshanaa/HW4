"""Confusion matrix for detector evaluation (L07 §13.2).

The detectors make binary predictions ("is node X a god node?"); the
mini_repo answer key records the ground truth for a fixed candidate set
(planted defects plus false-positive guards). Comparing the two yields
the standard TP/FP/FN/TN cells and precision/recall/F1 — the lesson's
agent-evaluation discipline applied to our deterministic spine. The
matching is by node id so the scorer needs no graph, only the findings.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from hw4.constants import FindingKind
from hw4.services.detectors.base import Finding


@dataclass(frozen=True)
class Candidate:
    """One labeled ground-truth fact the detectors are scored against."""

    target: str
    kind: FindingKind
    is_defect: bool
    rationale: str


@dataclass(frozen=True)
class Outcome:
    """A candidate after scoring: whether it was predicted, and its cell."""

    candidate: Candidate
    predicted: bool

    @property
    def cell(self) -> str:
        if self.candidate.is_defect:
            return "TP" if self.predicted else "FN"
        return "FP" if self.predicted else "TN"


@dataclass(frozen=True)
class ConfusionMatrix:
    """2x2 outcome counts plus the derived classification metrics."""

    outcomes: list[Outcome]

    def _count(self, cell: str) -> int:
        return sum(1 for o in self.outcomes if o.cell == cell)

    @property
    def tp(self) -> int:
        return self._count("TP")

    @property
    def fp(self) -> int:
        return self._count("FP")

    @property
    def fn(self) -> int:
        return self._count("FN")

    @property
    def tn(self) -> int:
        return self._count("TN")

    @property
    def precision(self) -> float:
        denom = self.tp + self.fp
        return self.tp / denom if denom else 0.0

    @property
    def recall(self) -> float:
        denom = self.tp + self.fn
        return self.tp / denom if denom else 0.0

    @property
    def f1(self) -> float:
        denom = self.precision + self.recall
        return 2 * self.precision * self.recall / denom if denom else 0.0

    @property
    def accuracy(self) -> float:
        total = len(self.outcomes)
        return (self.tp + self.tn) / total if total else 0.0

    def to_dict(self) -> dict:
        return {
            "cells": {"tp": self.tp, "fp": self.fp, "fn": self.fn, "tn": self.tn},
            "metrics": {
                "precision": round(self.precision, 4),
                "recall": round(self.recall, 4),
                "f1": round(self.f1, 4),
                "accuracy": round(self.accuracy, 4),
            },
            "outcomes": [
                {
                    "target": o.candidate.target,
                    "kind": o.candidate.kind.value,
                    "expected": "defect" if o.candidate.is_defect else "clean",
                    "predicted": o.predicted,
                    "cell": o.cell,
                    "rationale": o.candidate.rationale,
                }
                for o in self.outcomes
            ],
        }


def _node_matches(node: str, target: str) -> bool:
    """A finding node satisfies a target by id, child prefix, or missing: tag."""
    return (
        node == target
        or node.startswith(target + ".")
        or node.removeprefix("missing:") == target
    )


def _predicted(findings: list[Finding], candidate: Candidate) -> bool:
    return any(
        f.kind == candidate.kind and any(_node_matches(n, candidate.target) for n in f.nodes)
        for f in findings
    )


def evaluate(findings: list[Finding], candidates: list[Candidate]) -> ConfusionMatrix:
    """Score detector findings against the labeled candidate set."""
    return ConfusionMatrix([Outcome(c, _predicted(findings, c)) for c in candidates])


def load_answer_key(path: Path | str) -> list[Candidate]:
    """Read the JSON ground-truth file into Candidate records."""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return [
        Candidate(
            target=item["target"],
            kind=FindingKind(item["kind"]),
            is_defect=item["label"] == "defect",
            rationale=item.get("rationale", ""),
        )
        for item in raw["candidates"]
    ]

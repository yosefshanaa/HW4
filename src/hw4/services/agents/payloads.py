"""Typed handoff payloads (PLAN §3.2, T298).

No free-text blob handoffs — free text is where token waste and
ambiguity live. Finding and FixPlan are reused from their services;
the two payloads unique to the agent layer live here.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class AnalysisRequest:
    """Orchestrator -> RepoAgent/GraphAnalyst."""

    repo_path: str
    iteration: int | None = None
    narrative_top_n: int = 3

    def to_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True)

    @classmethod
    def from_json(cls, raw: str) -> AnalysisRequest:
        return cls(**json.loads(raw))


@dataclass(frozen=True)
class IterationVerdict:
    """QAAgent -> Orchestrator after one loop iteration."""

    verdict: str  # improved / neutral / regressed
    tests_green: bool
    stop: bool
    reason: str = ""
    notes: str = ""

    def to_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True)

    @classmethod
    def from_json(cls, raw: str) -> IterationVerdict:
        return cls(**json.loads(raw))

"""Immutable project-wide constants and enumerations.

Why enums and not strings: every downstream consumer (detectors, agents,
findings, loop log) must carry the evidence class and stop reason explicitly;
a typo'd string would silently corrupt the evidence chain that Part-C's
responsible-inference method depends on.

Configurable *values* (thresholds, limits, model ids) do NOT belong here —
they live in config/ (guidelines §7.2). Only invariants of the domain do.
"""

from __future__ import annotations

from enum import Enum


class EdgeEvidence(str, Enum):
    """Evidence strength of a graph edge (L07 §6, Part-C evidence scale).

    EXTRACTED — deterministic, found directly in source (import / call).
    INFERRED  — LLM/heuristic semantic inference; useful, needs validation.
    AMBIGUOUS — uncertain; a stop-flag requiring human review, never an
                input to automated fixes.
    """

    EXTRACTED = "EXTRACTED"
    INFERRED = "INFERRED"
    AMBIGUOUS = "AMBIGUOUS"


class FindingKind(str, Enum):
    """Architectural defect categories the detectors can hypothesize."""

    SPOF = "SPOF"
    GOD_NODE = "GOD_NODE"
    ISOLATED = "ISOLATED"
    TRACE_GAP = "TRACE_GAP"
    DUPLICATION = "DUPLICATION"


class FindingStatus(str, Enum):
    """Lifecycle of a finding: hypothesis until source-validated (Part-C)."""

    HYPOTHESIS = "hypothesis"
    VALIDATED = "validated"
    REJECTED = "rejected"
    FIXED = "fixed"
    BLOCKED = "blocked"


class StopReason(str, Enum):
    """Why the improvement loop terminated — exactly one per run (FR-7.2)."""

    MAX_ITERATIONS = "MAX_ITERATIONS"
    GOAL_METRIC_REACHED = "GOAL_METRIC_REACHED"
    TESTS_GREEN_NO_MORE_FINDINGS = "TESTS_GREEN_NO_MORE_FINDINGS"
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"
    NO_SAFE_ACTION = "NO_SAFE_ACTION"


class ModelTier(str, Enum):
    """Cost tiers for LLM usage (ADR-3): cheap for drafts, strong for fixes."""

    CHEAP = "cheap"
    STRONG = "strong"

"""Tests for hw4.constants — enum integrity and string round-trips."""

import pytest

from hw4.constants import EdgeEvidence, FindingKind, FindingStatus, ModelTier, StopReason


class TestEdgeEvidence:
    def test_members(self):
        assert {e.name for e in EdgeEvidence} == {"EXTRACTED", "INFERRED", "AMBIGUOUS"}

    def test_string_round_trip(self):
        assert EdgeEvidence("EXTRACTED") is EdgeEvidence.EXTRACTED
        assert EdgeEvidence.INFERRED.value == "INFERRED"

    def test_is_str_subclass_for_json_serialization(self):
        assert isinstance(EdgeEvidence.AMBIGUOUS, str)

    def test_unknown_value_rejected(self):
        with pytest.raises(ValueError):
            EdgeEvidence("GUESSED")


class TestFindingKind:
    def test_members(self):
        expected = {"SPOF", "GOD_NODE", "ISOLATED", "TRACE_GAP", "DUPLICATION"}
        assert {k.name for k in FindingKind} == expected


class TestFindingStatus:
    def test_lifecycle_members(self):
        expected = {"hypothesis", "validated", "rejected", "fixed", "blocked"}
        assert {s.value for s in FindingStatus} == expected


class TestStopReason:
    def test_members(self):
        expected = {
            "MAX_ITERATIONS",
            "GOAL_METRIC_REACHED",
            "TESTS_GREEN_NO_MORE_FINDINGS",
            "BUDGET_EXCEEDED",
            "NO_SAFE_ACTION",
        }
        assert {r.value for r in StopReason} == expected


class TestModelTier:
    def test_members(self):
        assert {t.value for t in ModelTier} == {"cheap", "strong"}

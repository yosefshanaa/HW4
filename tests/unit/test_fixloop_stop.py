"""Tests for fixloop.stop — targeted rules + full-space invariants."""

import itertools

import pytest

from hw4.constants import StopReason
from hw4.services.fixloop.stop import IterationOutcome, LoopState, evaluate


def state(**overrides):
    base = {
        "iteration": 1, "max_iterations": 3, "tests_green": True,
        "verdict": "neutral", "budget_exceeded": False, "findings_remaining": 2,
    }
    base.update(overrides)
    return LoopState(**base)


class TestRules:
    def test_budget_beats_everything(self):
        outcome = evaluate(state(budget_exceeded=True, verdict="improved"))
        assert outcome == IterationOutcome(True, True, StopReason.BUDGET_EXCEEDED)

    def test_green_improved_reaches_goal(self):
        outcome = evaluate(state(verdict="improved"))
        assert outcome == IterationOutcome(True, True, StopReason.GOAL_METRIC_REACHED)

    def test_red_tests_reject_and_continue_while_findings_remain(self):
        outcome = evaluate(state(tests_green=False))
        assert outcome == IterationOutcome(False, False, None)

    def test_red_tests_with_nothing_left_is_no_safe_action(self):
        outcome = evaluate(state(tests_green=False, findings_remaining=0))
        assert outcome == IterationOutcome(False, True, StopReason.NO_SAFE_ACTION)

    def test_green_neutral_with_nothing_left_stops_cleanly(self):
        outcome = evaluate(state(findings_remaining=0))
        assert outcome == IterationOutcome(True, True, StopReason.TESTS_GREEN_NO_MORE_FINDINGS)

    def test_regression_is_rejected_even_with_green_tests(self):
        outcome = evaluate(state(verdict="regressed"))
        assert outcome.accept is False

    def test_iteration_cap(self):
        outcome = evaluate(state(iteration=3))
        assert outcome == IterationOutcome(True, True, StopReason.MAX_ITERATIONS)

    def test_mid_loop_neutral_continues(self):
        assert evaluate(state()) == IterationOutcome(True, False, None)


class TestFullSpaceInvariants:
    SPACE = list(itertools.product(
        (1, 3),                       # iteration (3 == at cap)
        (True, False),                # tests_green
        ("improved", "neutral", "regressed"),
        (True, False),                # budget_exceeded
        (0, 2),                       # findings_remaining
    ))

    @pytest.mark.parametrize("iteration,green,verdict,budget,remaining", SPACE)
    def test_invariants_hold_everywhere(self, iteration, green, verdict, budget, remaining):
        outcome = evaluate(state(
            iteration=iteration, tests_green=green, verdict=verdict,
            budget_exceeded=budget, findings_remaining=remaining,
        ))
        # exactly one reason iff stopping
        assert (outcome.reason is not None) == outcome.stop
        # a red-test iteration is never accepted
        if not green:
            assert not outcome.accept
        # a regression is never accepted
        if verdict == "regressed":
            assert not outcome.accept
        # budget always stops, with the budget reason
        if budget:
            assert outcome.stop and outcome.reason is StopReason.BUDGET_EXCEEDED
        # the loop can only continue if work remains and the cap is not hit
        if not outcome.stop:
            assert remaining > 0 and iteration < 3

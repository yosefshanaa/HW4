"""Stop-condition evaluation — a pure, exhaustively testable function (T329).

Rule priority (FR-7.2, PRD_fix_loop §2): budget beats everything; red
tests force a revert; an improved metric on green tests is the goal; a
neutral green iteration is kept but does not stop the loop by itself.
Every run terminates with exactly ONE StopReason — tested as an
invariant over the full input space.
"""

from __future__ import annotations

from dataclasses import dataclass

from hw4.constants import StopReason
from hw4.services.graph_diff import IMPROVED, REGRESSED


@dataclass(frozen=True)
class LoopState:
    """Everything the stop rule may consider, nothing it may not."""

    iteration: int  # 1-based number of the iteration just finished
    max_iterations: int
    tests_green: bool
    verdict: str  # graph_diff: improved / neutral / regressed
    budget_exceeded: bool
    findings_remaining: int  # actionable findings left AFTER this one


@dataclass(frozen=True)
class IterationOutcome:
    """accept = keep the change; stop = end the loop with `reason`."""

    accept: bool
    stop: bool
    reason: StopReason | None


def evaluate(state: LoopState) -> IterationOutcome:
    accept = state.tests_green and state.verdict != REGRESSED
    if state.budget_exceeded:
        return IterationOutcome(accept=accept, stop=True, reason=StopReason.BUDGET_EXCEEDED)
    if accept and state.verdict == IMPROVED:
        return IterationOutcome(accept=True, stop=True, reason=StopReason.GOAL_METRIC_REACHED)
    if state.findings_remaining <= 0:
        reason = (
            StopReason.TESTS_GREEN_NO_MORE_FINDINGS if accept else StopReason.NO_SAFE_ACTION
        )
        return IterationOutcome(accept=accept, stop=True, reason=reason)
    if state.iteration >= state.max_iterations:
        return IterationOutcome(accept=accept, stop=True, reason=StopReason.MAX_ITERATIONS)
    return IterationOutcome(accept=accept, stop=False, reason=None)

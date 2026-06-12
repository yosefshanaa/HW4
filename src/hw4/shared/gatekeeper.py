"""Central API gatekeeper — no external API call may bypass it (NFR-2, §5).

One choke point gives us four properties for free everywhere: config-driven
rate limiting, queue-instead-of-crash on saturation, bounded retries on
transient failures, and a complete token/cost audit trail in the Ledger —
which is also the budget firewall that hard-stops runaway agent loops.

Clock and sleeper are injected so tests control time instead of sleeping.
"""

from __future__ import annotations

import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass

from hw4.shared.config import Config
from hw4.shared.ledger import Ledger
from hw4.shared.logging_setup import get_logger, log_event

MINUTE = 60.0
HOUR = 3600.0


class BudgetExceededError(RuntimeError):
    """Cumulative spend reached budget.max_usd — the run must stop."""


class TransientApiError(RuntimeError):
    """Retryable failure (rate-limit response, network blip, 5xx)."""


class RetriesExhaustedError(RuntimeError):
    """Transient failures persisted beyond max_retries."""


@dataclass(frozen=True)
class CallResult:
    """What a gated callable returns: a value plus its token usage."""

    value: object
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass(frozen=True)
class QueueStatus:
    """Observability for the saturation queue (guidelines §5.1)."""

    waits: int
    total_wait_seconds: float
    minute_window_used: int
    hour_window_used: int


class ApiGatekeeper:
    """Centralized API call manager (guidelines §5.1 interface)."""

    def __init__(
        self,
        config: Config,
        ledger: Ledger,
        service: str = "default",
        clock: Callable[[], float] = time.monotonic,
        sleeper: Callable[[float], None] = time.sleep,
    ):
        limits = config.service_limits(service)
        self._rpm = int(limits["requests_per_minute"])
        self._rph = int(limits["requests_per_hour"])
        self._retry_after = float(limits["retry_after_seconds"])
        self._max_retries = int(limits["max_retries"])
        self._max_usd = float(config.get("budget.max_usd"))
        self._warn_usd = float(config.get("budget.warn_usd", default=self._max_usd))
        self._ledger = ledger
        self._clock = clock
        self._sleep = sleeper
        self._minute_window: deque[float] = deque()
        self._hour_window: deque[float] = deque()
        self._waits = 0
        self._total_wait = 0.0

    def _evict(self, now: float) -> None:
        while self._minute_window and now - self._minute_window[0] >= MINUTE:
            self._minute_window.popleft()
        while self._hour_window and now - self._hour_window[0] >= HOUR:
            self._hour_window.popleft()

    def _wait_for_slot(self) -> None:
        """Queue (never drop) until both rate windows have room (§5.3)."""
        while True:
            now = self._clock()
            self._evict(now)
            delays = []
            if len(self._minute_window) >= self._rpm:
                delays.append(MINUTE - (now - self._minute_window[0]))
            if len(self._hour_window) >= self._rph:
                delays.append(HOUR - (now - self._hour_window[0]))
            if not delays:
                return
            wait = max(max(delays), 0.0) + 0.01
            self._waits += 1
            self._total_wait += wait
            log_event(get_logger("gatekeeper"), "rate-limit queue wait", seconds=round(wait, 2))
            self._sleep(wait)

    def _check_budget(self) -> None:
        spent = self._ledger.total_cost()
        if spent >= self._max_usd:
            raise BudgetExceededError(f"spent ${spent:.4f} >= budget ${self._max_usd:.2f}")
        if spent >= self._warn_usd:
            log_event(get_logger("gatekeeper"), "budget warning", spent_usd=spent)

    def execute(self, call: Callable[[], CallResult], *, purpose_tag: str, model: str = "") -> object:
        """Run one gated call: budget check, slot wait, retries, ledger row."""
        self._check_budget()
        self._wait_for_slot()
        attempts = 0
        started = self._clock()
        while True:
            try:
                result = call()
                break
            except TransientApiError as exc:
                attempts += 1
                if attempts > self._max_retries:
                    self._record(purpose_tag, model, 0, 0, started, status="retries_exhausted")
                    raise RetriesExhaustedError(str(exc)) from exc
                self._sleep(self._retry_after)
        stamp = self._clock()
        self._minute_window.append(stamp)
        self._hour_window.append(stamp)
        status = "ok" if attempts == 0 else "retry_ok"
        self._record(purpose_tag, model, result.input_tokens, result.output_tokens, started, status)
        return result.value

    def _record(
        self, tag: str, model: str, tokens_in: int, tokens_out: int, started: float, status: str
    ) -> None:
        self._ledger.record(
            purpose_tag=tag,
            model=model,
            input_tokens=tokens_in,
            output_tokens=tokens_out,
            latency_ms=int((self._clock() - started) * 1000),
            status=status,
        )

    def get_queue_status(self) -> QueueStatus:
        """Queue depth and stats (guidelines §5.1 interface)."""
        self._evict(self._clock())
        return QueueStatus(
            waits=self._waits,
            total_wait_seconds=round(self._total_wait, 3),
            minute_window_used=len(self._minute_window),
            hour_window_used=len(self._hour_window),
        )

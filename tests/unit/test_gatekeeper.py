"""Tests for hw4.shared.gatekeeper — limits, queueing, retries, budget."""

import pytest

from hw4.shared.config import Config
from hw4.shared.gatekeeper import (
    ApiGatekeeper,
    BudgetExceededError,
    CallResult,
    RetriesExhaustedError,
    TransientApiError,
)
from hw4.shared.ledger import Ledger

from .test_config import write_config_dir


class FakeClock:
    """Deterministic time: advances only when told (or when sleeping)."""

    def __init__(self):
        self.now = 1000.0
        self.sleeps = []

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds


def make_gatekeeper(tmp_path, *, rpm=2, rph=100, max_retries=2, max_usd=10.0, pricing=None):
    setup = {
        "version": "1.00",
        "paths": {"results": "results"},
        "pricing_per_mtok": pricing or {"m": {"input": 1.0, "output": 1.0}},
        "budget": {"max_usd": max_usd, "warn_usd": max_usd},
    }
    rate_limits = {
        "rate_limits": {
            "version": "1.00",
            "services": {
                "default": {
                    "requests_per_minute": rpm,
                    "requests_per_hour": rph,
                    "concurrent_max": 5,
                    "retry_after_seconds": 30,
                    "max_retries": max_retries,
                    "queue_depth_max": 50,
                }
            },
        }
    }
    cfg = Config(write_config_dir(tmp_path / "cfg", setup=setup, rate_limits=rate_limits), environ={})
    ledger = Ledger(cfg, tmp_path / "ledger.jsonl")
    clock = FakeClock()
    gate = ApiGatekeeper(cfg, ledger, clock=clock, sleeper=clock.sleep)
    return gate, ledger, clock


def ok_call(value="v", tokens=(10, 5)):
    return lambda: CallResult(value=value, input_tokens=tokens[0], output_tokens=tokens[1])


class TestExecute:
    def test_returns_call_value(self, tmp_path):
        gate, _, _ = make_gatekeeper(tmp_path)
        assert gate.execute(ok_call("answer"), purpose_tag="t", model="m") == "answer"

    def test_every_call_logged_to_ledger(self, tmp_path):
        gate, ledger, _ = make_gatekeeper(tmp_path)
        gate.execute(ok_call(), purpose_tag="experiment.A.q1", model="m")
        entry = ledger.entries()[0]
        assert entry.purpose_tag == "experiment.A.q1"
        assert entry.input_tokens == 10
        assert entry.status == "ok"


class TestRateLimiting:
    def test_within_limit_no_waiting(self, tmp_path):
        gate, _, clock = make_gatekeeper(tmp_path, rpm=5)
        for _ in range(3):
            gate.execute(ok_call(), purpose_tag="t", model="m")
        assert clock.sleeps == []

    def test_saturation_queues_until_window_frees(self, tmp_path):
        gate, _, clock = make_gatekeeper(tmp_path, rpm=2)
        for _ in range(2):
            gate.execute(ok_call(), purpose_tag="t", model="m")
        gate.execute(ok_call(), purpose_tag="t", model="m")  # third must wait ~60s
        assert len(clock.sleeps) == 1
        assert clock.sleeps[0] == pytest.approx(60, abs=1)

    def test_queue_stats_exposed(self, tmp_path):
        gate, _, _ = make_gatekeeper(tmp_path, rpm=1)
        gate.execute(ok_call(), purpose_tag="t", model="m")
        gate.execute(ok_call(), purpose_tag="t", model="m")
        status = gate.get_queue_status()
        assert status.waits == 1
        assert status.total_wait_seconds > 0


class TestRetries:
    def test_transient_failure_retried_then_succeeds(self, tmp_path):
        gate, ledger, clock = make_gatekeeper(tmp_path)
        attempts = {"n": 0}

        def flaky():
            attempts["n"] += 1
            if attempts["n"] < 2:
                raise TransientApiError("429")
            return CallResult(value="done", input_tokens=1, output_tokens=1)

        assert gate.execute(flaky, purpose_tag="t", model="m") == "done"
        assert clock.sleeps == [30]  # retry_after from config
        assert ledger.entries()[0].status == "retry_ok"

    def test_retries_exhausted_raises_and_logs(self, tmp_path):
        gate, ledger, _ = make_gatekeeper(tmp_path, max_retries=1)

        def always_failing():
            raise TransientApiError("503")

        with pytest.raises(RetriesExhaustedError):
            gate.execute(always_failing, purpose_tag="t", model="m")
        assert ledger.entries()[0].status == "retries_exhausted"

    def test_non_transient_error_propagates_immediately(self, tmp_path):
        gate, _, clock = make_gatekeeper(tmp_path)

        def broken():
            raise ValueError("bad request")

        with pytest.raises(ValueError):
            gate.execute(broken, purpose_tag="t", model="m")
        assert clock.sleeps == []


class TestBudget:
    def test_budget_exceeded_blocks_before_calling(self, tmp_path):
        pricing = {"m": {"input": 1_000_000.0, "output": 0.0}}  # $1 per input token
        gate, _, _ = make_gatekeeper(tmp_path, max_usd=5.0, pricing=pricing)
        gate.execute(ok_call(tokens=(6, 0)), purpose_tag="t", model="m")  # spends $6
        with pytest.raises(BudgetExceededError):
            gate.execute(ok_call(), purpose_tag="t", model="m")

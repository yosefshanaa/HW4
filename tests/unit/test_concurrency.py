"""Concurrency stress tests — thread-safe gatekeeper/ledger + parallel wiki (§15)."""

import json
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from hw4.sdk.sdk import Hw4Sdk
from hw4.shared.config import Config
from hw4.shared.gatekeeper import ApiGatekeeper, CallResult
from hw4.shared.ledger import Ledger

from .test_config import write_config_dir
from .test_operations import FAST_RATE_LIMITS, FULL_SETUP

MINI_REPO = Path(__file__).resolve().parents[1] / "fixtures" / "mini_repo"
PROSE = "SUMMARY: generated.\nOPEN QUESTIONS:\n- q?\n"
N = 64


def _config(tmp_path, *, rpm=100000, rph=100000):
    setup = {
        "version": "1.00",
        "paths": {"results": "results"},
        "pricing_per_mtok": {"m": {"input": 1.0, "output": 1.0}},
        "budget": {"max_usd": 1e9, "warn_usd": 1e9},
    }
    rate_limits = {"rate_limits": {"version": "1.00", "services": {"default": {
        "requests_per_minute": rpm, "requests_per_hour": rph, "concurrent_max": 5,
        "retry_after_seconds": 0, "max_retries": 1, "queue_depth_max": 50}}}}
    return Config(write_config_dir(tmp_path / "cfg", setup=setup, rate_limits=rate_limits), environ={})


class ThreadSafeClock:
    """Deterministic clock for many threads: sleep advances shared fake time."""

    def __init__(self):
        self.t = 1000.0
        self.sleeps = 0
        self._lk = threading.Lock()

    def __call__(self):
        with self._lk:
            return self.t

    def sleep(self, seconds):
        with self._lk:
            self.t += seconds
            self.sleeps += 1


def _spawn(fn, count, workers=16):
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(fn, range(count)))


class TestLedgerThreadSafety:
    def test_concurrent_records_lose_no_rows(self, tmp_path):
        ledger = Ledger(_config(tmp_path), tmp_path / "ledger.jsonl")
        _spawn(lambda i: ledger.record(purpose_tag=f"t{i}", model="m",
               input_tokens=1, output_tokens=2, latency_ms=0), N)
        entries = ledger.entries()
        assert len(entries) == N
        assert {e.purpose_tag for e in entries} == {f"t{i}" for i in range(N)}
        assert sum(e.input_tokens for e in entries) == N

    def test_no_torn_jsonl_lines(self, tmp_path):
        ledger = Ledger(_config(tmp_path), tmp_path / "ledger.jsonl")
        _spawn(lambda i: ledger.record(purpose_tag="t", model="m",
               input_tokens=i, output_tokens=0, latency_ms=0), N)
        lines = (tmp_path / "ledger.jsonl").read_text(encoding="utf-8").splitlines()
        assert len(lines) == N
        for line in lines:  # every physical line is a whole JSON object
            json.loads(line)


class TestGatekeeperThreadSafety:
    def test_concurrent_execute_records_every_call(self, tmp_path):
        cfg = _config(tmp_path)
        ledger = Ledger(cfg, tmp_path / "ledger.jsonl")
        gate = ApiGatekeeper(cfg, ledger)  # real clock/sleeper, generous limits
        results = sorted(_spawn(lambda i: gate.execute(
            lambda i=i: CallResult(value=i, input_tokens=1, output_tokens=0),
            purpose_tag="c", model="m"), N))
        assert results == list(range(N))
        assert len(ledger.entries()) == N
        assert gate.get_queue_status().minute_window_used == N

    def test_saturation_queues_and_drops_nothing(self, tmp_path):
        cfg = _config(tmp_path, rpm=4)
        clock = ThreadSafeClock()
        ledger = Ledger(cfg, tmp_path / "ledger.jsonl")
        gate = ApiGatekeeper(cfg, ledger, clock=clock, sleeper=clock.sleep)
        _spawn(lambda i: gate.execute(
            lambda i=i: CallResult(value=i, input_tokens=1, output_tokens=0),
            purpose_tag="c", model="m"), 12, workers=8)
        assert len(ledger.entries()) == 12  # queued, never dropped
        assert gate.get_queue_status().waits > 0  # the limiter engaged under contention


class ThreadSafeTransport:
    """Records concurrent sends under a lock; returns one canned response."""

    def __init__(self, fill):
        self.fill = fill
        self.calls = []
        self._lk = threading.Lock()

    def send(self, model, messages, system, temperature, max_tokens):
        with self._lk:
            self.calls.append(model)
        return self.fill


class TestParallelWikiBuild:
    def test_all_pages_written_and_ledgered(self, tmp_path):
        from .test_llm_client import response

        write_config_dir(tmp_path / "config", setup={**FULL_SETUP,
                         "vault": {**FULL_SETUP["vault"], "wiki_workers": 4}},
                         rate_limits=FAST_RATE_LIMITS)
        transport = ThreadSafeTransport(response(text=PROSE))
        sdk = Hw4Sdk(config_dir="config", environ={}, base_dir=tmp_path, transport=transport)
        sdk.build_graph(MINI_REPO)
        report = sdk.build_vault()
        assert len(report.pages) > 1  # parallel branch genuinely exercised
        assert all(p.exists() and p.read_text(encoding="utf-8").strip() for p in report.pages)
        wiki_rows = [e for e in sdk.ledger.entries() if e.purpose_tag.startswith("wiki.gen.")]
        assert len(wiki_rows) == len(report.pages)  # one ledger row per page, none lost

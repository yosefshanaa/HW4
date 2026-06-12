"""Tests for hw4.shared.process_runner — capture, failure, timeout, audit."""

import sys

import pytest

from hw4.shared.process_runner import (
    ProcessFailedError,
    ProcessRunner,
    ProcessTimeoutError,
)

PY = sys.executable


def make_runner(timeout=10.0):
    return ProcessRunner(timeout_seconds=timeout)


class TestRun:
    def test_success_captures_stdout(self):
        result = make_runner().run([PY, "-c", "print('out')"])
        assert result.ok
        assert result.stdout.strip() == "out"

    def test_nonzero_exit_returned_not_raised(self):
        result = make_runner().run([PY, "-c", "raise SystemExit(3)"])
        assert not result.ok
        assert result.returncode == 3

    def test_stderr_captured(self):
        result = make_runner().run([PY, "-c", "import sys; sys.stderr.write('boom')"])
        assert "boom" in result.stderr

    def test_duration_recorded(self):
        result = make_runner().run([PY, "-c", "pass"])
        assert result.duration_seconds >= 0

    def test_cwd_respected(self, tmp_path):
        result = make_runner().run([PY, "-c", "import os; print(os.getcwd())"], cwd=tmp_path)
        assert result.stdout.strip().endswith(tmp_path.name)

    def test_timeout_raises(self):
        runner = make_runner(timeout=0.2)
        with pytest.raises(ProcessTimeoutError, match="timed out"):
            runner.run([PY, "-c", "import time; time.sleep(5)"])


class TestRunChecked:
    def test_success_passes_through(self):
        assert make_runner().run_checked([PY, "-c", "pass"]).ok

    def test_failure_raises_with_result_attached(self):
        with pytest.raises(ProcessFailedError) as excinfo:
            make_runner().run_checked([PY, "-c", "raise SystemExit(2)"])
        assert excinfo.value.result.returncode == 2


class TestAuditTrail:
    def test_history_records_every_invocation(self):
        runner = make_runner()
        runner.run([PY, "-c", "pass"])
        runner.run([PY, "-c", "raise SystemExit(1)"])
        assert len(runner.history) == 2
        assert runner.history[1].returncode == 1

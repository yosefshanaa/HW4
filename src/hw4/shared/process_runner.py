"""Single choke point for subprocess execution (graphify / git / pytest).

Mirrors the Gatekeeper philosophy for non-HTTP externals: every shell-out
goes through one wrapper that enforces timeouts, captures output, and logs
the invocation — so the loop audit can reconstruct exactly what ran (T047),
and tests can fake the entire outside world by faking one class.
"""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

from hw4.shared.logging_setup import get_logger, log_event


class ProcessTimeoutError(RuntimeError):
    """Raised when a subprocess exceeds its allotted timeout."""


class ProcessFailedError(RuntimeError):
    """Raised by run_checked when the subprocess exits nonzero."""

    def __init__(self, result: ProcessResult):
        self.result = result
        super().__init__(f"command failed rc={result.returncode}: {' '.join(result.command)}")


@dataclass(frozen=True)
class ProcessResult:
    """Outcome of one subprocess invocation."""

    command: list[str]
    returncode: int
    stdout: str
    stderr: str
    duration_seconds: float

    @property
    def ok(self) -> bool:
        return self.returncode == 0


@dataclass
class ProcessRunner:
    """Run external commands with timeout, capture, and an audit trail."""

    timeout_seconds: float
    history: list[ProcessResult] = field(default_factory=list)

    def run(self, command: list[str], cwd: Path | str | None = None) -> ProcessResult:
        """Execute; nonzero exit is returned (caller decides), timeout raises."""
        logger = get_logger("process")
        started = time.monotonic()
        try:
            completed = subprocess.run(
                command,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            log_event(logger, "process timeout", command=command, timeout=self.timeout_seconds)
            raise ProcessTimeoutError(f"timed out after {self.timeout_seconds}s: {command}") from exc
        result = ProcessResult(
            command=list(command),
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            duration_seconds=time.monotonic() - started,
        )
        self.history.append(result)
        log_event(
            logger,
            "process finished",
            command=command,
            returncode=result.returncode,
            duration=round(result.duration_seconds, 3),
        )
        return result

    def run_checked(self, command: list[str], cwd: Path | str | None = None) -> ProcessResult:
        """Execute and raise ProcessFailedError on nonzero exit."""
        result = self.run(command, cwd=cwd)
        if not result.ok:
            raise ProcessFailedError(result)
        return result

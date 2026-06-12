"""Hw4Sdk — the single entry point to all business logic (NFR-1, PLAN §1.2).

The CLI, agents, notebook, and tests all consume this facade; nothing
else imports services directly. Shared infrastructure (config, ledger,
gatekeeper, llm client) is wired here exactly once, lazily, so every
consumer shares one budget firewall and one audit trail per run.

Constructor injection everywhere: pass a prebuilt Config or transport
to substitute fakes in tests. Lifecycle methods that belong to later
phases raise ServiceNotReadyError until their service module lands —
the facade's surface is complete from day one, its depth grows.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from hw4.shared.config import Config
from hw4.shared.gatekeeper import ApiGatekeeper
from hw4.shared.ledger import Ledger
from hw4.shared.llm_client import LlmClient, make_anthropic_transport


class ServiceNotReadyError(NotImplementedError):
    """The requested capability's service module has not landed yet."""


def _new_run_id() -> str:
    return datetime.now(timezone.utc).strftime("run-%Y%m%d-%H%M%S")


class Hw4Sdk:
    """Facade over graph/vault/analysis/agents/experiment services."""

    def __init__(
        self,
        config: Config | None = None,
        *,
        config_dir: str = "config",
        environ: dict[str, str] | None = None,
        transport=None,
        base_dir: Path | str = ".",
        run_id: str = "",
    ):
        self._base_dir = Path(base_dir)
        self._config = config or Config(self._base_dir / config_dir, environ=environ)
        self._run_id = run_id or _new_run_id()
        self._transport = transport
        self._ledger: Ledger | None = None
        self._gatekeeper: ApiGatekeeper | None = None
        self._llm: LlmClient | None = None

    @property
    def config(self) -> Config:
        return self._config

    @property
    def run_id(self) -> str:
        return self._run_id

    @property
    def results_dir(self) -> Path:
        return self._base_dir / self._config.path("results")

    @property
    def ledger(self) -> Ledger:
        if self._ledger is None:
            self._ledger = Ledger(self._config, self.results_dir / "ledger.jsonl")
        return self._ledger

    @property
    def gatekeeper(self) -> ApiGatekeeper:
        if self._gatekeeper is None:
            self._gatekeeper = ApiGatekeeper(self._config, self.ledger)
        return self._gatekeeper

    @property
    def llm(self) -> LlmClient:
        """Gated LLM client; real Anthropic transport unless one was injected."""
        if self._llm is None:
            transport = self._transport or make_anthropic_transport(self._config)
            self._llm = LlmClient(self._config, self.gatekeeper, transport)
        return self._llm

    def _not_ready(self, capability: str, phase: str) -> ServiceNotReadyError:
        return ServiceNotReadyError(
            f"{capability} is wired in {phase} (docs/TODO.md); not available yet"
        )

    def build_graph(self, repo_path: Path | str):
        """Run graphify/fallback extractor on the target repo (FR-2)."""
        raise self._not_ready("build_graph", "Phase 4")

    def build_vault(self, graph_path: Path | str):
        """Generate the Obsidian vault from a graph (FR-3)."""
        raise self._not_ready("build_vault", "Phase 5")

    def analyze(self, graph_path: Path | str):
        """Run all detectors, return ranked findings (FR-6)."""
        raise self._not_ready("analyze", "Phase 6")

    def ask(self, question: str, *, mode: str = "graph"):
        """Answer a question about the repo, graph-guided or naive (FR-8)."""
        raise self._not_ready("ask", "Phase 5")

    def fix(self, finding_id: str):
        """Run the test-guarded improvement loop on one finding (FR-7)."""
        raise self._not_ready("fix", "Phase 8")

    def run_experiment(self):
        """Token-savings A/B experiment over the question set (FR-8)."""
        raise self._not_ready("run_experiment", "Phase 7")

    def report(self):
        """Aggregate findings, diffs, and ledger into the final report (FR-9)."""
        raise self._not_ready("report", "Phase 9")

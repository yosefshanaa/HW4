"""Hw4Sdk — the single entry point to all business logic (NFR-1, PLAN §1.2).

The CLI, agents, notebook, and tests all consume this facade; nothing
else imports services directly. Shared infrastructure (config, ledger,
gatekeeper, llm client) is wired here exactly once, lazily, so every
consumer shares one budget firewall and one audit trail per run.

Constructor injection everywhere: pass a prebuilt Config or transport
to substitute fakes in tests. Every lifecycle method is wired; the
implementations live in operations/fix_ops/experiment_ops (§3.2 split).
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from hw4.sdk import experiment_ops, fix_ops, operations
from hw4.sdk.errors import ServiceNotReadyError
from hw4.services import graph_metrics
from hw4.services.graph_models import Graph
from hw4.services.graph_runner import BuildRecord, GraphRunner
from hw4.shared.config import Config
from hw4.shared.gatekeeper import ApiGatekeeper
from hw4.shared.ledger import Ledger
from hw4.shared.llm_client import LlmClient, make_anthropic_transport

__all__ = ["Hw4Sdk", "ServiceNotReadyError"]


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
    def base_dir(self) -> Path:
        return self._base_dir

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

    def build_graph(self, repo_path: Path | str, iteration: int | None = None) -> BuildRecord:
        """Extract one immutable graph iteration + metrics snapshot (FR-2).

        iteration defaults to the next free number, so the loop's
        re-graph step is just another call to this method.
        """
        runner = GraphRunner(self._config, results_dir=self.results_dir)
        if iteration is None:
            latest = runner.latest_iteration()
            iteration = 0 if latest is None else latest + 1
        record = runner.build(repo_path, iteration)
        metrics = graph_metrics.compute(Graph.load(record.graph_path), self._config)
        metrics.dump(record.graph_path.parent / "metrics.json")
        return record

    def build_vault(self, graph_path: Path | str | None = None):
        """Generate the Obsidian vault from a graph (FR-3)."""
        return operations.build_vault(self, graph_path)

    def analyze(self, graph_path: Path | str | None = None):
        """Run all detectors, return ranked findings (FR-6)."""
        return operations.analyze(self, graph_path)

    def analyze_with_agents(self, repo_path: Path | str | None = None):
        """Crew-driven analyze flow: deterministic spine + LLM narratives (FR-5).

        Same findings.json as analyze() by construction; the agents add
        careful-language interpretation, never facts. Import is local —
        the crewai dependency tree should not tax non-agent commands.
        """
        from hw4.services.agents.crew import analyze_flow
        from hw4.services.agents.payloads import AnalysisRequest

        if repo_path is None:
            repo_path = self._base_dir / self._config.path("workspace") / str(
                self._config.get("repo.default_dirname")
            )
        return analyze_flow(self, AnalysisRequest(repo_path=str(repo_path)))

    def ask(self, question: str, *, mode: str = "graph"):
        """Answer a question about the repo, graph-guided or naive (FR-8)."""
        return operations.ask(self, question, mode=mode)

    def fix(self, finding_id: str = "", *, auto: bool = False):
        """Run the test-guarded improvement loop (FR-7)."""
        return fix_ops.fix(self, finding_id, auto=auto)

    def run_experiment(self, condition: str = "both"):
        """Token-savings A/B experiment over the question set (FR-8)."""
        return experiment_ops.run_experiment(self, condition)

    def report(self, *, dashboard: bool = False):
        """Aggregate findings, diffs, and ledger into the final report (FR-9)."""
        path = experiment_ops.report(self)
        if dashboard:
            from hw4.services.dashboard import generate

            generate(self)
        return path

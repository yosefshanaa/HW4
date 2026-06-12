"""Graph build orchestration — versioned iteration artifacts (FR-2.6, T140).

Each fix-loop iteration gets its own immutable directory under
results/graphs/: the before/after chain of graph.json files *is* the
evidence that refactoring improved the structure (ADR-6), so an
existing iteration is never overwritten — rebuilding the same number is
an error, not a silent replace. A manifest records backend id, scope,
duration, and a content hash so reruns are provably deterministic (T166).
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from hw4.services.extractor import extract
from hw4.shared.config import Config
from hw4.shared.logging_setup import get_logger, log_event


class IterationExistsError(RuntimeError):
    """This iteration was already built — artifacts are immutable."""


class EmptyGraphError(RuntimeError):
    """Extraction produced zero nodes — scan scope is misconfigured."""


@dataclass(frozen=True)
class BuildRecord:
    """Receipt for one graph build."""

    iteration: int
    graph_path: Path
    manifest_path: Path
    content_hash: str
    duration_seconds: float
    nodes: int
    edges: int


class GraphRunner:
    """Build and locate per-iteration graph artifacts."""

    def __init__(self, config: Config, results_dir: Path | str | None = None):
        self._config = config
        base = Path(results_dir) if results_dir else Path(config.path("results"))
        self._graphs_dir = base / "graphs"

    def iteration_dir(self, iteration: int) -> Path:
        return self._graphs_dir / f"i{iteration:02d}"

    def graph_path(self, iteration: int) -> Path:
        return self.iteration_dir(iteration) / "graph.json"

    def latest_iteration(self) -> int | None:
        if not self._graphs_dir.is_dir():
            return None
        built = sorted(
            int(p.name[1:]) for p in self._graphs_dir.iterdir()
            if p.name.startswith("i") and (p / "graph.json").exists()
        )
        return built[-1] if built else None

    def build(self, repo_path: Path | str, iteration: int) -> BuildRecord:
        """Extract one immutable graph iteration + manifest."""
        graph_file = self.graph_path(iteration)
        if graph_file.exists():
            raise IterationExistsError(f"iteration {iteration} already built: {graph_file}")
        started = time.monotonic()
        graph = extract(repo_path, self._config, iteration=iteration)
        if not graph.nodes:
            raise EmptyGraphError(f"no nodes extracted from {repo_path} — check graph.* config")
        duration = time.monotonic() - started
        graph.dump(graph_file)
        content_hash = hashlib.sha256(graph_file.read_bytes()).hexdigest()
        manifest_path = self._write_manifest(
            graph_file, repo_path, iteration, graph, content_hash, duration
        )
        record = BuildRecord(
            iteration=iteration,
            graph_path=graph_file,
            manifest_path=manifest_path,
            content_hash=content_hash,
            duration_seconds=round(duration, 3),
            nodes=len(graph.nodes),
            edges=len(graph.edges),
        )
        log_event(get_logger("graph_runner"), "graph built",
                  iteration=iteration, nodes=record.nodes, edges=record.edges,
                  duration=record.duration_seconds, hash=content_hash[:12])
        return record

    def _write_manifest(self, graph_file, repo_path, iteration, graph, content_hash, duration):
        manifest = {
            "version": graph.version,
            "backend": graph.backend,
            "iteration": iteration,
            "repo_path": str(repo_path),
            "scan_scope": {
                "exclude_dirs": self._config.get("graph.exclude_dirs"),
                "code_exclude_dirs": self._config.get("graph.code_exclude_dirs", default=[]),
                "doc_suffixes": self._config.get("graph.doc_suffixes"),
            },
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "duration_seconds": round(duration, 3),
            "content_hash": content_hash,
            "nodes": len(graph.nodes),
            "edges": len(graph.edges),
        }
        path = graph_file.parent / "manifest.json"
        path.write_text(json.dumps(manifest, indent=1, sort_keys=True), encoding="utf-8")
        return path

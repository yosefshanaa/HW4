"""Graph-guided debugging case (EX04 §5.3-5.4) — the deterministic spine.

Reproduce the planted bug (run the spec against the buggy version), use the
graph to LOCALIZE it (the failing test's `tested_by` edge points at the
implicated module — no full-tree read), then verify the fix turns the spec
green. Token accounting compares naive whole-package reading against the
graph-guided single-module focus. No LLM here: the CrewAI analyst narrates
the root cause on top of this spine (the project's deterministic-spine rule).
"""

from __future__ import annotations

import importlib.util
from dataclasses import dataclass
from pathlib import Path

from hw4.services.extractor import extract
from hw4.shared.config import Config

# Canonical reproduction: bytes 0-499 of a 1000-byte resource is 500 bytes
# (HTTP ranges are inclusive). The buggy version returns 499.
SPEC_HEADER = "bytes=0-499"
SPEC_LENGTH = 1000
SPEC_EXPECTED = 500


@dataclass(frozen=True)
class DebugResult:
    """Outcome of one graph-guided debug run."""

    case: str
    expected: int
    buggy_value: int
    fixed_value: int
    reproduced: bool
    fixed: bool
    located_module: str
    naive_tokens: int
    graph_tokens: int

    @property
    def savings(self) -> float:
        return 1 - self.graph_tokens / self.naive_tokens if self.naive_tokens else 0.0


def _content_length(module_path: Path) -> int:
    spec = importlib.util.spec_from_file_location(module_path.stem, module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.parse_byte_range(SPEC_HEADER, SPEC_LENGTH)[2]


def _locate(graph) -> str:
    """Implicated module = source of the failing test's tested_by edge."""
    tests = {n for n in graph.nodes if n.startswith("tests.")}
    for edge in graph.edges:
        if edge.relation == "tested_by" and edge.dst in tests:
            return edge.src
    return ""


def run_debug_case(root: Path | str, config: Config) -> DebugResult:
    pkg = Path(root) / "httprange"
    buggy = _content_length(pkg / "parser_buggy.py")
    fixed = _content_length(pkg / "parser.py")
    graph = extract(root, config)
    naive = sum(len(p.read_text(encoding="utf-8")) for p in sorted(pkg.glob("*.py"))) // 4
    graph_tokens = len((pkg / "parser.py").read_text(encoding="utf-8")) // 4
    return DebugResult(
        case=f"{SPEC_HEADER} of {SPEC_LENGTH}",
        expected=SPEC_EXPECTED,
        buggy_value=buggy,
        fixed_value=fixed,
        reproduced=buggy != SPEC_EXPECTED,
        fixed=fixed == SPEC_EXPECTED,
        located_module=_locate(graph),
        naive_tokens=naive,
        graph_tokens=graph_tokens,
    )

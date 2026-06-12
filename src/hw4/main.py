"""hw4 CLI — a thin shell over Hw4Sdk (NFR-1: zero business logic here).

Every subcommand maps 1:1 to one SDK method; this module only parses
arguments, builds the facade, dispatches, and converts errors to exit
codes. Anything smarter than that belongs behind the SDK.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from hw4.sdk.sdk import Hw4Sdk, ServiceNotReadyError
from hw4.shared.version import __version__

EXIT_OK = 0
EXIT_NOT_READY = 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hw4", description="Graph-guided repo comprehension and repair (EX04)."
    )
    parser.add_argument("--version", action="version", version=f"hw4 {__version__}")
    parser.add_argument("--config-dir", default="config", help="directory with the JSON configs")
    sub = parser.add_subparsers(dest="command", required=True)

    graph = sub.add_parser("graph", help="build the knowledge graph from a repo (FR-2)")
    graph.add_argument("repo_path", help="path to the target repository")
    graph.add_argument("--iteration", type=int, default=None,
                       help="iteration number (default: next free)")

    vault = sub.add_parser("vault", help="generate the Obsidian vault from a graph (FR-3)")
    vault.add_argument("graph_path", nargs="?", default=None,
                       help="path to graph.json (default: latest iteration)")

    analyze = sub.add_parser("analyze", help="run detectors, rank findings (FR-6)")
    analyze.add_argument("graph_path", nargs="?", default=None,
                         help="path to graph.json (default: latest iteration)")
    analyze.add_argument("--agents", action="store_true",
                         help="crew-driven flow (adds LLM narratives; same findings)")

    ask = sub.add_parser("ask", help="answer a question about the repo (FR-8)")
    ask.add_argument("question")
    ask.add_argument("--mode", choices=("graph", "naive"), default="graph")

    fix = sub.add_parser("fix", help="run the test-guarded fix loop on a finding (FR-7)")
    fix.add_argument("finding_id", nargs="?", default="")
    fix.add_argument("--auto", action="store_true",
                     help="loop over all validated findings in rank order")

    experiment = sub.add_parser("experiment", help="token-savings A/B experiment (FR-8)")
    experiment.add_argument("--condition", choices=("A", "B", "both"), default="both")
    sub.add_parser("report", help="aggregate the final report (FR-9)")
    return parser


def dispatch(sdk: Hw4Sdk, args: argparse.Namespace) -> object:
    """Route one parsed command to its SDK method — nothing else."""
    handlers = {
        "graph": lambda: sdk.build_graph(args.repo_path, iteration=args.iteration),
        "vault": lambda: sdk.build_vault(args.graph_path),
        "analyze": lambda: (
            sdk.analyze_with_agents() if args.agents else sdk.analyze(args.graph_path)
        ),
        "ask": lambda: sdk.ask(args.question, mode=args.mode),
        "fix": lambda: sdk.fix(args.finding_id, auto=args.auto),
        "experiment": lambda: sdk.run_experiment(condition=args.condition),
        "report": sdk.report,
    }
    return handlers[args.command]()


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    sdk = Hw4Sdk(config_dir=args.config_dir)
    try:
        result = dispatch(sdk, args)
    except ServiceNotReadyError as exc:
        print(f"hw4: {exc}", file=sys.stderr)
        return EXIT_NOT_READY
    if result is not None:
        print(result)
    return EXIT_OK


if __name__ == "__main__":  # pragma: no cover - module execution path
    sys.exit(main())

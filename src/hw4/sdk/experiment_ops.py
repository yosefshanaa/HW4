"""Experiment + report wiring behind the facade (§3.2 split).

run_experiment drives both conditions over the frozen dataset through
the gated runner; report aggregates every committed artifact (findings,
loop log, comparison, ledger) into one human-readable summary.
"""

from __future__ import annotations

import json
from pathlib import Path

from hw4.sdk.fix_ops import target_repo_path
from hw4.sdk.operations import latest_graph
from hw4.services.experiment.compare import compare, to_markdown
from hw4.services.experiment.conditions import graph_prompt_builder, naive_prompt_builder
from hw4.services.experiment.questions import load_questions
from hw4.services.experiment.runner import ExperimentRunner
from hw4.services.retrieval import Retriever
from hw4.services.vault_builder import VaultBuilder


def run_experiment(sdk, condition: str = "both") -> dict:
    """Run condition A, B, or both; compare when both exist (FR-8)."""
    questions = load_questions(sdk.base_dir / sdk.config.path("data") / "questions.yaml")
    runner = ExperimentRunner(sdk.config, sdk.llm, sdk.results_dir)
    result: dict = {}
    if condition in ("A", "both"):
        builder = naive_prompt_builder(target_repo_path(sdk), sdk.config)
        result["A"] = str(runner.run("A", questions, builder))
    if condition in ("B", "both"):
        vault = VaultBuilder(sdk.config, base_dir=sdk.base_dir)
        builder = graph_prompt_builder(Retriever(sdk.config, vault), latest_graph(sdk))
        result["B"] = str(runner.run("B", questions, builder))
    a_path, b_path = runner.output_path("A"), runner.output_path("B")
    if a_path.exists() and b_path.exists():
        comparison = compare(a_path, b_path, sdk.results_dir / "experiment" / "comparison.json")
        result["comparison"] = comparison["totals"]
    return result


def report(sdk) -> Path:
    """Aggregate all artifacts into results/REPORT.md (FR-9)."""
    sections = ["# HW4 run report\n"]
    findings_path = sdk.results_dir / "findings.json"
    if findings_path.exists():
        doc = json.loads(findings_path.read_text(encoding="utf-8"))
        kinds: dict[str, int] = {}
        for finding in doc["findings"]:
            kinds[finding["kind"]] = kinds.get(finding["kind"], 0) + 1
        counts = ", ".join(f"{kind}: {n}" for kind, n in sorted(kinds.items()))
        sections.append(
            f"## Findings\n{len(doc['findings'])} hypotheses ({counts}); "
            "validation trail in results/FINDINGS.md.\n"
        )
    loop_path = sdk.results_dir / "loop_log.json"
    if loop_path.exists():
        log = json.loads(loop_path.read_text(encoding="utf-8"))
        sections.append(
            f"## Fix loop\n{len(log['iterations'])} iteration(s); "
            f"stop reason: **{log['stop_reason']}**.\n"
        )
    comparison_path = sdk.results_dir / "experiment" / "comparison.json"
    if comparison_path.exists():
        comparison = json.loads(comparison_path.read_text(encoding="utf-8"))
        sections.append(
            "## Token experiment\n"
            f"Overall input-token savings: "
            f"**{comparison['totals']['overall_savings']:.1%}** "
            f"(target ≥70%).\n\n{to_markdown(comparison)}\n"
        )
    totals = sdk.ledger.totals()
    sections.append(
        "## Cost\n"
        f"{totals['calls']} gated calls; {totals['input_tokens']} in / "
        f"{totals['output_tokens']} out tokens; **${totals['cost_usd']:.4f}** total.\n"
    )
    out = sdk.results_dir / "REPORT.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(sections), encoding="utf-8")
    return out

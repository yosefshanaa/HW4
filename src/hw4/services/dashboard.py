"""Refactor Truth Dashboard (ADR-6, T403-T407).

Answers ONE question per iteration: did the structure improve, or did
the picture merely change? Consumes loop_log.json and ledger totals
only — no new analysis happens here, so the dashboard can never
disagree with the artifacts it summarizes. The moved-not-improved guard
(T406) surfaces iterations whose 'improvement' left the top bottleneck
score essentially intact while the graph hash changed — exactly the
rename blind spot documented in graph_diff (T156).
"""

from __future__ import annotations

import json
from pathlib import Path

MOVED_NOT_IMPROVED_RATIO = 0.9  # after >= 90% of before => barely moved


def render(loop_log: dict, tokens_by_finding: dict[str, dict] | None = None) -> str:
    lines = ["# Refactor Truth Dashboard", ""]
    iterations = loop_log.get("iterations", [])
    stop = loop_log.get("stop_reason") or "n/a"
    lines.append(f"**Run verdict:** stop reason `{stop}` · {len(iterations)} iteration(s)")
    if loop_log.get("note"):
        lines.append(f"**Note:** {loop_log['note']}")
    lines.append("")
    if not iterations:
        lines.append("_No iterations executed — nothing to show, honestly._")
        return "\n".join(lines)
    for entry in iterations:
        lines.extend(_card(entry, (tokens_by_finding or {}).get(entry["finding_id"])))
    lines.append(
        "---\n*Known limitation (T156): a renamed bottleneck appears as "
        "remove+add; suspected renames are flagged by graph_diff, and "
        "barely-moved scores are highlighted above rather than hidden.*"
    )
    return "\n".join(lines)


def _card(entry: dict, tokens: dict | None) -> list[str]:
    deltas = entry["metric_deltas"]
    before, after = deltas["bottleneck_before"], deltas["bottleneck_after"]
    status = "ACCEPTED" if entry["accepted"] else "REVERTED"
    lines = [
        f"## Iteration {entry['iteration']} — {entry['finding_id']} · {status}",
        "",
        f"- strategy: {entry['strategy']}",
        f"- tests: {'green' if entry['tests_green'] else 'RED'} · "
        f"verdict: **{entry['verdict']}**",
        f"- top bottleneck score: {before} → {after}"
        + (f" (Δ {round(before - after, 4)})" if before or after else ""),
        f"- isolated components: {deltas['isolated_before']} → {deltas['isolated_after']}",
        f"- graph: `{entry['graph_hash_before'][:12]}` → `{entry['graph_hash_after'][:12]}`",
    ]
    if entry.get("characterization_test"):
        lines.append(f"- characterization tests: `{entry['characterization_test']}`")
    if tokens:
        lines.append(
            f"- tokens: {tokens.get('input_tokens', 0)} in / "
            f"{tokens.get('output_tokens', 0)} out (${tokens.get('cost_usd', 0):.4f})"
        )
    if (
        entry["accepted"]
        and entry["verdict"] == "improved"
        and before > 0
        and after >= before * MOVED_NOT_IMPROVED_RATIO
    ):
        lines.append(
            "- ⚠️ **moved-not-improved?** top score barely changed while the "
            "graph did — verify the bottleneck didn't just get renamed (T406)"
        )
    lines.append("")
    return lines


def generate(sdk) -> Path:
    """Render results/dashboard.md from the committed artifacts."""
    log_path = sdk.results_dir / "loop_log.json"
    loop_log = (
        json.loads(log_path.read_text(encoding="utf-8")) if log_path.exists()
        else {"iterations": [], "stop_reason": None, "note": "no loop run yet"}
    )
    tokens_by_finding = {}
    for entry in loop_log.get("iterations", []):
        fid = entry["finding_id"]
        totals = sdk.ledger.totals(purpose_prefix=f"fixloop.edit.{fid}")
        char = sdk.ledger.totals(purpose_prefix=f"fixloop.chartest.{fid}")
        tokens_by_finding[fid] = {
            key: totals[key] + char[key]
            for key in ("calls", "input_tokens", "output_tokens", "cost_usd")
        }
    out = sdk.results_dir / "dashboard.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(loop_log, tokens_by_finding), encoding="utf-8")
    return out

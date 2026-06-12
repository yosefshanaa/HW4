"""A/B comparison — the headline numbers, hand-verifiable (T359-T362).

Savings definition (one formula, used everywhere):
    savings = 1 - tokens_B / tokens_A          (input tokens, per question
    summed over repetitions; API-metadata numbers from the runner cells).
Quality columns ride along when scores exist; a savings number without
its quality column is never reported alone (PRD_token_experiment §1).
"""

from __future__ import annotations

import json
from pathlib import Path
from statistics import mean, median

from hw4.shared.version import __version__


def load_cells(path: Path | str) -> list[dict]:
    return json.loads(Path(path).read_text(encoding="utf-8"))["cells"]


def compare(a_path: Path | str, b_path: Path | str, out_path: Path | str) -> dict:
    a_cells, b_cells = load_cells(a_path), load_cells(b_path)
    a_by_q, b_by_q = _sum_by_question(a_cells), _sum_by_question(b_cells)
    if set(a_by_q) != set(b_by_q):
        raise ValueError("conditions cover different question sets — runs incomplete")
    per_question = []
    for qid in sorted(a_by_q):
        a, b = a_by_q[qid], b_by_q[qid]
        per_question.append({
            "question_id": qid,
            "tier": a["tier"],
            "input_tokens_A": a["input"],
            "input_tokens_B": b["input"],
            "output_tokens_A": a["output"],
            "output_tokens_B": b["output"],
            "savings": _savings(a["input"], b["input"]),
            "truncated_A": a["truncated"],
            "truncated_B": b["truncated"],
        })
    savings_values = [row["savings"] for row in per_question]
    total_a = sum(row["input_tokens_A"] for row in per_question)
    total_b = sum(row["input_tokens_B"] for row in per_question)
    comparison = {
        "version": __version__,
        "per_question": per_question,
        "totals": {
            "input_tokens_A": total_a,
            "input_tokens_B": total_b,
            "overall_savings": _savings(total_a, total_b),
            "mean_savings": round(mean(savings_values), 4),
            "median_savings": round(median(savings_values), 4),
        },
        "by_tier": _by_tier(per_question),
        "below_target": [
            row["question_id"] for row in per_question if row["savings"] < 0.70
        ],
    }
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(comparison, indent=1, sort_keys=True), encoding="utf-8")
    return comparison


def to_markdown(comparison: dict) -> str:
    lines = [
        "| Q | tier | in-tokens A | in-tokens B | savings | trunc A |",
        "|---|---|---|---|---|---|",
    ]
    for row in comparison["per_question"]:
        lines.append(
            f"| {row['question_id']} | {row['tier']} | {row['input_tokens_A']} "
            f"| {row['input_tokens_B']} | {row['savings']:.1%} "
            f"| {'yes' if row['truncated_A'] else ''} |"
        )
    totals = comparison["totals"]
    lines.append(
        f"| **total** | | **{totals['input_tokens_A']}** | **{totals['input_tokens_B']}** "
        f"| **{totals['overall_savings']:.1%}** | |"
    )
    return "\n".join(lines)


def _sum_by_question(cells: list[dict]) -> dict[str, dict]:
    grouped: dict[str, dict] = {}
    for cell in cells:
        entry = grouped.setdefault(cell["question_id"], {
            "tier": cell.get("tier", ""), "input": 0, "output": 0, "truncated": False,
        })
        entry["input"] += int(cell["input_tokens"])
        entry["output"] += int(cell["output_tokens"])
        entry["truncated"] = entry["truncated"] or bool(cell.get("truncated"))
    return grouped


def _savings(tokens_a: int, tokens_b: int) -> float:
    if tokens_a <= 0:
        return 0.0
    return round(1 - tokens_b / tokens_a, 4)


def _by_tier(per_question: list[dict]) -> dict[str, float]:
    tiers: dict[str, list[float]] = {}
    for row in per_question:
        tiers.setdefault(row["tier"], []).append(row["savings"])
    return {tier: round(mean(values), 4) for tier, values in sorted(tiers.items())}

"""loop_log.json entry builders (§3.2 split from loop.py).

One schema, two shapes: a measured iteration and an unappliable one.
Kept apart from the loop so the control flow reads as control flow.
"""

from __future__ import annotations

from datetime import datetime, timezone


def iteration_entry(iteration, finding, fix_plan, apply_result, tests_green,
                    base_hash, new_hash, delta, outcome, test_output) -> dict:
    return {
        "iteration": iteration,
        "finding_id": finding.id,
        "strategy": fix_plan.strategy,
        "files_changed": list(apply_result.files_changed),
        "characterization_test": apply_result.characterization_test,
        "tests_green": tests_green,
        "graph_hash_before": base_hash,
        "graph_hash_after": new_hash,
        "metric_deltas": {
            "bottleneck_before": delta.top_bottleneck_before,
            "bottleneck_after": delta.top_bottleneck_after,
            "isolated_before": delta.isolated_before,
            "isolated_after": delta.isolated_after,
        },
        "verdict": outcome[0],
        "accepted": outcome[1],
        "stop_reason": outcome[2],
        "test_output_tail": "" if tests_green else test_output[-1200:],
        "recorded_utc": datetime.now(timezone.utc).isoformat(),
    }


def blocked_entry(iteration: int, finding, fix_plan, error: str) -> dict:
    return {
        "iteration": iteration,
        "finding_id": finding.id,
        "strategy": fix_plan.strategy,
        "files_changed": [],
        "characterization_test": "",
        "tests_green": False,
        "graph_hash_before": "",
        "graph_hash_after": "",
        "metric_deltas": {"bottleneck_before": 0, "bottleneck_after": 0,
                          "isolated_before": 0, "isolated_after": 0},
        "verdict": "unappliable",
        "accepted": False,
        "stop_reason": None,
        "error": error,
        "recorded_utc": datetime.now(timezone.utc).isoformat(),
    }

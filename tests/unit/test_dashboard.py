"""Tests for the Refactor Truth Dashboard — fixture logs, honest empties."""

from hw4.services.dashboard import render


def entry(**overrides):
    base = {
        "iteration": 1, "finding_id": "F-005", "strategy": "extract helpers",
        "files_changed": ["src/werkzeug/http.py"], "characterization_test": "",
        "tests_green": True, "graph_hash_before": "a" * 64,
        "graph_hash_after": "b" * 64,
        "metric_deltas": {"bottleneck_before": 1.0, "bottleneck_after": 0.5,
                          "isolated_before": 0, "isolated_after": 0},
        "verdict": "improved", "accepted": True, "stop_reason": "GOAL_METRIC_REACHED",
    }
    base.update(overrides)
    return base


class TestRender:
    def test_accepted_iteration_card(self):
        text = render({"iterations": [entry()], "stop_reason": "GOAL_METRIC_REACHED"})
        assert "Iteration 1 — F-005 · ACCEPTED" in text
        assert "1.0 → 0.5" in text
        assert "`aaaaaaaaaaaa` → `bbbbbbbbbbbb`" in text

    def test_reverted_iteration_card(self):
        text = render({"iterations": [entry(accepted=False, tests_green=False,
                                            verdict="regressed")],
                       "stop_reason": "NO_SAFE_ACTION"})
        assert "REVERTED" in text and "RED" in text

    def test_zero_iterations_is_honest(self):
        text = render({"iterations": [], "stop_reason": "NO_SAFE_ACTION",
                       "note": "no plannable findings"})
        assert "nothing to show, honestly" in text
        assert "no plannable findings" in text

    def test_moved_not_improved_guard_fires(self):
        """T406: improved verdict but the score barely moved -> warn."""
        suspicious = entry(metric_deltas={"bottleneck_before": 1.0,
                                          "bottleneck_after": 0.95,
                                          "isolated_before": 1, "isolated_after": 0})
        text = render({"iterations": [suspicious], "stop_reason": "GOAL_METRIC_REACHED"})
        assert "moved-not-improved?" in text

    def test_guard_silent_on_real_improvement(self):
        text = render({"iterations": [entry()], "stop_reason": "GOAL_METRIC_REACHED"})
        assert "moved-not-improved?" not in text

    def test_tokens_rendered_when_provided(self):
        text = render({"iterations": [entry()], "stop_reason": "GOAL_METRIC_REACHED"},
                      {"F-005": {"calls": 2, "input_tokens": 1000,
                                 "output_tokens": 200, "cost_usd": 0.012}})
        assert "1000 in / 200 out ($0.0120)" in text

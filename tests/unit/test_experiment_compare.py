"""Tests for experiment.compare — hand-computed fixtures, no surprises."""

import json

import pytest

from hw4.services.experiment.compare import compare, to_markdown


def write_condition(tmp_path, condition, cells):
    path = tmp_path / f"condition_{condition}.json"
    path.write_text(json.dumps({"version": "1.00", "condition": condition, "cells": cells}))
    return path


def cell(qid, tier, tokens_in, tokens_out=50, truncated=False):
    return {"question_id": qid, "tier": tier, "input_tokens": tokens_in,
            "output_tokens": tokens_out, "truncated": truncated}


def fixture_paths(tmp_path):
    # hand-computed: Q-01 A=10000 B=2000 -> 80%; Q-02 A=8000 B=4000 -> 50%
    a = write_condition(tmp_path, "A", [
        cell("Q-01", "locate", 6000, truncated=True), cell("Q-01", "locate", 4000),
        cell("Q-02", "path", 5000), cell("Q-02", "path", 3000),
    ])
    b = write_condition(tmp_path, "B", [
        cell("Q-01", "locate", 1500), cell("Q-01", "locate", 500),
        cell("Q-02", "path", 2500), cell("Q-02", "path", 1500),
    ])
    return a, b


class TestCompare:
    def test_per_question_savings_hand_verified(self, tmp_path):
        a, b = fixture_paths(tmp_path)
        result = compare(a, b, tmp_path / "comparison.json")
        by_q = {row["question_id"]: row for row in result["per_question"]}
        assert by_q["Q-01"]["savings"] == 0.8
        assert by_q["Q-02"]["savings"] == 0.5
        assert by_q["Q-01"]["truncated_A"] is True

    def test_totals_and_target_list(self, tmp_path):
        a, b = fixture_paths(tmp_path)
        result = compare(a, b, tmp_path / "comparison.json")
        totals = result["totals"]
        assert totals["input_tokens_A"] == 18000
        assert totals["input_tokens_B"] == 6000
        assert totals["overall_savings"] == round(1 - 6000 / 18000, 4)
        assert totals["mean_savings"] == 0.65
        assert result["below_target"] == ["Q-02"]  # 50% < 70% -> must be analyzed

    def test_by_tier_breakdown(self, tmp_path):
        a, b = fixture_paths(tmp_path)
        result = compare(a, b, tmp_path / "comparison.json")
        assert result["by_tier"] == {"locate": 0.8, "path": 0.5}

    def test_mismatched_question_sets_rejected(self, tmp_path):
        a = write_condition(tmp_path, "A", [cell("Q-01", "locate", 100)])
        b = write_condition(tmp_path, "B", [cell("Q-99", "locate", 10)])
        with pytest.raises(ValueError, match="different question sets"):
            compare(a, b, tmp_path / "comparison.json")

    def test_artifact_written(self, tmp_path):
        a, b = fixture_paths(tmp_path)
        compare(a, b, tmp_path / "out" / "comparison.json")
        doc = json.loads((tmp_path / "out" / "comparison.json").read_text())
        assert doc["totals"]["overall_savings"] > 0


class TestMarkdown:
    def test_table_renders_rows_and_totals(self, tmp_path):
        a, b = fixture_paths(tmp_path)
        table = to_markdown(compare(a, b, tmp_path / "comparison.json"))
        assert "| Q-01 | locate | 10000 | 2000 | 80.0% | yes |" in table
        assert "**total**" in table

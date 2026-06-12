"""Tests for runner + scoring — pairing, resume, blinding, aggregation."""

import json

import pytest

from hw4.services.experiment.questions import Question
from hw4.services.experiment.runner import ExperimentRunner, preflight_estimate
from hw4.services.experiment.scoring import (
    ScoreRecord,
    aggregate,
    blind_sheet,
    load_scores,
    save_blind_pack,
    save_scores,
)
from hw4.shared.config import Config
from hw4.shared.llm_client import LlmClient

from .test_config import write_config_dir
from .test_gatekeeper import make_gatekeeper
from .test_llm_client import FakeTransport, response

QUESTIONS = [
    Question("Q-01", "locate", "where is x?", "ref", ("a.py",)),
    Question("Q-02", "path", "how does y flow?", "ref", ("b.py",)),
]

SETUP = {
    "version": "1.00",
    "paths": {"results": "results"},
    "models": {"cheap": "model-cheap", "strong": "model-strong"},
    "llm": {"max_output_tokens": 64, "api_key_env": "K"},
    "experiment": {"repetitions": 2, "temperature": 0.0, "model_tier": "strong",
                   "shuffle_seed": 42, "n_questions_min": 1,
                   "naive_context_token_cap": 16000, "assumed_output_tokens": 100},
}


def make_runner(tmp_path, script_len=20):
    cfg = Config(write_config_dir(tmp_path / "cfg", setup=SETUP), environ={})
    gate, ledger, _ = make_gatekeeper(tmp_path, rpm=1000, rph=100000)
    transport = FakeTransport([], fill=response(text="answer [a.py]", tokens=(500, 50)))
    llm = LlmClient(cfg, gate, transport)
    runner = ExperimentRunner(cfg, llm, tmp_path / "results")
    return runner, transport, ledger, cfg


def build_prompt(question):
    return f"PROMPT for {question.id}", {"prompt_token_estimate": 10, "truncated": False}


class TestRunner:
    def test_all_cells_run_with_ledger_tags(self, tmp_path):
        runner, transport, ledger, _ = make_runner(tmp_path)
        path = runner.run("A", QUESTIONS, build_prompt)
        doc = json.loads(path.read_text())
        assert len(doc["cells"]) == 4  # 2 questions x 2 reps
        tags = sorted(e.purpose_tag for e in ledger.entries())
        assert tags == ["experiment.A.Q-01", "experiment.A.Q-01",
                        "experiment.A.Q-02", "experiment.A.Q-02"]
        assert all(call["model"] == "model-strong" for call in transport.calls)

    def test_tokens_recorded_from_api_metadata(self, tmp_path):
        runner, _, _, _ = make_runner(tmp_path)
        doc = json.loads(runner.run("A", QUESTIONS, build_prompt).read_text())
        assert all(cell["input_tokens"] == 500 for cell in doc["cells"])

    def test_shuffle_is_deterministic(self, tmp_path):
        runner1, t1, _, _ = make_runner(tmp_path / "x")
        runner2, t2, _, _ = make_runner(tmp_path / "y")
        runner1.run("A", QUESTIONS, build_prompt)
        runner2.run("A", QUESTIONS, build_prompt)
        assert [c["messages"] for c in t1.calls] == [c["messages"] for c in t2.calls]

    def test_resume_skips_measured_cells(self, tmp_path):
        runner, transport, _, _ = make_runner(tmp_path)
        path = runner.run("A", QUESTIONS, build_prompt)
        calls_before = len(transport.calls)
        doc = json.loads(path.read_text())
        doc["cells"] = doc["cells"][:1]  # simulate crash after one cell
        path.write_text(json.dumps(doc))
        runner.run("A", QUESTIONS, build_prompt)
        assert len(transport.calls) == calls_before + 3  # only missing cells rerun

    def test_preflight_estimates_cost(self, tmp_path):
        _, _, _, cfg = make_runner(tmp_path)
        estimate = preflight_estimate(
            QUESTIONS, build_prompt, cfg, {"input": 3.0, "output": 15.0}
        )
        assert estimate["cells"] == 4
        assert estimate["cost_usd_estimate"] > 0


class TestScoring:
    CELLS = [
        {"question_id": "Q-01", "condition": "A", "repetition": 1, "answer": "x"},
        {"question_id": "Q-01", "condition": "B", "repetition": 1, "answer": "y"},
    ]

    def test_blind_sheet_masks_condition(self, tmp_path):
        sheet, key = blind_sheet(self.CELLS, seed=1)
        assert all("condition" not in row for row in sheet)
        assert {key[r["answer_id"]]["condition"] for r in sheet} == {"A", "B"}

    def test_pack_separates_sheet_from_sealed_key(self, tmp_path):
        sheet_path, key_path = save_blind_pack(self.CELLS, 1, tmp_path / "exp")
        assert sheet_path.name == "scoring_sheet.json"
        assert key_path.name == "blinding_key.json"

    def test_invalid_scores_rejected(self):
        with pytest.raises(ValueError):
            ScoreRecord("A-001", "Q-01", correctness=3, citation_correct=0, scorer="s")
        with pytest.raises(ValueError):
            ScoreRecord("A-001", "Q-01", correctness=2, citation_correct=2, scorer="s")

    def test_scores_round_trip_and_aggregate(self, tmp_path):
        _, key = blind_sheet(self.CELLS, seed=1)
        ids = sorted(key)
        records = [
            ScoreRecord(ids[0], "Q-01", 2, 1, "s1"),
            ScoreRecord(ids[1], "Q-01", 1, 0, "s1"),
        ]
        path = save_scores(records, tmp_path / "scores.jsonl")
        loaded = load_scores(path)
        summary = aggregate(loaded, key)
        assert set(summary) == {"A", "B"}
        assert sum(c["n"] for c in summary.values()) == 2

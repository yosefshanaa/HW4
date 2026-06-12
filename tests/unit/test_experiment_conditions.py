"""Tests for hw4.services.experiment.conditions — Condition A assembly."""

from hw4.services.experiment.conditions import (
    EXPERIMENT_INSTRUCTIONS,
    naive_bundle,
)
from hw4.services.experiment.questions import Question
from hw4.shared.config import Config

from .test_config import write_config_dir


def make_repo(tmp_path):
    repo = tmp_path / "repo"
    (repo / "pkg").mkdir(parents=True)
    (repo / "pkg" / "engine.py").write_text(
        "def run_pipeline():\n    'engine pipeline runs here'\n" * 3
    )
    (repo / "pkg" / "helpers.py").write_text("def helper():\n    return 'pipeline'\n")
    (repo / "pkg" / "unrelated.py").write_text("X = 1\n")
    return repo


def make_config(tmp_path, cap=16000):
    setup = {
        "version": "1.00",
        "paths": {"results": "results"},
        "graph": {"exclude_dirs": [".git"], "doc_suffixes": [".md"],
                  "max_mentions_per_doc": 50},
        "experiment": {"naive_context_token_cap": cap, "shuffle_seed": 42,
                       "model_tier": "strong", "repetitions": 2,
                       "temperature": 0.0, "n_questions_min": 1},
    }
    return Config(write_config_dir(tmp_path / "cfg", setup=setup), environ={})


QUESTION = Question(
    id="Q-01", tier="locate", question="where does the engine pipeline run?",
    reference_answer="pkg/engine.py", reference_files=("pkg/engine.py",),
)


class TestNaiveBundle:
    def test_deterministic_assembly(self, tmp_path):
        repo, cfg = make_repo(tmp_path), make_config(tmp_path)
        first = naive_bundle(QUESTION, repo, cfg)
        second = naive_bundle(QUESTION, repo, cfg)
        assert first.text == second.text

    def test_grep_ranking_puts_best_match_first(self, tmp_path):
        repo, cfg = make_repo(tmp_path), make_config(tmp_path)
        bundle = naive_bundle(QUESTION, repo, cfg)
        assert bundle.files[0] == "pkg/engine.py"
        assert "pkg/unrelated.py" not in bundle.files  # zero grep hits

    def test_listing_simulates_default_skill_load(self, tmp_path):
        repo, cfg = make_repo(tmp_path), make_config(tmp_path)
        bundle = naive_bundle(QUESTION, repo, cfg)
        assert "repository file listing" in bundle.text
        assert "- pkg/unrelated.py" in bundle.text  # listed even if not included

    def test_assembly_edge_placement_matches_condition_b(self, tmp_path):
        repo, cfg = make_repo(tmp_path), make_config(tmp_path)
        text = naive_bundle(QUESTION, repo, cfg).assemble()
        assert text.startswith(EXPERIMENT_INSTRUCTIONS)
        assert text.rstrip().endswith(QUESTION.question)

    def test_tiny_cap_truncates_and_flags(self, tmp_path):
        repo = make_repo(tmp_path)
        bundle = naive_bundle(QUESTION, repo, make_config(tmp_path, cap=40))
        assert bundle.truncated
        assert len(bundle.files) < 2
        assert bundle.token_estimate > 0

"""Tests for hw4.services.experiment.questions — frozen-dataset validation."""

from pathlib import Path

import pytest
import yaml

from hw4.services.experiment.questions import (
    DatasetError,
    dataset_hash,
    load_questions,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
REAL_DATASET = REPO_ROOT / "data" / "questions.yaml"
TARGET = REPO_ROOT / "workspace" / "target"


def write_dataset(tmp_path, questions):
    path = tmp_path / "questions.yaml"
    path.write_text(yaml.safe_dump({"version": "1.00", "questions": questions}))
    return path


def question(qid="Q-01", tier="locate", files=("a.py",)):
    return {
        "id": qid, "tier": tier, "question": "where?",
        "reference_answer": "answer", "reference_files": list(files),
    }


def full_tier_set(tmp_path, overrides=None):
    questions = [
        question("Q-01", "locate"),
        question("Q-02", "path"),
        question("Q-03", "impact"),
    ]
    for index, override in (overrides or {}).items():
        questions[index].update(override)
    return write_dataset(tmp_path, questions)


class TestRealDataset:
    def test_real_dataset_is_valid_with_tier_minimums(self):
        questions = load_questions(REAL_DATASET)
        assert len(questions) >= 10
        tiers = [q.tier for q in questions]
        assert tiers.count("locate") >= 3
        assert tiers.count("path") >= 4
        assert tiers.count("impact") >= 3

    @pytest.mark.skipif(not TARGET.is_dir(), reason="target clone not present")
    def test_real_reference_files_exist_in_target(self):
        load_questions(REAL_DATASET, repo_root=TARGET)

    def test_hash_is_stable(self):
        assert dataset_hash(REAL_DATASET) == dataset_hash(REAL_DATASET)


class TestValidation:
    def test_duplicate_id_rejected(self, tmp_path):
        path = full_tier_set(tmp_path, {1: {"id": "Q-01"}})
        with pytest.raises(DatasetError, match="duplicate"):
            load_questions(path)

    def test_unknown_tier_rejected(self, tmp_path):
        path = full_tier_set(tmp_path, {0: {"tier": "vibes"}})
        with pytest.raises(DatasetError, match="vibes"):
            load_questions(path)

    def test_missing_tier_coverage_rejected(self, tmp_path):
        path = write_dataset(tmp_path, [question("Q-01", "locate")])
        with pytest.raises(DatasetError, match="every tier"):
            load_questions(path)

    def test_missing_reference_file_rejected_with_root(self, tmp_path):
        path = full_tier_set(tmp_path)
        (tmp_path / "repo").mkdir()
        with pytest.raises(DatasetError, match="reference file missing"):
            load_questions(path, repo_root=tmp_path / "repo")

    def test_empty_answer_rejected(self, tmp_path):
        path = full_tier_set(tmp_path, {2: {"reference_answer": ""}})
        with pytest.raises(DatasetError, match="mandatory"):
            load_questions(path)

"""Experiment dataset loader + validation (FR-8.1, T267).

The dataset is frozen science: load-time validation rejects anything
that would quietly corrupt the A/B comparison — duplicate ids, unknown
tiers, reference files that don't exist at the pinned SHA. The content
hash recorded at freeze time (PRD_token_experiment) lets anyone verify
no post-hoc key edits happened (T266).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import yaml

from hw4.shared.version import assert_config_compatible

TIERS = ("locate", "path", "impact")


class DatasetError(ValueError):
    """The question dataset violates its schema — refuse to experiment."""


@dataclass(frozen=True)
class Question:
    """One frozen experiment question with its reference key."""

    id: str
    tier: str
    question: str
    reference_answer: str
    reference_files: tuple[str, ...]


def dataset_hash(path: Path | str) -> str:
    """sha256 of the raw bytes — the freeze seal (T266)."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_questions(path: Path | str, repo_root: Path | str | None = None) -> list[Question]:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    assert_config_compatible(str(raw.get("version", "")), source="questions.yaml")
    questions, seen_ids, seen_tiers = [], set(), set()
    for item in raw.get("questions", []):
        question = Question(
            id=str(item["id"]),
            tier=str(item["tier"]),
            question=str(item["question"]).strip(),
            reference_answer=str(item["reference_answer"]).strip(),
            reference_files=tuple(item.get("reference_files", [])),
        )
        if question.id in seen_ids:
            raise DatasetError(f"duplicate question id {question.id}")
        if question.tier not in TIERS:
            raise DatasetError(f"{question.id}: unknown tier {question.tier!r}")
        if not question.reference_answer or not question.reference_files:
            raise DatasetError(f"{question.id}: reference answer/files are mandatory")
        seen_ids.add(question.id)
        seen_tiers.add(question.tier)
        questions.append(question)
    if not questions:
        raise DatasetError("dataset contains no questions")
    if seen_tiers != set(TIERS):
        raise DatasetError(f"every tier must be represented; missing {set(TIERS) - seen_tiers}")
    if repo_root is not None:
        _check_files_exist(questions, Path(repo_root))
    return questions


def _check_files_exist(questions: list[Question], repo_root: Path) -> None:
    for question in questions:
        for name in question.reference_files:
            if not (repo_root / name).is_file():
                raise DatasetError(f"{question.id}: reference file missing: {name}")

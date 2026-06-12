"""Blind scoring records + aggregation (T277, SCORING_RUBRIC.md).

The blinding is mechanical: answers are shuffled (seeded) and given
opaque ids; the answer_id -> (condition, repetition) key is written to a
SEPARATE sealed file the scorer must not open until scores are locked.
"""

from __future__ import annotations

import json
import random
from dataclasses import asdict, dataclass
from pathlib import Path

VALID_CORRECTNESS = (0, 1, 2)


@dataclass(frozen=True)
class ScoreRecord:
    """One scored answer per the rubric (correctness 0-2, citation 0/1)."""

    answer_id: str
    question_id: str
    correctness: int
    citation_correct: int
    scorer: str

    def __post_init__(self):
        if self.correctness not in VALID_CORRECTNESS:
            raise ValueError(f"correctness must be one of {VALID_CORRECTNESS}")
        if self.citation_correct not in (0, 1):
            raise ValueError("citation_correct must be 0 or 1")


def blind_sheet(cells: list[dict], seed: int) -> tuple[list[dict], dict]:
    """(masked sheet for scoring, sealed key mapping answer_id -> cell)."""
    shuffled = list(cells)
    random.Random(seed).shuffle(shuffled)
    sheet, key = [], {}
    for index, cell in enumerate(shuffled, start=1):
        answer_id = f"A-{index:03d}"
        sheet.append({
            "answer_id": answer_id,
            "question_id": cell["question_id"],
            "answer": cell["answer"],
        })
        key[answer_id] = {
            "condition": cell["condition"],
            "repetition": cell["repetition"],
        }
    return sheet, key


def save_blind_pack(cells: list[dict], seed: int, out_dir: Path | str) -> tuple[Path, Path]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    sheet, key = blind_sheet(cells, seed)
    sheet_path = out_dir / "scoring_sheet.json"
    key_path = out_dir / "blinding_key.json"
    sheet_path.write_text(json.dumps(sheet, indent=1), encoding="utf-8")
    key_path.write_text(json.dumps(key, indent=1, sort_keys=True), encoding="utf-8")
    return sheet_path, key_path


def save_scores(records: list[ScoreRecord], path: Path | str) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(asdict(record)) + "\n")
    return path


def load_scores(path: Path | str) -> list[ScoreRecord]:
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    return [ScoreRecord(**json.loads(line)) for line in lines if line.strip()]


def aggregate(records: list[ScoreRecord], key: dict) -> dict:
    """Per-condition quality summary after unblinding."""
    by_condition: dict[str, list[ScoreRecord]] = {}
    for record in records:
        condition = key[record.answer_id]["condition"]
        by_condition.setdefault(condition, []).append(record)
    summary = {}
    for condition, scored in sorted(by_condition.items()):
        summary[condition] = {
            "n": len(scored),
            "mean_correctness": round(sum(r.correctness for r in scored) / len(scored), 3),
            "citation_rate": round(sum(r.citation_correct for r in scored) / len(scored), 3),
        }
    return summary

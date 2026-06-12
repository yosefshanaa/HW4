"""Experiment runner — paired, repeated, crash-resumable (T271-T273).

Controls live here so the science is defensible: temperature and model
tier from config, deterministic shuffle (seeded) so neither condition
benefits from ordering, persistence after EVERY cell so a crash resumes
instead of double-spending, and one purpose tag per cell so the ledger
is the measurement instrument (tokens from API metadata, PLAN §4.4).
There is no cache anywhere in this path (T210).
"""

from __future__ import annotations

import json
import random
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

from hw4.constants import ModelTier
from hw4.services.experiment.questions import Question
from hw4.shared.config import Config
from hw4.shared.llm_client import LlmClient
from hw4.shared.version import __version__

PromptBuilder = Callable[[Question], tuple[str, dict]]


class ExperimentRunner:
    """Run one condition over the frozen dataset."""

    def __init__(self, config: Config, llm: LlmClient, results_dir: Path | str):
        self._reps = int(config.get("experiment.repetitions"))
        self._temperature = float(config.get("experiment.temperature"))
        self._tier = ModelTier(str(config.get("experiment.model_tier")))
        self._seed = int(config.get("experiment.shuffle_seed"))
        self._dir = Path(results_dir) / "experiment"
        self._llm = llm

    def output_path(self, condition: str) -> Path:
        return self._dir / f"condition_{condition}.json"

    def run(self, condition: str, questions: list[Question], build_prompt: PromptBuilder) -> Path:
        path = self.output_path(condition)
        doc = self._load_or_init(path, condition)
        done = {(cell["question_id"], cell["repetition"]) for cell in doc["cells"]}
        for question, repetition in self._schedule(questions):
            if (question.id, repetition) in done:
                continue  # resume: never re-spend a measured cell
            prompt, meta = build_prompt(question)
            response = self._llm.complete(
                [{"role": "user", "content": prompt}],
                purpose_tag=f"experiment.{condition}.{question.id}",
                tier=self._tier,
                temperature=self._temperature,
            )
            doc["cells"].append({
                "question_id": question.id,
                "tier": question.tier,
                "condition": condition,
                "repetition": repetition,
                "answer": response.text,
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
                "model": response.model,
                "recorded_utc": datetime.now(timezone.utc).isoformat(),
                **meta,
            })
            self._persist(path, doc)  # after every cell: crash == resume point
        return path

    def _schedule(self, questions: list[Question]) -> list[tuple[Question, int]]:
        cells = [(q, rep) for q in questions for rep in range(1, self._reps + 1)]
        random.Random(self._seed).shuffle(cells)
        return cells

    def _load_or_init(self, path: Path, condition: str) -> dict:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return {"version": __version__, "condition": condition, "cells": []}

    @staticmethod
    def _persist(path: Path, doc: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(doc, indent=1, sort_keys=True), encoding="utf-8")


def preflight_estimate(
    questions: list[Question],
    build_prompt: PromptBuilder,
    config: Config,
    price_per_mtok: dict,
) -> dict:
    """Cost ceiling BEFORE spending (T274) — estimates, clearly labeled."""
    reps = int(config.get("experiment.repetitions"))
    assumed_out = int(config.get("experiment.assumed_output_tokens"))
    input_estimate = 0
    for question in questions:
        prompt, _meta = build_prompt(question)
        input_estimate += (len(prompt) // 4) * reps
    output_estimate = assumed_out * len(questions) * reps
    cost = (
        input_estimate * float(price_per_mtok["input"])
        + output_estimate * float(price_per_mtok["output"])
    ) / 1_000_000
    return {
        "cells": len(questions) * reps,
        "input_tokens_estimate": input_estimate,
        "output_tokens_estimate": output_estimate,
        "cost_usd_estimate": round(cost, 4),
    }

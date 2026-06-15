"""Detector evaluation op — confusion matrix vs the planted answer key.

Kept out of operations.py so the §3.2 facade split stays clean: the SDK
method delegates here, this module owns the extract->detect->score->write
pipeline. Fully deterministic (no LLM, no network): it re-extracts the
fixture, runs every detector, and scores the findings against the
ground-truth labels the fixture's README documents (L07 §13.2).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from hw4.services import graph_metrics
from hw4.services.detectors import registry
from hw4.services.evaluation import confusion
from hw4.services.extractor import extract

DEFAULT_TARGET = "tests/fixtures/mini_repo"
DEFAULT_ANSWER_KEY = "tests/fixtures/mini_repo_answer_key.json"


@dataclass(frozen=True)
class EvaluationReport:
    """What one evaluation run produced."""

    matrix: confusion.ConfusionMatrix
    json_path: Path
    markdown_path: Path

    def __str__(self) -> str:
        m = self.matrix
        return (
            f"confusion matrix: P={m.precision:.2f} R={m.recall:.2f} F1={m.f1:.2f} "
            f"(TP={m.tp} FP={m.fp} FN={m.fn} TN={m.tn}) -> {self.markdown_path}"
        )


def evaluate(sdk, target_path=None, answer_key_path=None) -> EvaluationReport:
    base = Path(sdk.base_dir)
    target = Path(target_path) if target_path else base / DEFAULT_TARGET
    key_path = Path(answer_key_path) if answer_key_path else base / DEFAULT_ANSWER_KEY
    graph = extract(target, sdk.config)
    metrics = graph_metrics.compute(graph, sdk.config)
    findings = registry.run_all(graph, metrics, sdk.config)
    matrix = confusion.evaluate(findings, confusion.load_answer_key(key_path))
    sdk.results_dir.mkdir(parents=True, exist_ok=True)
    json_path = sdk.results_dir / "confusion_matrix.json"
    payload = {"version": "1.00", "target": target.as_posix(), **matrix.to_dict()}
    json_path.write_text(json.dumps(payload, indent=1), encoding="utf-8")
    md_path = sdk.results_dir / "CONFUSION_MATRIX.md"
    md_path.write_text(_render_markdown(matrix, target.as_posix()), encoding="utf-8")
    return EvaluationReport(matrix=matrix, json_path=json_path, markdown_path=md_path)


def _render_markdown(matrix: confusion.ConfusionMatrix, target: str) -> str:
    m = matrix
    rows = "\n".join(
        f"| `{o.candidate.target}` | {o.candidate.kind.value} | {_label(o.candidate.is_defect)} "
        f"| {'yes' if o.predicted else 'no'} | **{o.cell}** | {o.candidate.rationale} |"
        for o in m.outcomes
    )
    return f"""# Confusion matrix — detector evaluation (L07 §13.2)

Deterministic detectors run over `{target}` and scored against its
planted-defect answer key. A candidate is *predicted positive* when a
finding of the matching kind names the candidate node; *expected* is the
ground-truth label the fixture documents. No LLM or network is involved,
so this artifact is fully reproducible via `hw4 evaluate`.

|                 | Actual defect | Actual clean |
|-----------------|---------------|--------------|
| **Pred defect** | TP = {m.tp}   | FP = {m.fp}  |
| **Pred clean**  | FN = {m.fn}   | TN = {m.tn}  |

| Metric | Value |
|---|---|
| Precision | {m.precision:.3f} |
| Recall | {m.recall:.3f} |
| F1 | {m.f1:.3f} |
| Accuracy | {m.accuracy:.3f} |

## Per-candidate outcomes

| Node | Detector | Expected | Predicted | Cell | Why |
|---|---|---|---|---|---|
{rows}

## Reading

Recall **{m.recall:.2f}** — all {m.tp + m.fn} planted defects were detected.
Precision **{m.precision:.2f}** — {m.fp} benign node(s) flagged (see the
per-candidate rationale; isolation is reported as a triage *finding*, not a
diagnosis, per Part-C). The healthy-hub guards (`app.utils`) stay unflagged,
the {m.tn} true negatives that keep precision from collapsing.
"""


def _label(is_defect: bool) -> str:
    return "defect" if is_defect else "clean"

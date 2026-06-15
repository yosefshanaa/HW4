# PRD — Agent Evaluation (Confusion Matrix)

**Status:** approved 2026-06-15 · **Serves:** L07 §13.2 (agent evaluation) ·
**Implements in:** `services/evaluation/confusion.py`, `sdk/eval_ops.py`, CLI `hw4 evaluate`

## 1. Description & theory

L07 §13.2 asks for an explicit, measurable answer to *"is the agent any
good?"* — not a demo, a **confusion matrix** over labeled ground truth.
Our detectors (`PRD_defect_detection.md`) make binary calls — *is this
node a god node? is this island a real orphan? does this doc claim exist?*
— so they are exactly a classifier, and the right yardstick is
precision/recall/F1 against a known answer key.

The answer key already exists and is honest: `tests/fixtures/mini_repo`
is a synthetic target whose README documents its **planted defects** plus
two deliberate **false-positive guards** (a healthy hub that must *not* be
flagged). We turn that README into a machine-readable
`tests/fixtures/mini_repo_answer_key.json`, run the real deterministic
detector spine over the fixture, and score finding-vs-truth.

Crucially we do **not** hand-tune for a perfect score. The published
result is **P = 0.75, R = 1.00, F1 = 0.86** (TP 3 / FP 1 / FN 0 / TN 2):
every planted defect is caught, and the single false positive is the
fixture's `conftest.py`, which the isolation detector correctly observes
is disconnected. Per Part-C, isolation is reported as a *triage finding,
not a diagnosis* — so that FP is a known, explained precision cost, not a
masked bug. A suspiciously perfect matrix on a fixture you control is
worth less than an honest one that surfaces its own failure mode.

## 2. Interfaces & I/O

```python
@dataclass(frozen=True)
class Candidate:        # one labeled (node, detector-kind) ground-truth fact
    target: str; kind: FindingKind; is_defect: bool; rationale: str

class ConfusionMatrix:  # outcomes -> tp/fp/fn/tn + precision/recall/f1/accuracy + to_dict()
def evaluate(findings, candidates) -> ConfusionMatrix
def load_answer_key(path) -> list[Candidate]
```

A candidate is **predicted positive** when some finding of the matching
`kind` names the candidate node (exact id, child-symbol prefix, or a
`missing:` doc-gap tag). Matching is purely over finding node ids, so the
scorer needs no graph at evaluation time — only the findings and the key.

**CLI:** `hw4 evaluate [target] [--answer-key PATH]` (defaults: the
mini_repo fixture and its key). **Artifacts:** `results/confusion_matrix.json`
(cells, metrics, per-candidate outcomes) and `results/CONFUSION_MATRIX.md`
(2×2 table, metrics, per-candidate breakdown with rationale). Fully
deterministic — no LLM, no network — so the matrix is reproducible.

## 3. Constraints, alternatives, rationale

| Decision | Alternatives | Why chosen |
|---|---|---|
| Score the deterministic detector spine | Score the LLM narrators | The detectors are the falsifiable classifier; the LLM only narrates findings, so a classifier metric belongs on the spine. The token experiment already scores LLM answer quality (`SCORING.md`). |
| Match by node id, no graph at score time | Re-resolve node→source_file via the graph | Keeps the scorer a pure function of (findings, key) — trivially testable, no graph dependency, and the answer key is expressed in the same node-id vocabulary the detectors emit. |
| Answer key as a sibling JSON outside the scanned fixture | Embed in the README / inside `mini_repo/` | A `.json` inside the fixture would not be parsed as code or doc, but keeping it a sibling guarantees it can never perturb extraction, and it stays a single source of truth the README already prose-documents. |
| Count `conftest` isolation as an honest FP | Exclude test scaffolding / relabel as TP | Reporting and explaining the FP demonstrates the precision/recall trade-off and the Part-C "finding, not diagnosis" stance; hiding it would overstate the tool. |

## 4. Acceptance

- `hw4 evaluate` writes both artifacts and prints `P/R/F1` + the cell counts.
- Matrix on mini_repo is exactly TP 3 / FP 1 / FN 0 / TN 2 (R = 1.00, P = 0.75).
- The lone FP is `conftest`; the healthy-hub guards (`app.utils`) are true negatives.
- Unit tests cover the matrix math, node matching, answer-key loading, and the
  end-to-end run (`tests/unit/test_confusion.py`); gates stay green.

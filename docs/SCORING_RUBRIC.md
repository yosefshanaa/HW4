# SCORING_RUBRIC.md — blind answer scoring for the token experiment (T092)

Applies to every answer in both conditions (A naive / B graph-guided).
Quality is reported **next to** token savings — savings that destroy
correctness are a failure (PRD_token_experiment §1).

## Blinding protocol

1. Export answers to a scoring sheet with columns: `answer_id (random)`,
   `question_id`, `answer_text`, `cited_files`. Condition and repetition
   are **masked**; mapping is kept sealed in
   `results/experiment/blinding_key.json` until both scores are locked.
2. Both teammates score independently; disagreements adjudicated together
   against `reference_answer` + source; the adjudicated score is final
   and the disagreement is logged (it measures rubric clarity).

## Correctness score

| Score | Criterion |
|---|---|
| **2 — correct** | Matches the reference answer's substance; no materially wrong claim; for `path` tier the full chain is right; for `impact` tier all major affected areas named. |
| **1 — partial** | Right direction but incomplete (e.g. half the chain, one of two impact areas) or contains a minor wrong detail that doesn't invalidate the core. |
| **0 — wrong** | Core claim incorrect, hallucinated entities, or non-answer ("cannot determine" when the reference shows it's determinable). |

## Citation score (independent of correctness)

| Score | Criterion |
|---|---|
| **1 — correct citations** | Every file the answer relies on is named and appears in `reference_files` (or is verifiably equivalent at the pinned SHA). |
| **0 — missing/wrong** | No file citations, fabricated paths, or citations that don't support the claim. |

## Reporting

Per condition: mean correctness (0–2), citation rate (0–1), per-tier
breakdown, and the per-question table in `comparison.json`. Decision rule
for the KPI: B's token savings count only if `mean_correctness(B) ≥
mean_correctness(A)` and `citation_rate(B) ≥ citation_rate(A)`; otherwise
the report analyzes the quality regression as a primary result.

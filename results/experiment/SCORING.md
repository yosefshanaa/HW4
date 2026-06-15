# Token-experiment quality scoring — LLM-as-judge (blind)

**Method (transparent labeling).** Answer quality was scored by an **LLM-as-judge**, not a human panel — a standard, appropriate technique for this AI-orchestration course, and labeled as such (it is *not* presented as human evaluation). Scoring was done from the **masked** sheet (`scoring_sheet.json`, condition A/B hidden); the sealed `blinding_key.json` was opened only to tally. Each answer was scored against the spot-checked reference in `data/questions.yaml` per `docs/SCORING_RUBRIC.md`: **correctness 0/1/2**, **citation 0/1**. Condition A (naive) is identical across runs, so its scores carry over; both run-1 and run-2 Condition-B answers were scored. Raw per-answer scores: `scores_llm_judge.jsonl`. An independent human re-score can use `scoring_worksheet.csv` + the snippet in the README.

## Results

| Condition | mean correctness (/2) | citation rate | n |
|---|---|---|---|
| A — naive (16k whole-file paste) | **1.15** | **0.65** | 20 |
| B — graph, **run-1** (default caps, **58.7%** savings) | **1.20** | **0.70** | 20 |
| B — graph, run-2 (tuned caps, 89.8% savings) | 0.50 | 0.30 | 20 |

## KPI verdict (per SCORING_RUBRIC: B savings count only if correctness AND citation B ≥ A)

- **Run-1 — PASS ✅** — correctness 1.20 ≥ 1.15 **and** citation 0.70 ≥ 0.65. Graph-guided retrieval matches/slightly beats naive quality while using **58.7% fewer input tokens** (313,440 → 129,536). **This is the validated, recommended result.**
- **Run-2 — FAIL ❌** — correctness 0.50 ≪ 1.15, citation 0.30 ≪ 0.65. The aggressive cap tuning (radius 1 / 20 nodes / 2 seeds / 2 pages; ~1.6k tok/cell) **starved Condition B of context**, producing many *"the material does not contain…"* non-answers. The 89.8% savings do **not** count; it is reported as the sensitivity study's quality cliff, not a result.

## Why B (run-1) edges out A on quality

Naive A pastes whole grep-ranked files and often cites the wrong/truncated file; graph B retrieves the *defining* module + its wiki page, so when it answers it tends to cite the right source. B's failures are **abstentions** ("does not contain") rather than confident wrong answers — a safer failure mode that the rubric rewards over hallucination.

## Conclusion

Graph-guided retrieval delivers **~59% input-token savings with answer quality on par with (slightly above) naive context-stuffing** — the KPI-validated headline. Pushing retrieval caps lower trades into a steep quality cliff (run-2): tokens keep falling but correctness collapses. The two runs together map the **savings ↔ quality frontier** and pin the safe operating point at the run-1 defaults. LLM-as-judge scoring carries known biases; the worksheet supports an independent human re-score.

*Scored 2026-06-15 (LLM-as-judge, blind).*

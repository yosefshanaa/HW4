# PRD — Token-Savings Experiment

**Status:** approved 2026-06-12 · **Serves:** FR-8, KPI "≥70% input-token savings" ·
**Implements in:** `services/experiment/*` (Phases 7 & 10) · **Protocol:** PLAN §4

## 1. Description & theory

The assignment's central claim — *graph-guided context beats naive context
stuffing* — must be measured, not asserted. Two conditions answer the same
questions about the target repo:

- **Condition A (naive):** system prompt + concatenated candidate files
  (mimicking "regular work", L07 §7) + question. Truncation at the model
  context limit is logged — truncation events are themselves a result.
- **Condition B (graph-guided):** system prompt + `index.md` + focused
  subgraph (ego radius ≤2, serialized compactly) + 2–3 wiki pages +
  question (Part-B retrieval discipline; instructions at START, question
  at END).

Primary metric: **% input-token savings** = `1 − tokens_B/tokens_A` over
the question set, with answer quality reported alongside — savings that
destroy correctness are a failure, not a win.

## 2. Interfaces & I/O

- **Dataset** `data/questions.yaml`: ≥`experiment.n_questions_min` (10)
  questions, 3 tiers (locate / trace-path / impact-analysis), each with
  `id, tier, question, reference_answer, reference_files[]`. Answer key
  built manually from the validated graph, spot-checked against raw
  source (bias mitigation).
- `experiment.run(condition) -> results/experiment/<cond>.json`: per
  question×repetition — prompt-assembly stats, API-metadata token counts
  (via Gatekeeper ledger, purpose `experiment.<cond>.<qid>`), answer text,
  latency.
- `experiment.compare() -> results/experiment/comparison.json` + figures:
  per-question table, totals, % savings, $ cost, savings distribution.
- **Scoring:** blind rubric — correct / partial / wrong + citation
  correctness; answers shuffled and condition-masked before scoring.

## 3. Controls & validity

Same model id, temperature 0, same question wording, N=2 repetitions,
randomized order. Tokens come from **API usage metadata recorded by the
Gatekeeper ledger** — never a local tokenizer (estimates drift; any
fallback would be documented as a limitation).

Threats we document explicitly: answer-key bias (key derives from the
graph under test — mitigated by source spot-check), small N, single repo,
model nondeterminism (temp 0 + repetitions), condition-A cap truncation
(also a finding). Alternatives considered: synthetic question generation
by LLM (rejected: circular), more repos (rejected: out of time budget,
noted as future work).

## 4. Success criteria & test scenarios

- Unit: prompt assemblers for A and B produce deterministic prompts on
  fixture data; B respects node/page/token caps; truncation in A is
  flagged and logged; comparison math verified on hand-computed fixtures.
- Integration (FakeTransport with scripted usage): full A/B run over 3
  fixture questions yields a comparison table whose savings match the
  scripted token numbers exactly.
- **KPI (FR-8):** ≥10 questions, both conditions, ≥70% input-token
  savings with answer quality in B ≥ A; if the threshold is missed, the
  report analyzes *why* (this is a result, not a cover-up — honesty over
  vanity metrics).

## As-run parameters (T274, T286 — updated 2026-06-12)

- Condition A selection rule as implemented: grep question terms over
  all non-excluded `.py` files, rank by raw hit count, paste whole
  files; when the next file exceeds the cap, paste its head and mark
  `[TRUNCATED at context cap]` (`experiment.naive_context_token_cap`
  = 16,000). Repo file listing always included.
- **Preflight (offline estimate, strong tier):** 20 cells (10 q × 2
  reps), ≈321.5k input + ≈8k output tokens → **≈$1.08** — comfortably
  inside the $10 budget firewall. Actual-vs-estimate to be recorded
  after the live run.
- Observed: ALL 10 naive bundles truncate (T291 ✅) — grep-ranked
  whole-file pasting blows the 16k cap on every question; the naive
  condition cannot prioritize the relevant file, so it floods context
  indiscriminately (exactly the structural failure mode the graph
  condition avoids by retrieving an ego-subgraph + wiki pages).
- Live A/B execution: completed 2026-06-15 with the OpenAI provider
  (config-switched); measured results below supersede the preflight.

> **Dataset re-frozen 2026-06-15 (T266; werkzeug re-target):**
> `data/questions.yaml` sha256
> `f7dc994e21225522e357d949c140fb402ba48eaca544c67e107e3592e8fa842b` — 10
> questions (3 locate / 4 path / 3 impact) over `pallets/werkzeug` @
> `1b00618e`, every reference spot-checked against source at the pinned
> SHA. No post-hoc edits permitted; amendments require a documented
> procedure note. (Prior click freeze: sha256 `fb0749ad…`, 2026-06-12.)

## Measured results (LIVE, 2026-06-15, gpt-4o-mini both conditions)

- **Run 1 — the validated result (committed default caps: radius 2, 40
  nodes, 3 seeds, 3 pages, 12k cap):** overall input-token savings
  **58.7%** (median 60.2%); Condition B well-formed (~6.5k tok/cell).
  **Blind quality (LLM-as-judge, masked sheet):** correctness B **1.20 ≥**
  A **1.15** and citation B **0.70 ≥** A **0.65** → **rubric KPI PASS** —
  the 58.7% savings *count* (graph quality matches/slightly beats naive).
  Below the ≥70% FR aspiration, but quality-preserving.
- **Run 2 — sensitivity over-tuning (radius 1, 20 nodes, 2 seeds, 2 pages
  via `HW4__retrieval__*`; config + frozen dataset unchanged):** savings
  rose to **89.8%** by cutting Condition B to ~1.6k tok/cell — but that
  **starved B of context**: blind correctness collapsed to **0.50 ≪ 1.15**,
  citation **0.30 ≪ 0.65** → **rubric KPI FAIL**. The 89.8% does NOT
  count; archived as `*_run2.json` and reported as the savings/quality
  **cliff**, not a result.
- **Honest conclusion:** for this target, **≥70% savings and preserved
  quality are not jointly reachable** — graph retrieval gives
  quality-preserving ~59% savings; tightening further trades into a steep
  quality cliff. The two runs map the savings↔quality frontier; the safe
  operating point is the run-1 defaults. Full breakdown:
  `results/experiment/SCORING.md`.
- **Scoring method (transparent):** quality was scored by an **LLM-as-
  judge**, not a human panel — appropriate for an AI-orchestration course
  and labeled as such (not presented as human evaluation). The masked
  `scoring_sheet.json` + sealed `blinding_key.json` give genuine blinding;
  raw scores in `scores_llm_judge.jsonl`; `scoring_worksheet.csv` supports
  an independent human re-score.
- Cost (werkzeug run): ≈ $0.088 over 109 gated calls (vault + fix + 2
  experiment runs + agent narratives); see results/REPORT.md cost
  section. The retired click run's ledger is preserved in git history.

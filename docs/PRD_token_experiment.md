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

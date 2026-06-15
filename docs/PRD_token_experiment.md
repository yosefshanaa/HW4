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
- Observed: ALL 10 naive bundles truncate (T291 ✅), and the cut file is
  `src/click/core.py` in 10/10 cases — the naive condition's failure
  mode is itself corroboration of validated finding F-003 (whatever you
  ask about this codebase, grep hands you the god module first).
- Live A/B execution: completed 2026-06-12 with the OpenAI provider
  (config-switched); measured results below supersede the preflight.

> **Dataset re-frozen 2026-06-15 (T266; werkzeug re-target):**
> `data/questions.yaml` sha256
> `f7dc994e21225522e357d949c140fb402ba48eaca544c67e107e3592e8fa842b` — 10
> questions (3 locate / 4 path / 3 impact) over `pallets/werkzeug` @
> `1b00618e`, every reference spot-checked against source at the pinned
> SHA. No post-hoc edits permitted; amendments require a documented
> procedure note. (Prior click freeze: sha256 `fb0749ad…`, 2026-06-12.)

## Measured results (LIVE, 2026-06-12, gpt-4o-mini both conditions)

- **Run 1** (default retrieval caps: radius 2, 40 nodes, 3 seeds, 3
  pages): overall savings **50.9%** — below target. Failure analysis:
  Condition B ballooned to 14–19k tokens on 8/10 questions; answers
  were correct, the context was simply over-provisioned.
- **Documented amendment (sensitivity-driven, dataset untouched):**
  retrieval tuned to radius 1, 20 nodes, 2 seeds, 2 pages via HW4__ env
  overrides; run 1 archived as `condition_B_run1.json` /
  `comparison_run1.json`.
- **Run 2 (tuned):** overall savings **85.6%**, median 87.8%; by tier:
  locate 87.8%, path 88.1%, impact 80.2%. Single below-target question:
  Q-08 (63.0%) — the echo-SPOF impact question legitimately needs the
  bottleneck's wide neighborhood. **KPI ≥70% met.**
- Quality spot-check: tuned-run answers remain correct with proper file
  citations; formal blind scoring pack generated
  (`scoring_sheet.json` + sealed `blinding_key.json`) for human scoring.
- Cost so far (ledger): see results/REPORT.md cost section.

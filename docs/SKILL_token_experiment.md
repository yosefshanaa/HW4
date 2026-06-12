---
name: token-experiment-runner
description: >
  Run the defensible A/B token experiment: frozen dataset, naive vs
  graph-guided context, ledger-sourced measurement, blind scoring. Use when
  asked to MEASURE context-strategy efficiency, not just assert it.
allowed-tools: [run_experiment, ledger_status, read_artifact]
version: "1.00"
---

# SKILL: token-experiment-runner (T400)

## When to use

- "prove/measure the token savings", "compare retrieval strategies",
  "is the graph context actually cheaper?"

## Procedure

1. Verify the dataset is FROZEN (sha256 in PRD_token_experiment) — if it
   changed, the experiment restarts; no post-hoc key edits ever.
2. Preflight cost (`preflight_estimate`) and check the budget firewall
   headroom before any cell is spent.
3. Run conditions via `run_experiment` (A, then B, or both): temp 0,
   strong tier, seeded shuffle, resume-on-crash; never bypass the
   runner (its purpose tags ARE the measurement).
4. Tokens come ONLY from the Gatekeeper ledger (API metadata). A local
   estimate may guard budgets; it may never be reported as a result.
5. Score blind: `scoring.save_blind_pack` separates the sheet from the
   sealed key; aggregate only after all scores are locked.
6. Report savings NEXT TO quality — savings with wrong answers is a
   failure mode, and below-70% questions get a written failure analysis.

## Guardrails

| Class | Policy |
|---|---|
| Read-only (ledger_status, read_artifact) | auto |
| Spending (run_experiment) | budget firewall enforced by the Gatekeeper; resume instead of re-spend |
| Irreversible (editing the dataset or measured cells) | forbidden — frozen by hash; amendments need a documented procedure note |

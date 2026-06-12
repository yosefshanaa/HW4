---
name: graph-guided-codebase-analysis
description: >
  Reverse-engineer and safely refactor an unfamiliar Python repo through its
  knowledge graph: index-first retrieval, evidence-chained findings,
  test-guarded fixes. Use when asked to understand, audit, or improve a
  codebase you did not write.
allowed-tools: [build_graph, run_detectors, retrieve_context, run_fix_loop,
                ledger_status, read_artifact]
version: "1.00"
---

# SKILL: graph-guided codebase analysis

## When to use (problem → skill)

Trigger phrases and patterns:
- "how does this repo work / where is X implemented / what breaks if…"
- "find architectural problems / technical debt in <repo>"
- "refactor this safely / prove the refactor helped"
- any task on a codebase ≥ ~3k LOC that you have not read end-to-end —
  naive file-pasting burns the context window before insight arrives.

Do NOT use for: single-file scripts (just read them), non-code corpora,
or repos you cannot legally clone and modify.

## Procedure (the protocol — follow in order)

1. **Identify the task tier**: locate / trace-path / impact-analysis.
2. **Load the skill** (this file); confirm the guardrail class of the
   intended action *before* acting.
3. **Read `index.md` first** — it is the only default context. Never
   start from raw files.
4. **Retrieve focused context**: ego-subgraph (radius ≤ 2, capped) +
   2–3 wiki pages via `retrieve_context`. Whole files are allowed only
   for an explicit source-validation step.
5. **Act within evidence discipline**: EXTRACTED supports claims;
   INFERRED must be hedged with confidence; AMBIGUOUS is a stop-flag
   for human check — never an input to automated change.
6. **Return a traceable result**: every claim cites node ids + source
   files; every change cites its finding id, branch, and graph delta.

## Guardrails

| Class | Examples | Policy |
|---|---|---|
| Read-only | build_graph, run_detectors, retrieve_context, ledger_status, read_artifact | auto-approved; results are immutable artifacts |
| Reversible | run_fix_loop edits | allowed ONLY on `fix/<finding-id>` branches with a recorded base SHA; red tests force revert (enforced: `Applier.apply`/`revert`, tested in test_fixloop_applier) |
| Irreversible | deleting code/files, pushing to remotes, publishing reports | **human approval required**; no tool in `allowed-tools` can do these — deletion is not a planner strategy at all (enforced: `planner.HUMAN_ONLY` refusals, tested) |

For sensitive deployments, set this skill to *disable-model-invocation*:
a human loads it explicitly; the model may not self-activate it (Part-B
slide 11 concept).

## Skill refresh & compaction recovery (anti-drift)

- Re-read **Procedure** before any reversible action and after every
  `/compact`-style history compression — compaction keeps the RULES
  block verbatim (`agents/context.py`), but the *procedure* must be
  reloaded from this file, not from memory.
- If you notice yourself pasting whole files without a validation step,
  stop: that is skill drift, re-enter at step 3.

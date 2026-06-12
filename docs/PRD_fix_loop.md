# PRD — Test-Guarded Fix & Improvement Loop

**Status:** approved 2026-06-12 · **Serves:** FR-7, ADR-6 ·
**Implements in:** `services/fixloop/{planner,applier,stop,loop}.py` (Phase 9)

## 1. Description & theory

The loop closes the assignment's circle: *graph reveals defect → fix is
applied → tests guard behavior → re-graph proves structural improvement*.
Improvement must be **provable on both axes** — behavioral (target test
suite stays green) and structural (graph metric delta) — or the iteration
is reverted. A refactor that passes tests but doesn't move the metric is
`neutral` (kept, logged honestly); one that breaks tests is reverted and
the finding marked `blocked`.

Safety doctrine (in priority order): never edit `main` (work on
`fix/<finding-id>` branches); never fix from `INFERRED`/`AMBIGUOUS`
evidence alone; if the target repo lacks tests around the touched area,
generate **characterization tests first** (pin current behavior, FR-7.5)
and only then refactor; every iteration is one atomic, revertable unit.

```
while iteration < loop.max_iterations:
    finding = next validated finding (EXTRACTED evidence, rank order)
    plan    = planner.plan(finding)          # strong model, focused context
    diff    = applier.apply(plan)            # on branch, char-tests first
    tests   = run target suite               # red ⇒ revert, finding=blocked
    delta   = graph_diff(re-graph)
    verdict = stop.judge(tests, delta)       # improved/neutral/regressed
    append loop_log.json entry
    if verdict.stop: break
```

Every run terminates with exactly one `StopReason`: `MAX_ITERATIONS`,
`GOAL_METRIC_REACHED` (metric improved ≥ `loop.metric_improvement_threshold`),
`TESTS_GREEN_NO_MORE_FINDINGS`, `BUDGET_EXCEEDED`, `NO_SAFE_ACTION`.

## 2. Interfaces & I/O

- `planner.plan(finding, context) -> FixPlan(finding_id, rationale,
  target_files[], steps[], expected_metric_delta, risk_notes)`
- `applier.apply(plan) -> ApplyResult(branch, diff_stats, char_tests_added)`
  — git operations via `ProcessRunner`; revert = branch reset, recorded.
- `stop.judge(tests, delta, budget) -> IterationVerdict(improved|neutral|
  regressed, stop: bool, reason: StopReason | None)` — a pure function,
  fully truth-table-tested.
- `loop_log.json` entry: iteration, finding_id, plan summary, diff_stats,
  tests {passed, failed, duration}, graph hash before/after, metric
  deltas, tokens spent (ledger slice `fixloop.i<NN>.*`), verdict,
  stop_reason. This log *is* the Refactor Truth Dashboard's data (ADR-6).

## 3. Constraints, alternatives, rationale

| Decision | Alternatives | Why chosen |
|---|---|---|
| Revert on red tests | attempt repair of the fix | bounded cost; a failed fix is a *finding about the finding*, logged |
| Branch per finding | fix in working tree | atomic revert, clean diffs as evidence, target repo never corrupted |
| Characterization tests before refactor | trust existing suite | unfamiliar repo ⇒ unknown coverage; pinning behavior is the only guard we control |
| Pure-function stop judge | inline loop conditionals | truth table is testable exhaustively; loop termination is provable |

Constraint: the loop itself makes **no** LLM calls — only planner/applier
do, through agents/Gatekeeper. Loop = deterministic control flow.

## 4. Success criteria & test scenarios

- `stop.judge` truth table: all combinations of {tests green/red, delta
  improved/neutral/regressed, budget ok/exceeded, findings remaining/none}
  → exactly one verdict+reason (exhaustive parametrized test).
- Loop with scripted planner/applier fakes on mini_repo: green-path run
  produces a complete `loop_log.json`; red-test path reverts and blocks;
  budget exhaustion stops with `BUDGET_EXCEEDED`.
- Applier on a throwaway git repo fixture: branch created, revert
  restores byte-identical tree.
- **KPI (FR-7, PRD §9):** ≥1 finding on the real target auto-fixed with
  tests green and a positive structural delta, end-to-end in the log.

## As-built notes (T345, 2026-06-12)

- Planner deviation from §2: the plan *skeleton* is rule-based (strategy
  per finding kind, hard refusals) — only edit content is LLM work, in
  the applier. Rationale: deterministic refusal doctrine is testable;
  prose plans add cost without adding safety.
- Edit format: SEARCH/REPLACE blocks (byte-exact match) rather than
  unified diff — fuzzy application is structurally impossible; one
  retry with the parse/apply error as feedback.
- Stop truth table implemented exactly as §2 with a 48-state invariant
  sweep (test_fixloop_stop) — exactly one StopReason per run, red tests
  and regressions never accepted, budget always wins.
- Live target run blocked on ANTHROPIC_API_KEY; control flow proven
  with scripted collaborators end to end.

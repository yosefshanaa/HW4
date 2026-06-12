# PROMPTS.md — AI prompt log (NFR-14, guidelines §10)

Chronological log of the prompts that drove this project. Verbatim user
prompts are quoted; the per-module development prompts that derive from
them are summarized once as a pattern instead of 500 near-identical
entries. Update at every phase exit.

## P-001 · 2026-06-11 · Requirements synthesis

> "from downloads read those file L07-Lesson-Summary.pdf,
> Part-A-Active_Knowledge_Architecture.pdf, PART-B-…, PART-C-…,
> software_submission_guidelines-V3.pdf — read this very carefully, from
> the Lesson-summary there is the HomeWork that we should do, make Full
> prd, plan, todo (after reading the Hw), you must be very critical, and
> make those 3 files in a very detailed critical way (todo usually
> 300-800 todos)."

**Output:** `docs/PRD.md` (FR-1…FR-11, NFR-1…NFR-18, KPIs, 12 risks),
`docs/PLAN.md` (C4 diagrams, file map, ADR-1…7, experiment protocol),
`docs/TODO.md` (515 tasks, 17 phases).
**Lesson:** merging the two grading axes (assignment substance +
engineering guidelines) into one requirement set up front prevented
rework later — every TODO task cites the FR/NFR it serves.

## P-002 · 2026-06-11 · Repository creation

> "ok now firstly, make a repo in github, and name it HW4"

**Output:** private repo `yosefshanaa/HW4`, initial commit.

## P-003 · 2026-06-12 · Implementation kickoff (standing instruction)

> "i want you to start working on the implementation, keep in mind that
> we get grades on the commit number (so commit and push every change…),
> implement based on the prd, plan, todo"

**Standing policy derived:** one commit per module/document, pushed
immediately; conventional-commit messages citing TODO task IDs.

## P-pattern · per-module TDD prompts (Phase 1 onward)

Every module in `src/hw4/` is developed with the same prompt shape
against the coding agent:

1. *Context:* paste the module's PLAN §1.3 line + its FR/NFR clauses +
   the relevant TODO task IDs.
2. *Constraint block:* ≤150 code lines, config-driven (no literals),
   tests first in `tests/unit/test_<module>.py`, fakes over mocks for
   time/network (FakeClock, FakeTransport), coverage ≥85%, ruff clean.
3. *Ask:* "write the failing tests, then the module, then run
   `scripts/check_gates.py`; stop if RED."

**Lesson (2026-06-12):** piping pytest through `tail` without
`set -o pipefail` let a red suite slip into a commit once (740a822,
fixed in 6ca3398). The gates script — not ad-hoc pipes — is now the
pre-commit check of record.

## P-004 · 2026-06-12 · Target repo vetting (Phase 3)

Self-directed under P-003's standing instruction. Shortlist prompt
pattern: "vet {click, starlette, dateutil} against ADR-2 criteria using
our own RepoService.loc_stats; run each candidate's test suite in an
ephemeral uv env; timebox BugsInPy and abandon on interpreter-pinning
friction with evidence." Decision and table recorded in
`docs/TARGET_REPO.md`. **Lesson:** dogfooding `loc_stats` for vetting
caught the `core.py` god-node hypothesis before any graph existed.

## P-005 · 2026-06-12 · Graph pipeline (Phase 4)

Per-module TDD prompts per P-pattern (models → queries → extractor →
runner → metrics → diff → SDK/CLI wiring). One extra prompt class:
*smoke-then-fix* — "run the extractor on the real target, list evidence
distribution and missing:* nodes, diagnose false gaps." That run drove
two resolution fixes (re-export tier; code/doc scan-scope split) before
any detector could consume bad edges. **Lesson:** validating extraction
quality on the real target *before* building consumers is cheap
insurance — AMBIGUOUS noise dropped 163→11 edges.

## P-006 · 2026-06-12 · Detection & analysis (Phase 6)

Detector TDD per P-pattern with one addition per detector: a mandatory
false-positive test ("the healthy hub must NOT be flagged") written
before the true-positive test. Target-run triage prompt: "for each
hypothesis, complete the Part-C 5 steps; reject with a cited reason or
validate with cited source lines." **Lesson:** the first live run was
the real test — p98 percentile gate came from triage pain (55 false
god nodes), not from foresight; budget a smoke-triage round into every
detector's schedule.

## P-007 · 2026-06-12 · Experiment machinery (Phase 7)

The experiment prompt (verbatim, both conditions — it IS the
methodology): system-less user message of
`EXPERIMENT_INSTRUCTIONS + "\n\n" + <condition middle> + "\n\nQUESTION: <q>"`
where instructions =
"Answer the question at the end using ONLY the material below. Cite the
source files your answer relies on. If the material is insufficient,
say exactly that instead of guessing."
Condition A middle = repo file listing + grep-ranked whole/partial
files; Condition B middle = index.md + focused subgraph + top wiki
pages. **Lesson:** the first preflight shipped zero file content in A
(top-ranked file alone blew the cap) — naive assemblers need the
"paste as much as fits" rule or the baseline is a strawman.

## P-008 · 2026-06-12 · Fix loop (Phase 9)

Applier prompts (verbatim, they are the fixer methodology): EDIT_SYSTEM
demands SEARCH/REPLACE blocks byte-exact against listed files only;
CHAR_SYSTEM demands a pytest file pinning CURRENT behavior. Failed
attempts are re-prompted once with the exact apply error as feedback.
**Lesson:** the retry-with-error-feedback path was cheaper to test than
to reason about — scripted bad-then-good responses caught a tree-state
bug (revert must happen before retry, or the second patch applies to a
half-edited file).

## P-009 · 2026-06-12 · Agents (Phase 8)

Agent system prompts are data in `agents/roles.py` (role/goal/backstory
per PLAN §3.1) — the analyst's goal embeds the careful-language rule and
the focused-context discipline verbatim. The SKILL Procedure section is
reloaded into every narrative prompt (anti-drift, asserted in tests).
**Lesson:** the framework decision resolved itself empirically — crewai
resolved cleanly under uv (ADR-1 trigger did not fire), and NFR-2 was
preserved by subclassing BaseLLM rather than letting litellm talk to
providers directly.

## P-010 · 2026-06-12 · Notebook & dashboard (Phases 11/13)

Notebook is GENERATED (scripts/build_notebook.py) so cells stay in
lockstep with artifact schemas; executed headlessly via nbclient.
**Lesson:** pending-live cells that degrade to labeled estimates beat
empty placeholders — the offline projection (60.5%) exposed a possible
sub-target savings figure early enough to study the retrieval-cap knobs
(§4 sensitivity) before spending tokens.

*Maintained continuously; see git history for the per-commit trail.*

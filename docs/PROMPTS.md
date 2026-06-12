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

*Maintained continuously; see git history for the per-commit trail.*

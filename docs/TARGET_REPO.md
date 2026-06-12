# TARGET_REPO.md — target repository provenance (FR-1)

> **Status: TEMPLATE** — locked when Phase 3 selects the repo. Every field
> below is mandatory before any analysis result may cite the repo.

## Identity

| Field | Value |
|---|---|
| Repository URL | _tbd_ |
| Commit SHA analyzed | _tbd (pinned; all results reference this SHA)_ |
| Clone date | _tbd_ |
| License | _tbd (must permit analysis + modification)_ |
| Language / framework | Python ≥3.x, _tbd_ |
| Size | _tbd_ LOC across _tbd_ files (`repo_service.loc_stats`) |
| Test suite | _tbd_ (runner, test count, baseline pass rate, duration) |

## Unfamiliarity attestation

The assignment requires reverse-engineering an **unfamiliar** repository.

- [ ] Neither teammate has read or contributed to this codebase before.
- [ ] Neither teammate has worked on a direct fork/derivative of it.
- Prior exposure, if any (honest note): _tbd_

## Selection decision trail

Candidates considered (≥3), with the ADR-2 criteria — mid-size (roughly
3k–30k LOC), runnable test suite, permissive license, single-language
Python, BugsInPy candidate only if installable inside the 90-min timebox:

| Candidate | LOC | Tests run? | License | Verdict & why |
|---|---|---|---|---|
| _tbd_ | | | | |
| _tbd_ | | | | |
| _tbd_ | | | | |

**Chosen:** _tbd_ — rationale: _tbd_

## Sanity gate (must pass before Phase 4)

- [ ] `repo_service.clone` pins the SHA into `workspace/` (gitignored).
- [ ] Target test suite runs to completion locally via `uv run` /
      `ProcessRunner`; baseline results recorded above.
- [ ] License text copied to `workspace/` notes; attribution line added
      to README §License.

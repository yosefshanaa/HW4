# TARGET_REPO.md — target repository provenance (FR-1)

> **Status: LOCKED 2026-06-12** (Phase 3, T109/T115). All analysis results
> reference the pinned SHA below. Decision instantiates ADR-2.

## Identity

| Field | Value |
|---|---|
| Repository URL | https://github.com/pallets/click |
| Commit SHA analyzed | `8a1b1a33d739be05b7e91251e3c0dde77c5e152f` (detached) |
| Clone date | 2026-06-12 |
| License | BSD-3-Clause (`license-files = ["LICENSE.txt"]` in its pyproject) |
| Language / framework | Pure Python ≥3.11 (per upstream pyproject), CLI toolkit |
| Size | 20,437 code lines across 63 `.py` files (`RepoService.loc_stats`); src-only: 9,075 lines / 17 files |
| Test suite | pytest; **baseline at pinned SHA: 1,672 passed, 24 skipped, 31,000 deselected, 1 xfailed in ~14 s** via `uv run --no-project --isolated --with-editable . --with pytest pytest tests -q` |

## Unfamiliarity attestation

- [ ] Student attests: has *used* click as a library consumer but has
      never read, contributed to, or reverse-engineered its internals.
      _(sign with initials + date before submission — T116)_
- Prior exposure note: consumer-level API familiarity only (decorators);
  internal architecture (Context/Command/Parameter machinery, parser,
  shell completion) unknown — which is exactly the analysis target.

## Selection decision trail (T106–T109)

Candidates vetted 2026-06-12 with our own `RepoService.loc_stats`
(dogfooding), ~15 min each:

| Candidate | src LOC / files | Tests run? | License | Verdict & why |
|---|---|---|---|---|
| **pallets/click** | 9,075 / 17 | ✅ 1,672 pass in 4 s, zero extra deps beyond pytest | BSD-3 | **CHOSEN** — `core.py` at 2,689 code lines (30% of src) is a pre-registered god-node hypothesis; rich inter-module import graph; blazing-fast suite is ideal for a loop that reruns tests every iteration |
| encode/starlette (fallback) | 5,351 / 34 | needs httpx/anyio/trio | BSD-3 | strong modularity but higher test-dep friction; named fallback |
| dateutil/dateutil | 5,725 / 17 | extra deps; subpackages largely independent | Apache/BSD dual | flatter inter-module graph ⇒ less interesting bottleneck analysis |

### BugsInPy timebox attempt (T108 — abandoned with evidence, ≈15 min)

`soarsmu/BugsInPy` cloned and inspected: every bug pins a legacy
interpreter (e.g. black bug 1 → `python_version="3.8.3"`, youtube-dl
bug 2 → `3.7.0`) provisioned by bash scripts/venv or Docker. That
directly conflicts with this project's uv-only / py≥3.10 constraints and
would spend the analysis budget on environment archaeology. Abandoned
inside the 90-min timebox, as explicitly sanctioned (L07 §11.2, ADR-2).

## Naive pre-graph impression (T119 — contrast anchor for the report)

Reading file names and sizes only (no graph yet): `core.py` appears to
own Command/Group/Context/Parameter — likely everything routes through
it (god-node/SPOF hypothesis H1). `types.py`, `termui.py`,
`shell_completion.py` look like leaf concerns. `decorators.py` is
probably a thin facade over `core`. Hypotheses to test in Phase 4/6;
upstream `docs/*.md` (api, options, arguments…) gives FR-4.7
traceability material (T120).

## Sanity gate (passed 2026-06-12)

- [x] Cloned by `RepoService.clone` into `workspace/target/` (gitignored), detached at the pinned SHA.
- [x] Test suite runs to completion via uv ephemeral env; baseline recorded above (T117).
- [x] BSD-3-Clause permits use/modification/redistribution with attribution (clauses 1–2); educational modification clearly allowed — attribution kept in README §License (T121).
- [x] Regeneration: `rm -rf workspace/target` then `uv run hw4 graph https://github.com/pallets/click` (or `RepoService.clone(url, commit=<SHA>)`) — documented in README (T122).

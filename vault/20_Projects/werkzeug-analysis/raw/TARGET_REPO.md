# TARGET_REPO.md — target repository provenance (FR-1)

> **Status: LOCKED 2026-06-15** (re-target from click). All analysis
> results reference the pinned SHA below. Decision instantiates ADR-2.
> Supersedes the 2026-06-12 click lock (see Selection trail).

## Identity

| Field | Value |
|---|---|
| Repository URL | https://github.com/pallets/werkzeug |
| Commit SHA analyzed | `1b00618e787f40dfb21eba29caf8f8be7c8e1d93` (detached) |
| Clone date | 2026-06-15 |
| License | BSD-3-Clause (`license-files = ["LICENSE.txt"]` in its pyproject) |
| Language / framework | Pure Python ≥3.10 (per upstream pyproject), WSGI utility library (the toolkit under Flask) |
| Size | 27,498 code lines across **138 `.py` files** (`RepoService.loc_stats`); src-only: 16,829 lines / 52 files |
| Test suite | pytest; **baseline at pinned SHA: 992 passed, 0 skipped, 0 xfailed in ~60 s** (58.6 s / 60.3 s on two runs — stable, no serving-port flakes) via `uv run --no-project --isolated --with-editable . --with pytest --with pytest-timeout --with cryptography --with ephemeral-port-reserve --with watchdog pytest tests -q` |

## Unfamiliarity attestation

- [ ] Student attests: has *used* werkzeug only transitively (as a Flask
      consumer) but has never read, contributed to, or reverse-engineered
      its internals. _(sign with initials + date before submission — T116)_
- Prior exposure note: framework-consumer familiarity only (Flask routes,
  request/response objects); werkzeug's internal architecture (routing
  state machine, sansio/wrappers split, the http header layer,
  datastructures, dev server) is unknown — which is exactly the analysis
  target.

## Selection decision trail (T106–T109, re-target 2026-06-15)

The original target, **pallets/click** @ `8a1b1a3`, was locked 2026-06-12
and fully analyzed. It satisfied the LOC bar (20,437 code lines) but
carried only **63 `.py` files** — below the course floor of *"~10,000+
LOC **AND at least 70 code files**."* On 2026-06-15 the course confirmed
63 files is insufficient, forcing a re-target.

**pallets/werkzeug** clears the bar with margin and is the lowest-friction
swap because the (repo-agnostic) pipeline transfers unchanged:

| Candidate | files / src LOC | Tests run? | License | Verdict & why |
|---|---|---|---|---|
| **pallets/werkzeug** | 138 / 16,829 src | ✅ 992 pass in ~60 s (needs cryptography, ephemeral-port-reserve, pytest-timeout, watchdog) | BSD-3 | **CHOSEN** — same `src/` layout + Pallets pytest tooling as click ⇒ zero pipeline change; one runtime dep (markupsafe); `http.py` (1,543 LOC, 21 importers) is a pre-registered god-node/SPOF hypothesis; rich inter-module graph across routing / wrappers / sansio / datastructures |
| Textualize/rich (fallback) | 100 / ~38k | terminal/snapshot tests flaky headless | MIT | flat `rich/` layout would need a loc_stats/extractor fix; named fallback only |
| (prior) pallets/click | 63 / 9,075 src | ✅ 1,672 pass in ~14 s | BSD-3 | retired — fails the ≥70-file floor |

### BugsInPy timebox attempt (T108 — abandoned with evidence, ≈15 min)

Carried over from the click trail: `soarsmu/BugsInPy` was inspected and
abandoned — every bug pins a legacy interpreter provisioned by bash/Docker,
conflicting with this project's uv-only / py≥3.10 constraints (L07 §11.2,
ADR-2).

## Naive pre-graph impression (T119 — contrast anchor for the report)

Reading file names and sizes only (no graph yet): `http.py` (1,543 LOC)
looks like a header parse/dump utility hub everything depends on
(god-node/SPOF hypothesis H1); `routing/map.py` + `routing/rules.py`
own URL matching; `wrappers/{request,response}.py` are the public WSGI
objects sitting on a `sansio/` framework-agnostic base; `datastructures/`
and `exceptions.py` look like cross-cutting leaf concerns. `serving.py`
and `debug/` look like dev-only side branches. Hypotheses to test in
Phase 4/6; upstream `docs/*.rst` + `CHANGES.rst` give FR-4.7 traceability
material (T120).

## Sanity gate (passed 2026-06-15)

- [x] Cloned by `RepoService.clone` into `workspace/target/` (gitignored), detached at the pinned SHA.
- [x] Test suite runs to completion via uv ephemeral env; baseline recorded above (T117).
- [x] BSD-3-Clause permits use/modification/redistribution with attribution (clauses 1–2); educational modification clearly allowed — attribution kept in README §License (T121).
- [x] Regeneration: `rm -rf workspace/target` then `uv run hw4 graph https://github.com/pallets/werkzeug` (or `RepoService.clone(url, commit=<SHA>)`) — documented in README (T122).

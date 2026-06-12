# Iteration 0 — graph validation record (T157–T162, T164–T166)

Target: `pallets/click` @ `8a1b1a3` · Backend: `ast_extractor/1.00` ·
Built 2026-06-12 · content hash `fd4af707afe0…1839` · extraction 2.81 s
(NFR-18 ✅, T165) · rebuild reproduces an identical content hash (T166).

## Stats (T164)

| Nodes: 1,226 | Edges: 2,070 |
|---|---|
| function 1,017 · class 103 · doc 99 · module 49 · rationale 9 (incl. 9 `missing:*` placeholders) | implements 1,168 · calls 478 · imports 202 · mentions 174 · tested_by 78 · rationale_for 9 |
| | evidence: EXTRACTED 1,930 · INFERRED 129 · AMBIGUOUS 11 |

Plausibility vs LOC (T158): 49 modules / 20,437 code lines ≈ 417
lines/module; 1,017 functions ≈ 20 lines/function — consistent with a
mature CLI library. ✅

## EXTRACTED spot-check — 10 random edges (T158): 10/10 confirmed

Verified by opening the cited file at the claimed construct, e.g.:

| Edge | Evidence in source |
|---|---|
| `click.core —imports→ click.decorators` | `core.py:1170,1768` `from .decorators import …` (function-level imports — AST walk catches them) |
| `Command.format_help_text —calls→ _format_deprecated_label` | def `core.py:98`; call sites `core.py:1206,1238` |
| `_compat.open_stream —calls→ _wrap_io_open` | def `_compat.py:357`; calls `:393,:446` |
| `click.parser —imports→ click._utils` | `parser.py:33–34` |
| 6 further edges (test calls into `CliRunner`/`Option`, package re-export imports) | all confirmed |

## INFERRED spot-check — 5 random mentions (T159): 5/5 plausible

E.g. `doc:docs/parameter-types.md → click.utils.echo` (docs cite the
re-export `click.echo`; resolver correctly lands on the defining module,
conf 0.6). Precision impression: high; no wrong target among sampled.

## AMBIGUOUS triage — all 11 edges (T160)

All 11 are `doc → missing:*` placeholders. Human check resolves them:

- **9 are extractor-limitation false gaps**: `click.UNPROCESSED/STRING/INT/FLOAT/BOOL/UUID` are module-level *constants* (`types.py:1348` etc.), `Context.params` / `ParameterSource.DEFAULT_MAP` are attributes/enum members — our symbol index covers def/class only. They exist; not trace gaps. Limitation documented in PRD_graph_pipeline.
- **2 are URL artifacts** (`click.palletsprojects.com`) — prose noise, not code claims.

Per Part-C: AMBIGUOUS = stop-flag for human check worked exactly as
designed — none were auto-consumed, all were triaged. (The mechanism's
true-positive path is proven on mini_repo's planted `app.plugins` gap.)

## T161/T162 notes

No `graph.html`/`GRAPH_REPORT.md` — fallback backend (ADR-4) emits JSON
only; visual rendering arrives with the Refactor Truth Dashboard
(Phase 13). Narrative-vs-evidence checking therefore not applicable. ✅ n/a

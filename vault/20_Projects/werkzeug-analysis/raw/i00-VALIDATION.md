# Iteration 0 — graph validation record (T157–T162, T164–T166)

Target: `pallets/werkzeug` @ `1b00618e` · Backend: `ast_extractor/1.00` ·
Built 2026-06-15 · content hash `54274cf9e3ff…aed93` · extraction ~95.6 s
(NFR-18 ✅, T165 — slower than click's 2.8 s: ~3× the files over a
`/mnt/c` mount) · rebuild reproduces an identical content hash
(`54274cf9…` on both builds, T166 ✅).

## Stats (T164)

| Nodes: 1,912 | Edges: 3,304 |
|---|---|
| function 1,553 · class 219 · module 84 · doc 43 · rationale 13 | implements 1,932 · calls 747 · imports 369 · tested_by 186 · mentions 57 · rationale_for 13 |
| | evidence: EXTRACTED 3,235 · INFERRED 68 · AMBIGUOUS 1 |

Scope mirrors click: `src/werkzeug` (52 modules) + `tests/` (32 modules);
`examples/` and `docs/*.py` excluded from code, `docs/*.rst|md` still
scanned for documentation traceability.

Plausibility vs LOC (T158): 84 modules / 32,032 analyzed code lines ≈ 381
lines/module; 1,553 functions ≈ 20.6 lines/function — consistent with a
mature WSGI library (src-only `src/werkzeug` = 21,885 lines). ✅

## EXTRACTED spot-check — 10 edges (T158): 10/10 confirmed

Verified by opening the cited file at the claimed construct:

| Edge | Evidence in source |
|---|---|
| `datastructures.accept —imports→ werkzeug.http` | `datastructures/accept.py:20` `from .http import …` |
| `formparser —imports→ werkzeug.http` | `formparser.py:14` `from .http import parse_options_header` |
| `wrappers.request —imports→ sansio.request` | `wrappers/request.py:20` `from ..sansio.request import Request as _SansIORequest`; `:32` `class Request(_SansIORequest)` |
| `wrappers.request —imports→ formparser` | `wrappers/request.py:19` `from ..formparser import FormDataParser` |
| `routing.map —imports→ routing.matcher` | `routing/map.py:28` `from .matcher import StateMachineMatcher`; `:115` instantiation |
| `routing.map —imports→ werkzeug.exceptions` | `routing/map.py:17` `from ..exceptions import NotFound` (also MethodNotAllowed, HTTPException) |
| `exceptions.HTTPException.get_response —calls→ _internal._get_environ` | `exceptions.py` `get_response` body |
| `debug.DebuggedApplication.log_pin_request —calls→ wrappers.response.Response` | `debug/__init__.py` pin-auth path |
| `Request.__init__ —calls→ datastructures.EnvironHeaders` | `wrappers/request.py:128` `headers=EnvironHeaders(environ)` |
| `werkzeug.wrappers —tested_by→ tests.live_apps.data_app` | test app imports `Request`/`Response` from the package |

## INFERRED spot-check — sample of 68 (T159): plausible

All 68 INFERRED edges are bare-name `calls` resolved to a unique symbol
at conf 0.6 (non-unique names are skipped, never guessed). E.g.
`tests.test_exceptions.test_passing_response —calls→ werkzeug.test.TestResponse`
and `tests.test_serving.test_ssl_dev_cert —calls→ tests.conftest.dev_server`
— the resolver correctly lands on the single defining symbol. Precision
impression: high; no wrong target among the sampled edges.

## AMBIGUOUS triage — all 1 edge (T160)

The single AMBIGUOUS edge is `doc:CHANGES.rst —mentions→
missing:werkzeug.wsgi.make_line_iter`. Human check resolves it: this is
a **changelog-history artifact, not a trace gap**. `CHANGES.rst:468`
records *"Deprecate `werkzeug.wsgi.make_line_iter` and `make_chunk_iter`
(:pr:`2613`)"*; both symbols were since removed — `wsgi.py` now exposes
only `LimitedStream` (`wsgi.py:439`). The changelog correctly documents a
removed symbol; nothing to implement or fix. (The mechanism's
true-positive path is proven on mini_repo's planted gap.) Per Part-C,
AMBIGUOUS = stop-flag for human check, and it fired exactly as designed —
not auto-consumed.

## T161/T162 notes

No `graph.html`/`GRAPH_REPORT.md` — the fallback backend (ADR-4) emits
JSON only; visual rendering arrives with the Refactor Truth Dashboard.
Narrative-vs-evidence checking therefore not applicable. ✅ n/a

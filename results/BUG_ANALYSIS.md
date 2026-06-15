# Bug analysis — graph-guided debugging (EX04 §5.3-5.4)

## Problem
`httprange.parse_byte_range(header, resource_length)` parses a single HTTP
`bytes=start-end` range. For `bytes=0-499 of 1000` the content length must be
**500** bytes — HTTP byte ranges are inclusive of `end` (RFC 9110
§14.1.2). The buggy version returns **499**, silently dropping
the last byte of every range.

## Reproduction (red)
Running the spec (`tests/test_range.py::test_inclusive_range_length`) against
`parser_buggy.py`: `parse_byte_range("bytes=0-499", 1000)`
returns length **499**, expected **500** → **reproduced**.

## Root cause
Off-by-one: the length was computed as `end - start` (end-exclusive) instead
of `end - start + 1`. An inclusive range `0-499` spans 500 byte positions,
not 499. The check passes types and bounds, so only a behavioural spec test
exposes it.

## Graph-guided research path
Instead of reading the whole package, we start from the failing test and
follow the graph: `tests.test_range` →(`tested_by`)→ **`httprange.parser`**.
The graph names the implicated module directly, so the fix is scoped to one
file — `httprange.parser` — without a full-tree scan.

## The fix (before → after)
```diff
- content_length = end - start      # parser_buggy.py — off-by-one
+ content_length = end - start + 1  # parser.py — inclusive range
```

## Verification (green)
The same spec against the fixed `parser.py` returns length **500**
== **500** → **fix verified**. The
four spec cases (inclusive length, open-ended suffix, single byte, rejected
unsatisfiable) all pass.

## Naive vs graph-guided — the four §5.5 dimensions
| Dimension | Naive (read everything) | Graph-guided (localize first) |
|---|---|---|
| Tokens consumed | 560 | **273** (51% fewer) |
| Files / textual units read | 3 (whole `httprange/` package) | **1** (`httprange.parser` only) |
| Research rounds | 1 whole-package sweep, then hunt for the line | 1 graph localization (`tested_by` edge) → 1 targeted read |
| Speed/quality to root cause | scan all 3 files for the off-by-one | graph names the module + function directly — no scan |

Graph-guided localization reaches the fix reading **51% fewer
tokens** and **3→1 files**: the graph turned "read
everything" into "read the one file the failing test points at".

## Graph-guided agent workflow (§5.3)
`hw4 debug --agent` runs the CrewAI **analyst** on this spine: it is handed the
symptom and **only** the graph-localized module's source (the
273-token snippet, not the 560-token package) and
writes its careful-language root-cause narrative to `results/agent_debug.md`,
ledger-tagged `agent.analyst`. That snippet-on-demand context reduction — graph
first, one file second, never the whole tree — is the efficiency mechanism. The
fix itself is verified deterministically by the spec (red→green above), not by
the LLM.

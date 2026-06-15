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

## Token comparison — naive vs graph-guided
| Approach | What is read | ~tokens |
|---|---|---|
| Naive | whole `httprange/` package pasted | 560 |
| Graph-guided | only the located module `httprange.parser` | 273 |

Graph-guided localization reads **51% fewer tokens** to reach the
fix — the graph turned "read everything" into "read the one file the failing
test points at". The CrewAI analyst narrates this root cause on top of the
deterministic spine (`hw4 debug`); the fix itself is verified by the spec.

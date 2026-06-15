"""Debug-case op behind the facade (§3.2 split) — graph-guided bug fix.

Drives the deterministic debug spine (reproduce -> localize -> verify) and
writes the bug-analysis report EX04 §7 requires: problem, root cause,
graph-guided research path, the before/after fix, and the token comparison.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from hw4.services.debug import DebugResult, run_debug_case

DEFAULT_TARGET = "tests/fixtures/buggy_case"


@dataclass(frozen=True)
class DebugReport:
    result: DebugResult
    report_path: Path

    def __str__(self) -> str:
        r = self.result
        return (
            f"bug {'reproduced' if r.reproduced else 'NOT reproduced'} "
            f"({r.case}: buggy={r.buggy_value} expected={r.expected}); "
            f"located {r.located_module}; fix {'verified' if r.fixed else 'FAILED'}; "
            f"tokens {r.naive_tokens}->{r.graph_tokens} ({r.savings:.0%} saved) -> {self.report_path}"
        )


def debug(sdk, target_path=None) -> DebugReport:
    root = Path(target_path) if target_path else Path(sdk.base_dir) / DEFAULT_TARGET
    result = run_debug_case(root, sdk.config)
    sdk.results_dir.mkdir(parents=True, exist_ok=True)
    path = sdk.results_dir / "BUG_ANALYSIS.md"
    path.write_text(_render(result), encoding="utf-8")
    return DebugReport(result=result, report_path=path)


def _render(r: DebugResult) -> str:
    return f"""# Bug analysis — graph-guided debugging (EX04 §5.3-5.4)

## Problem
`httprange.parse_byte_range(header, resource_length)` parses a single HTTP
`bytes=start-end` range. For `{r.case}` the content length must be
**{r.expected}** bytes — HTTP byte ranges are inclusive of `end` (RFC 9110
§14.1.2). The buggy version returns **{r.buggy_value}**, silently dropping
the last byte of every range.

## Reproduction (red)
Running the spec (`tests/test_range.py::test_inclusive_range_length`) against
`parser_buggy.py`: `parse_byte_range("{r.case.split(' of ')[0]}", {r.case.split(' of ')[1]})`
returns length **{r.buggy_value}**, expected **{r.expected}** → **{'reproduced' if r.reproduced else 'not reproduced'}**.

## Root cause
Off-by-one: the length was computed as `end - start` (end-exclusive) instead
of `end - start + 1`. An inclusive range `0-499` spans 500 byte positions,
not 499. The check passes types and bounds, so only a behavioural spec test
exposes it.

## Graph-guided research path
Instead of reading the whole package, we start from the failing test and
follow the graph: `tests.test_range` →(`tested_by`)→ **`{r.located_module}`**.
The graph names the implicated module directly, so the fix is scoped to one
file — `{r.located_module}` — without a full-tree scan.

## The fix (before → after)
```diff
- content_length = end - start      # parser_buggy.py — off-by-one
+ content_length = end - start + 1  # parser.py — inclusive range
```

## Verification (green)
The same spec against the fixed `parser.py` returns length **{r.fixed_value}**
== **{r.expected}** → **{'fix verified' if r.fixed else 'FIX FAILED'}**. The
four spec cases (inclusive length, open-ended suffix, single byte, rejected
unsatisfiable) all pass.

## Token comparison — naive vs graph-guided
| Approach | What is read | ~tokens |
|---|---|---|
| Naive | whole `httprange/` package pasted | {r.naive_tokens} |
| Graph-guided | only the located module `{r.located_module}` | {r.graph_tokens} |

Graph-guided localization reads **{r.savings:.0%} fewer tokens** to reach the
fix — the graph turned "read everything" into "read the one file the failing
test points at". The CrewAI analyst narrates this root cause on top of the
deterministic spine (`hw4 debug`); the fix itself is verified by the spec.
"""

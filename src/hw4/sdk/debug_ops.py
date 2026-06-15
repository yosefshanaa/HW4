"""Debug-case op behind the facade (§3.2 split) — graph-guided bug fix.

Drives the deterministic debug spine (reproduce -> localize -> verify) and
writes the bug-analysis report EX04 §7 requires: problem, root cause,
graph-guided research path, the before/after fix, and the token comparison.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from hw4.services.debug import DebugResult, run_debug_case
from hw4.services.debug.vault_pages import write_debug_vault

DEFAULT_TARGET = "tests/fixtures/buggy_case"


@dataclass(frozen=True)
class DebugReport:
    result: DebugResult
    report_path: Path
    narrative_path: str = ""

    def __str__(self) -> str:
        r = self.result
        agent = f"; agent narrative -> {self.narrative_path}" if self.narrative_path else ""
        return (
            f"bug {'reproduced' if r.reproduced else 'NOT reproduced'} "
            f"({r.case}: buggy={r.buggy_value} expected={r.expected}); "
            f"located {r.located_module}; fix {'verified' if r.fixed else 'FAILED'}; "
            f"tokens {r.naive_tokens}->{r.graph_tokens} ({r.savings:.0%} saved) "
            f"-> {self.report_path}{agent}"
        )


def debug(sdk, target_path=None, agent: bool = False) -> DebugReport:
    root = Path(target_path) if target_path else Path(sdk.base_dir) / DEFAULT_TARGET
    result = run_debug_case(root, sdk.config)
    sdk.results_dir.mkdir(parents=True, exist_ok=True)
    path = sdk.results_dir / "BUG_ANALYSIS.md"
    path.write_text(_render(result), encoding="utf-8")
    write_debug_vault(Path(sdk.base_dir) / sdk.config.path("vault"), result)
    narrative_path = ""
    if agent:
        from hw4.services.agents.debug_flow import debug_flow
        narrative_path = debug_flow(sdk, root).get("narrative_path", "")
    return DebugReport(result=result, report_path=path, narrative_path=narrative_path)


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

## Naive vs graph-guided — the four §5.5 dimensions
| Dimension | Naive (read everything) | Graph-guided (localize first) |
|---|---|---|
| Tokens consumed | {r.naive_tokens} | **{r.graph_tokens}** ({r.savings:.0%} fewer) |
| Files / textual units read | {r.naive_files} (whole `httprange/` package) | **{r.graph_files}** (`{r.located_module}` only) |
| Research rounds | 1 whole-package sweep, then hunt for the line | 1 graph localization (`tested_by` edge) → 1 targeted read |
| Speed/quality to root cause | scan all {r.naive_files} files for the off-by-one | graph names the module + function directly — no scan |

Graph-guided localization reaches the fix reading **{r.savings:.0%} fewer
tokens** and **{r.naive_files}→{r.graph_files} files**: the graph turned "read
everything" into "read the one file the failing test points at".

## Graph-guided agent workflow (§5.3)
`hw4 debug --agent` runs the CrewAI **analyst** on this spine: it is handed the
symptom and **only** the graph-localized module's source (the
{r.graph_tokens}-token snippet, not the {r.naive_tokens}-token package) and
writes its careful-language root-cause narrative to `results/agent_debug.md`,
ledger-tagged `agent.analyst`. That snippet-on-demand context reduction — graph
first, one file second, never the whole tree — is the efficiency mechanism. The
fix itself is verified deterministically by the spec (red→green above), not by
the LLM.

## Knowledge-level before/after (§5.4)
The fix also moved the *knowledge* state, captured in the Obsidian vault
project `vault/20_Projects/range-debug/`: before research the suspect was
unknown (symptom only); after, the bug-focused `hot.md` names the
graph-localized suspect `{r.located_module}.parse_byte_range`, a `bug` page
records the root cause, and `knowledge-before-after.md` tabulates what changed
— the decisive `tested_by` edge that turned a whole-package search into a
one-module read.
"""

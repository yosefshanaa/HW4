# Bug analysis — real discovered bugs in `andela/buggy-python` (graph-guided fix)

This is the **second** debugging deliverable and the honest one: a *real bug
neither of us wrote*, found in an external repo and fixed. The first
([`BUG_ANALYSIS.md`](BUG_ANALYSIS.md)) is a deterministic, unit-tested *planted*
demonstration; this one is a genuine discovered fix on third-party code.

## Target & provenance
[`andela/buggy-python`](https://github.com/andela/buggy-python) @
`887009334e17556880f62d58315f96c2b305aa05` (2018-07-19) — an EX04-suggested
repo of deliberately buggy Python for debugging practice. **The bugs are
andela's**, authored for teaching; we located and fixed them. The repo's own
`main.py` is the verification harness (their rule: do not modify it) — its
assertions are the spec. Vendored at [`examples/buggy-python/`](../examples/buggy-python/).

## Reproduction (red) — the harness crashes
```
$ python main.py
ImportError: cannot import name 'lambda_array' from 'snippets'
```
…and behind that first failure sit four more genuine defects across the
`snippets` package.

## Graph-guided localization
We graphified the repo (`results/buggy_python/{graph.json,GRAPH_REPORT.md}`,
16 nodes / 18 edges). The failing harness `main.py` resolves to one edge —
`main —imports→ snippets` — and the package's `implements` edges expand it to
exactly the four modules to inspect: `foobar`, `loop`, `io`, `__init__`. The
graph turns "read the whole repo" into "read the four modules the harness
depends on" — no guesswork.

## The bugs & root causes
| File | Root cause | Fix |
|---|---|---|
| `snippets/__init__.py` | exports commented out — only `foo` is re-exported, so the other five imports in `main.py` fail | export all five functions |
| `snippets/loop.py` | `lambda_methods = {}` (a dict, but `main.py` does `lambdas[0]`), `for i in 10` (an int isn't iterable), `lambdamethods.push(...)` (typo + Python lists have no `.push`) | `[]` · `range(10)` · `lambda_methods.append(...)` |
| `snippets/foobar.py` | **mutable default argument** `def foo(bar=[])` — the *same* list is reused across calls, so the second `foo()` returns `["baz","baz"]` | `bar=None` then `if bar is None: bar = []` |
| `snippets/io.py` | `data("loans")` (a dict isn't callable), `!==` (not valid Python), `is "paid"` (identity, not equality), `sun`/`length` (typos for `sum`/`len`), `loan.amount` (attribute access on a dict) | `data["loans"]` · `!=`/`==` · `sum`/`len` · `loan["amount"]` |

## The fix (before → after)
Full diff: [`examples/buggy-python/THE_FIX.patch`](../examples/buggy-python/THE_FIX.patch). The headline logic bug:
```diff
- def foo(bar=[]):
+ def foo(bar=None):
+     if bar is None:
+         bar = []
      bar.append("baz")
      return bar
```

## Verification (green) — andela's own harness now passes
```
$ python main.py
All test passed successfully!! 😀
```
Every assertion holds, including the data ones computed from `loans.json`
(11 paid loans → 29493.85304; 4 unpaid → 11062; average 2681.2593672727276).

## Token comparison (naive vs graph-guided)
| Approach | Files read | ~tokens |
|---|---|---|
| Naive | whole repo (5 `.py`) | ~710 |
| Graph-guided | the 4 `snippets` modules the harness imports | ~431 |

~39% fewer tokens even on a tiny repo; the method is the point — the graph
named the modules to open from the failing harness, instead of reading
everything. (The large-scale savings number is the werkzeug Q&A experiment:
58.7%.)

## Honesty note
The bugs were authored by andela, not by us — this is a genuine discovered
fix, verified by the upstream harness. It complements the planted
`buggy_case` (which stays as the offline, gate-verified unit demonstration).

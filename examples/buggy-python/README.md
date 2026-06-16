# buggy-python — real discovered-bug target (graph-guided fix)

**Source:** [`andela/buggy-python`](https://github.com/andela/buggy-python) @ `887009334e17556880f62d58315f96c2b305aa05` (2018-07-19) — one of the EX04-suggested buggy repos. **The bugs here were authored by andela** for debugging practice; we did *not* write them. This is the **buggy-code target** — the companion to the large, clean, graphified [werkzeug analysis](../../README.md) in the repo root.

`main.py` is andela's own verification harness (their instruction: *do not modify it*); its assertions are the spec. This folder holds the **fixed** solution — `python main.py` prints `All test passed successfully!! 😀`. The original buggy state is preserved inline in [`THE_FIX.patch`](THE_FIX.patch) (its `-` lines are the bugs).

## What was broken — located via the graph, fixed by us

| File | Real bug (andela's) | Fix |
|---|---|---|
| `snippets/__init__.py` | only `foo` exported; `main.py` imports 5 more → `ImportError` | export all five functions |
| `snippets/loop.py` | `lambda_methods = {}` (dict), `for i in 10` (int not iterable), `lambdamethods.push(...)` (typo + lists have no `.push`) | `[]`, `range(10)`, `lambda_methods.append(...)` |
| `snippets/foobar.py` | mutable default argument `def foo(bar=[])` — the list persists across calls | `bar=None` + `if bar is None: bar = []` |
| `snippets/io.py` | `data("loans")` (dict isn't callable), `!==` (not valid Python), `is "paid"` (identity vs equality), `sun`/`length` typos, `loan.amount` (attr access on a dict) | `data["loans"]`, `!=` / `==`, `sum` / `len`, `loan["amount"]` |

## Verify

```bash
cd examples/buggy-python && python main.py    # → All test passed successfully!! 😀
git apply -R THE_FIX.patch                     # (optional) revert to the original buggy state
```

Full root-cause analysis, graph localization, before/after, and token comparison: [`results/BUG_ANALYSIS_buggy_python.md`](../../results/BUG_ANALYSIS_buggy_python.md). Graph artifacts: [`results/buggy_python/`](../../results/buggy_python/).

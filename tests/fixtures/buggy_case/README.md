# buggy_case — debug-case target (broken-python style)

A deliberately small Python package with **one planted functional bug**, so
the graph-guided debugging loop has a concrete defect to find, root-cause,
and fix (EX04 §5.3–5.4). Chosen over a heavy BugsInPy environment per the
lecturer's "prefer a small, well-explained case" guidance (§6).

## The planted bug

`httprange.parse_byte_range(header, resource_length)` parses a single HTTP
`bytes=start-end` range. HTTP byte ranges are **inclusive** of `end`
(RFC 9110 §14.1.2): `bytes=0-499` of a 1000-byte resource is **500** bytes.

| File | Behaviour |
|---|---|
| `httprange/parser.py` | **fixed** — `length = end - start + 1` (correct, inclusive) |
| `httprange/parser_buggy.py` | **before** — `length = end - start` (off-by-one: drops the last byte) |

The buggy version returns 499 for `bytes=0-499`, silently truncating one
byte off every range — the classic kind of boundary bug that passes a
casual read and only a spec test catches.

## Reproduce

```bash
cd tests/fixtures/buggy_case && python -m pytest -q   # passes on the fixed parser
uv run hw4 debug                                       # red→green + graph localization + report
```

`tests/test_range.py` pins the inclusive-range spec; `hw4 debug` reproduces
the bug on the buggy version, locates the module via the graph's `tested_by`
edge, verifies the fix turns the spec green, and writes `results/BUG_ANALYSIS.md`.

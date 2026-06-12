# mini_repo — synthetic analysis target (test fixture, T123)

A deliberately flawed tiny codebase powering hw4's unit and integration
tests without network access. **Planted defects (the answer key):**

| Planted defect | Where | Detector that must find it |
|---|---|---|
| God node | `app/engine.py` — imports and drives every other app module, mixes loading, math, and formatting concerns | `god_node` |
| Healthy hub (false-positive guard) | `app/utils.py` — high fan-in, single concern; must NOT be flagged | `god_node`, `spof` |
| Orphan module | `orphan/legacy.py` — no inbound imports from the main component | `isolation` |
| Traceability gap | this README documents `app.plugins`, which does not exist | `traceability` |

## Documented architecture (intentionally partly false)

- `app.engine` — pipeline entry point; orchestrates everything.
- `app.models` — record types.
- `app.plugins` — dynamic plugin loader for custom report formats.
  (Planted lie: no such module exists anywhere in the tree.)

Run its own tests with `pytest` from this directory (3 tests, no deps).

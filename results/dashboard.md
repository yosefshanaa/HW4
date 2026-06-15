# Refactor Truth Dashboard

**Run verdict:** stop reason `NO_SAFE_ACTION` · 1 iteration(s)

## Iteration 2 — F-005 · REVERTED

- strategy: extract the SMALLEST cohesive group of private module-level helper functions (e.g. formatting/label helpers) into one new sibling module; move ONLY functions with no class/state dependencies, import them back by name so every existing reference keeps working; do not move classes, do not touch the public API, do not reorder anything else
- tests: green · verdict: **regressed**
- top bottleneck score: 0.106 → 0.106 (Δ 0.0)
- isolated components: 1250 → 1253
- graph: `a37ab4bf54dc` → `975c2e2246ea`
- tokens: 25204 in / 2152 out ($0.0051)

---
*Known limitation (T156): a renamed bottleneck appears as remove+add; suspected renames are flagged by graph_diff, and barely-moved scores are highlighted above rather than hidden.*
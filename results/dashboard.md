# Refactor Truth Dashboard

**Run verdict:** stop reason `NO_SAFE_ACTION` · 1 iteration(s)

## Iteration 12 — F-003 · REVERTED

- strategy: extract the SMALLEST cohesive group of private module-level helper functions (e.g. formatting/label helpers) into one new sibling module; move ONLY functions with no class/state dependencies, import them back by name so every existing reference keeps working; do not move classes, do not touch the public API, do not reorder anything else
- tests: RED · verdict: **regressed**
- top bottleneck score: 0.4965 → 0.4948 (Δ 0.0017)
- isolated components: 846 → 848
- graph: `bc4f17d43c37` → `193ad5c9c4dc`
- tokens: 183984 in / 8605 out ($0.4710)

---
*Known limitation (T156): a renamed bottleneck appears as remove+add; suspected renames are flagged by graph_diff, and barely-moved scores are highlighted above rather than hidden.*
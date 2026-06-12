# Finding F-NNN — <one-line title>

> **TEMPLATE** (T090/T095). One file per finding, named `F-NNN-<slug>.md`.
> The five numbered sections below are the Part-C inference pipeline and
> are **mandatory** — a finding missing any section is not reportable.
> Machine-readable twin lives in `results/findings.json`.

| Field | Value |
|---|---|
| Kind | SPOF / GOD_NODE / ISOLATED / TRACE_GAP / DUPLICATION |
| Status | hypothesis → validated / rejected → fixed / blocked |
| Confidence | 0.00–1.00 (= min over the evidence chain) |
| Nodes | `<graph node ids>` |
| Detector | `<module>` with thresholds from config v`<version>` |

## 1. Observation (what the graph shows)

Raw, neutral statement of the signal. *"Node `auth.session` has
betweenness 0.41 (rank 1/214) and lies on 9 of 11 inter-community
paths."* No interpretation yet.

## 2. Relation analysis (what kinds of edges, what evidence class)

Which relations produce the signal (`calls`, `imports`, `mentions`…) and
their evidence classes. EXTRACTED edges support strong claims; INFERRED
must be flagged; AMBIGUOUS routes the finding to human review and blocks
automated fixing.

## 3. Confidence (qualified conclusion, careful language)

The Part-C formula: **source → qualified conclusion → confidence →
finding → relation type.** Write *"the call topology suggests X
(confidence 0.7) because…"*, never *"X is broken"*. State what would
*lower* the confidence if true.

## 4. Context (why it matters here)

Domain reading: is this hub a healthy utility or a mandatory bottleneck?
What breaks, and for whom, if this node fails or changes? Impact estimate
used in ranking.

## 5. Source validation (the graph is testimony, not verdict)

Direct evidence from the code itself: file paths + line references read
to confirm or refute the hypothesis. Outcome: `validated` or `rejected`,
with the decisive snippet cited. Only validated findings with EXTRACTED
evidence are eligible for the fix loop (PRD_fix_loop §1).

## Disposition

Suggested action, fix-loop eligibility, and — after the loop — links to
the fix branch, `loop_log.json` iteration, and graph delta.

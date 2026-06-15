# Confusion matrix — detector evaluation (L07 §13.2)

Deterministic detectors run over `tests/fixtures/mini_repo` and scored against its
planted-defect answer key. A candidate is *predicted positive* when a
finding of the matching kind names the candidate node; *expected* is the
ground-truth label the fixture documents. No LLM or network is involved,
so this artifact is fully reproducible via `hw4 evaluate`.

|                 | Actual defect | Actual clean |
|-----------------|---------------|--------------|
| **Pred defect** | TP = 3   | FP = 1  |
| **Pred clean**  | FN = 0   | TN = 2  |

| Metric | Value |
|---|---|
| Precision | 0.750 |
| Recall | 1.000 |
| F1 | 0.857 |
| Accuracy | 0.833 |

## Per-candidate outcomes

| Node | Detector | Expected | Predicted | Cell | Why |
|---|---|---|---|---|---|
| `app.engine` | GOD_NODE | defect | yes | **TP** | app/engine.py imports and drives every other app module, mixing loading, math, and formatting concerns. |
| `app.utils` | GOD_NODE | clean | no | **TN** | Healthy hub: high fan-in but a single concern. The god-node detector's healthy-hub counter-check must NOT flag it. |
| `app.utils` | SPOF | clean | no | **TN** | Shared helper, but no mandatory-path bottleneck. Guards against over-flagging common utilities as single points of failure. |
| `orphan.legacy` | ISOLATED | defect | yes | **TP** | orphan/legacy.py has no inbound or outbound imports to the main component. |
| `conftest` | ISOLATED | clean | yes | **FP** | Test scaffolding, genuinely disconnected. A correct topological observation but not a code defect; surfaced for human triage, so it costs precision rather than masking a real bug. |
| `app.plugins` | TRACE_GAP | defect | yes | **TP** | The README documents app.plugins, which exists nowhere in the tree — a documented-but-absent claim. |

## Reading

Recall **1.00** — all 3 planted defects were detected.
Precision **0.75** — 1 benign node(s) flagged (see the
per-candidate rationale; isolation is reported as a triage *finding*, not a
diagnosis, per Part-C). The healthy-hub guards (`app.utils`) stay unflagged,
the 2 true negatives that keep precision from collapsing.

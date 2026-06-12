# PRD — Architectural Defect Detection

**Status:** approved 2026-06-12 · **Serves:** FR-6, Part-C inference pipeline ·
**Implements in:** `services/detectors/{base,spof,god_node,isolation,traceability,duplication}.py` (Phase 6)

## 1. Description & theory

Detectors turn graph metrics into **falsifiable findings**, not verdicts.
Part-C's discipline applies end-to-end: every finding carries an evidence
chain (observation → relation → confidence → context → source validation)
and careful language ("X *suggests* Y, confidence 0.7 because…"). A graph
signal is a *hypothesis*; it becomes `validated` only after source-level
confirmation, and only `validated` findings with `EXTRACTED` evidence are
eligible for the automated fix loop. `AMBIGUOUS`-based hypotheses route to
human review, never to fixes.

Five detectors (config-thresholded, all deterministic):

| Detector | Signal | Adjudication theory |
|---|---|---|
| **SPOF** | high betweenness + lies on mandatory paths (bridge / articulation point) | a hub everyone *can* route around is healthy; a node everyone *must* route through is a single point of failure (Part-C hub-vs-bottleneck) |
| **God node** | fan-in+fan-out ≥ threshold × community median; touches many communities | distinguish "popular utility" (high fan-in, one concern) from "does everything" (high fan-out across concerns) |
| **Isolation** | components/communities with no inbound edges from main component | classify: dead code vs entry point vs docs island vs test island |
| **Traceability gap** | `doc`/`rationale` nodes with no `mentions`/`rationale_for` edge to code (or vice versa) | documented-but-unimplemented or implemented-but-undocumented |
| **Duplication** | `semantically_similar_to` edges (INFERRED) above confidence cap | hypothesis only — must be source-verified before `validated` |

## 2. Interfaces & I/O

```python
class Detector(ABC):
    kind: FindingKind
    def detect(self, graph: Graph, metrics: Metrics) -> list[Finding]
```

`Finding` (serialized to `results/findings.json`): `id ("F-001")`, `kind`,
`nodes[]`, `evidence_chain[]` (each step: observation, relation, evidence
class, confidence, source_file), `confidence` (min over chain — a chain is
as strong as its weakest link), `status ∈ {hypothesis, validated, rejected,
fixed, blocked}`, `suggested_action`. Ranking: `confidence × impact`
(impact = normalized centrality of involved nodes). All thresholds live in
`config/setup.json:detectors.*` — **zero magic numbers in code**.

## 3. Constraints, alternatives, rationale

| Decision | Alternatives | Why chosen |
|---|---|---|
| Deterministic detectors + LLM only for narrative | LLM-judges the graph directly | metrics are token-free and reproducible (L07 AST point); LLM verdicts are neither |
| min-confidence chain aggregation | mean/product | conservative; mirrors Part-C "weakest evidence bounds the claim" |
| Findings as data (JSON) | findings as prose | feeds fix loop, dashboard, and report from one source of truth |
| Five fixed detectors | pluggable registry | scope control; ABC keeps extension cheap if needed |

## 3.1 As-built thresholds (T246, updated 2026-06-12)

`config/setup.json:detectors.*` — spof: mandatory ratio ≥0.3 within
betweenness top-5; god_node: degree > max(2×median, **p98 of nonzero
degrees**) AND fan_out ≥3 AND ≥2 communities (the percentile gate was
added after the first target run flagged 55 nodes — call graphs are
leaf-dominated, median multiples alone are meaningless); isolation:
groups merged over ALL relations and must not touch the main component;
duplication: pair confidence ≥0.5. Target result: 67 → 15 hypotheses,
2 validated (results/FINDINGS.md).

## 4. Success criteria & test scenarios

Each detector is fixture-tested on `tests/fixtures/mini_repo`'s graph with
**planted** defects (known answer key): the planted god node is found and
the healthy hub is *not* flagged (false-positive test is mandatory per
detector); the planted orphan module is isolated; the planted doc-gap
surfaces; chains carry correct evidence classes; ranking orders the god
node above the doc gap. **KPI (PRD §9):** ≥2 findings on the real target
validated at source level; ≥1 eligible for the fix loop.

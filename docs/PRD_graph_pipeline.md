# PRD — Graph Generation Pipeline

**Status:** approved 2026-06-12 · **Serves:** FR-2, FR-1 (provenance), ADR-4, ADR-5 ·
**Implements in:** `services/{graph_runner,graph_models,graph_metrics,graph_diff,repo_service}.py` (Phase 3–4)

## 1. Description & theory

The knowledge graph is the project's load-bearing artifact: detectors,
retrieval, the fix loop's verdict, and the token experiment all read it.
The pipeline turns a cloned repository into a **normalized graph contract**
(PLAN §2.1) regardless of which extractor produced it:

```json
{"version": "1.00", "iteration": 0,
 "nodes": [{"id", "type": "function|class|module|doc|rationale", "label", "source_file", "community"}],
 "edges": [{"src", "dst", "relation": "calls|imports|implements|mentions|tested_by|rationale_for|semantically_similar_to",
            "evidence": "EXTRACTED|INFERRED|AMBIGUOUS", "confidence": 0.0-1.0}]}
```

Theory (L07 §4, Part-C): deterministic AST-level extraction is ~token-free
and trustworthy (`EXTRACTED`); LLM-inferred semantics are cheaper to store
than to recompute but must be marked (`INFERRED`); anything uncertain is a
flag for human review (`AMBIGUOUS`) and **never** feeds automated fixes.
Evidence is a first-class enum so no consumer can drop it accidentally.

Primary extractor was planned as **Graphify** (course tool) run via
`ProcessRunner`; ADR-4 reserved a minimal `ast`-based fallback emitting
the *identical* contract.

> **ADR-4 gate closed 2026-06-12 (T131–T136):** discovery spike found no
> obtainable Graphify distribution (PyPI 404 for `graphify`/
> `graphify-cli`; course materials contain only the Part-C PDF describing
> its outputs, not the tool). **Fallback activated:** in-repo
> `ast_extractor` backend — module/class/function nodes; `imports`/
> `calls` edges as EXTRACTED; doc-mention edges as INFERRED; fuzzy
> matches as AMBIGUOUS; docstrings/TODO comments become `rationale`
> nodes (T137–T139). Backend id is recorded in every graph artifact so a
> later real-Graphify run slots in without downstream change.

## 2. Interfaces & I/O

- `repo_service.clone(url) -> RepoInfo(path, commit_sha, license, loc_stats)`
  — provenance recorded into `docs/TARGET_REPO.md` data (FR-1).
- `graph_runner.build(repo_path, iteration) -> Path` — runs extractor,
  normalizes raw output, writes `results/graphs/graph-i<NN>.json`.
- `graph_models.load(path) -> Graph` / `dump(graph, path)` — validation:
  unknown evidence/relation values, dangling edge endpoints, and version
  mismatch are **errors at load time**, not downstream surprises.
- `graph_metrics.compute(graph) -> Metrics` — degree, fan-in/out,
  betweenness, communities (greedy modularity), bridges, isolated
  components (networkx, ADR-5). Hub-vs-bottleneck adjudication outputs a
  `bottleneck_score = betweenness_rank × mandatory_path_ratio` plus rubric
  text — evidence for a human/agent verdict, never an automatic one.
- `graph_diff.diff(before, after) -> GraphDelta` — node/edge add/remove
  sets + metric deltas (max betweenness, community count, isolated count);
  feeds the fix loop's `IterationVerdict` and the Refactor Truth Dashboard
  (ADR-6).

## 3. Constraints, alternatives, rationale

| Decision | Alternatives | Why chosen |
|---|---|---|
| Normalize to our own contract | consume Graphify output directly | tool independence (ADR-4); validation at one boundary |
| networkx for metrics | igraph (faster), hand-rolled | pure-Python install via uv, ubiquitous, scale is small (≤10k nodes) |
| Graph files versioned per iteration | mutate one file | the before/after diff *is* the evidence of improvement (FR-2.7) |
| AST fallback in-repo | depend on Graphify availability | R1 (top risk) mitigated; same contract ⇒ zero downstream change |

Constraints: extractor runs through `ProcessRunner` only (timeout, audit);
all thresholds (community algorithm, caps) from config; files ≤150 lines —
models/metrics/diff/runner are separate modules by design.

## 4. Success criteria & test scenarios

- Contract: load(valid)→Graph; dangling edge / bad enum / version
  mismatch → typed errors (fixture JSONs).
- Metrics on a hand-built 10-node fixture with *known* answers: the
  planted hub has max betweenness; the planted bridge is detected; the
  orphan island is listed.
- Diff: removing the god node's edges shows in `GraphDelta` exactly;
  empty diff for identical graphs.
- Runner: fake extractor binary (shell stub) exercises subprocess path,
  timeout, and nonzero-rc handling without Graphify installed.
- **KPI (FR-2):** graph for the target repo builds reproducibly from a
  clean clone in one command; ≥1 re-graph per fix-loop iteration.

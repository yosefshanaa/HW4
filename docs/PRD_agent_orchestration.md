# PRD — Multi-Agent Orchestration

**Status:** approved 2026-06-12 · **Serves:** FR-5, ADR-1, ADR-7 ·
**Implements in:** `services/agents/{crew,roles,tools,context}.py` (Phase 8)

## 1. Description & theory

Agents here are **orchestration sugar over deterministic services** (PLAN
§3.1). Everything computable without an LLM — metrics, diffs, test runs,
graph builds — runs as plain Python; the LLM is reserved for interpreting
evidence, writing refactor plans, generating code edits, and careful
conclusions. This is the lecture's AST argument applied to agent design:
deterministic analysis is ~token-free, reproducible, and never
hallucinates; spending model tokens on it is waste and risk.

Five roles (CrewAI, ADR-1): **Orchestrator** (routes tasks, enforces
budget; logic lives in `fixloop/loop.py`, not in the agent), **RepoAgent**
(clone, graphify, target tests — mostly LLM-free), **GraphAnalyst**
(detector execution + evidence narrative; cheap model), **ArchitectFixer**
(refactor plan + edits; strong model, focused-subgraph context only),
**QAAgent** (tests, ruff, graph-diff verdict, stop conditions; rejects on
any red).

**Context packing** (Part-B edge placement): critical instructions at the
START of the prompt, the question/task at the END, retrieved material in
between; focused subgraph (ego radius ≤2, ≤`max_nodes`) instead of file
dumps; loop history compacted between iterations. Cap:
`retrieval.context_token_cap`.

## 2. Interfaces & I/O

- Handoffs are **typed payloads** (dataclasses → JSON): `AnalysisRequest`,
  `Finding`, `FixPlan`, `IterationVerdict`. No free-text blob handoffs —
  free text is where token waste and ambiguity live.
- Agent tools delegate to SDK services only (`tools.py` contains zero
  logic); every LLM call inside any agent flows through the Gatekeeper
  with purpose tag `agent.<role>.<task>` — per-role cost is a ledger
  query, not an estimate.
- Model tiers from config: GraphAnalyst/QAAgent narrative → `cheap`;
  ArchitectFixer → `strong` (ADR-3).

## 3. Constraints, alternatives, rationale

| Decision | Alternatives | Why chosen |
|---|---|---|
| CrewAI | LangGraph, AutoGen, hand-rolled | course-sanctioned, role/goal/backstory model fits 1:1; revisit-trigger in ADR-1 if it fights the loop |
| Loop logic in plain Python, not agent autonomy | full agent self-direction | determinism, testability, budget control; agent "decides" only within one bounded task |
| Typed payloads | conversational memory | replayable, diffable, unit-testable without LLM |
| Tools → SDK only | tools with direct service/API access | single gatekeeper choke point survives agent layer (NFR-2) |

## 4. Success criteria & test scenarios

- Unit (no LLM): tool functions call the right SDK methods (RecordingSdk);
  context packer respects START/END placement, node cap, and token cap on
  synthetic inputs; payload round-trips JSON.
- Integration (FakeTransport): one scripted crew pass over the mini_repo
  fixture produces a `FixPlan` from a planted finding, with every call
  ledgered under `agent.*` tags.
- **KPI (FR-5):** full loop run on the target repo with per-role token
  costs reported from the ledger; zero ungated LLM calls.

## As-built notes (T313, 2026-06-12)

- crewai 1.14.7 via uv (ADR-1 revisit trigger did not fire). Agent LLM
  traffic flows through `GatedCrewLLM(BaseLLM)` -> our `LlmClient` ->
  Gatekeeper; the bridge refuses anything but the gated client (tested).
- analyze flow as designed: deterministic spine (graph build, detectors
  — zero LLM) + LLM narratives; findings.json provably identical to the
  direct SDK path (test_agents::TestAnalyzeFlow).
- Compaction keeps the RULES block verbatim and reduced synthetic
  history ≥50% (T300); budget firewall halts narrative generation
  mid-flow without losing the deterministic results (T304).
- Live kickoff demo + target narratives pending ANTHROPIC_API_KEY.

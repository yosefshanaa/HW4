# PRD — EX04: Reverse Engineering of Graph Knowledge Systems with AI Agents

| Field | Value |
|---|---|
| Document | Product Requirements Document (PRD) |
| Project | EX04 — Graph-Based Reverse Engineering + Architectural-Bug-Fixing AI Agents |
| Course | Lecture 07 — Dr. Yoram Segal, June 2026 |
| Version | 1.00 |
| Status | DRAFT — requires approval before any code is written (mandatory workflow §2.5 of submission guidelines) |
| Authors | <student name + ID>, <student name + ID> |
| Sources | L07-Lesson-Summary.pdf, Part-A (Active Knowledge Architecture), Part-B (Graph Knowledge Architectures & Context Management), Part-C (Graph Literacy), software_submission_guidelines-V3.pdf |

---

## 1. Overview and Context

The job market no longer rewards a graduate who can only write lines of code. The course's thesis (L07 §1) is that a graduate must operate like a **software architect**: read, understand, and improve large codebases they have never seen, while spending **70%–95% fewer tokens** than naive LLM workflows.

This project applies that thesis end-to-end. We take an unfamiliar Python repository, convert it into a **knowledge graph** with Graphify (also spelled "Grphify" in course material), navigate it through **Obsidian**, perform **reverse engineering at the architecture level** (not line-by-line), and then build a **multi-agent AI system** (CrewAI / LangGraph) that detects and repairs **architectural bugs** (Single Point of Failure, bottlenecks, god nodes, overload paths) in a measurable, test-guarded improvement loop.

The deliverable is judged on two axes simultaneously:

1. **The assignment substance** (L07 §11 + Part-B final-project slide): graph build, reverse-engineering artifacts, agents, architectural fix loop, **measured token savings**, SKILL protocol with guardrails, before/after metrics.
2. **Engineering excellence** (submission guidelines V3): SDK architecture, API Gatekeeper, TDD with ≥85% coverage, Ruff zero violations, ≤150-line files, `uv`-only tooling, configuration-driven values, secrets hygiene, cost analysis, research notebook, prompt log.

A submission that nails one axis and ignores the other fails. This PRD therefore treats the guidelines as **hard requirements**, not decoration.

### 1.1 Critical reading of the assignment (what is actually being graded)

A critical analysis of the lecture summary reveals the implicit grading signals; we make them explicit so the project optimizes for them:

- **"Do not settle for documented code — the value is in extracting understanding"** (L07 §11.1.3). Reproducing an existing README is worth nothing. The architecture diagrams must be *derived from the graph* and must contain claims that are not in the repo's own docs.
- **"Who failed to save tokens must explain why"** (L07 §12). Token measurement is not optional garnish; it is a first-class experiment with a methodology, a dataset of questions, and a confusion-of-results analysis. An unmeasured claim of savings is a failing answer.
- **"Multiple agents are preferred over one"** (L07 §11 box). Orchestration of specialized agents is explicitly rewarded — it echoes the previous lecture's orchestration material.
- **"The architect does not work in real-time"** (L07 §10.2 box). Graphify must be re-run after every meaningful change; the loop "fix → re-graph → re-test → evaluate stop condition" is the actual product being graded, not the single fix.
- **"Creativity is the heart"** (L07 §12). The base is written for everyone; the differentiator is a self-initiated extension (see FR-9).
- **Careful inference language** (Part-C throughout). Conclusions must follow the EXTRACTED > INFERRED > AMBIGUOUS evidence scale and the 5-step responsible-inference pipeline. Overclaiming from a pretty graph is explicitly called out as an error.
- **"The choice of repository does not affect the grade; what you learn from it does"** (L07 §11.2). So repo choice is a risk-management decision, not a prestige decision.

## 2. Problem Statement

### 2.1 The user problem

A developer (or AI agent) confronted with an unknown codebase has two bad options today:

1. **Stuff everything into the context window** — hits the context bottleneck, suffers *Lost in the Middle* degradation, *context rot*, attention dilution, and enormous token cost (Part-B slides 2, 14–16).
2. **Naive RAG** — retrieves by vector similarity, which captures *topical similarity* but not *associative/structural relations* ("movie–popcorn–parking" problem, L07 §2.1); the window fills with near-relevant noise; signal-to-noise drops.

### 2.2 The systemic problem

Even when a human understands the code, there is no machine-checkable bridge between **planning documents (PRD/PLAN/TODO)** and **implementation** — gaps such as unimplemented requirements, undocumented modules, SPOFs and overload paths remain invisible (Part-A "Plan vs. Code" synthesis slide; Part-C traceability-gap pattern).

### 2.3 What this project delivers

A reproducible pipeline + agent crew in which:
- the repository becomes a queryable knowledge graph (structure layer),
- an LLM Wiki becomes curated semantic memory (meaning layer),
- SKILLs become controlled activation protocols with guardrails (action layer),
- and context engineering (focused subgraph retrieval, compaction, edge placement) keeps the agent's window short, clean, and mapped —
so that architectural questions are answered and architectural bugs are fixed with **dramatically fewer tokens** and **evidence-backed** conclusions.

## 3. Goals, KPIs, and Acceptance Criteria

### 3.1 Goals

| # | Goal |
|---|---|
| G1 | Reverse-engineer an unfamiliar Python repository at the architecture level using Graphify + Obsidian |
| G2 | Detect ≥2 architectural defects (SPOF / bottleneck / god node / traceability gap) with graph evidence |
| G3 | Automatically repair ≥1 architectural defect via an agent loop guarded by unit tests and a stop condition |
| G4 | Prove token savings of graph-guided retrieval vs. naive context loading, with measured numbers |
| G5 | Full compliance with submission guidelines V3 (engineering-excellence axis) |
| G6 | Deliver one creative extension beyond the base assignment |

### 3.2 Measurable KPIs

| KPI | Target | Measurement method |
|---|---|---|
| Token reduction (input tokens per architecture question, naive vs. graph-guided) | ≥70% reduction (course-stated band 70–95%); if not achieved, a written root-cause analysis is mandatory | Fixed question set (N≥10), identical model, tokens counted from API usage metadata; logged per call by the Gatekeeper |
| Answer quality under savings | ≥80% of graph-guided answers rated correct against a hand-built answer key | Rubric-scored evaluation table (correct / partially correct / wrong) |
| Architectural defects detected | ≥2, each with evidence chain (edge type, confidence, source_file) | GRAPH_REPORT + analysis doc cross-referenced to graph.json |
| Defects auto-fixed by agents | ≥1 merged fix | Diff + re-run Graphify shows structural improvement (e.g., reduced betweenness of god node); all unit tests pass |
| Improvement-loop iterations | ≤ configured max (default 3) with explicit stop condition evaluated each iteration | Loop log (results/loop_log.json) |
| Test coverage of OUR tool code | ≥85% (hard fail-under) | `uv run pytest --cov`, fail_under=85 |
| Ruff violations | 0 | `uv run ruff check` in CI/pre-submission checklist |
| Max file length | ≤150 code lines per file | Automated check script |
| Graph rebuild after each fix iteration | 100% of iterations | Loop log includes graph hash per iteration |
| Cost ceiling | ≤ configured budget (default: $10 total LLM spend) | Gatekeeper token/cost ledger |

### 3.3 Acceptance criteria (definition of done for the whole project)

1. `uv run hw4 --help` works on a clean machine after `uv sync` with zero manual steps beyond `.env` creation from `.env-example`.
2. `docs/` contains PRD.md, PLAN.md, TODO.md and **dedicated PRDs** for every central mechanism (§14 below), all approved before implementation commits.
3. Graph artifacts exist and are reproducible: `graph.json`, `graph.html`, `GRAPH_REPORT.md`, Obsidian vault with index.md, wiki/ pages, log.md.
4. Reverse-engineering deliverables exist: block diagram, OOP class scheme, community map, hub/bridge/SPOF analysis — each conclusion labeled by evidence level (EXTRACTED / INFERRED / AMBIGUOUS) with source_file references.
5. Agent crew runs end-to-end: analyze → detect → propose → fix → re-graph → re-test → stop-condition; all LLM calls pass through the Gatekeeper; every call is logged with token counts.
6. Token experiment table (before/after) is in the results notebook with plots; savings ≥70% or a serious explanation of why not.
7. At least one SKILL.md with frontmatter (name, description, allowed-tools), procedure, and guardrails (read-only / reversible / irreversible classification).
8. All quality gates green: coverage ≥85%, Ruff 0, file-size check, no hardcoded values, no secrets, uv.lock committed.
9. README.md is a full user manual (install, usage, examples, config guide, license).
10. Prompt engineering log documents the significant prompts used to build the project.
11. Final checklist (guidelines §17/§20.9) is filled in and every line is true.

## 4. Stakeholders and Target Users

| Stakeholder | Interest |
|---|---|
| Course staff (Dr. Segal) | Evidence of architectural thinking, token economics, agent orchestration, guideline compliance |
| Students (authors) | Grade; reusable portfolio asset ("work like an architect") |
| Secondary user persona | Any developer onboarding to an unknown Python repo who wants graph-guided, cheap, evidence-backed answers |
| AI agents (consumers) | The SDK and vault are designed to be consumed by agents, not only humans (L07 §3) |

## 5. Scope

### 5.1 In scope

- One target Python repository (selection criteria in §11 / ADR-2 in PLAN).
- Graphify pipeline execution, output parsing, and graph-literacy analysis (Part-C method).
- Obsidian vault construction: Portfolio → Domain → Project taxonomy; raw/ → wiki/ → index.md → log.md (LLM Wiki anatomy, Part-B slide 6).
- Reverse-engineering artifacts (block diagram, OOP scheme, communities, hubs/bridges, traceability paths).
- Multi-agent system (CrewAI or LangGraph — ADR-1) with ≥3 specialized agents + orchestration.
- Architectural bug detection (SPOF, bottleneck/god node, isolated cluster, docs-without-code traceability gap, suspected duplication) — each as a *hypothesis validated against source*, per Part-C.
- Automated fix loop with unit-test guard, Graphify re-run, stop condition.
- Token measurement experiment (before/after) + cost analysis.
- SKILL.md protocol + guardrails + skill-listing budget awareness.
- Our own tool implemented to guidelines V3 (SDK, Gatekeeper, TDD, config, uv, etc.).
- One creative extension (FR-9).

### 5.2 Out of scope (explicit, to prevent scope creep)

- Fixing *functional* bugs in the target repo (BugsInPy-style bug reproduction) — the assignment targets **architectural** defects; functional test suites of the target repo are used only as a safety net where feasible.
- Production deployment, CI/CD servers, Docker images (local-only per L07 §12 "all tools run locally").
- Training/fine-tuning models.
- GUI development; the interface is CLI (+ Obsidian as the visual layer).
- Multi-repo portfolio analysis (creative extension may touch it, but it is not a commitment).
- Real-time graph updates while typing — graph re-runs are batch, post-change (L07 §10.2).

### 5.3 Boundary risks called out now (critical)

- **BugsInPy is heavy**: it requires per-bug pinned environments and old Python versions; the lecturer explicitly said "if the installation gets complicated — don't insist, move to a simpler repo; the choice doesn't affect the grade" (L07 §11.2). We therefore treat BugsInPy as *one candidate*, not a default. Decision gate in TODO Phase 3 with a hard timebox.
- **Graphify availability/behavior** (originally under-specified). **Resolved (2026-06-15):** Graphify is the real, obtainable `safishamsi/graphify` tool, exporting node-link `graph.json`. We ship *both* backends — a tested Graphify ingestion adapter and the in-repo AST extractor (the reproducible default; pedagogically aligned — AST extraction is "pure logical analysis, ~free of tokens", L07 §4.1) — selectable via `graph.backend`. ADR-4 revised accordingly.

## 6. Functional Requirements

IDs are stable and referenced by PLAN and TODO. Priorities: **P0** = must (grade-critical), **P1** = should, **P2** = nice-to-have.

### FR-1 — Target repository acquisition (P0)
1.1 Clone a lecturer-approved GitHub repository OR a significant personal codebase (approval required, L07 §11.1.1).
1.2 Record provenance: URL, commit hash, license, LOC count, file count — in `docs/TARGET_REPO.md`.
1.3 The repo must be *unfamiliar* to the team (attestation in TARGET_REPO.md) — familiarity defeats the assignment's purpose.
1.4 Repo sanity gate: pure(ish) Python, 3k–40k LOC, importable, has some test suite or at least testable units; timeboxed setup (≤90 min) else fallback to a simpler candidate.

### FR-2 — Graph generation pipeline (P0)
2.1 Run Graphify on the target repo from CLI; persist `graph.json`, `graph.html`, `GRAPH_REPORT.md` under `results/graphs/<iteration>/`.
2.2 Configure scan scope (Vault entry decision — what to scan is a token-cost decision, L07 §5).
2.3 Parse graph.json into typed models: Node(id, type, label, source_file, community), Edge(src, dst, relation, evidence ∈ {EXTRACTED, INFERRED, AMBIGUOUS}, confidence).
2.4 Validate the three edge-evidence classes are preserved and queryable (L07 §6, Part-C evidence scale).
2.5 Compute graph metrics: degree, betweenness centrality, community partition, bridges, isolated clusters, fan-in/fan-out per node.
2.6 Re-runnable: a single command regenerates the graph for any iteration; outputs are versioned per iteration, never overwritten.
2.7 Graph diff: compare two iterations (nodes/edges added/removed, centrality deltas, modularity delta) — required to *prove* a refactor improved structure (Part-C "Diff" slide).

### FR-3 — Obsidian vault & LLM Wiki (P0)
3.1 Vault taxonomy: `00_Portfolio/10_Domains/20_Projects/30_Comparisons` (Part-A case study 1) — Project holds PRD, PLAN, TODO, code links.
3.2 LLM Wiki anatomy: `raw/` (unprocessed inputs), `wiki/` (short, linked Markdown knowledge pages), `index.md` (navigation hub read FIRST), `log.md` (ingestion traceability) — Part-B slide 6.
3.3 Note anatomy: frontmatter (type, status, project), one idea per note, wikilinks `[[...]]` to form the graph (Part-A note-anatomy slide).
3.4 Workflow rule encoded in the skill: question → index.md → 2–3 wiki pages → answer; never load the whole vault (Part-B guided-retrieval rule).
3.5 The vault must render correctly in Obsidian's graph view (manual verification + screenshots for README).

### FR-4 — Reverse-engineering analysis (P0)
4.1 Macro analysis: communities, bridges, hubs, isolated areas — "who against whom: where's the server, where's the client" (L07 §10).
4.2 Meso: per-community interpretation (what holds it together: domain, layer, docs, rationale) — community ≠ folder (Part-C).
4.3 Micro: per-claim validation — read relation → check confidence → open source_file (Part-C 5-step responsible inference).
4.4 Deliverables: system block diagram; OOP class scheme (key classes, inheritance/composition); data/control flow for ≥1 critical path read as a *path*, not a keyword (e.g., auth-style flow, Part-C path reading).
4.5 Hub vs. bottleneck adjudication for top-3 central nodes using degree + betweenness + relation types + rationale (Part-C god-node slide).
4.6 Every architectural claim carries an evidence label and a source pointer; AMBIGUOUS edges trigger manual checks, documented.
4.7 PRD-vs-implementation traceability check on the target repo if it has docs: which documented features lack code links, which modules lack documentation (L07 §10.2, Part-C docs-without-code).

### FR-5 — Multi-agent system (P0)
5.1 Framework: CrewAI or LangGraph (ADR-1 in PLAN decides; requirement is that the choice is justified, not which one).
5.2 Minimum agent roles (L07 §11 box "ריבוי סוכנים"):
  - **Repo Agent** — clone/update, environment, run Graphify, run tests.
  - **Graph Analyst Agent** — query graph.json, compute metrics, detect defect hypotheses, rank by evidence.
  - **Architect/Fixer Agent** — turn a confirmed defect into a refactor plan and code edits consistent with the graph.
  - **QA Agent** — run unit tests, run Ruff, evaluate stop condition, accept/reject the iteration.
5.3 Orchestrator coordinates the loop; agent-to-agent handoffs are structured (typed task payloads), not free text blobs.
5.4 Every agent's LLM access goes through OUR SDK → Gatekeeper (token logging, rate limits, retries, queueing). No direct API calls.
5.5 Agent context discipline: agents receive *focused subgraphs / wiki pages*, never the full repo; critical instructions placed at context edges; compaction between iterations (Part-B: position-aware design, /compact protocol).

### FR-6 — Architectural defect detection (P0)
6.1 Detectors (each emits: hypothesis, evidence chain, confidence, affected nodes):
  - SPOF / mandatory-path node (high betweenness + no alternative path).
  - God node / bottleneck (fan-in+fan-out outlier; distinguish healthy hub per Part-C criteria).
  - Isolated cluster (finding, not verdict — classify: intentional standalone / dead code / parser miss / semantic-only link, Part-C).
  - Docs↔code traceability gap (docs community without implements/tested_by edges).
  - Suspected duplication (semantically_similar_to ⇒ hypothesis only; verify purpose/usage/tests before recommending merge, Part-C exercise 3).
6.2 Output: `results/findings.json` + human-readable findings chapter with careful conclusion sentences ("the graph suggests…; source validation shows…").
6.3 At least one finding must be validated to EXTRACTED-level evidence before the fix loop may target it.

### FR-7 — Automated fix & improvement loop (P0)
7.1 Loop: select finding → plan refactor → apply code change → run target-repo unit tests (or our characterization tests) → re-run Graphify → graph diff → QA verdict → stop or iterate.
7.2 Stop conditions (config-driven, all logged): max_iterations (default 3), tests green, structural metric improved ≥ threshold, OR no further safe action (give-up with explanation).
7.3 Safety: every change on a branch; reversible (git); irreversible actions out of scope for autonomy (guardrails, Part-B slide 11).
7.4 Each iteration appends to `results/loop_log.json`: finding id, diff stats, test results, graph hash before/after, metric deltas, tokens spent.
7.5 If the target repo has no usable tests around the touched area, the Fixer must first generate characterization tests (red-green discipline applies to the fix too).

### FR-8 — Token economics experiment (P0)
8.1 Question dataset: ≥10 fixed architecture questions about the target repo (e.g., "what implements X flow?", "what breaks if module Y is removed?"), each with a hand-validated reference answer.
8.2 Condition A (baseline "before"): naive context — relevant files / skill descriptions stuffed into the prompt the way the lecture describes regular work (L07 §7).
8.3 Condition B ("after"): graph-guided — index-first retrieval, focused subgraph + 2–3 wiki pages.
8.4 Identical model + temperature + question phrasing across conditions; tokens (input/output) read from API usage metadata via the Gatekeeper ledger; N≥2 runs per question to average variance.
8.5 Analysis: per-question table, totals, % savings, answer-quality scoring, cost in $; plots in the results notebook; honest discussion of any question where savings failed (mandated by L07 §12).
8.6 Optional stretch (P2): accuracy-vs-noise curve — inject distractor context and show *Lost in the Middle*-style degradation (ties to Part-B research grounding).

### FR-9 — Creative extension (P1, but explicitly rewarded)
One self-chosen extension, proposed in PLAN, e.g.: Graphify on the org/team structure analogy (L07 §12 example), graph-driven test-gap heatmap, a `diff`-based "did the refactor help" dashboard, hyperedge modeling of requirement→module→test→WHY claims (Part-C), or automatic PRD-gap report generator. Selection recorded as ADR-6.

### FR-10 — SKILL protocol & guardrails (P0 — Part-B final-project step 2)
10.1 ≥1 `SKILL.md` with YAML frontmatter: name, routing description (short, discriminative — skill-listing budget awareness, Part-B slides 12–13), allowed-tools.
10.2 Body: when-to-use, procedure (identify task → load skill → read instructions → activate tool → return traceable result), warnings.
10.3 Guardrails section: read-only auto-allowed; reversible requires recovery path; irreversible (delete/send/publish) requires explicit human approval; note disable-model-invocation where relevant.
10.4 Skill refresh rule documented: re-read skill before sensitive/complex steps (skill drift, Part-B slide 17).

### FR-11 — Measurement & reporting (P0 — Part-B final-project step 3)
Metrics captured: source traceability rate (answers citing correct source_file), noise reduction (tokens), correct-file identification rate, correct-tool activation. Reported in the notebook + README summary.

### FR-12 — Agent evaluation: confusion matrix (P0 — L07 §13.2)
The detectors are a binary classifier, so they are scored as one. `hw4 evaluate` runs the deterministic detector spine over the `mini_repo` fixture and compares findings to a labeled, machine-readable answer key (planted defects + false-positive guards), emitting TP/FP/FN/TN and precision/recall/F1 to `results/CONFUSION_MATRIX.md`. The published result is the honest, un-tuned one (P=0.75, R=1.00); the single FP is explained, not hidden. Detailed in `docs/PRD_agent_evaluation.md`.

### FR-13 — Graph-guided debugging case (P0 — EX04 §5.3–5.4)
A concrete *functional* bug, found → root-caused → fixed → verified, distinct from the architectural fix loop (FR-7). `hw4 debug` runs a small planted-bug target (`tests/fixtures/buggy_case`: an HTTP byte-range off-by-one): it reproduces the bug (red), **localizes it via the graph** (the failing test's `tested_by` edge names the implicated module — no full-tree read), verifies the fix turns the spec green, and writes `results/BUG_ANALYSIS.md` (problem, root cause, research path, before/after, token comparison: 51% fewer tokens than naive whole-package reading). Verification is deterministic (red→green); the CrewAI analyst narrates the root cause on the spine. Small target chosen per the lecturer's §6 "prefer a small, well-explained case" guidance.

## 7. Non-Functional Requirements

| ID | Requirement | Source |
|---|---|---|
| NFR-1 | SDK-based architecture: ALL business logic behind an SDK class; CLI is a thin shell | Guidelines §4 |
| NFR-2 | API Gatekeeper: every external API call (LLM, GitHub) passes through one central gatekeeper with config-driven rate limits, FIFO queue, retries, full call logging | Guidelines §5 |
| NFR-3 | TDD red-green-refactor; every module has a test file; every public function ≥1 test; coverage ≥85% fail-under | Guidelines §6 |
| NFR-4 | Ruff zero violations with the prescribed rule set (E,F,W,I,N,UP,B,C4,SIM; line-length 100; py310 target) | Guidelines §7.1 |
| NFR-5 | No hardcoded config values; config/ JSON hierarchy + constants.py + .env for secrets; .env-example committed; .gitignore covers .env, *.pem, *.key, credentials.json | Guidelines §7.2–7.4 |
| NFR-6 | Versioning: code version.py, "version" key in every JSON config, startup validation; versions start at 1.00 | Guidelines §8.1 |
| NFR-7 | `uv` exclusively: uv sync/add/run/lock; pyproject.toml single source of truth; uv.lock committed; no pip/venv anywhere (code, docs, CI) | Guidelines §8.4 |
| NFR-8 | Files ≤150 code lines; split strategies per guidelines §3.2 | Guidelines §3.2 |
| NFR-9 | OOP, no code duplication (2+ copies ⇒ extract; 3+ try/except pattern ⇒ wrapper; 3+ identical methods ⇒ base/mixin) | Guidelines §4.2 |
| NFR-10 | Package organization: pyproject metadata, __init__.py exports + __version__, relative paths only | Guidelines §14 |
| NFR-11 | Docstrings on every function/class/module; comments explain WHY | Guidelines §3.3 |
| NFR-12 | Research artifacts: parameter study (e.g., scan-depth / max_iterations / retrieval-k sensitivity), Jupyter results notebook, quality visualizations | Guidelines §9 |
| NFR-13 | Cost: token & $ ledger, per-model table, optimization strategies; budget alert threshold in config | Guidelines §11 |
| NFR-14 | Prompt engineering log (`docs/PROMPTS.md`) | Guidelines §8.3 |
| NFR-15 | Git hygiene: meaningful commits, feature branches, PRs if pair-working, tags for v1.00 | Guidelines §8.2 |
| NFR-16 | Runs fully locally (lecture constraint); only LLM API is remote | L07 §12 |
| NFR-17 | Reproducibility: fixed seeds where applicable; pinned deps; documented model versions (model IDs are config values) | Guidelines + scientific hygiene |
| NFR-18 | Performance envelope: full pipeline (graph + analysis, excluding LLM latency) completes < 10 min on a laptop for the chosen repo size | Practicality (5-hour budget statement, L07 §12) |
| NFR-19 | Parallelism on the genuine bottleneck: I/O-bound wiki generation runs on a thread pool; shared state (gatekeeper rate windows, ledger) is lock-guarded; CPU-bound stages stay single-threaded; opt-out via config | Guidelines §15 (ADR-8) |

## 8. User Stories (selected)

- **US-1** As a developer new to repo X, I ask `hw4 ask "how does the request flow reach the database?"` and receive an answer citing graph nodes + source files, using a focused subgraph instead of the whole repo.
- **US-2** As an architect, I run `hw4 analyze` and receive a ranked findings list (SPOF, god nodes, gaps), each with evidence level and confidence, phrased cautiously.
- **US-3** As a maintainer, I run `hw4 fix --finding F-003` and the agent crew produces a branch with a refactor, green tests, and a graph diff proving reduced bottleneck centrality.
- **US-4** As a student, I run `hw4 experiment` and get the before/after token table + plots that prove (or honestly disprove) ≥70% savings.
- **US-5** As a grader, I open README.md and can reproduce everything with `uv sync && uv run hw4 ...` plus an `.env` file.

## 9. Assumptions

1. Graphify (course tool) is obtainable (`safishamsi/graphify`) and ingestible via our adapter; the AST backend remains the default so the pipeline never *depends* on it (ADR-4, revised 2026-06-15).
2. We have API access to at least one LLM (Anthropic Claude and/or other); model identity is configuration, not code.
3. Obsidian desktop is available for visual verification; the vault itself is plain Markdown (no proprietary lock-in).
4. The pair has ~5 focused hours for the core path (lecturer estimate) + overhead for guidelines compliance; budget honestly tracked (see PLAN §12). We critically note the 5-hour estimate covers the *core assignment*, not V3 excellence overhead; our plan budgets ~3× that and says so.
5. Lecturer approval is obtainable asynchronously for: target repo (if personal), fallback extractor (if needed).

## 10. Dependencies

| Dependency | Type | Risk if unavailable |
|---|---|---|
| Graphify CLI | Course tool | Fallback AST extractor (ADR-4) |
| Obsidian | Desktop app (free) | Vault still valid Markdown; screenshots impossible → use graph.html |
| CrewAI / LangGraph | PyPI | Choose the other (ADR-1) |
| LLM API key(s) | External service | Hard blocker → multiple-provider config |
| Target repo | GitHub | Pre-vetted candidate list (3 repos) in PLAN |
| networkx (metrics) | PyPI | Pure-python fallback algorithms |
| uv, pytest, pytest-cov, ruff | PyPI | None (mandatory) |

## 11. Constraints

- Local execution only; small/lean tools (L07 §12).
- Token budget ceiling enforced by Gatekeeper (config `budget.max_usd`).
- Timeline: lecture date June 2026; submission deadline per course site (placeholder — confirm). Internal freeze: all P0 done before any P1/P2.
- No secrets in repo, ever; submission zip must be re-scanned for secrets.
- The target repo's license must permit cloning and modification for educational use; license recorded.

## 12. Risks and Mitigations (critical register)

| # | Risk | L | I | Mitigation |
|---|---|---|---|---|
| R1 | BugsInPy environment quicksand burns hours | H | M | 90-min timebox; pre-vetted simpler candidates; lecturer explicitly permits switching |
| R2 | Graphify tool unavailable / undocumented flags / schema mismatch | M | H | **Retired 2026-06-15:** Graphify obtainable; tested node-link adapter + AST default both ship (ADR-4 revised). Schema drift handled at the single `Graph.from_dict` boundary |
| R3 | Token savings < 70% | M | H | This is survivable IF analyzed (lecture allows "explain why"); design experiment first, optimize retrieval (smaller subgraphs, index-first) before concluding |
| R4 | Agent fix breaks target repo silently (no tests around touched code) | M | H | Characterization tests written before fix; branch isolation; QA agent gate; revert path |
| R5 | LLM cost blowout from agent loops | M | M | Gatekeeper budget ceiling + per-iteration token cap; cached graph context; cheap model for drafts, strong model for final |
| R6 | Coverage 85% on agent code that calls LLMs | H | M | Strict DI + mocks for all LLM/tool calls; deterministic unit fixtures; LLM-touching code isolated in thin adapters |
| R7 | 150-line limit vs. complex services | M | L | Split strategy planned per module from the start (mixins, constants.py, models split) |
| R8 | Over-claiming from graph visuals (Part-C anti-pattern) → grade penalty | M | M | Enforce 5-step inference + evidence labels in findings template; peer-review each claim |
| R9 | Lost-in-the-middle inside our own agent prompts | M | M | Context engineering: instructions at edges, compaction between iterations, short windows (Part-B) |
| R10 | Pair time mismanagement; perfectionism on P2 items | M | M | P0/P1/P2 discipline in TODO; "stop and think" rule if >30 min stuck (lecturer hint) |
| R11 | Hebrew/RTL content in vault confusing tooling | L | L | Vault content in English; Hebrew only where pedagogically required |
| R12 | Submission packaging misses a mandatory artifact | M | H | Final checklist phase in TODO mirrors guidelines §20.9 line-by-line |

## 13. Timeline and Milestones (summary — detail in PLAN §12)

| Milestone | Content | Exit gate |
|---|---|---|
| M0 | Docs approved (PRD/PLAN/TODO + dedicated PRDs) | Lecturer/self sign-off; zero code before this |
| M1 | Skeleton + quality gates green on empty SDK | uv, ruff, pytest, coverage pipeline runs |
| M2 | Target repo locked + Graphify produces graph artifacts | graph.json parsed & validated |
| M3 | Vault + wiki + reverse-engineering artifacts | Diagrams + evidence-labeled findings draft |
| M4 | Baseline token experiment (Condition A) recorded | Ledger shows N≥10 questions measured |
| M5 | Agent crew MVP (analyze→detect) | findings.json generated by agents |
| M6 | Fix loop end-to-end with stop condition | ≥1 fix, tests green, graph diff improved |
| M7 | Condition B + comparison + notebook + cost analysis | KPI table complete |
| M8 | Polish, SKILL.md, README, prompt log, final checklist, package | Every checklist line true |

## 14. Dedicated PRDs (mandatory per guidelines §2.3)

To be authored in Phase 2 (each ≤2 pages, with I/O spec, constraints, alternatives, test scenarios):

1. `docs/PRD_graph_pipeline.md` — Graphify execution, parsing, metrics, diff.
2. `docs/PRD_agent_orchestration.md` — roles, framework, handoffs, context discipline, loop control.
3. `docs/PRD_defect_detection.md` — detector algorithms, evidence model, thresholds.
4. `docs/PRD_fix_loop.md` — refactor planning, safety, stop conditions, characterization tests.
5. `docs/PRD_token_experiment.md` — A/B methodology, question dataset, scoring rubric, statistics.
6. `docs/PRD_gatekeeper.md` — rate limiting, queueing, retry, ledger schema.
7. `docs/PRD_agent_evaluation.md` — confusion-matrix scoring of the detector spine vs the planted answer key (L07 §13.2; added 2026-06-15).

## 15. Open Questions (to resolve before M2 — tracked in TODO Phase 2)

1. ~~Exact Graphify distribution channel + version we must use (course repo? pip? Claude-integrated?). → blocks ADR-4 decision.~~ **Resolved 2026-06-15:** Graphify is [`safishamsi/graphify`](https://github.com/safishamsi/graphify) (npm / graphify.net), exporting node-link `graph.json`. We ship a real ingestion adapter (`extractor/graphify.py`, selectable via `graph.backend`) but keep the AST backend as the reproducible default — ADR-4 revised, see PLAN.md.
2. Submission deadline + format (zip naming convention appears to be `<id1>_<id2>_hw4.zip` based on prior assignments — confirm).
3. Is modifying the target repo in-place acceptable, or must fixes live as patch files? (We assume branch-in-clone is fine.)
4. Which LLM provider(s) are sanctioned for the experiment (cost reimbursement? free tier?).
5. Does the grader require Obsidian screenshots, the vault itself, or both? (We deliver both.)

---
*End of PRD v1.00. No implementation work may begin until this document and PLAN.md/TODO.md are reviewed and the dedicated PRDs are drafted (guidelines mandatory workflow §2.5).*

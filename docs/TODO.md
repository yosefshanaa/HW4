# TODO — EX04: Task Tracking

| Field | Value |
|---|---|
| Document | Task list (TODO) |
| Project | EX04 — Graph-Based Reverse Engineering + Architectural-Bug-Fixing AI Agents |
| Version | 1.00 |
| Parents | docs/PRD.md v1.00, docs/PLAN.md v1.00 |

**Legend** — Status: `[ ]` not started · `[~]` in progress · `[x]` done · `[!]` blocked.
Priority: **P0** grade-critical (assignment core ∪ mandatory guideline gates) · **P1** should · **P2** stretch.
Owner: `A` / `B` / `AB` (pair) — assign at phase kickoff; default `AB`.
Every task's definition-of-done is its verifiable phrasing; phase-level DoD is the exit gate (PLAN §12).
Rule: if stuck >30 min on any single task — stop, think, descope or switch (L07 §12).

---

## Phase 0 — Environment & Tooling (Milestone M1)
**Phase DoD:** clean machine can run `uv sync` + quality-gates script green on the empty skeleton; no pip/venv anywhere.

- [x] T001 (P0) Verify Python ≥3.10 available locally; record exact version in README prerequisites
- [x] T002 (P0) Install `uv`; verify `uv --version`; document install command for graders
- [x] T003 (P0) Confirm rule with both teammates: NO `pip install`, `python -m`, `venv`, `virtualenv` anywhere — code, docs, scripts, muscle memory
- [x] T004 (P0) `git init` repository in HW4 root; set user.name/user.email
- [x] T005 (P0) Create `.gitignore`: `.env`, `*.pem`, `*.key`, `credentials.json`, `workspace/`, `__pycache__/`, `.coverage`, `htmlcov/`, `.ruff_cache/`, `results/logs/`
- [x] T006 (P0) Create `.env-example` with dummy values for every secret we anticipate (LLM key(s)); commit it
- [ ] T007 (P0) Create local `.env` from example with real key; verify it is NOT tracked (`git status`)
- [x] T008 (P0) `uv init` / author `pyproject.toml`: name `hw4`, version `1.00`, description, authors, license, `requires-python >=3.10`
- [x] T009 (P0) `uv add` runtime deps: networkx, typer (or argparse stdlib — decide now), pydantic (or dataclasses — decide now), pyyaml, anthropic (or chosen provider SDK), crewai
- [x] T010 (P0) `uv add --dev` dev deps: pytest, pytest-cov, ruff
- [x] T011 (P0) Commit `uv.lock`; verify `uv sync` from scratch in a temp clone reproduces env
- [x] T012 (P0) Configure `[tool.ruff]` per guidelines §7.1: line-length 100, target py310, select E,F,W,I,N,UP,B,C4,SIM, ignore E501
- [x] T013 (P0) Configure `[tool.coverage.run]` source=["src"], omit main.py/tests/gui; `[tool.coverage.report] fail_under = 85`
- [x] T014 (P0) Configure `[tool.pytest.ini_options]`: testpaths, addopts `--cov=src --cov-report=term-missing`
- [x] T015 (P0) Verify `uv run ruff check` runs (passes trivially on empty src)
- [x] T016 (P0) Verify `uv run pytest` runs (collects zero tests without error)
- [x] T017 (P0) Create `scripts/check_gates.py` skeleton: runs ruff, pytest+cov, file-length check, hardcode grep, secrets grep; exits nonzero on any failure
- [x] T018 (P0) Implement file-length checker: fail if any `src/**/*.py` exceeds 150 code lines (blank + comment lines excluded per guidelines §3.2)
- [x] T019 (P1) Implement hardcode grep: flag `http(s)://` literals, numeric rate/timeout assignments, `api_key =` patterns inside src/
- [x] T020 (P1) Implement secrets grep: scan tracked files for key-like strings (`sk-`, `AKIA`, long base64) — run also at packaging time
- [x] T021 (P0) Create directory skeleton exactly as PLAN §1.3 (src/hw4/{sdk,services,shared,services/detectors,services/agents,services/fixloop,services/experiment}, tests/{unit,integration}, config, docs, vault, data, results, notebooks, workspace)
- [x] T022 (P0) Add `__init__.py` to every package dir; root `src/hw4/__init__.py` exports `__version__`
- [ ] T023 (P0) Verify Obsidian desktop installed; create empty test vault; confirm graph view renders
- [x] T024 (P0) Verify git CLI + GitHub access (clone over https) from this machine
- [x] T025 (P1) Decide CLI framework (typer vs argparse) — record one-line note in PLAN §1.3 margin; stdlib argparse acceptable to cut deps
- [x] T026 (P1) Set up pre-commit habit (manual or hook): run check_gates before every commit
- [x] T027 (P1) Create `Makefile`-style task runner OR document `uv run` invocations in README dev section (no make dependency required)
- [ ] T028 (P2) Configure editor (ruff plugin, 100-col ruler) for both teammates
- [x] T029 (P0) First commit: skeleton + tooling, message "chore: project skeleton + quality gates (v1.00)"
- [x] T030 (P0) Smoke-test `uv run python -c "import hw4"` succeeds

## Phase 1 — Shared Infrastructure & SDK Skeleton (Milestone M1)
**Phase DoD:** Hw4Sdk facade + gatekeeper + config + ledger + process runner implemented, unit-tested, coverage ≥85% on shared/, ruff clean.

### constants & version
- [x] T031 (P0) `constants.py`: Enums `EdgeEvidence{EXTRACTED,INFERRED,AMBIGUOUS}`, `FindingKind{SPOF,GOD_NODE,ISOLATED,TRACE_GAP,DUPLICATION}`, `StopReason{MAX_ITERATIONS,GOAL_METRIC_REACHED,TESTS_GREEN_NO_MORE_FINDINGS,BUDGET_EXCEEDED,NO_SAFE_ACTION}`
- [x] T032 (P0) Tests for constants: enum membership, string round-trip
- [x] T033 (P0) `shared/version.py`: `__version__ = "1.00"`; helper `assert_config_compatible(cfg_version)`
- [x] T034 (P0) Test version compatibility check (match, mismatch raises)

### config
- [x] T035 (P0) Write `config/setup.json` v1.00: paths (workspace, results, vault), models{cheap,strong}, retrieval{k, ego_radius, max_nodes}, loop{max_iterations, metric_improvement_threshold}, experiment{n_questions_min, repetitions, temperature}, budget{max_usd, warn_usd}
- [x] T036 (P0) Write `config/rate_limits.json` v1.00 per guidelines §5.2 schema (default service: rpm 30, rph 500, concurrent 5, retry_after 30, max_retries 3, queue_depth)
- [x] T037 (P0) Write `config/logging_config.json` (level, format, file targets)
- [x] T038 (P0) TDD `shared/config.py`: load JSON files, merge env overrides, typed getters with defaults, fail on missing mandatory keys
- [x] T039 (P0) config.py validates `"version"` key of every JSON at startup against compatibility rule (NFR-6)
- [x] T040 (P0) Tests: valid load, missing file, missing version, env override, default fallback (≥5 cases)
- [x] T041 (P0) Secrets: config exposes `get_secret(name)` reading ONLY from env; test that secrets never appear in config files
- [ ] T042 (P1) Negative test: constructing config with hardcoded-looking override logs a warning (guard habit)

### logging & process runner
- [x] T043 (P0) TDD `shared/logging_setup.py`: structured jsonl logger factory writing to results/logs/<run-id>.jsonl + console
- [x] T044 (P0) Tests: log record schema, file creation, level filtering
- [x] T045 (P0) TDD `shared/process_runner.py`: run subprocess with timeout, captured output, raise-or-return policy, structured log of cmd/duration/rc
- [x] T046 (P0) Tests: success, nonzero rc, timeout kill, output capture (use `echo`/`false` portable commands or python -c)
- [x] T047 (P1) ProcessRunner records every invocation to run log (deterministic audit trail for graphify/pytest/git calls)

### gatekeeper + ledger + llm client
- [x] T048 (P0) TDD `shared/ledger.py`: append-only CSV/JSONL ledger — fields: ts, purpose_tag, model, input_tokens, output_tokens, cost_usd, latency_ms, status
- [x] T049 (P0) Ledger cost computation from per-model price table in config (prices are CONFIG, not code)
- [x] T050 (P0) Tests: append, totals by purpose tag, budget summation, file rotation safety
- [x] T051 (P0) TDD `shared/gatekeeper.py` class `ApiGatekeeper(config)` with `execute(call, *, purpose_tag)` per guidelines §5.1 interface
- [x] T052 (P0) Gatekeeper: rate-limit check before execution (rpm/rph windows from rate_limits.json)
- [x] T053 (P0) Gatekeeper: FIFO queue when saturated — request waits, never dropped; configurable max queue depth with backpressure warning
- [x] T054 (P0) Gatekeeper: retry transient failures (max_retries, retry_after backoff from config)
- [x] T055 (P0) Gatekeeper: every call logged to ledger; budget ceiling check — raise `BudgetExceeded` when cumulative cost ≥ budget.max_usd
- [x] T056 (P0) Gatekeeper: `get_queue_status()` returns depth + stats
- [x] T057 (P0) Tests: limit enforcement (time-mocked), queue order, retry then success, retry exhaustion, budget stop, logging side-effect (≥8 cases)
- [x] T058 (P0) TDD `shared/llm_client.py`: provider-agnostic interface `complete(messages, model_tier) -> (text, usage)`; Anthropic adapter; usage tokens read from API response metadata
- [x] T059 (P0) llm_client is ONLY callable through gatekeeper.execute (enforce by constructor wiring; test that direct use without gatekeeper raises)
- [x] T060 (P0) Tests with fake transport: success, usage extraction, provider error mapping, model-tier resolution from config
- [ ] T061 (P1) Second-provider adapter stub behind same interface (compile-time proof of swappability; can be NotImplemented)

### SDK facade & CLI
- [x] T062 (P0) TDD `sdk/sdk.py` class `Hw4Sdk(config)`: method stubs `build_graph()`, `build_vault()`, `analyze()`, `ask(question)`, `fix(finding_id)`, `run_experiment()`, `report()` — each delegates to services; NO business logic in CLI/agents (NFR-1)
- [x] T063 (P0) Tests: facade wires services with shared gatekeeper/config instances (constructor injection)
- [x] T064 (P0) `main.py` CLI: subcommands graph/vault/analyze/ask/fix/experiment/report/gates — thin parse→SDK calls only
- [x] T065 (P0) CLI smoke tests: `--help`, unknown command error, each subcommand reaches SDK stub (mocked)
- [x] T066 (P0) Wire `uv run hw4` entry point in pyproject `[project.scripts]`; verify it executes
- [x] T067 (P0) Run check_gates: ruff 0, coverage ≥85% on implemented modules, file lengths OK
- [x] T068 (P0) Commit Phase 1, tag `m1-skeleton`
- [x] T069 (P1) Review pass: any duplicated logic across shared modules? extract now (NFR-9)
- [x] T070 (P1) Docstrings audit: every public function/class/module has docstring explaining WHY (NFR-11)
- [ ] T071 (P1) `__init__.py` exports audit: `__all__` defined in sdk and shared packages
- [ ] T072 (P2) Type-check pass with mypy/pyright locally (not a gate, hygiene only)
- [x] T073 (P0) Verify relative imports/paths only; no absolute filesystem paths in code (paths come from config) (NFR-10)
- [x] T074 (P1) Start `docs/PROMPTS.md` with prompts used so far for scaffolding (NFR-14)
- [x] T075 (P1) Record any deviation discovered between PLAN file map and reality — update PLAN (living doc, version bump note)

## Phase 2 — Documentation Suite & Approvals (Milestone M0 — gates implementation)
**Phase DoD:** PRD/PLAN/TODO reviewed by both teammates; all 6 dedicated PRDs drafted; open questions dispatched to lecturer.

- [ ] T076 (P0) Both teammates read L07 summary + Part-A/B/C + guidelines end-to-end (no skimming) — initial each section
- [ ] T077 (P0) Review docs/PRD.md v1.00 line-by-line; resolve TODO-markers; bump to approved status
- [ ] T078 (P0) Review docs/PLAN.md v1.00; sanity-check file map vs 150-line budget; approve
- [ ] T079 (P0) Review this TODO; assign owners per phase; mark P2 items we pre-emptively drop if time-poor
- [ ] T080 (P0) Send lecturer the open questions (PRD §15): Graphify distribution, deadline/zip format, in-place fix policy, sanctioned LLM providers
- [x] T081 (P0) Write `docs/PRD_graph_pipeline.md`: Graphify invocation contract, graph.json normalization spec, metrics list, diff semantics, I/O, test scenarios
- [ ] T082 (P0) Write `docs/PRD_agent_orchestration.md`: roles, payload schemas, context-packing rules, loop interaction, failure modes
- [x] T083 (P0) Write `docs/PRD_defect_detection.md`: per-detector algorithm, thresholds (config), evidence-chain format, false-positive policy
- [ ] T084 (P0) Write `docs/PRD_fix_loop.md`: planner I/O, applier safety (branch, revert), characterization tests, stop-condition truth table
- [ ] T085 (P0) Write `docs/PRD_token_experiment.md`: full methodology (PLAN §4), scoring rubric, validity threats, analysis plan
- [x] T086 (P0) Write `docs/PRD_gatekeeper.md`: rate/queue/retry/ledger spec + sequence diagram
- [ ] T087 (P0) Cross-check each dedicated PRD contains: detailed description+theory, I/O expectations, constraints+alternatives+chosen rationale, success criteria+test scenarios (guidelines §2.3)
- [ ] T088 (P0) Approve all dedicated PRDs (initials + date in header) — implementation of that mechanism may not start before its PRD is approved (guidelines §2.5)
- [ ] T089 (P1) Create `docs/TARGET_REPO.md` template: provenance fields, unfamiliarity attestation, license, decision trail
- [ ] T090 (P1) Create findings template `results/FINDINGS.template.md` with Part-C careful-language formula: source → qualified conclusion → confidence → finding → relation type
- [ ] T091 (P1) Create `data/questions.template.yaml` schema: id, tier(locate/path/impact), question, reference_answer, reference_files[]
- [ ] T092 (P0) Define answer-scoring rubric doc (correct/partial/wrong + citation correctness criteria, blind-scoring protocol)
- [ ] T093 (P1) Decide vault language policy (English; Hebrew only where pedagogically needed) — note in PLAN
- [ ] T094 (P1) Add ADR index section check: ADR-1..7 present in PLAN, each with revisit-trigger
- [ ] T095 (P0) Re-read Part-C 5-step inference pipeline; paste it verbatim into FINDINGS.template.md as mandatory section headers (Observation/Relation/Confidence/Context/Source-validation)
- [ ] T096 (P1) Define diagram tooling for block diagram + class scheme (mermaid in markdown, exported PNG to assets/) — verify mermaid renders
- [ ] T097 (P1) Define loop_log.json schema doc (iteration, finding_id, diff_stats, tests, graph_hash_before/after, metric_deltas, tokens, verdict, stop_reason)
- [ ] T098 (P1) Define findings.json schema doc (id, kind, nodes[], evidence_chain[], confidence, status{hypothesis,validated,rejected,fixed,blocked})
- [ ] T099 (P2) Glossary page in vault: hub, bridge, community, betweenness, SPOF, evidence classes (reused later as wiki seed)
- [ ] T100 (P0) Commit docs suite; tag `m0-docs-approved`
- [x] T101 (P1) Log doc-authoring prompts to PROMPTS.md
- [ ] T102 (P1) Calendar check: confirm submission deadline; back-plan milestones M2–M8 with dates; write into PLAN §12
- [ ] T103 (P2) Set up shared scratchpad for pair notes (decisions made verbally must land in ADRs same day)
- [ ] T104 (P0) Verify no implementation code (beyond Phase-1 infra) exists before this gate — honest check
- [ ] T105 (P1) Risk review: walk PRD §12 register; anything new? add R13+ if so

## Phase 3 — Target Repository Selection & Acquisition (Milestone M2 start)
**Phase DoD:** TARGET_REPO.md locked: one repo chosen, cloned into workspace/, provenance + license recorded, sanity gate passed.

- [ ] T106 (P0) Build candidate shortlist (≥3 repos) meeting criteria: pure(ish) Python, 3k–40k LOC, pytest suite present, imports on py3.10+, permissive license, genuinely unfamiliar to both teammates
- [ ] T107 (P0) Candidate vetting table: LOC (cloc/`wc`), file count, test command, install friction estimate, license — 15 min per candidate max
- [ ] T108 (P0) BugsInPy timebox attempt (≤90 min hard stop): clone framework, try ONE project env setup; if friction → abandon without guilt (lecturer-sanctioned, L07 §11.2)
- [ ] T109 (P0) Decision meeting: pick primary repo + named fallback; record decision trail + reasons in TARGET_REPO.md (ADR-2 instantiation)
- [ ] T110 (P0) If personal codebase chosen instead — obtain explicit lecturer approval BEFORE proceeding (L07 §11.1.1); archive the approval message
- [ ] T111 (P0) TDD `services/repo_service.py`: clone(url, dest), checkout(commit), provenance() → {url, commit_hash, branch, license, loc, files}
- [ ] T112 (P0) repo_service: LOC counter (code lines per file, totals) — reused later by file-length checks on target analysis
- [ ] T113 (P0) Tests: clone into tmp (use local fixture repo, not network), provenance fields, checkout behavior, error on dirty workspace
- [ ] T114 (P0) Clone chosen repo into `workspace/target/` (gitignored); pin to specific commit hash
- [ ] T115 (P0) Record provenance into TARGET_REPO.md: URL, commit, license text reference, LOC, file count, date
- [ ] T116 (P0) Unfamiliarity attestation signed by both teammates in TARGET_REPO.md
- [ ] T117 (P0) Verify target test suite runs: `uv run` (or repo's own runner) — record baseline pass/fail counts + runtime
- [ ] T118 (P0) If target tests cannot run at all: document why + plan characterization-test strategy (feeds FR-7.5); reconsider fallback repo if coverage is zero around everything
- [ ] T119 (P1) Snapshot target repo metrics baseline: top-10 largest files, package layout sketch (1 paragraph, pre-graph naive impression — useful contrast for the report)
- [ ] T120 (P1) Identify target repo's own docs (README/docs/) for FR-4.7 traceability check later
- [ ] T121 (P1) License compliance note: confirm educational modification permitted; cite clause
- [ ] T122 (P0) Define `workspace/` lifecycle: never committed; regeneration command documented in README
- [ ] T123 (P1) Create tiny synthetic fixture repo under `tests/fixtures/mini_repo/` (≤10 files: 2 packages, planted god-node module, an orphan module, a docs file referencing nonexistent module) — powers ALL unit/integration tests without network
- [ ] T124 (P0) Tests using mini_repo: repo_service provenance + LOC on fixture
- [ ] T125 (P1) Mini_repo includes a tiny pytest suite (3 tests) so fix-loop integration tests can run real pytest cheaply
- [ ] T126 (P1) Commit Phase 3 (without workspace/)
- [ ] T127 (P1) PROMPTS.md update
- [ ] T128 (P2) Note interesting first impressions/questions about target for the question dataset (Phase 7 seed)
- [ ] T129 (P0) Gate check: ruff/coverage/length still green
- [ ] T130 (P1) Update TODO statuses; flag slippage vs PLAN §12 budget

## Phase 4 — Graph Generation Pipeline (Milestone M2)
**Phase DoD:** `uv run hw4 graph` produces versioned graph artifacts for iteration 0; graph.json parsed into validated models; metrics computed; ADR-4 decision (real Graphify vs fallback) closed.

### Graphify discovery spike (timeboxed 2h)
- [ ] T131 (P0) Locate Graphify distribution (course materials / lecturer link / package index); record exact name+version
- [ ] T132 (P0) Install per its docs (via uv tooling if Python; document precisely)
- [ ] T133 (P0) Run Graphify on mini_repo fixture first; inspect actual outputs (graph.json? graph.html? GRAPH_REPORT.md? hot.md/index.md?)
- [ ] T134 (P0) Document real output schema + flags in PRD_graph_pipeline.md (replace assumptions with facts; diff vs our contract)
- [ ] T135 (P0) Decide scan scope config for target (which dirs; vault entry decision = token decision, L07 §5)
- [ ] T136 (P0) ADR-4 gate: if tool unusable by spike end → activate fallback AST extractor; notify lecturer; record decision
- [ ] T137 (P0) (If fallback) TDD AST backend: module/class/function nodes; import+call EXTRACTED edges; same graph.json contract
- [ ] T138 (P0) (If fallback) heuristic doc-mention edges marked INFERRED; anything regex-fuzzy marked AMBIGUOUS — never silently upgraded
- [ ] T139 (P1) (If fallback) docstring/TODO/WHY comments extracted as rationale nodes (keeps Part-C rationale layer alive)

### runner + models
- [ ] T140 (P0) TDD `services/graph_runner.py`: invoke backend via ProcessRunner; output dir `results/graphs/<iteration>/`; never overwrite previous iterations (FR-2.6)
- [ ] T141 (P0) graph_runner records: backend id+version, command, duration, scan scope, content hash of graph.json
- [ ] T142 (P0) Tests: output versioning, hash stability on identical input, failure surfaces cleanly
- [ ] T143 (P0) TDD `services/graph_models.py`: Node/Edge/Graph dataclasses per PLAN §2.1 contract; `from_json`/`to_json`; schema validation with precise error messages
- [ ] T144 (P0) Normalizer: map real Graphify output fields → our contract; unknown relation types preserved verbatim + logged
- [ ] T145 (P0) Evidence enum enforced on every edge; missing evidence → AMBIGUOUS + warning (conservative default, Part-C)
- [ ] T146 (P0) Tests: round-trip, malformed json, unknown fields tolerated, evidence default, large-graph load time sanity
- [ ] T147 (P0) Graph convenience queries: neighbors(), ego_subgraph(node, radius, cap), nodes_by_type(), edges_by_evidence()
- [ ] T148 (P0) Tests for queries incl. cap behavior (retrieval depends on caps)

### metrics + diff
- [ ] T149 (P0) TDD `services/graph_metrics.py`: degree, fan-in/out, betweenness (networkx), communities (greedy modularity), bridges, isolated components
- [ ] T150 (P0) Bottleneck rubric: betweenness rank × mandatory-path ratio + relation-type profile → structured evidence object (NOT a verdict) (Part-C)
- [ ] T151 (P0) Tests on planted fixture graph: god node ranks top betweenness; orphan detected; communities ≥2; bridge found
- [ ] T152 (P0) Metrics snapshot persisted: `results/graphs/<iter>/metrics.json` (versioned)
- [ ] T153 (P0) TDD `services/graph_diff.py`: nodes/edges added/removed, per-node centrality deltas, modularity delta, isolated-count delta
- [ ] T154 (P0) Diff verdict helper: `improved/regressed/neutral` vs config thresholds — feeds QA agent + dashboard
- [ ] T155 (P0) Tests: synthetic before/after pairs for each verdict class
- [ ] T156 (P1) Guard: diff must detect "bottleneck merely renamed/moved" (same topology, new node id) — at minimum document the limitation honestly if not solved

### execute on target
- [ ] T157 (P0) Run pipeline on TARGET repo → iteration 0 artifacts under results/graphs/0/
- [ ] T158 (P0) Validate parsed graph: node/edge counts plausible vs LOC; spot-check 10 random EXTRACTED edges against source files (open the file, confirm the call/import exists)
- [ ] T159 (P0) Spot-check 5 INFERRED edges — classify each as plausible/wrong; record precision impression in FINDINGS notes
- [ ] T160 (P0) List all AMBIGUOUS edges; triage which require human check during analysis (Part-C: ambiguous = stop flag)
- [ ] T161 (P0) Open graph.html (or our rendering) — visual sanity: communities visible, no rendering explosion
- [ ] T162 (P0) Read GRAPH_REPORT.md (if produced) — note claims to verify, never trust as-is (Part-C: report gives narrative, JSON gives evidence)
- [ ] T163 (P0) Wire `Hw4Sdk.build_graph()` + CLI `hw4 graph --iteration N`; integration test on mini_repo
- [ ] T164 (P1) Record graph stats table (nodes by type, edges by relation, evidence distribution) → goes in README + notebook
- [ ] T165 (P1) Time the full pipeline; verify NFR-18 (<10 min non-LLM)
- [ ] T166 (P1) Re-run pipeline twice; confirm deterministic hash (or document nondeterminism source)
- [ ] T167 (P0) Gate check + commit; tag `m2-graph`
- [ ] T168 (P1) PROMPTS.md update
- [ ] T169 (P2) Performance: cache parsed Graph object keyed by file hash (only if load >2s)
- [ ] T170 (P1) Update PRD_graph_pipeline.md with as-built facts (doc drift kills credibility)
- [ ] T171 (P1) File-length audit on new modules; split if any >130 lines (early margin)
- [ ] T172 (P1) Effort tracking update vs PLAN budget

## Phase 5 — Obsidian Vault & LLM Wiki (Milestone M3 start)
**Phase DoD:** vault opens in Obsidian, taxonomy + index-first navigation works, wiki pages generated for key entities, retrieval returns focused context under caps.

- [ ] T173 (P0) TDD `services/vault_builder.py`: create taxonomy `00_Portfolio/10_Domains/20_Projects/30_Comparisons` + project folder with `raw/`, `wiki/`, `index.md`, `log.md` (Part-A case study; Part-B anatomy)
- [ ] T174 (P0) Portfolio/Domain/Project notes carry frontmatter (type/status/project) and a one-line routing title (titles are the graph fuel, L07 §5)
- [ ] T175 (P0) Tests: structure creation idempotent, frontmatter valid YAML, re-run does not clobber human edits (guard or versioned sections)
- [ ] T176 (P0) TDD `services/wiki_writer.py`: generate wiki page per major entity (top-N central modules/classes, each community, each architectural decision found) — short pages, one concept each, wikilinked
- [ ] T177 (P0) Wiki page template: Summary (≤3 sentences), Evidence (relations + confidence + source_file), Links (`[[...]]`), Open-questions
- [ ] T178 (P0) Page generation uses LLM (cheap tier) THROUGH gatekeeper with purpose tag `wiki.gen`; deterministic fields (evidence lists) injected programmatically, not asked from the LLM
- [ ] T179 (P0) Tests with mocked LLM: template fill, wikilink integrity (no links to nonexistent pages), length cap enforcement
- [ ] T180 (P0) `index.md` generator: compact navigation map — communities → key pages; reads in <1 screen (index-first rule, Part-B)
- [ ] T181 (P0) `log.md` appender: every ingestion/update logged (what, when, source, tool) — traceability (Part-B)
- [ ] T182 (P0) Tests: index regeneration stable order, log append-only
- [ ] T183 (P0) Copy/lin raw inputs into `raw/`: GRAPH_REPORT.md, provenance, target README snapshot (raw vs wiki separation)
- [ ] T184 (P0) Run vault build on target analysis; open in Obsidian; verify graph view shows hub-and-spoke around index + community clusters
- [ ] T185 (P0) Capture 3+ screenshots (vault graph view, a wiki page, index.md) → assets/ for README
- [ ] T186 (P0) TDD `services/retrieval.py`: question → index match → ego-subgraph (radius/cap from config) + top wiki pages (2–3) → ContextBundle
- [ ] T187 (P0) ContextBundle assembly enforces edge placement: instructions first, question last, evidence in middle kept SHORT (Part-B position-aware)
- [ ] T188 (P0) ContextBundle reports its own token estimate (tokenizer estimate OK here — it's a budget guard, not the experiment measurement)
- [ ] T189 (P0) Tests: matching, caps respected, bundle structure, token-estimate guard trips on oversize
- [ ] T190 (P0) `Hw4Sdk.build_vault()` + CLI `hw4 vault`; integration test on mini_repo
- [ ] T191 (P0) `Hw4Sdk.ask()` MVP: retrieval bundle → LLM → answer with cited node ids + source files (purpose tag `ask`)
- [ ] T192 (P0) Tests (mock LLM): ask returns citations; refuses to answer without retrieval hits (no hallucinated context)
- [ ] T193 (P1) Manual QA: ask 3 real questions about target; verify citations point at real files; note quality
- [ ] T194 (P1) Vault wiki pages for: each detected community (after Phase 6 feeds back), top-5 hubs, the chosen critical path
- [ ] T195 (P1) `30_Comparisons/` note comparing naive-vs-graph approaches (seeds the experiment narrative)
- [ ] T196 (P1) Hebrew-content check: ensure tooling handles any RTL content gracefully (R11)
- [ ] T197 (P0) Gate check + commit; tag `m3-vault`
- [ ] T198 (P1) PROMPTS.md update (wiki-gen prompts + iterations)
- [ ] T199 (P2) Obsidian hotkeys/canvas exploration for nicer screenshots
- [ ] T200 (P1) Effort tracking update
- [ ] T201 (P1) Wikilink lint: script verifying zero broken `[[links]]` in vault (becomes part of check_gates P1)
- [ ] T202 (P2) Auto-generate Mermaid overview inside index.md (communities as subgraphs)
- [ ] T203 (P1) Verify vault contains the PRD/PLAN/TODO links under 20_Projects (the system that documents itself appears in its own graph — L07 §13.1)
- [ ] T204 (P1) Doc: vault rebuild instructions in README (one command)
- [ ] T205 (P2) Style pass: consistent note titles as routing descriptions (short, discriminative — skill-budget lesson applied to notes, Part-B 12)
- [ ] T206 (P1) Review: any wiki page >40 lines? split (short pages re-retrieve better)
- [ ] T207 (P1) Update PRD_graph_pipeline / agent PRDs with retrieval as-built details
- [ ] T208 (P0) Sanity: ask() total context tokens for a typical question < configured cap (proves the savings mechanism exists before measuring it)
- [ ] T209 (P2) Cache retrieval bundles keyed by question hash (saves money in repeated experiment runs — but careful: experiment must bypass cache; add flag)
- [ ] T210 (P0) Experiment-bypass flag implemented + tested (cached results would invalidate the A/B science)

## Phase 6 — Reverse Engineering & Defect Detection (Milestone M3)
**Phase DoD:** FINDINGS.md draft with evidence-labeled architecture analysis (macro/meso/micro), block diagram + OOP scheme exported, findings.json with ≥2 validated defects.

### macro / meso / micro analysis (human-led, graph-assisted)
- [ ] T211 (P0) Macro pass on iteration-0 graph: list communities + sizes; identify hubs, bridges, isolated areas (Part-C three-level reading)
- [ ] T212 (P0) "Who against whom" sketch: client/server/CLI/library boundaries from community structure (L07 §10)
- [ ] T213 (P0) Meso pass: for each major community write 2–3 sentence interpretation (what holds it: domain/layer/docs) — community ≠ folder check explicitly (Part-C)
- [ ] T214 (P0) Micro pass: for every claim that will appear in FINDINGS, perform 5-step inference (Observe→Relation→Confidence→Context→Source-validate) and record each step
- [ ] T215 (P0) Choose ≥1 critical flow; read it as a PATH (entry → controller → state → persistence → policy), labeling each edge's relation+evidence (Part-C path reading)
- [ ] T216 (P0) Hub-vs-bottleneck adjudication for top-3 central nodes using rubric (T150) + manual relation review; cautious verdict sentences
- [ ] T217 (P0) Draw system block diagram (mermaid → PNG in assets/): layers, communities, key flows — derived from graph, annotated with evidence levels
- [ ] T218 (P0) Draw OOP class scheme for the core community: key classes, inheritance/composition, responsibilities (mermaid classDiagram → assets/)
- [ ] T219 (P0) Cross-check both diagrams contain ≥3 claims NOT present in the target's own docs (the "extraction of understanding" requirement, L07 §11.1.3) — mark them
- [ ] T220 (P0) Target-docs traceability check (FR-4.7): docs claims ↔ graph nodes; list documented-but-unlinked features and undocumented modules
- [ ] T221 (P1) Rationale harvest: WHY/TODO/NOTE comments near central nodes; add as context to findings (Part-C rationale layer)
- [ ] T222 (P0) Write FINDINGS.md architecture chapters (macro/meso/micro/path) using template + careful language formula

### detectors (automated, fixture-tested)
- [ ] T223 (P0) TDD `detectors/base.py`: Detector ABC `detect(graph, metrics) -> list[Finding]`; Finding carries kind, nodes, evidence_chain (each link: relation, evidence class, confidence, source_file), status=hypothesis
- [ ] T224 (P0) Tests: Finding serialization to findings.json schema (T098)
- [ ] T225 (P0) TDD `detectors/spof.py`: high betweenness + no alternative path between its neighbor sets ⇒ SPOF hypothesis; thresholds from config
- [ ] T226 (P0) Tests on fixtures: planted SPOF found; healthy redundant hub NOT flagged (bridge with fallback path, L07 §10.1)
- [ ] T227 (P0) TDD `detectors/god_node.py`: fan-in+fan-out outlier (z-score or top-percentile from config) + rubric profile attached
- [ ] T228 (P0) Tests: planted god node found; large-but-cohesive abstraction not auto-condemned (healthy-hub criteria attached as evidence)
- [ ] T229 (P0) TDD `detectors/isolation.py`: isolated components classified with checklist {intentional standalone, deprecated/dead, parser miss, semantic-only} — output is a finding REQUIRING human triage (Part-C: isolation is a finding, not a diagnosis)
- [ ] T230 (P0) Tests: orphan in fixture flagged with classification options, not a verdict
- [ ] T231 (P0) TDD `detectors/traceability.py`: docs community with zero implements/tested_by/mentions edges into code ⇒ TRACE_GAP hypothesis
- [ ] T232 (P0) Tests: planted docs-gap in fixture found
- [ ] T233 (P1) TDD `detectors/duplication.py`: semantically_similar_to pairs (if backend provides) ⇒ DUPLICATION hypothesis with mandatory verify-checklist (purpose/usage/tests) — never a delete recommendation (Part-C ex. 3)
- [ ] T234 (P1) Tests: similar pair emitted as hypothesis with checklist fields
- [ ] T235 (P0) Detector registry + `Hw4Sdk.analyze()` runs all detectors → findings.json; CLI `hw4 analyze`
- [ ] T236 (P0) Integration test: analyze(mini_repo graph) yields planted findings exactly
- [ ] T237 (P0) Run analyze on TARGET iteration-0 graph; triage every hypothesis manually
- [ ] T238 (P0) For ≥2 findings: complete source validation to EXTRACTED-backed status=validated (open files, confirm) — fix loop may only consume validated findings (FR-6.3)
- [ ] T239 (P0) For each rejected hypothesis: record why (false-positive analysis is part of the report's credibility)
- [ ] T240 (P0) Merge automated findings into FINDINGS.md with evidence chains + confidence + careful phrasing
- [ ] T241 (P1) Rank validated findings by (impact, fix safety, test coverage around area) → pick fix-loop target order
- [ ] T242 (P1) Pre-fix metric baseline per finding (e.g., god node betweenness percentile) — the number the diff must improve

### wrap
- [ ] T243 (P0) Gate check + commit; tag `m3-analysis`
- [ ] T244 (P1) Vault feedback: wiki pages for each validated finding (linked from index)
- [ ] T245 (P1) PROMPTS.md update
- [ ] T246 (P1) Update PRD_defect_detection.md with as-built thresholds
- [ ] T247 (P1) Effort tracking update
- [ ] T248 (P2) Optional: hyperedge note modeling requirement→module→test→WHY as one group-claim for the chosen path (Part-C hyperedge)
- [ ] T249 (P1) Peer review: each teammate red-teams the other's findings for overclaiming (R8)
- [ ] T250 (P1) Screenshot the target graph with findings highlighted → assets/
- [ ] T251 (P2) Mini literature note in notebook: Lost in the Middle (Liu et al. 2024) citation + 2-sentence relevance (Part-B grounding)
- [ ] T252 (P0) Check: every FINDINGS.md conclusion sentence uses qualified language matching its evidence level (search for unqualified "is/must/always" near INFERRED claims)
- [ ] T253 (P1) File-length audit; refactor any service >130 lines
- [ ] T254 (P1) Coverage check on detectors ≥85%
- [ ] T255 (P2) Export FINDINGS.md → vault wiki mirror
- [ ] T256 (P1) Confirm findings.json schema matches doc (T098) byte-for-byte (json schema validation test)
- [ ] T257 (P2) Graph-literacy self-test: can each teammate explain every edge label used? (oral check, 10 min)
- [ ] T258 (P1) List AMBIGUOUS edges consumed anywhere in findings → must be zero or explicitly human-resolved
- [ ] T259 (P2) Record 2–3 "surprises" the graph revealed vs naive impression (T119) — strong report material
- [ ] T260 (P1) Update block diagram / class scheme if detector results changed the picture
- [ ] T261 (P0) Verify ≥2 validated defects exist — else loop back (this is a KPI)
- [ ] T262 (P1) Status sync: TODO statuses, slippage check

## Phase 7 — Token Experiment: Dataset & Baseline Condition A (Milestone M4)
**Phase DoD:** question dataset locked; Condition A measured for all questions with ledger rows; baseline table archived.

- [ ] T263 (P0) Author `data/questions.yaml`: ≥10 questions across tiers (≥3 locate, ≥4 trace-path, ≥3 impact) (FR-8.1)
- [ ] T264 (P0) Hand-build reference answers + reference source files per question; spot-check each against raw source (not only against the graph — answer-key bias mitigation, PLAN §4)
- [ ] T265 (P0) Both teammates review the key; disagreements resolved before any measurement (no post-hoc key edits — freeze it)
- [ ] T266 (P0) Freeze dataset: commit + record content hash in PRD_token_experiment.md
- [ ] T267 (P0) TDD `experiment/questions.py`: loader + schema validation (ids unique, tiers valid, files exist in target)
- [ ] T268 (P0) TDD `experiment/conditions.py` Condition A builder: naive context = concatenate candidate files (selection rule documented: e.g., all files matching naive keyword grep, as a developer would) + skill-listing simulation per L07 §7
- [ ] T269 (P0) Condition A truncation policy: if context exceeds model cap, truncate + LOG the truncation (it is itself a result)
- [ ] T270 (P0) Tests: deterministic context assembly, truncation logging, token estimate
- [ ] T271 (P0) TDD `experiment/runner.py`: for each question × condition × repetition → gatekeeper call (purpose `experiment.A`/`experiment.B`), persist answer + usage to results/experiment/
- [ ] T272 (P0) Runner: temperature 0, fixed model (strong tier), randomized question order, cache-bypass flag ON (T210)
- [ ] T273 (P0) Tests (mock LLM): pairing, repetition count, ledger rows per call, resume-on-crash (idempotent by run id)
- [ ] T274 (P0) Cost preflight: estimate Condition A total cost from context sizes BEFORE running; confirm under budget; record estimate vs actual later
- [ ] T275 (P0) RUN Condition A on target: N questions × 2 reps; archive raw outputs
- [ ] T276 (P0) Verify ledger rows complete (tokens in/out from API metadata, not estimates) for every call; any gaps → rerun those cells
- [ ] T277 (P0) TDD `experiment/scoring.py`: rubric scoring record (per answer: correctness, citation correctness, scorer id)
- [ ] T278 (P0) Blind-score Condition A answers (both teammates, adjudicate disagreements per protocol T092)
- [ ] T279 (P1) Baseline table: per-question tokens + score; archive `results/experiment/condition_A.json`
- [ ] T280 (P1) Sanity reflections: did naive condition hit Lost-in-the-Middle symptoms (right file present but answer wrong)? note instances — gold for the report
- [ ] T281 (P0) Gate check + commit; tag `m4-baseline`
- [ ] T282 (P1) PROMPTS.md update (experiment prompts verbatim — they ARE the methodology)
- [ ] T283 (P1) Effort + budget tracking update (actual $ vs preflight)
- [ ] T284 (P2) If any question is degenerate (both conditions trivially answer), replace it BEFORE running B? — NO: dataset frozen (T266); instead note as limitation. (Task = write the limitation note if applicable)
- [ ] T285 (P1) Verify experiment artifacts contain zero secrets/keys (raw payload logs!)
- [ ] T286 (P1) Update PRD_token_experiment.md with as-run parameters
- [ ] T287 (P2) Dry-run one question through Condition B informally to confirm plumbing before Phase 10 (no recorded measurement)
- [ ] T288 (P1) Coverage on experiment/ modules ≥85%
- [ ] T289 (P1) Findings: file-length audit on experiment modules
- [ ] T290 (P2) Back up results/ to second location (cheap insurance)
- [ ] T291 (P0) Confirm question set includes ≥1 question whose naive condition exceeds context (demonstrates the bottleneck thesis) — if not, add an impact-tier question variant via documented amendment procedure
- [ ] T292 (P1) Status sync

## Phase 8 — Multi-Agent System (Milestone M5)
**Phase DoD:** crew (Repo, GraphAnalyst, ArchitectFixer, QA + orchestrator) runs analyze→detect end-to-end on mini_repo with mocked LLM in tests and on target live; all LLM traffic via gatekeeper; findings.json produced by agents matches direct-SDK output.

- [ ] T293 (P0) Install/pin agent framework per ADR-1 (CrewAI); `uv add crewai`; resolve version conflicts NOW (revisit-trigger check)
- [ ] T294 (P0) If CrewAI conflicts with env → execute ADR-1 fallback to LangGraph; update ADR with evidence
- [ ] T295 (P0) TDD `agents/tools.py`: tool wrappers (run_graphify, load_graph, run_metrics, run_detectors, retrieve_context, run_tests, apply_edit, graph_diff) — each a thin delegate to SDK services; NO logic in tools
- [ ] T296 (P0) Tests: every tool delegates correctly (mock SDK), tool I/O is JSON-serializable
- [ ] T297 (P0) TDD `agents/roles.py`: role/goal/backstory definitions for RepoAgent, GraphAnalyst, ArchitectFixer, QAAgent — goals phrased with context discipline ("you receive focused subgraphs; never request full files unless source-validation step")
- [ ] T298 (P0) Typed payload dataclasses: AnalysisRequest, Finding (reuse), FixPlan, IterationVerdict — serialization tests (PLAN §3.2)
- [ ] T299 (P0) TDD `agents/context.py`: pack payload+bundle with instructions at start, task at end; history compaction summarizer between iterations (purpose tag `compact`) (FR-5.5)
- [ ] T300 (P0) Tests: packing order, compaction reduces tokens ≥50% on synthetic history, critical rules survive compaction (assert rule text present post-compact) (Part-B /compact protocol)
- [ ] T301 (P0) TDD `agents/crew.py`: wire roles+tools+orchestration for the ANALYZE flow (Repo→Analyst→findings.json)
- [ ] T302 (P0) Integration test (mock LLM): analyze flow on mini_repo emits planted findings; equality vs direct `Hw4Sdk.analyze()` output
- [ ] T303 (P0) Enforcement test: attempt direct LLM call from an agent bypassing gatekeeper raises (FR-5.4 / NFR-2)
- [ ] T304 (P0) Budget guard test: crew run halts gracefully on BudgetExceeded mid-flow, state persisted
- [ ] T305 (P0) Run live analyze-crew on TARGET (cheap model); compare findings vs Phase 6 — reconcile differences, document
- [ ] T306 (P0) Ledger audit: every agent step tagged (`agent.analyst`, `agent.fixer`, ...) — required for cost table
- [ ] T307 (P1) Agent narrative quality pass: analyst's finding write-ups use careful language; add system-prompt rule if not (evidence-level vocabulary enforced in prompt)
- [ ] T308 (P0) CLI `hw4 analyze --agents` (agent path) vs `hw4 analyze` (direct path) — both supported; README explains why (determinism vs demonstration)
- [ ] T309 (P1) Failure-mode tests: tool exception → orchestrator retries once → surfaces structured error (no silent swallow)
- [ ] T310 (P1) Timeout per agent step (config) tested
- [ ] T311 (P0) Gate check + commit; tag `m5-agents`
- [ ] T312 (P1) PROMPTS.md: agent system prompts verbatim + iteration history
- [ ] T313 (P1) Update PRD_agent_orchestration.md as-built
- [ ] T314 (P1) Coverage on agents/ ≥85% (mock-heavy; adapters thin per ADR-7)
- [ ] T315 (P1) File-length audit (roles/backstories can bloat — extract to data file if >150)
- [ ] T316 (P2) Trace visualization: sequence log of one crew run rendered to markdown (nice README artifact)
- [ ] T317 (P1) Effort + budget tracking update
- [ ] T318 (P2) Stress: run analyze-crew twice; confirm idempotent outputs (or document LLM variance handling)
- [ ] T319 (P1) Verify agent context sizes per step < config caps (proves discipline held in practice; log assertion)
- [ ] T320 (P1) Status sync

## Phase 9 — Fix & Improvement Loop (Milestone M6)
**Phase DoD:** ≥1 validated finding fixed by the crew on a branch; target tests green; graph re-run shows structural improvement; loop_log.json complete with explicit stop reason.

- [ ] T321 (P0) TDD `fixloop/planner.py`: validated Finding → FixPlan {strategy (split module / introduce interface / extract function / add redundancy), affected files, expected metric delta, test strategy}
- [ ] T322 (P0) Planner constraints: refuse AMBIGUOUS-based findings; refuse plans touching files without test coverage unless characterization step included (FR-7.5)
- [ ] T323 (P0) Tests: plan structure, refusal paths, strategy selection on fixture findings
- [ ] T324 (P0) TDD `fixloop/applier.py`: create branch `fix/<finding-id>` in workspace clone; apply edits; verify clean revert path
- [ ] T325 (P0) Applier edit mechanics: LLM (strong tier, purpose `fixloop.edit`) proposes unified-diff-style edits against ONLY the focused files; applier validates patch applies cleanly; reject+retry once on failure
- [ ] T326 (P0) Tests (mock LLM, mini_repo): branch isolation, patch apply, revert restores hash, retry path
- [ ] T327 (P0) Characterization-test generator: for uncovered touched code, generate pinning tests FIRST, run them green on ORIGINAL code before any edit (red-green discipline applied to the fix)
- [ ] T328 (P0) Tests: characterization flow on mini_repo's uncovered module
- [ ] T329 (P0) TDD `fixloop/stop.py`: evaluate StopReason truth table from {iteration, tests, metric delta, budget, remaining findings} (FR-7.2) — pure function, exhaustive unit tests
- [ ] T330 (P0) TDD `fixloop/loop.py`: full iteration per PLAN §3.3 pseudocode; every iteration appends loop_log.json entry {finding, diff stats, tests, graph hashes, metric deltas, tokens, verdict, stop_reason}
- [ ] T331 (P0) Loop integration test on mini_repo (mock LLM with scripted good fix): 1 iteration → improved verdict → GOAL_METRIC_REACHED stop
- [ ] T332 (P0) Loop integration test: scripted bad fix → tests red → revert → finding marked blocked → NO_SAFE_ACTION or next finding
- [ ] T333 (P0) Loop integration test: MAX_ITERATIONS path
- [ ] T334 (P0) QA verdict wiring: tests green AND diff verdict improved ⇒ accept; else revert (graph_diff thresholds from config)
- [ ] T335 (P0) Graphify re-run REQUIRED inside every iteration (L07 §10.2 — architect re-runs after every substantive change); assert in loop test that graph hash changes are recorded per iteration
- [ ] T336 (P0) CLI `hw4 fix --finding F-xxx` + `hw4 fix --auto` (loop over ranked findings)
- [ ] T337 (P0) RUN live fix loop on TARGET for top-ranked validated finding (strong model, budget-guarded)
- [ ] T338 (P0) Verify on target: branch diff readable; target test suite green (or characterization suite green); graph iteration k+1 artifacts saved
- [ ] T339 (P0) Verify structural improvement number (e.g., god-node betweenness percentile drop ≥ threshold) recorded in loop_log
- [ ] T340 (P0) If improvement not achieved: iterate within caps OR record honest NO_SAFE_ACTION analysis (an honest negative with analysis beats a cosmetic "improvement" — diff question, Part-C)
- [ ] T341 (P1) Second finding fix attempt if budget+time allow (strengthens ≥1 KPI to 2)
- [ ] T342 (P0) Post-fix Ruff run on TOUCHED target files only (we don't lint the whole foreign repo — document this boundary)
- [ ] T343 (P0) Gate check + commit (our repo); tag `m6-fixloop`; preserve target branch in workspace + export patch file to results/patches/
- [ ] T344 (P1) PROMPTS.md: fixer prompts + failed attempts (failures are methodology data)
- [ ] T345 (P1) Update PRD_fix_loop.md as-built (esp. stop-condition truth table actuals)
- [ ] T346 (P1) Vault: wiki page per executed fix (what/why/evidence/result) linked from index
- [ ] T347 (P1) Coverage ≥85% on fixloop/
- [ ] T348 (P1) File-length audit
- [ ] T349 (P2) Record a short screen capture / annotated log of one full loop run (demo asset)
- [ ] T350 (P1) Effort + budget tracking update
- [ ] T351 (P1) Loop tokens accounting: per-iteration token totals from ledger → will feed cost analysis
- [ ] T352 (P1) Status sync; descope decision point for P2 backlog if slipping

## Phase 10 — Token Experiment: Condition B & Comparison (Milestone M7)
**Phase DoD:** Condition B measured; per-question comparison table complete; savings KPI computed; failures analyzed in writing.

- [ ] T353 (P0) TDD Condition B builder in `experiment/conditions.py`: graph-guided context = index + focused subgraph + 2–3 wiki pages (reuses retrieval.py; identical question wording)
- [ ] T354 (P0) Tests: B-context determinism, caps, same-question parity with A records
- [ ] T355 (P0) Preflight cost estimate for Condition B; confirm budget headroom
- [ ] T356 (P0) RUN Condition B: same N questions × 2 reps, same model/temp, cache bypass, randomized order
- [ ] T357 (P0) Ledger completeness audit for B rows
- [ ] T358 (P0) Blind-score Condition B answers per rubric (same protocol, same scorers)
- [ ] T359 (P0) Build comparison table: per question — input/output tokens A vs B, % savings, score A vs B, citation correctness A vs B
- [ ] T360 (P0) Compute headline KPIs: total input-token savings %, mean per-question savings, quality delta — check ≥70% target
- [ ] T361 (P0) Per-question failure analysis for every question with savings <70% OR quality regression — root cause (retrieval miss? subgraph too large? question type?) (mandated by L07 §12)
- [ ] T362 (P0) Honest-quality check: if B answers degraded vs A anywhere, say so prominently — savings with wrong answers is a failure mode, not a win
- [ ] T363 (P1) FR-11 metrics from same runs: source-traceability rate, correct-file identification rate, correct-tool activation (from agent logs)
- [ ] T364 (P1) Effect of tiers: savings by question tier (locate vs path vs impact) — one chart
- [ ] T365 (P2) Stretch: distractor-injection mini-run (3 questions) demonstrating Lost-in-the-Middle degradation curve (FR-8.6)
- [ ] T366 (P0) Persist `results/experiment/comparison.json` + raw artifacts; freeze
- [ ] T367 (P0) Gate check + commit; tag `m7-experiment`
- [ ] T368 (P1) PROMPTS.md update
- [ ] T369 (P1) Update PRD_token_experiment.md with results summary + limitations section (validity threats realized or not)
- [ ] T370 (P1) Effort + budget update (actual total $ so far)
- [ ] T371 (P1) Re-verify no secrets in archived raw payloads
- [ ] T372 (P1) Status sync

## Phase 11 — Research Notebook, Visualization & Cost Analysis (Milestone M7)
**Phase DoD:** notebooks/analysis.ipynb executes top-to-bottom from committed artifacts; all required plots render; cost chapter complete.

- [ ] T373 (P0) Notebook section 1 — Setup: load comparison.json, ledger, loop_log, metrics snapshots (paths from config; no hardcoded paths)
- [ ] T374 (P0) Section 2 — Graph overview: nodes/edges/evidence distribution table + community size bar chart
- [ ] T375 (P0) Section 3 — Token experiment: per-question grouped bar (A vs B input tokens), savings % bar, quality comparison table
- [ ] T376 (P0) Section 4 — Savings statistics: totals, mean/median savings, savings-by-tier; LaTeX formula for savings metric definition (guidelines §9.2 expects professional formulas)
- [ ] T377 (P0) Section 5 — Fix loop: per-iteration metric deltas chart (e.g., betweenness percentile before/after), loop_log table render
- [ ] T378 (P0) Section 6 — Parameter sensitivity study (NFR-12): vary retrieval k ∈ {1,2,3 pages} and ego radius ∈ {1,2} on a 3-question subsample; chart tokens vs quality (OAT approach, guidelines §9.1)
- [ ] T379 (P0) Section 7 — Cost analysis (guidelines §11): per-model input/output tokens + $ table from ledger purpose tags; cost per phase (wiki-gen / agents / fixloop / experiment); optimization strategies discussion (cheap-vs-strong tiering results)
- [ ] T380 (P0) Section 8 — FR-11 metrics: traceability rate, correct-file rate, tool-activation correctness
- [ ] T381 (P0) Section 9 — Conclusions: KPI table vs PRD §3.2 targets; honest misses + reasons
- [ ] T382 (P0) All charts: labeled axes, legends, consistent accessible palette, high resolution; export PNGs to assets/ (guidelines §9.3)
- [ ] T383 (P0) Restart-kernel → run-all clean execution verified; runtime noted
- [ ] T384 (P1) Academic citation: Liu et al. 2024 (Lost in the Middle), Vaswani et al. (Attention) where relevant (Part-B sources)
- [ ] T385 (P1) Budget alerts demonstration: show warn threshold log line from a real run (guidelines §11.2)
- [ ] T386 (P1) Notebook prose pass: every chart has 2–3 sentences of interpretation (a chart without a claim is decoration)
- [ ] T387 (P0) Commit notebook + exported figures
- [ ] T388 (P1) PROMPTS.md update
- [ ] T389 (P1) Effort tracking update
- [ ] T390 (P2) Optional appendix: nondeterminism note (rep variance between identical runs)
- [ ] T391 (P1) Status sync

## Phase 12 — SKILL Protocol & Guardrails (Milestone M8 start)
**Phase DoD:** SKILL.md complete (frontmatter, procedure, guardrails), copied into vault, referenced by agents; guardrail behavior demonstrably enforced.

- [ ] T392 (P0) Author `docs/SKILL.md` frontmatter: name `graph-guided-codebase-analysis`, short discriminative routing description (skill-listing budget lesson — short, sharp, activating; Part-B 12–13), allowed-tools list
- [ ] T393 (P0) Body — When to use: trigger phrases + problem patterns (problem→skill paradigm, Part-A skill-to-need slide)
- [ ] T394 (P0) Body — Procedure: identify task → load skill → read index.md → retrieve focused context → act → return traceable result (Part-B protocol)
- [ ] T395 (P0) Body — Guardrails table: read-only (auto), reversible (requires revert path — branch edits), irreversible (delete/send/publish — human approval required); note disable-model-invocation concept for sensitive skills (Part-B slide 11)
- [ ] T396 (P0) Skill-refresh rule documented: re-read SKILL before complex/sensitive steps; /compact recovery protocol (skill drift, Part-B 17)
- [ ] T397 (P0) Copy skill into vault wiki + link from index
- [ ] T398 (P1) Wire skill text into agent system prompts (fixer + analyst read the procedure section verbatim at session start)
- [ ] T399 (P1) Guardrail enforcement test: applier refuses non-branch (irreversible) edit path; deletion-type plan requires `--confirm` flag (demonstrable, not aspirational)
- [ ] T400 (P1) Second skill (P1): `token-experiment-runner` skill documenting the A/B protocol as an activation protocol
- [ ] T401 (P1) Commit; PROMPTS.md update
- [ ] T402 (P2) Skill-listing budget demo: show truncated-description behavior in a note (educational tie-in)

## Phase 13 — Creative Extension: Refactor Truth Dashboard (ADR-6)
**Phase DoD:** dashboard artifact generated per loop run; answers "did structure improve or did the picture just change?" with numbers.

- [ ] T403 (P1) Define dashboard content: per-iteration cards — bottleneck deltas (top-5 nodes), modularity delta, isolated-component delta, tests status, tokens spent, verdict
- [ ] T404 (P1) TDD dashboard generator (markdown first; HTML if cheap): consumes loop_log.json + metrics snapshots only (no new analysis)
- [ ] T405 (P1) Tests: renders from fixture loop_log; handles 0-iteration and failed-run logs
- [ ] T406 (P1) "Moved-not-improved" guard surfaced: highlight when a new node's centrality rose as much as the old one fell (T156 limitation made visible)
- [ ] T407 (P1) CLI `hw4 report --dashboard`; output to results/dashboard.md (+ html)
- [ ] T408 (P1) Generate on real target loop run; screenshot → assets/
- [ ] T409 (P1) README + notebook reference the dashboard; one-paragraph rationale tying to Part-C diff philosophy
- [ ] T410 (P2) Bonus idea parked explicitly (org-graph / test-gap heatmap) — recorded as future work in README (shows deliberate scope control)
- [ ] T411 (P1) Commit; tag `m8-extension`
- [ ] T412 (P2) Effort tracking update

## Phase 14 — Testing & Quality Hardening (continuous; final sweep here)
**Phase DoD:** check_gates fully green on the complete codebase; coverage ≥85% global; zero ruff; zero oversize files; error paths tested.

- [ ] T413 (P0) Full `uv run pytest` suite green; flaky tests eliminated (run 3× consecutively)
- [ ] T414 (P0) Global coverage ≥85% verified; fill gaps in lowest-covered modules first (target: no module <70%)
- [ ] T415 (P0) Every public function has ≥1 test — automated audit script or manual checklist per module
- [ ] T416 (P0) Error-path coverage: malformed graph.json, missing config key, LLM timeout, rate-limit saturation, budget exceeded, subprocess failure, patch-apply failure — each has an explicit test
- [ ] T417 (P0) Edge cases documented (guidelines §6.3): boundary inputs per module listed in docstrings/tests (empty graph, single-node graph, zero findings, empty question set)
- [ ] T418 (P0) `uv run ruff check` → 0 violations
- [ ] T419 (P0) File-length checker → 0 violations (split offenders per §3.2 strategies)
- [ ] T420 (P0) Hardcode grep → 0 hits (all config values from config/; constants in constants.py; defaults via cfg.get)
- [ ] T421 (P0) Secrets grep on full tree + results/ artifacts → 0 hits
- [ ] T422 (P0) Duplication review: any logic in 2+ places → extract (mixin/base/shared util); document the 3 extraction decisions made (NFR-9 evidence)
- [ ] T423 (P0) Mixin rules audit if mixins used: one concern each, no method overrides between mixins, independently testable (guidelines §4.2)
- [ ] T424 (P0) Docstring completeness: every module/class/public function; comments explain WHY not WHAT (spot-check 10 files)
- [ ] T425 (P0) Integration test: full pipeline on mini_repo (graph→vault→analyze→fix→report) with fakes — single command, green
- [ ] T426 (P1) Test naming/structure mirror src 1:1 — fix drift
- [ ] T427 (P1) conftest fixtures documented (what each fake provides)
- [ ] T428 (P1) Automated test report artifact (pass/fail counts) saved to results/ (guidelines §6.4)
- [ ] T429 (P1) Thread/process safety review: we are single-process; if any parallelism was added (e.g., parallel question runs), verify locks/queues per guidelines §15; else write one-paragraph justification of single-threaded design
- [ ] T430 (P1) Startup config-version validation demonstrably fails on mismatched version (manual test + unit test)
- [ ] T431 (P1) `__init__.py` exports + `__version__` final audit
- [ ] T432 (P1) Relative-paths audit (no absolute paths)
- [ ] T433 (P1) Dead code sweep (unused functions/imports — ruff F401 + manual)
- [ ] T434 (P0) Commit; tag `quality-hardened`
- [ ] T435 (P1) Record gate outputs (text) → results/gates_final.txt for README evidence
- [ ] T436 (P2) Mutation-spot-check: intentionally break one detector, confirm a test fails (test-suite sanity)
- [ ] T437 (P1) Status sync

## Phase 15 — README & Documentation Polish (Milestone M8)
**Phase DoD:** README is a complete user manual; all docs current; prompt log complete.

- [ ] T438 (P0) README — Overview: what this is, course context, headline results (savings %, fixes, finding count) with links to evidence
- [ ] T439 (P0) README — Installation: prerequisites, `uv sync`, `.env` from `.env-example`, Obsidian optional step, troubleshooting (≥3 real issues we actually hit)
- [ ] T440 (P0) README — Usage: every CLI command with example invocation + expected output snippet (graph/vault/analyze/ask/fix/experiment/report/gates)
- [ ] T441 (P0) README — Typical workflow walkthrough: end-to-end on the target repo, with screenshots (Obsidian graph, dashboard, findings)
- [ ] T442 (P0) README — Configuration guide: every key in setup.json/rate_limits.json explained + effects
- [ ] T443 (P0) README — Architecture summary: C4 context diagram + 1-paragraph per layer; link to PLAN
- [ ] T444 (P0) README — Results summary: KPI table, link to notebook
- [ ] T445 (P0) README — License & credits: our license, target-repo attribution + license, third-party libs
- [ ] T446 (P1) README — Contribution guidelines (code standards pointer) (guidelines §2.1)
- [ ] T447 (P0) docs/PROMPTS.md final pass: significant prompts, context/goal each, output examples, iterative improvements, lessons (guidelines §8.3)
- [ ] T448 (P0) All dedicated PRDs reflect as-built reality (drift sweep)
- [ ] T449 (P0) TODO.md statuses all updated (this file is graded too — stale statuses look careless)
- [ ] T450 (P1) FINDINGS.md final language pass (qualified phrasing, evidence labels)
- [ ] T451 (P1) Spell/format pass on all docs; consistent heading levels; working relative links
- [ ] T452 (P1) Screenshots inventory complete in assets/ (vault graph, wiki page, dashboard, findings highlight, notebook charts)
- [ ] T453 (P1) Vault final tidy: index current, zero broken wikilinks (T201 script)
- [ ] T454 (P0) Commit; tag `docs-final`
- [ ] T455 (P2) Optional 2-min demo recording link

## Phase 16 — Final Checklist & Packaging (Milestone M8 — submission)
**Phase DoD:** guidelines §17/§20.9 checklist 100% true; zip submitted in correct format; clean-machine verification done.

### guidelines final checklist mirror (§17)
- [ ] T456 (P0) ✔ Comprehensive README at root (user-manual level)
- [ ] T457 (P0) ✔ docs/ with PRD.md, PLAN.md, TODO.md
- [ ] T458 (P0) ✔ Dedicated PRDs for every central algorithm/mechanism (6 files)
- [ ] T459 (P0) ✔ Architecture docs with clear diagrams
- [ ] T460 (P0) ✔ Documented prompt log
- [ ] T461 (P0) ✔ SDK architecture — all business logic behind SDK layer
- [ ] T462 (P0) ✔ OOP design — no duplication, inheritance/mixins used appropriately
- [ ] T463 (P0) ✔ API Gatekeeper — all external calls through it
- [ ] T464 (P0) ✔ Rate limits from configuration; queue management works
- [ ] T465 (P0) ✔ Files ≤150 code lines; comments + docstrings
- [ ] T466 (P0) ✔ Consistent code style, descriptive names
- [ ] T467 (P0) ✔ TDD evidenced (tests exist alongside/before code in git history)
- [ ] T468 (P0) ✔ Coverage ≥85%
- [ ] T469 (P0) ✔ Ruff zero violations
- [ ] T470 (P0) ✔ Edge cases documented + error handling
- [ ] T471 (P0) ✔ Automated test reports saved
- [ ] T472 (P0) ✔ Config files separate from code, versioned
- [ ] T473 (P0) ✔ .env-example with dummy values
- [ ] T474 (P0) ✔ No API keys/secrets in code or artifacts
- [ ] T475 (P0) ✔ .gitignore current
- [ ] T476 (P0) ✔ uv sole package manager; pyproject.toml + uv.lock present
- [ ] T477 (P0) ✔ Systematic experiments with parameter variation (sensitivity study)
- [ ] T478 (P0) ✔ Analysis notebook with graphs
- [ ] T479 (P0) ✔ Quality graphs, screenshots, architecture diagrams
- [ ] T480 (P0) ✔ Token cost analysis + optimization strategies
- [ ] T481 (P0) ✔ Extension points documented (where to add a detector / provider / framework adapter)
- [ ] T482 (P0) ✔ Professional Python package organization
- [ ] T483 (P1) ✔ Parallel-processing stance documented (used or justified absence)
- [ ] T484 (P1) ✔ Building-blocks design (Input/Output/Setup documented per service)
- [ ] T485 (P1) ✔ ISO/IEC 25010 mapping paragraph (which characteristics we address and how)
- [ ] T486 (P0) ✔ Git history orderly; license; attribution; run instructions

### assignment-substance final verification (L07 §11 + Part-B final slide)
- [ ] T487 (P0) ✔ Clone/provenance + approval evidence (if personal repo)
- [ ] T488 (P0) ✔ Graph artifacts (graph.json/html/REPORT + per-iteration) present + reproducible
- [ ] T489 (P0) ✔ Obsidian vault with index/wiki/log + screenshots
- [ ] T490 (P0) ✔ Block diagram + OOP scheme extracted (beyond existing docs — marked claims present)
- [ ] T491 (P0) ✔ Multi-agent crew (≥3 specialized roles) demonstrated
- [ ] T492 (P0) ✔ ≥2 validated architectural findings; ≥1 automated fix with tests green + graph diff improvement (or honest NO_SAFE_ACTION analysis)
- [ ] T493 (P0) ✔ Stop condition + unit-test gate per iteration in loop_log
- [ ] T494 (P0) ✔ Token before/after measured; ≥70% or written root-cause analysis
- [ ] T495 (P0) ✔ SKILL.md with guardrails; FR-11 metrics reported
- [ ] T496 (P0) ✔ Creative extension delivered + rationale

### package & ship
- [ ] T497 (P0) Bump/verify version 1.00 everywhere (version.py, configs); tag `v1.00`
- [ ] T498 (P0) Confirm zip naming convention with course (default `<id1>_<id2>_hw4.zip`); build zip EXCLUDING workspace/, .env, caches
- [ ] T499 (P0) Secrets scan on the actual zip contents (unzip to temp, grep) — zero hits
- [ ] T500 (P0) Clean-machine test: fresh clone/unzip → `uv sync` → `uv run hw4 gates` → `uv run hw4 graph` on mini fixture — all green, no manual fixes
- [ ] T501 (P0) Notebook executes on clean machine from committed artifacts
- [ ] T502 (P0) Final read-through of submission by BOTH teammates against this checklist — initials on each section
- [ ] T503 (P0) Submit; archive submission receipt/confirmation
- [ ] T504 (P1) Post-submission: tag repo `submitted`, back up results/ and vault/
- [ ] T505 (P2) Retrospective (30 min): what the graph taught us that grep couldn't; token-economics lessons; save as vault note (portfolio value, L07 §1)

---

## Backlog (P2 — only if time remains after T504)
- [ ] T506 (P2) Distractor-injection Lost-in-the-Middle mini-study (FR-8.6 full version)
- [ ] T507 (P2) Hyperedge group-claims modeled for 3 requirements (Part-C)
- [ ] T508 (P2) Second provider adapter live + cross-model savings comparison
- [ ] T509 (P2) GitHub Action stub that re-runs graphify on push (the commit-trigger idea, L07 §10.2 — documented as future work otherwise)
- [ ] T510 (P2) Org-structure graph demo (teams/roles as nodes) — L07 §12 creativity example
- [ ] T511 (P2) Test-gap heatmap from tested_by edge density per community
- [ ] T512 (P2) Auto-generated PRD-gap report for the target repo (docs↔code traceability as a product)
- [ ] T513 (P2) Obsidian canvas storyboard of the whole project for presentation
- [ ] T514 (P2) Compare greedy-modularity vs Louvain community stability (sensitivity appendix)
- [ ] T515 (P2) Token-savings confidence interval via additional repetitions (N=4)

---

### Progress summary table (update at every phase exit)

| Phase | Tasks | Done | Status | Exit date |
|---|---|---|---|---|
| 0 Environment | T001–T030 | 27/30 | in progress (T007 user .env, T023 Obsidian, T028 editor pending) | |
| 1 Shared infra & SDK | T031–T075 | 40/45 | done core; T042,T061,T071,T072,T074 open | 2026-06-12 |
| 2 Docs & approvals | T076–T105 | 0/30 | not started | |
| 3 Target repo | T106–T130 | 0/25 | not started | |
| 4 Graph pipeline | T131–T172 | 0/42 | not started | |
| 5 Vault & wiki | T173–T210 | 0/38 | not started | |
| 6 RevEng & detection | T211–T262 | 0/52 | not started | |
| 7 Experiment baseline | T263–T292 | 0/30 | not started | |
| 8 Agents | T293–T320 | 0/28 | not started | |
| 9 Fix loop | T321–T352 | 0/32 | not started | |
| 10 Experiment B | T353–T372 | 0/20 | not started | |
| 11 Notebook & cost | T373–T391 | 0/19 | not started | |
| 12 SKILL | T392–T402 | 0/11 | not started | |
| 13 Creative ext. | T403–T412 | 0/10 | not started | |
| 14 Quality hardening | T413–T437 | 0/25 | not started | |
| 15 README & docs | T438–T455 | 0/18 | not started | |
| 16 Final & ship | T456–T505 | 0/50 | not started | |
| Backlog | T506–T515 | 0/10 | parked | |
| **Total** | **515 tasks** | **67/515** | | |

*End of TODO v1.00.*

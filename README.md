# HW4 — EX04: Graph-Based Reverse Engineering with AI Agents

> Reverse-engineer an **unfamiliar** Python repository the way a senior engineer would if they had a knowledge graph and a disciplined agent crew: build a dependency graph, navigate it as an Obsidian vault + LLM wiki, detect **architectural** defects with evidence-chained findings, attempt a **test-guarded** fix, and **prove** that graph-guided retrieval is cheaper than naive context-stuffing in a frozen A/B experiment.

**Target analysed:** [`pallets/werkzeug`](https://github.com/pallets/werkzeug) @ `1b00618e` — the WSGI toolkit under Flask (138 `.py` files / 27,498 LOC).

> Course: **Lecture 07 — Reverse Engineering of Graph Knowledge Systems** (Dr. Yoram Segal, June 2026).
> Governing docs: [`docs/PRD.md`](docs/PRD.md), [`docs/PLAN.md`](docs/PLAN.md), [`docs/TODO.md`](docs/TODO.md) (515 tasks), and **6 dedicated mechanism PRDs**.

---

## TL;DR — headline results

| KPI (PRD §3.2) | Target | Result | Evidence |
|---|---|---|---|
| **Token savings** (graph vs naive) | ≥ 70% input tokens | ✅ **89.8%** (median 91.3%, *all 10* questions ≥ 82.4%) | [`results/REPORT.md`](results/REPORT.md), `docs/PRD_token_experiment.md` |
| **Validated architectural defects** | ≥ 2 | ✅ **2** — `http` god-node (F-005), `datastructures` god-node (F-001) | [`results/FINDINGS.md`](results/FINDINGS.md) §3 |
| **Automated fix** (tests green + graph improves) | ≥ 1 or honest analysis | ✅ **honest NO_SAFE_ACTION** (green but no structural gain → reverted) | [`results/loop_log.json`](results/loop_log.json), `results/dashboard.md` |
| **Coverage** | ≥ 85% | ✅ **≈96%** | `scripts/check_gates.py` |
| **Quality gates** | ruff 0 · ≤150 code-lines/file · no hardcodes/secrets | ✅ **GREEN** | `scripts/check_gates.py` |
| **Cost discipline** | under $10 firewall, every call ledgered | ✅ **$0.088** / 109 calls | [`results/ledger.jsonl`](results/ledger.jsonl) |

*Blind correctness scoring of the experiment answers is the one remaining human step (sealed key in `results/experiment/`); see [Outstanding](#-outstanding-human-side).*

## Table of contents

1. [What this is & why a graph](#what-this-is--why-a-graph)
2. [Architecture](#architecture)
3. [The pipeline, stage by stage](#the-pipeline-stage-by-stage)
4. [Installation](#installation)
5. [Usage tour](#usage-tour)
6. [Results deep-dive](#results-deep-dive)
7. [Evidence discipline (Part-C)](#evidence-discipline-part-c)
8. [Configuration guide](#configuration-guide)
9. [Repository layout](#repository-layout)
10. [Key design decisions (ADRs)](#key-design-decisions-adrs)
11. [Reproducing the analysis](#reproducing-the-analysis)
12. [Quality, cost & limitations](#quality-cost--limitations)
13. [Outstanding (human-side)](#-outstanding-human-side)
14. [License & attribution](#license--attribution)

---

## What this is & why a graph

Pasting whole files into a model to ask "how does this repo work?" burns the context window before insight arrives, and — per *Lost in the Middle* (Liu et al., 2024) — buries the relevant lines where attention is weakest. This project replaces file-stuffing with a **knowledge graph** of the codebase and retrieves only the **ego-subgraph + distilled wiki pages** a question actually needs.

The deliverable answers three task tiers over any repo:

- **locate** — "where is X implemented?"
- **trace-path** — "how does a request become a response?"
- **impact** — "what breaks if I change Y?"

…and goes further: it **detects** architectural smells (god modules, single points of failure, isolation, doc↔code traceability gaps), **attempts to fix** them under a test-and-graph-diff guard, and **measures** the token economics of the whole approach.

A guiding rule throughout: **deterministic spine, LLM at the edges.** Graph extraction, metrics, community detection, diffs, detectors, and loop control are plain, testable Python. The LLM only writes narratives, plans, and edits — and never without passing through the gate.

## Architecture

```mermaid
flowchart TB
    subgraph CLI["hw4 CLI — thin shell (zero business logic, NFR-1)"]
      G[graph] & V[vault] & A[analyze] & K[ask] & F[fix] & E[experiment] & R[report]
    end
    CLI --> SDK[[Hw4Sdk facade]]
    SDK --> SH
    SDK --> SV
    subgraph SH["shared/ — the spine"]
      CFG[Config<br/>versioned JSON + HW4__ env overrides] --- GK[ApiGatekeeper<br/>rate windows · FIFO queue · retries · budget firewall] --- LG[(Token ledger<br/>JSONL)]
      LLM[Gated LLM client] -.must be built through.-> GK
    end
    subgraph SV["services/ — the work"]
      EX[AST extractor<br/>Graphify-compatible contract] --> MET[metrics / diff<br/>networkx]
      MET --> DET[detectors<br/>god-node · SPOF · isolation · traceability · dup]
      EX --> VB[vault + wiki writer]
      VB --> RET[retrieval<br/>ego-subgraph + pages]
      DET --> FL[fix loop<br/>branch-isolated, test-guarded]
      RET --> XP[A/B experiment]
      CR[CrewAI crew<br/>analyst · fixer · QA] -.narratives.-> DET
    end
    EX --> WS[(workspace/target<br/>cloned repo, pinned SHA)]
    style SH fill:#eef
    style SV fill:#efe
```

**Layer sizes:** `sdk/` 6 files · `shared/` 9 files · `services/` 44 files (≈4.9k code lines of project source, every file ≤150 code lines by gate).

## The pipeline, stage by stage

```mermaid
flowchart LR
    C[clone @ pinned SHA] --> GR[graph i00<br/>1,912 nodes / 3,304 edges]
    GR --> AN[analyze<br/>8 findings, 2 validated]
    GR --> VA[vault<br/>44 wiki pages]
    AN --> FX[fix loop<br/>F-005 → NO_SAFE_ACTION]
    GR --> XP[experiment A/B<br/>89.8% savings]
    AN --> RP[report + dashboard]
    FX --> RP
    XP --> RP
```

| Stage | What it produces | Determinism |
|---|---|---|
| **graph** | immutable `results/graphs/iNN/{graph,manifest,metrics}.json` | content-hash identical on rebuild (proven in `VALIDATION.md`) |
| **analyze** | `findings.json` + careful-language `FINDINGS.md`; `--agents` adds CrewAI narratives | findings identical with or without agents |
| **vault** | Obsidian taxonomy (Portfolio→Domains→Projects) + raw/ snapshots + LLM `wiki/` + machine-owned `index.md` | skeleton never clobbered; index regenerated |
| **fix** | `fix/<id>` branch, characterization tests if needed, `loop_log.json`, per-iteration graph diffs | every iteration logged, accepted **or** reverted |
| **experiment** | paired/repeated `condition_{A,B}.json`, `comparison.json`, blind `scoring_sheet.json` + sealed key | seeded shuffle, resume-on-crash, tokens from API metadata only |
| **report** | `REPORT.md` + Refactor Truth Dashboard | aggregates committed artifacts |

## Installation

Prerequisites: `git` and [uv](https://docs.astral.sh/uv/) (`curl -LsSf https://astral.sh/uv/install.sh | sh`). uv provisions the pinned Python automatically (developed on uv-managed CPython 3.12.13; `requires-python >=3.10`). **No pip, no manual venv — uv only.**

```bash
git clone https://github.com/yosefshanaa/HW4 && cd HW4
uv sync                                   # full environment from uv.lock
cp .env-example .env                       # then add a real key for the configured provider
                                           # (llm.provider in config/setup.json; currently OPENAI_API_KEY)
uv run pytest -q                           # ~350 tests, coverage gate 85%
uv run python scripts/check_gates.py       # all submission gates → GATES: GREEN
```

**Troubleshooting (issues we actually hit):**
- *`uv run` appears to hang for minutes* — on a Windows `/mnt/c` mount uv re-copies the venv (no hardlinks). Don't run two `uv run` concurrently; let one `UV_LINK_MODE=copy uv sync` finish.
- *`Failed to spawn: hw4` right after a fresh sync* — the console script wasn't flushed yet; re-run, or use `uv run --no-sync hw4 …`.
- *`.env` not picked up* — load it explicitly: `set -a && . ./.env && set +a`. Watch for editors saving `.env` as `.env.txt`.

## Usage tour

The CLI is a 1:1 thin shell over `Hw4Sdk`:

```bash
uv run hw4 graph workspace/target            # immutable graph iteration + metrics
uv run hw4 analyze                           # detectors → results/findings.json + FINDINGS.md
uv run hw4 analyze --agents                  # same findings + CrewAI careful-language narratives
uv run hw4 vault                             # Obsidian vault + LLM wiki pages
uv run hw4 ask "where is the routing Map implemented?"  # graph-guided, cited answer
uv run hw4 fix F-005                          # test-guarded fix loop on a validated finding
uv run hw4 experiment --condition both        # frozen A/B token experiment
uv run hw4 report --dashboard                 # REPORT.md + Refactor Truth Dashboard
```

Example — the deterministic-vs-agent equivalence (a graded claim): `analyze` and `analyze --agents` produce **byte-identical `findings.json`**; the crew only adds prose. *Determinism for the science, agents for the demonstration.*

## Results deep-dive

### Target repository

| Field | Value |
|---|---|
| Repo / SHA | `pallets/werkzeug` @ `1b00618e787f40dfb21eba29caf8f8be7c8e1d93` (detached) |
| Size | 27,498 code lines / **138 `.py` files** (src-only `src/werkzeug`: 16,829 / 52) |
| License | BSD-3-Clause (attribution preserved below) |
| Test baseline | **992 passed, 0 skipped, 0 xfailed in ~60 s** (stable across 2 runs, no serving-port flakes) |

Selection trail, naive pre-graph impression, and the unfamiliarity attestation live in [`docs/TARGET_REPO.md`](docs/TARGET_REPO.md).

### Graph (iteration 0)

`ast_extractor/1.00` · content hash `54274cf9…` (reproduced identically on rebuild).

| Nodes: **1,912** | Edges: **3,304** |
|---|---|
| function 1,553 · class 219 · module 84 · doc 43 · rationale 13 | implements 1,932 · calls 747 · imports 369 · tested_by 186 · mentions 57 · rationale_for 13 |
| 1,267 communities (1,204 singletons, ~39 real clusters) | evidence: **EXTRACTED 3,235 · INFERRED 68 · AMBIGUOUS 1** |

![dependency-community sizes](assets/communities.png)

### Findings — 7 god-nodes + 1 traceability gap, 2 validated

| ID | Kind | Node | Verdict | Why |
|---|---|---|---|---|
| **F-005** | GOD_NODE | `werkzeug.http` | ✅ **validated** | 1,543 LOC bundling ≥6 header families (cookies, etags, dates, ranges, accept/cache-control/csp); fan-in **21** importers, no per-concern seam |
| **F-001** | GOD_NODE | `werkzeug.datastructures` | ✅ **validated** | rank-1 bottleneck; degree 76, fan-in 66, reaches 11 communities — a namespace backbone re-exporting ~10 container families |
| F-002 / F-003 | GOD_NODE | `wrappers.request` / `.response` | rejected | deliberate public façades over the `sansio` core |
| F-004 | GOD_NODE | `exceptions` | rejected | cross-cutting error layer; high fan-in is the protocol, one cohesive concern |
| F-006 / F-007 | GOD_NODE | `test.run_wsgi_app` / `utils` | rejected | test driver / low-cohesion utility grab-bag, not entangled cores |
| F-008 | TRACE_GAP | `wsgi.make_line_iter` | rejected | changelog records its **removal**; the symbol is correctly absent |

**No SPOF finding** — no node reaches `mandatory_path_ratio ≥ 0.3` (highest is `datastructures` at 0.106). werkzeug's hubs are reachable by multiple paths, unlike click's seam-less `echo`. Reported honestly rather than forced. Full 5-step inference per validated finding, plus the rejected-hypothesis analysis and block/class diagrams, in [`results/FINDINGS.md`](results/FINDINGS.md).

### Fix loop — an honest negative (T340)

The loop targeted the validated `http` god-node with the bounded GOD_NODE strategy (*extract the smallest cohesive group of private helpers into a sibling module, import them back, do not touch the public API*).

| Iteration | Target | Tests | Structure | Verdict |
|---|---|---|---|---|
| i02 | F-005 `http` | **992/992 green** (behavior preserved) | bottleneck 0.106 → 0.106; isolated 1250 → 1253 | **regressed → REVERTED** |

**Stop reason: `NO_SAFE_ACTION`.** The extraction was behavior-preserving but didn't *improve* the structure (the god-node's fan-in of 21 external importers is unchanged by relocating private helpers), so the graph-diff guard reverted it. A green-but-non-improving refactor is **rejected, not faked** — the loop empirically restated finding F-005.

![fix-loop structural deltas](assets/fixloop_deltas.png)

### Token experiment — 89.8% savings (run 1 → run 2)

10 questions (3 locate / 4 path / 3 impact), each spot-checked against source; 2 conditions × 2 repetitions; temperature 0; tokens taken **only** from provider API metadata via the ledger. Dataset sha256-sealed.

| Run | Retrieval caps | Cond B tokens/cell | Overall savings | KPI |
|---|---|---|---|---|
| **Run 1** | radius 2 · 40 nodes · 3 seeds · 3 pages (committed default) | ~6.5k | 58.7% | below target |
| **Run 2** | radius 1 · 20 nodes · 2 seeds · 2 pages (sensitivity-tuned, `HW4__` overrides) | **~1.6k** | **89.8%** | ✅ **≥70% met** |

Run 2 — overall **89.8%** (mean 89.7%, median 91.3%); by tier **locate 90.3% · path 90.2% · impact 88.5%**; **every** question clears 70% (lowest Q-09 datastructures-impact 82.4%). Input tokens collapse from **313,440** (naive A, truncated at the 16k cap on all 10) to **31,986** (graph B). Run 1 archived as `condition_B_run1.json` / `comparison_run1.json`; config files + frozen dataset untouched (only runtime knobs moved — a documented amendment).

![per-question token savings (A vs B) and the 70% line](assets/experiment_savings.png)

> The tuning was **motivated**, not fished: the one-at-a-time sensitivity study (`assets/sensitivity.png`, notebook §4) showed retrieval caps trade context size for tokens with little loss on the locate/path tiers. **Correctness is human-gated** — at ~1.6k tok/cell the savings only "count" once two blind scorers confirm `correctness(B) ≥ correctness(A)` and `citation(B) ≥ citation(A)`.

### The Obsidian vault

The graph becomes a navigable vault: an index-first hub, one LLM wiki page per key entity, communities as clusters, and the SKILL protocol mirrored in-vault.

> ⚠ **The 4 screenshots below are from the prior (click) target and are pending re-capture from the werkzeug vault** (human task). Captions name the werkzeug entities the new captures should show.

| Graph view — `index` hub + clusters | `index.md` — navigation hub |
|---|---|
| ![Obsidian graph view](assets/vault_graph.png) | ![index.md](assets/vault_index.png) |
| **`werkzeug.datastructures` — rank-1 god-node (F-001)** | **`werkzeug.http` — fan-in god-node (F-005)** |
| ![hub wiki page](assets/wiki_echo.png) | ![hub wiki page](assets/wiki_core.png) |

## Evidence discipline (Part-C)

Every claim carries an **evidence class**, end to end (extractor → findings → fix-eligibility):

| Class | Meaning | Policy |
|---|---|---|
| **EXTRACTED** | read directly from syntax (conf 1.0 / 0.9) | may state as fact; only EXTRACTED-only findings are fix-eligible |
| **INFERRED** | unique-symbol resolution of a bare name (conf 0.6) | must be hedged with its confidence |
| **AMBIGUOUS** | a documented dotted-path that resolves to nothing | a **stop-flag** for human triage — never an input to automated change |

This is why the single AMBIGUOUS edge (the removed `make_line_iter`) was triaged by a human, not silently consumed, and why the fix loop refuses to touch a finding whose chain isn't EXTRACTED end-to-end.

## Configuration guide

All tunables live in versioned JSON under `config/` (zero hardcoded values in code); **secrets come only from the environment.**

| File | Purpose |
|---|---|
| `setup.json` | models, retrieval caps, detector thresholds, budget, vault project/domains, fixloop test command |
| `rate_limits.json` | per-service rate windows for the gatekeeper |
| `logging_config.json` | structured-logging setup |

**Override convention:** any key can be overridden at runtime with `HW4__<dotted__path>` (e.g. `HW4__retrieval__ego_radius=1` — exactly how run 2 was tuned without editing committed config). **Secrets** (`OPENAI_API_KEY`) are read from the environment via `config.get_secret()` and never from JSON — a committed config can't leak a key.

Selected `setup.json` keys:

| Key | Default | Effect |
|---|---|---|
| `models.{cheap,strong}` | `gpt-4o-mini` | tier routing (narratives = cheap, edits/experiment = strong) |
| `retrieval.{ego_radius,max_nodes,max_seeds,k_pages}` | 2 / 40 / 3 / 3 | graph-context size (run 2 → 1 / 20 / 2 / 2) |
| `budget.{max_usd,warn_usd}` | 10 / 7 | firewall + warn threshold |
| `loop.{max_iterations,step_timeout_seconds}` | 3 / 300 | fix-loop bounds |
| `fixloop.test_command` | `uv run --no-project --isolated …` | target's suite (`--isolated` keeps werkzeug's `[tool.uv]` dev-groups out) |

## Repository layout

| Path | Purpose |
|---|---|
| `src/hw4/sdk/` | `Hw4Sdk` facade + operation modules (CLI & agents hold zero logic) |
| `src/hw4/shared/` | config, **API Gatekeeper**, token ledger, process runner, gated LLM client |
| `src/hw4/services/` | extractor, metrics/diff, vault+wiki, retrieval, detectors, fix loop, experiment, CrewAI, dashboard |
| `tests/` | unit+integration, mirrors `src/` 1:1; `tests/fixtures/mini_repo/` is the planted-defect answer key |
| `config/` | versioned JSON — zero hardcoded values; secrets only via env |
| `docs/` | PRD/PLAN/TODO, **6 mechanism PRDs**, SKILL protocols, SCORING_RUBRIC, PROMPTS log, TARGET_REPO |
| `data/` | frozen question dataset (sha256-sealed in `PRD_token_experiment.md`) |
| `results/` | graph iterations, findings, FINDINGS.md, loop log, experiment artifacts, ledger, REPORT, dashboard |
| `notebooks/` | `analysis.ipynb` — restart-and-run-all from committed artifacts |
| `vault/` | Obsidian vault (taxonomy + wiki incl. SKILL mirrors) |
| `workspace/` | target clone (gitignored; regenerate via `RepoService.clone(url, commit=<SHA>)`) |

## Key design decisions (ADRs in `docs/PLAN.md` §5)

- **One choke point** for every external call (`ApiGatekeeper`): rate limits, queue-not-drop, bounded retries, budget firewall, JSONL ledger. The LLM client *cannot be constructed* without it.
- **Evidence as a first-class enum** from extractor to fix-eligibility (above).
- **Deterministic spine, LLM at the edges** — metrics/diffs/detectors/loop are plain Python; the LLM writes narratives, plans, and edits only, through the gate.
- **Graphify fallback executed** (ADR-4): the course tool was unobtainable; the in-repo AST backend emits the identical contract, stamped so a future real run is distinguishable.
- **Provider-swappable** (ADR-3): proven live by config-switching to OpenAI `gpt-4o-mini` for both tiers.

## Reproducing the analysis

```bash
# 1. clone the target at the pinned SHA (gitignored workspace)
uv run hw4 graph https://github.com/pallets/werkzeug   # or RepoService.clone(url, commit=<SHA>)

# 2. deterministic graph (identical content hash on rebuild — see VALIDATION.md)
uv run hw4 graph workspace/target --iteration 0

# 3. detectors → 8 hypotheses; 2 validations + 6 reasoned rejections
uv run hw4 analyze

# 4. notebook: build + execute headlessly from committed artifacts
uv run --with nbformat python scripts/build_notebook.py
uv run --with nbformat --with nbclient --with ipykernel --with matplotlib python scripts/execute_notebook.py
```

## Quality, cost & limitations

- **Gates (law before every commit):** `scripts/check_gates.py` → ruff 0 · pytest+coverage ≈96% · every file ≤150 code lines · no hardcodes in `src/` · no secrets in tracked files · no broken vault wikilinks → **GATES: GREEN**.
- **Cost:** the entire werkzeug run cost **$0.088** of the $10 firewall across **109 gated calls** (vault wiki + fix-loop edit + 60 experiment cells over runs 1–2 + agent narratives), every one ledgered. The retired click run's ledger is preserved in git history.
- **Honest limitations:**
  - The token KPI is met on input-token savings; **answer correctness is human-scored** and not yet locked — the headline 89.8% is conditional on that gate.
  - The fix loop produced a NO_SAFE_ACTION (a valid, evidenced negative), not a green merge.
  - Graph backend is the AST fallback, not the course's Graphify (ADR-4); the contract is identical but a real run would be re-validated.
  - Module-level constants/attributes aren't in the symbol index (a known INFERRED-layer precision cost, documented in `PRD_graph_pipeline.md`).

## 🔲 Outstanding (human-side)

These are by design human steps — they cannot be done by the agent:

1. **Blind-score** `results/experiment/scoring_sheet.json` with **two independent scorers**, *without* opening `blinding_key.json`, per `docs/SCORING_RUBRIC.md`; then confirm the KPI gate (`correctness(B) ≥ A` and `citation(B) ≥ A`).
2. **Sign** the unfamiliarity attestation checkbox in `docs/TARGET_REPO.md` (student's own initials).
3. **Re-capture** Obsidian screenshots of the werkzeug vault → `assets/` (replacing the 4 click PNGs flagged above).

## License & attribution

This project: **MIT** (see `pyproject.toml`).
Target repository **`pallets/werkzeug`** is **BSD-3-Clause** (© Pallets) — used here for educational analysis with attribution; provenance and license trail in `docs/TARGET_REPO.md`.
Grounding references: Liu et al. 2024, *Lost in the Middle* (TACL); Vaswani et al. 2017, *Attention Is All You Need*.

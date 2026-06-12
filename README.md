# HW4 — EX04: Graph-Based Reverse Engineering with AI Agents

Reverse-engineers an unfamiliar Python repository through a knowledge
graph (AST extractor with a Graphify-compatible contract), navigates it
as an Obsidian vault + LLM wiki, detects **architectural** defects
(SPOF, god modules, isolation, traceability gaps) with evidence-chained
findings, fixes them in a **test-guarded improvement loop**, and
measures the **token savings** of graph-guided retrieval vs naive
context stuffing in a frozen A/B experiment.

> Course: Lecture 07 — Reverse Engineering of Graph Knowledge Systems
> (Dr. Yoram Segal, June 2026). Governing docs: `docs/PRD.md`,
> `docs/PLAN.md`, `docs/TODO.md` (515 tasks), 6 dedicated mechanism PRDs.

## Status at a glance

| Axis | State |
|---|---|
| Engineering | 338 tests green · coverage ≈96% (gate 85%) · ruff 0 · all files ≤150 code lines · `scripts/check_gates.py` GREEN |
| Analysis | target `pallets/click@8a1b1a3` graphed (1,226 nodes / 2,070 edges), **2 source-validated defects** (`results/FINDINGS.md`) |
| Live LLM runs | wiki generation, agent narratives, A/B measurement, live fix loop — **pending `ANTHROPIC_API_KEY` in `.env`** (everything else proven with fake transports) |

## Installation

Prerequisites: `git` and [uv](https://docs.astral.sh/uv/) — install with
`curl -LsSf https://astral.sh/uv/install.sh | sh`. uv provisions the
pinned Python automatically (developed on uv-managed CPython 3.12.13;
`requires-python >=3.10`). **No pip, no venv, ever** — uv only.

```bash
git clone https://github.com/yosefshanaa/HW4 && cd HW4
uv sync                 # full environment from uv.lock
cp .env-example .env    # then put a real ANTHROPIC_API_KEY inside
uv run pytest -q        # 338 tests, coverage gate 85%
uv run python scripts/check_gates.py   # all submission gates
```

## Usage tour (CLI = thin shell over the `Hw4Sdk` facade)

```bash
uv run hw4 graph workspace/target            # immutable graph iteration + metrics
uv run hw4 analyze                           # detectors -> results/findings.json
uv run hw4 analyze --agents                  # same findings + CrewAI narratives
uv run hw4 vault                             # Obsidian vault + LLM wiki pages
uv run hw4 ask "where is echo implemented?"  # graph-guided, cited answer
uv run hw4 fix F-003                         # test-guarded fix loop (branch-isolated)
uv run hw4 experiment --condition both       # frozen A/B token experiment
uv run hw4 report --dashboard                # REPORT.md + Refactor Truth Dashboard
```

Direct vs agent analyze: findings are identical by construction
(deterministic detectors); `--agents` adds careful-language narratives —
determinism for science, agents for demonstration.

## Repository layout

| Path | Purpose |
|---|---|
| `src/hw4/sdk/` | `Hw4Sdk` facade + operation modules (NFR-1: CLI/agents hold zero logic) |
| `src/hw4/shared/` | config (versioned JSON + env overrides), **API Gatekeeper** (rate windows, FIFO queue, retries, budget firewall), token ledger, process runner, gated LLM client |
| `src/hw4/services/` | extractor (graph contract), metrics/diff, vault+wiki, retrieval, detectors, fix loop, experiment, CrewAI agents, dashboard |
| `tests/` | unit+integration, mirrors `src/` 1:1; `tests/fixtures/mini_repo/` is the planted-defect answer key |
| `config/` | versioned JSON config — **zero hardcoded values in code**; secrets only via env |
| `docs/` | PRD/PLAN/TODO, 6 mechanism PRDs, SKILL protocols, PROMPTS log, TARGET_REPO |
| `data/` | frozen question dataset (sha256-sealed in PRD_token_experiment) |
| `results/` | graph iterations, findings, FINDINGS.md, loop log, experiment artifacts |
| `notebooks/` | `analysis.ipynb` — executes top-to-bottom from committed artifacts |
| `vault/` | Obsidian vault (taxonomy + wiki incl. SKILL mirrors) |
| `workspace/` | target clone (gitignored; regenerate: `rm -rf workspace/target` then `RepoService.clone(url, commit=<SHA>)`) |

## Reproducing the analysis

1. `uv run hw4 graph workspace/target --iteration 0` — deterministic:
   identical content hash on rebuild (proven in `results/graphs/i00/VALIDATION.md`).
2. `uv run hw4 analyze` — 15 hypotheses on click; triage trail with
   2 validations + 13 reasoned rejections in `results/FINDINGS.md`.
3. Notebook: build/execute without touching the project venv:
   `uv run --with nbformat python scripts/build_notebook.py` then
   `uv run --with nbformat --with nbclient --with ipykernel --with matplotlib python scripts/execute_notebook.py`.

## Key design decisions (ADRs in `docs/PLAN.md` §5)

- **One choke point** for every external call (`ApiGatekeeper`): rate
  limits, queue-not-drop, bounded retries, budget firewall, JSONL token
  ledger. The LLM client cannot be constructed without it.
- **Evidence as a first-class enum** (EXTRACTED/INFERRED/AMBIGUOUS) from
  extractor to findings to fix-eligibility: AMBIGUOUS never feeds
  automated change.
- **Deterministic spine, LLM at the edges**: metrics, diffs, detectors,
  loop control are plain Python; the LLM writes narratives, plans, and
  edits only — through the gate.
- **Graphify fallback executed** (ADR-4): the course tool was
  unobtainable; the in-repo AST backend emits the identical contract.
- Future work parked deliberately (T410): org-graph heatmap, test-gap
  overlay — see `docs/TODO.md` backlog.

## License

MIT — see `pyproject.toml`. Target repository `pallets/click` is
BSD-3-Clause; provenance and attribution in `docs/TARGET_REPO.md`.

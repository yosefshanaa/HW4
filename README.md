# HW4 — EX04: Graph-Based Reverse Engineering with AI Agents

Reverse-engineers an unfamiliar Python repository through a knowledge graph
(Graphify / AST fallback), navigates it as an Obsidian vault + LLM Wiki, and
drives a multi-agent loop that detects and fixes **architectural** defects
(SPOF, god nodes, traceability gaps) while proving **token savings** of
graph-guided retrieval versus naive context stuffing.

> Course: Lecture 07 — Reverse Engineering of Graph Knowledge Systems
> (Dr. Yoram Segal, June 2026). See `docs/PRD.md`, `docs/PLAN.md`,
> `docs/TODO.md` for the full requirement/architecture/task suite.

## Status

Under active development — milestone M1 (skeleton + quality gates).
This README will become a complete user manual by milestone M8
(installation, usage tour, configuration guide, results).

## Quick start (development)

Prerequisites: `git` and [uv](https://docs.astral.sh/uv/) — install with
`curl -LsSf https://astral.sh/uv/install.sh | sh`. uv provisions the
pinned Python automatically (developed on uv-managed CPython 3.12.13;
`requires-python >=3.10`). **No pip, no venv, ever** — uv only.

```bash
uv sync                 # install all dependencies from uv.lock
cp .env-example .env    # then fill in real API keys
uv run pytest           # run test suite (coverage gate: 85%)
uv run ruff check       # lint (zero violations policy)
```

## Repository layout

| Path | Purpose |
|---|---|
| `src/hw4/` | The tool: SDK facade, services, shared infra (gatekeeper, config) |
| `tests/` | Unit + integration tests (mirror `src/` 1:1) |
| `config/` | Versioned JSON configuration (no hardcoded values in code) |
| `docs/` | PRD, PLAN, TODO, dedicated PRDs, prompt log |
| `vault/` | Obsidian vault (LLM Wiki: raw / wiki / index.md / log.md) |
| `results/` | Graph iterations, findings, experiment data, figures |
| `workspace/` | Cloned target repository (gitignored, regenerable) |

Target repo (locked, see `docs/TARGET_REPO.md`): **pallets/click** pinned at
`8a1b1a3`. Regenerate the workspace anytime: `rm -rf workspace/target`, then
re-clone via `RepoService.clone(url, commit=<SHA>)` — never edit it on `main`.

## License

MIT — see `pyproject.toml`. Target-repository attribution will be recorded
in `docs/TARGET_REPO.md`.

"""Build notebooks/analysis.ipynb programmatically (Phase 11).

Why generated: the notebook must always match the artifact schema the
code produces; generating it from one script keeps them in lockstep and
makes 'restart kernel -> run all' reproducible by construction.

Run (ephemeral overlay keeps heavy viz deps out of the project venv):
    uv run --with nbformat python scripts/build_notebook.py
    uv run --with nbformat --with nbclient --with ipykernel \
        --with matplotlib python scripts/execute_notebook.py
"""

from __future__ import annotations

import pathlib

import nbformat as nbf

nb = nbf.v4.new_notebook()
cells = []


def md(text: str) -> None:
    cells.append(nbf.v4.new_markdown_cell(text))


def code(source: str) -> None:
    cells.append(nbf.v4.new_code_cell(source))


md("""# HW4 — Research Notebook: graph-guided analysis of pallets/werkzeug

Executes top-to-bottom from **committed artifacts** (`results/`,
`config/`, `data/`) — including the LIVE 2026-06-15 measurements
(experiment comparison, fix-loop log). Cells degrade to clearly-labeled
estimates if an artifact is absent; nothing here invents numbers.

Grounding: Liu et al. 2024, *Lost in the Middle: How Language Models Use
Long Contexts* (TACL) — the position-aware context assembly used by both
the retriever and the experiment conditions; Vaswani et al. 2017,
*Attention Is All You Need* — why attention over long undifferentiated
context degrades.
""")

code("""# §1 Setup — every path comes from config (no hardcoded paths)
import json
from pathlib import Path
import matplotlib.pyplot as plt

from hw4.shared.config import Config
from hw4.services.graph_models import Graph

ROOT = Path.cwd() if (Path.cwd() / "config").is_dir() else Path.cwd().parent
cfg = Config(ROOT / "config", environ={})
RESULTS = ROOT / cfg.path("results")
ASSETS = ROOT / "assets"
ASSETS.mkdir(exist_ok=True)

def load_json(path):
    path = Path(path)
    return json.loads(path.read_text()) if path.exists() else None

manifest = load_json(RESULTS / "graphs/i00/manifest.json")
metrics = load_json(RESULTS / "graphs/i00/metrics.json")
findings = load_json(RESULTS / "findings.json")
comparison = load_json(RESULTS / "experiment/comparison.json")
loop_log = load_json(RESULTS / "loop_log.json")
print("artifacts:", {k: v is not None for k, v in {
    "manifest": manifest, "metrics": metrics, "findings": findings,
    "comparison": comparison, "loop_log": loop_log}.items()})""")

md("## §2 Graph overview — iteration 0")

code("""graph = Graph.load(RESULTS / "graphs/i00/graph.json")
from collections import Counter
node_types = Counter(n.type for n in graph.nodes.values())
evidence = Counter(e.evidence.value for e in graph.edges)
relations = Counter(e.relation for e in graph.edges)
print(f"nodes={len(graph.nodes)}  edges={len(graph.edges)}  "
      f"backend={graph.backend}  hash={manifest['content_hash'][:12]}")
print("node types:", dict(node_types))
print("evidence:", dict(evidence))
print("relations:", dict(relations))""")

code("""# community size distribution (dependency communities, singletons excluded)
sizes = Counter(metrics["community_of"].values())
big = sorted((s for s in sizes.values() if s >= 3), reverse=True)
fig, ax = plt.subplots(figsize=(8, 3.5))
ax.bar(range(len(big)), big, color="#4878a8")
ax.set_xlabel("community (rank by size)"); ax.set_ylabel("members")
ax.set_title("werkzeug i00 — dependency-community sizes (≥3 members)")
fig.tight_layout(); fig.savefig(ASSETS / "communities.png", dpi=150)
plt.show()
print(f"{len(big)} non-trivial communities; largest: {big[:5]}")""")

md("""Interpretation: a handful of real clusters (core package spine,
HTTP header + response layer, dev-server, form parsing, test suites)
over a long singleton tail — consistent with a mature single-purpose
library. The two validated findings sit exactly on the biggest
connectors (FINDINGS.md §3).""")

md("""## §3 Token experiment — A (naive) vs B (graph-guided)

Savings definition (per question $q$, repetitions summed):

$$\\mathrm{savings}_q = 1 - \\frac{T^{B}_{q}}{T^{A}_{q}}$$

where $T$ is **input tokens from the provider API metadata** recorded by
the Gatekeeper ledger — never a local estimate.""")

code("""if comparison:
    rows = comparison["per_question"]
    qids = [r["question_id"] for r in rows]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))
    x = range(len(qids))
    ax1.bar([i - 0.2 for i in x], [r["input_tokens_A"] for r in rows],
            width=0.4, label="A naive", color="#a85048")
    ax1.bar([i + 0.2 for i in x], [r["input_tokens_B"] for r in rows],
            width=0.4, label="B graph", color="#48a878")
    ax1.set_xticks(list(x), qids, rotation=45); ax1.legend()
    ax1.set_ylabel("input tokens"); ax1.set_title("input tokens per question")
    ax2.bar(x, [r["savings"] * 100 for r in rows], color="#4878a8")
    ax2.axhline(70, color="red", linestyle="--", label="70% target")
    ax2.set_xticks(list(x), qids, rotation=45); ax2.set_ylabel("savings %")
    ax2.set_title("per-question savings"); ax2.legend()
    fig.tight_layout(); fig.savefig(ASSETS / "experiment_savings.png", dpi=150)
    plt.show()
    print("totals:", comparison["totals"])
else:
    print("LIVE DATA PENDING (no comparison.json found).")
    print("Falling through to offline ESTIMATES below — budget-guard grade,")
    print("clearly not the measurement (PLAN §4.4).")""")

code("""# Offline projection (ESTIMATES): assemble both conditions' prompts now
target = ROOT / cfg.path("workspace") / str(cfg.get("repo.default_dirname"))
if comparison is None and target.is_dir():
    from hw4.services.experiment.conditions import naive_bundle
    from hw4.services.experiment.questions import load_questions
    from hw4.services.retrieval import Retriever, estimate_tokens
    from hw4.services.vault_builder import VaultBuilder

    questions = load_questions(ROOT / cfg.path("data") / "questions.yaml")
    retriever = Retriever(cfg, VaultBuilder(cfg, base_dir=ROOT))
    est = []
    for q in questions:
        a = naive_bundle(q, target, cfg).token_estimate
        try:
            b = retriever.retrieve(q.question, graph).token_estimate
        except Exception:
            b = None
        est.append((q.id, q.tier, a, b))
    fig, ax = plt.subplots(figsize=(9, 3.5))
    xs = range(len(est))
    ax.bar([i - 0.2 for i in xs], [e[2] for e in est], width=0.4,
           label="A est.", color="#d4a373")
    ax.bar([i + 0.2 for i in xs], [e[3] or 0 for e in est], width=0.4,
           label="B est.", color="#74a892")
    ax.set_xticks(list(xs), [e[0] for e in est], rotation=45)
    ax.set_ylabel("estimated tokens (chars/4)"); ax.legend()
    ax.set_title("ESTIMATED context sizes (pre-measurement projection)")
    fig.tight_layout(); fig.savefig(ASSETS / "experiment_estimates.png", dpi=150)
    plt.show()
    proj = [1 - (e[3] / e[2]) for e in est if e[3]]
    if proj:
        print(f"projected mean savings (estimate-grade): {sum(proj)/len(proj):.1%}")
""")

md("## §4 Parameter sensitivity (NFR-12, OAT) — retrieval caps vs context size")

code("""# Token side is measurable offline; the quality axis needs the live run.
if target.is_dir():
    from hw4.services.experiment.questions import load_questions
    from hw4.services.retrieval import Retriever
    from hw4.services.vault_builder import VaultBuilder
    import copy, itertools

    questions = load_questions(ROOT / cfg.path("data") / "questions.yaml")[:3]
    results = []
    for k_pages, radius in itertools.product((1, 2, 3), (1, 2)):
        env = {"HW4__retrieval__k_pages": str(k_pages),
               "HW4__retrieval__ego_radius": str(radius)}
        c = Config(ROOT / "config", environ=env)
        retr = Retriever(c, VaultBuilder(c, base_dir=ROOT))
        toks = []
        for q in questions:
            try:
                toks.append(retr.retrieve(q.question, graph).token_estimate)
            except Exception:
                pass
        if toks:
            results.append((f"k={k_pages},r={radius}", sum(toks) / len(toks)))
    if results:
        fig, ax = plt.subplots(figsize=(7, 3.2))
        ax.bar([r[0] for r in results], [r[1] for r in results], color="#4878a8")
        ax.set_ylabel("mean bundle tokens (est.)")
        ax.set_title("sensitivity: retrieval caps vs context size (3-question OAT)")
        fig.tight_layout(); fig.savefig(ASSETS / "sensitivity.png", dpi=150)
        plt.show()
        for label, value in results: print(f"{label}: {value:.0f}")""")

md("## §5 Fix loop — structural deltas per iteration")

code("""if loop_log and loop_log.get("iterations"):
    its = loop_log["iterations"]
    fig, ax = plt.subplots(figsize=(7, 3.2))
    ax.plot([i["iteration"] for i in its],
            [i["metric_deltas"]["bottleneck_before"] for i in its],
            "o--", label="before")
    ax.plot([i["iteration"] for i in its],
            [i["metric_deltas"]["bottleneck_after"] for i in its],
            "o-", label="after")
    ax.set_xlabel("iteration"); ax.set_ylabel("top bottleneck score"); ax.legend()
    ax.set_title("fix loop: did the structure actually improve?")
    fig.tight_layout(); fig.savefig(ASSETS / "fixloop_deltas.png", dpi=150)
    plt.show()
    print("stop reason:", loop_log["stop_reason"])
else:
    print("No loop run recorded yet (live fix run pending API key).")
    print("Control flow proven in tests; see results/dashboard.md once run.")""")

md("## §6 Cost analysis (guidelines §11) — ledger by purpose tag")

code("""from hw4.shared.ledger import Ledger
ledger = Ledger(cfg, RESULTS / "ledger.jsonl")
prefixes = ["wiki.gen", "agent", "fixloop", "experiment.A", "experiment.B",
            "ask", "compact"]
table = {p: ledger.totals(purpose_prefix=p) for p in prefixes}
print(f"{'purpose':<14}{'calls':>6}{'in_tok':>10}{'out_tok':>10}{'usd':>10}")
for p, t in table.items():
    print(f"{p:<14}{t['calls']:>6}{t['input_tokens']:>10}"
          f"{t['output_tokens']:>10}{t['cost_usd']:>10.4f}")
grand = ledger.totals()
print("-" * 50)
print(f"{'TOTAL':<14}{grand['calls']:>6}{grand['input_tokens']:>10}"
      f"{grand['output_tokens']:>10}{grand['cost_usd']:>10.4f}")
print(f"budget: ${cfg.get('budget.max_usd')} (warn ${cfg.get('budget.warn_usd')})")
print("Optimization already in force: cheap tier for narrative/wiki,")
print("strong tier only for code edits + experiment cells (ADR-3).")""")

md("""## §7 Conclusions — KPI status vs PRD §3.2

| KPI | Target | Status (LIVE, 2026-06-15) |
|---|---|---|
| Token savings | ≥70% input tokens | **below target: 58.7%** overall (median 60.2%); honest failure analysis — Condition B is already lean (~6.5k tok/cell), so the gap is bounded by the naive 16k cap, not over-provisioning |
| Validated defects | ≥2 | **met** — F-005 http god-node, F-001 datastructures god-node (source-validated) |
| Auto-fix | ≥1 loop fix, tests green | **honest NO_SAFE_ACTION**: the http helper-extraction kept all 992 target tests green but showed no structural gain, so the graph-diff guard reverted it (FINDINGS §8) |
| Coverage | ≥85% | **met** — ≈96% |
| Gates | ruff 0, ≤150 lines/file, no hardcodes/secrets | **met** — check_gates GREEN |

The auto-fix KPI is reported as an evidenced negative per T340: the
http god-node resists *metric-improving* extraction because its fan-in
(21 importers) is unchanged by relocating private helpers — the loop
restated finding F-005 empirically. Blind quality scoring of the
experiment answers (sheet + sealed key in results/experiment/) remains
a human step before final submission.""")

nb["cells"] = cells
nb["metadata"]["kernelspec"] = {
    "name": "python3", "display_name": "Python 3", "language": "python",
}
out = "notebooks/analysis.ipynb"
pathlib.Path("notebooks").mkdir(exist_ok=True)
nbf.write(nb, out)
print("wrote", out, f"({len(cells)} cells)")

"""Obsidian pages for the debugging case (EX04 §5.1, §5.4).

Gives the bug its own vault project so the knowledge architecture covers
the debugging thread, not just the architectural analysis: a bug-focused
`hot.md`, a navigation `index.md`, the bug page, and the knowledge-level
before/after the fix. Deterministic projection of the DebugResult — no LLM.
"""

from __future__ import annotations

from pathlib import Path

from hw4.services.debug.case import DebugResult
from hw4.services.vault_builder import AUTO_MARK, frontmatter

PROJECT = "range-debug"


def write_debug_vault(vault_dir: Path | str, result: DebugResult) -> Path:
    """Write the four debug pages; return the bug-focused hot.md path."""
    project = Path(vault_dir) / "20_Projects" / PROJECT
    project.mkdir(parents=True, exist_ok=True)
    pages = {
        "index.md": _index(),
        "hot.md": _hot(result),
        "bug.md": _bug(result),
        "knowledge-before-after.md": _knowledge(result),
    }
    for name, body in pages.items():
        (project / name).write_text(body, encoding="utf-8")
    return project / "hot.md"


def _head(note_type: str, title: str) -> str:
    return f"{frontmatter(note_type, PROJECT, status='generated').rstrip()}\n{AUTO_MARK}\n# {title}\n"


def _index() -> str:
    return _head("index", f"{PROJECT} — graph-guided debugging of the byte-range bug") + (
        "\nStart at [[hot]] for the focused bug context.\n\n## Pages\n"
        "- [[hot]] — focused context for the bug investigation\n"
        "- [[bug]] — the defect, root cause, and verified fix\n"
        "- [[knowledge-before-after]] — how understanding changed after the fix\n"
    )


def _hot(r: DebugResult) -> str:
    return _head("hot", "hot — focused context for the byte-range off-by-one") + (
        "\n> Load this first. The failing spec localizes the defect via the graph;\n"
        "> read ONLY the named module below — not the whole package.\n\n"
        "## Symptom\n"
        f"`parse_byte_range(\"{r.case.split(' of ')[0]}\", {r.case.split(' of ')[1]})` returns "
        f"content-length **{r.buggy_value}**, but HTTP ranges are inclusive "
        f"(RFC 9110 §14.1.2) → must be **{r.expected}**.\n\n"
        "## Graph localization (read first)\n"
        f"Failing test `tests.test_range` →(`tested_by`)→ **`{r.located_module}`** — the one "
        f"module to open ({r.graph_tokens} tok), not the whole package ({r.naive_tokens} tok).\n\n"
        f"## Suspect\n`{r.located_module}.parse_byte_range` — the content-length computation.\n\n"
        "## Links\n- [[bug]] — root cause + fix\n- [[index]] — debug navigation\n"
    )


def _bug(r: DebugResult) -> str:
    return _head("note", "bug — byte-range off-by-one") + (
        f"\n**Symptom:** length {r.buggy_value} for `{r.case}`, expected {r.expected}.\n\n"
        "**Root cause:** content length computed `end - start` (end-exclusive) instead of "
        "`end - start + 1` (HTTP ranges are inclusive).\n\n"
        f"**Fix:** add `+ 1`; the spec goes red→green ({r.buggy_value}→{r.fixed_value}).\n\n"
        "Full report: `results/BUG_ANALYSIS.md`. See [[knowledge-before-after]].\n"
    )


def _knowledge(r: DebugResult) -> str:
    return _head("note", "knowledge before / after the fix") + (
        "\nWhat the knowledge architecture looked like before the research, and after the fix "
        "(EX04 §5.4 — knowledge-level before/after):\n\n"
        "| Aspect | Before research | After fix |\n|---|---|---|\n"
        f"| Suspect node | unknown — symptom only | `{r.located_module}.parse_byte_range` (graph-localized) |\n"
        "| hot.md | none | points at the localized module + suspect |\n"
        f"| Decisive edge | — | `tests.test_range` —tested_by→ `{r.located_module}` |\n"
        "| Understanding | \"a range is wrong somewhere\" | inclusive-range contract pinned by 4 spec cases |\n"
        "| Pages added | — | [[bug]], [[hot]], this page |\n\n"
        "The graph turned a whole-package search into a one-module read: the failing test's "
        "`tested_by` edge was the link that named the suspect.\n"
    )

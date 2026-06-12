"""Experiment condition builders (FR-8.2, T268-T270).

Condition A mimics "regular work" (L07 §7): grep the repo for the
question's terms, open the matching files, and paste them whole — plus
a full file listing standing in for "all skill descriptions loaded by
default". Both conditions share the SAME instruction block and the same
instructions-first / question-last placement; only the middle differs —
that is the variable under test.

Truncation in A is not an error: it is logged and reported as a result
(the context bottleneck is the thesis). Token estimates here are budget
guards; the measured numbers come from the Gatekeeper ledger.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from hw4.services.experiment.questions import Question
from hw4.services.retrieval import estimate_tokens
from hw4.shared.config import Config
from hw4.shared.logging_setup import get_logger, log_event

WORD = re.compile(r"[a-z_][a-z0-9_]+")
MIN_PARTIAL_CHARS = 200  # below this, a file fragment carries no signal
EXPERIMENT_INSTRUCTIONS = (
    "Answer the question at the end using ONLY the material below. "
    "Cite the source files your answer relies on. "
    "If the material is insufficient, say exactly that instead of guessing."
)


@dataclass(frozen=True)
class NaiveBundle:
    """Condition A context: grep-selected whole files + a repo listing."""

    question: str
    files: list[str]
    text: str
    token_estimate: int
    truncated: bool

    def assemble(self, instructions: str = EXPERIMENT_INSTRUCTIONS) -> str:
        return f"{instructions}\n\n{self.text}\n\nQUESTION: {self.question}"


def naive_bundle(question: Question, repo_root: Path | str, config: Config) -> NaiveBundle:
    repo_root = Path(repo_root)
    cap = int(config.get("experiment.naive_context_token_cap"))
    sources = _python_sources(repo_root, set(config.get("graph.exclude_dirs")))
    ranked = _rank_by_grep(question.question, sources)

    parts = [_file_listing(sources, repo_root)]
    included, truncated = [], False
    for path, _score in ranked:
        rel = path.relative_to(repo_root).as_posix()
        content = path.read_text(encoding="utf-8", errors="replace")
        section = f"### file: {rel}\n{content}"
        if estimate_tokens("\n\n".join([*parts, section])) <= cap:
            parts.append(section)
            included.append(rel)
            continue
        # a developer pastes as much of the file as still fits — the cut
        # lands mid-file (the classic lost-in-the-middle setup), and the
        # truncation itself is a recorded result, not an error
        budget_chars = (cap - estimate_tokens("\n\n".join(parts))) * 4
        if budget_chars >= MIN_PARTIAL_CHARS:
            parts.append(section[:budget_chars] + "\n### [TRUNCATED at context cap]")
            included.append(f"{rel} (truncated)")
        truncated = True
        log_event(
            get_logger("experiment"),
            "condition A truncation",
            question=question.id,
            cut_file=rel,
        )
        break
    text = "\n\n".join(parts)
    return NaiveBundle(
        question=question.question,
        files=included,
        text=text,
        token_estimate=estimate_tokens(text),
        truncated=truncated,
    )


def naive_prompt_builder(repo_root: Path | str, config: Config):
    """PromptBuilder for Condition A (runner-compatible factory)."""

    def build(question: Question) -> tuple[str, dict]:
        bundle = naive_bundle(question, repo_root, config)
        return bundle.assemble(), {
            "prompt_token_estimate": bundle.token_estimate,
            "truncated": bundle.truncated,
            "files": bundle.files,
        }

    return build


def graph_prompt_builder(retriever, graph):
    """PromptBuilder for Condition B — same instructions, same placement;
    only the middle differs (index + focused subgraph + wiki pages)."""

    def build(question: Question) -> tuple[str, dict]:
        bundle = retriever.retrieve(question.question, graph)
        return bundle.assemble(EXPERIMENT_INSTRUCTIONS), {
            "prompt_token_estimate": bundle.token_estimate,
            "truncated": bundle.truncated,
            "matched_nodes": bundle.matched_nodes,
        }

    return build


def _python_sources(repo_root: Path, exclude_dirs: set[str]) -> list[Path]:
    return [
        path
        for path in sorted(repo_root.rglob("*.py"))
        if not any(part in exclude_dirs for part in path.relative_to(repo_root).parts)
    ]


def _rank_by_grep(question_text: str, sources: list[Path]) -> list[tuple[Path, int]]:
    """The 'developer greps' selection rule — documented, deterministic."""
    terms = set(WORD.findall(question_text.lower()))
    scored = []
    for path in sources:
        content = path.read_text(encoding="utf-8", errors="replace").lower()
        score = sum(content.count(term) for term in terms)
        if score > 0:
            scored.append((path, score))
    scored.sort(key=lambda item: (-item[1], item[0].as_posix()))
    return scored


def _file_listing(sources: list[Path], repo_root: Path) -> str:
    """Stands in for 'all skill descriptions present by default' (L07 §7)."""
    lines = ["### repository file listing"]
    lines += [f"- {p.relative_to(repo_root).as_posix()}" for p in sources]
    return "\n".join(lines)

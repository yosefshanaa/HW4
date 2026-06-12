"""Edit-block mechanics for the fix applier (§3.2 split from applier.py).

SEARCH/REPLACE and CREATE block parsing, byte-exact application with a
path jail, and the post-apply parse gate. Pure functions — no git, no
LLM — so every safety property here is unit-testable in isolation.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path

BLOCK = re.compile(
    r"FILE:\s*(?P<file>\S+)\s*\n<{7} SEARCH\n(?P<search>.*?)\n={7}\n(?P<replace>.*?)\n>{7} REPLACE",
    re.DOTALL,
)
CREATE_BLOCK = re.compile(
    r"FILE:\s*(?P<file>\S+)\s*\n<{7} CREATE\n(?P<content>.*?)\n>{7} CREATE",
    re.DOTALL,
)


class ApplyFailedError(RuntimeError):
    """The edit could not be applied safely; the tree was reverted."""


@dataclass(frozen=True)
class EditBlock:
    file: str
    search: str
    replace: str


def strip_fences(text: str) -> str:
    text = text.strip()
    if not text.startswith("```"):
        return text
    lines = text.splitlines()[1:]
    if lines and lines[-1].strip().startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines)


def parse_blocks(text: str) -> list[EditBlock]:
    return [
        EditBlock(m.group("file"), m.group("search"), m.group("replace"))
        for m in BLOCK.finditer(text)
    ]


def parse_creates(text: str) -> list[EditBlock]:
    """CREATE blocks reuse EditBlock with an empty search."""
    return [
        EditBlock(m.group("file"), "", m.group("content"))
        for m in CREATE_BLOCK.finditer(text)
    ]


def apply_blocks(
    repo: Path, blocks: list[EditBlock], creates: list[EditBlock], allowed: tuple[str, ...]
) -> list[str]:
    if not blocks and not creates:
        raise ApplyFailedError("no edit blocks found in the response")
    changed = []
    allowed_dirs = {str(Path(name).parent) for name in allowed}
    for block in creates:
        if str(Path(block.file).parent) not in allowed_dirs:
            raise ApplyFailedError(f"new file {block.file} outside the target directories")
        path = repo / block.file
        if path.exists():
            raise ApplyFailedError(f"CREATE targets existing file {block.file}")
        path.write_text(block.replace + "\n", encoding="utf-8")
        changed.append(block.file)
    for block in blocks:
        if block.file not in allowed:
            raise ApplyFailedError(f"edit touches non-target file {block.file}")
        path = repo / block.file
        content = path.read_text(encoding="utf-8")
        if block.search not in content:
            raise ApplyFailedError(f"SEARCH block does not match {block.file}")
        path.write_text(content.replace(block.search, block.replace, 1), encoding="utf-8")
        changed.append(block.file)
    _assert_python_parses(repo, changed)
    return changed


def _assert_python_parses(repo: Path, changed: list[str]) -> None:
    """A refactor that breaks parsing is rejected as feedback, not a red run."""
    for name in changed:
        if not name.endswith(".py"):
            continue
        try:
            ast.parse((repo / name).read_text(encoding="utf-8"))
        except SyntaxError as exc:
            raise ApplyFailedError(f"{name} no longer parses: {exc}") from exc

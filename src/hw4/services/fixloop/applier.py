"""Branch-isolated edit application (T324-T328).

Safety mechanics: every fix lives on `fix/<finding-id>`; the base SHA is
recorded before any edit so revert is one `git reset --hard`. The LLM
(strong tier, gated) proposes SEARCH/REPLACE blocks against ONLY the
plan's target files; a block that does not match exactly is rejected and
retried once with the error as feedback — we never fuzzy-apply. If the
plan demands characterization tests, they are generated and must pass on
the ORIGINAL code before any edit lands (FR-7.5).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from hw4.constants import ModelTier
from hw4.services.fixloop.planner import FixPlan
from hw4.shared.config import Config
from hw4.shared.llm_client import LlmClient
from hw4.shared.process_runner import ProcessRunner

BLOCK = re.compile(
    r"FILE:\s*(?P<file>\S+)\s*\n<{7} SEARCH\n(?P<search>.*?)\n={7}\n(?P<replace>.*?)\n>{7} REPLACE",
    re.DOTALL,
)
CREATE_BLOCK = re.compile(
    r"FILE:\s*(?P<file>\S+)\s*\n<{7} CREATE\n(?P<content>.*?)\n>{7} CREATE",
    re.DOTALL,
)
EDIT_SYSTEM = (
    "You are applying one bounded refactor. Respond ONLY with edit blocks.\n"
    "To edit an existing listed file:\n"
    "FILE: <path>\n<<<<<<< SEARCH\n<exact existing lines>\n=======\n"
    "<replacement lines>\n>>>>>>> REPLACE\n"
    "SEARCH must match the file byte-for-byte.\n"
    "To create ONE new module (only in the same directory as a listed file):\n"
    "FILE: <new path>\n<<<<<<< CREATE\n<full file content>\n>>>>>>> CREATE\n"
    "Every import you reference must exist after your blocks are applied."
)
CHAR_SYSTEM = (
    "Write one complete pytest file that pins the CURRENT behavior of the "
    "given code (characterization tests). Respond with Python code only."
)


class ApplyFailedError(RuntimeError):
    """The edit could not be applied safely; the tree was reverted."""


@dataclass(frozen=True)
class EditBlock:
    file: str
    search: str
    replace: str


@dataclass(frozen=True)
class ApplyResult:
    branch: str
    base_sha: str
    files_changed: tuple[str, ...]
    characterization_test: str = ""


def _strip_fences(text: str) -> str:
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
    import ast

    for name in changed:
        if not name.endswith(".py"):
            continue
        try:
            ast.parse((repo / name).read_text(encoding="utf-8"))
        except SyntaxError as exc:
            raise ApplyFailedError(f"{name} no longer parses: {exc}") from exc


class Applier:
    """Execute one FixPlan on a git working tree."""

    def __init__(self, config: Config, llm: LlmClient, runner: ProcessRunner, repo: Path | str):
        self._prefix = str(config.get("fixloop.branch_prefix"))
        self._test_command = [str(p) for p in config.get("fixloop.test_command")]
        self._retries = int(config.get("fixloop.max_edit_retries"))
        self._llm = llm
        self._runner = runner
        self._repo = Path(repo)

    def apply(self, plan: FixPlan) -> ApplyResult:
        base_sha = self._git("rev-parse", "HEAD").stdout.strip()
        branch = f"{self._prefix}{plan.finding_id}"
        self._git("checkout", "-B", branch)
        char_test = self._characterize(plan) if plan.needs_characterization else ""
        feedback = ""
        for _attempt in range(self._retries + 1):
            try:
                proposal = self._request_edits(plan, feedback)
                changed = apply_blocks(
                    self._repo, parse_blocks(proposal), parse_creates(proposal),
                    plan.target_files,
                )
                return ApplyResult(branch, base_sha, tuple(changed), char_test)
            except ApplyFailedError as exc:
                feedback = str(exc)
                self.revert(base_sha)
        raise ApplyFailedError(f"{plan.finding_id}: edits unappliable after retry: {feedback}")

    def run_tests(self) -> bool:
        result = self._runner.run(self._test_command, cwd=self._repo)
        # a red verdict must carry its evidence (live lesson 2026-06-12)
        self.last_test_output = (result.stdout[-1500:] + "\n" + result.stderr[-1500:]).strip()
        return result.ok

    def commit_accepted(self, finding_id: str) -> str:
        """Persist an ACCEPTED change on the fix branch — the audit trail
        must survive later checkouts (live gap found 2026-06-12)."""
        self._git("add", "-A")
        self._git("-c", "user.email=hw4@loop.local", "-c", "user.name=hw4-fixloop",
                  "commit", "-q", "-m", f"fix({finding_id}): accepted by improvement loop")
        return self._git("rev-parse", "HEAD").stdout.strip()

    def revert(self, base_sha: str) -> None:
        """Back to the pre-fix tree, including created files; the branch
        stays for audit and characterization tests are preserved."""
        self._git("reset", "--hard", base_sha)
        self._git("clean", "-fd", "-e", "tests/test_characterization_*")

    def _characterize(self, plan: FixPlan) -> str:
        prompt = "Code to pin:\n" + self._file_sections(plan.target_files)
        response = self._llm.complete(
            [{"role": "user", "content": prompt}],
            purpose_tag=f"fixloop.chartest.{plan.finding_id}",
            tier=ModelTier.STRONG, system=CHAR_SYSTEM,
        )
        test_path = self._repo / "tests" / f"test_characterization_{plan.finding_id}.py"
        test_path.parent.mkdir(exist_ok=True)
        test_path.write_text(_strip_fences(response.text), encoding="utf-8")
        if not self.run_tests():
            test_path.unlink()
            raise ApplyFailedError(
                f"{plan.finding_id}: characterization tests failed on ORIGINAL code"
            )
        return test_path.relative_to(self._repo).as_posix()

    def _request_edits(self, plan: FixPlan, feedback: str) -> str:
        prompt = (
            f"Strategy: {plan.strategy}\nSteps: {'; '.join(plan.steps)}\n"
            f"{'Previous attempt failed: ' + feedback if feedback else ''}\n"
            + self._file_sections(plan.target_files)
        )
        return self._llm.complete(
            [{"role": "user", "content": prompt}],
            purpose_tag=f"fixloop.edit.{plan.finding_id}",
            tier=ModelTier.STRONG, system=EDIT_SYSTEM,
        ).text

    def _file_sections(self, files: tuple[str, ...]) -> str:
        return "\n\n".join(
            f"### file: {name}\n{(self._repo / name).read_text(encoding='utf-8')}"
            for name in files
        )

    def _git(self, *args: str):
        return self._runner.run_checked(["git", "-C", str(self._repo), *args])

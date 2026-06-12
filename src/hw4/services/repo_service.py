"""Target repository acquisition & provenance (FR-1, PRD_graph_pipeline §2).

Every analysis result must trace back to one pinned commit, so cloning,
checkout, and provenance live together: you cannot obtain a RepoInfo
without the SHA, LOC stats, and license that TARGET_REPO.md requires.
All git invocations go through ProcessRunner (timeout + audit trail).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from hw4.shared.config import Config
from hw4.shared.process_runner import ProcessRunner

LICENSE_CANDIDATES = ("LICENSE", "LICENSE.txt", "LICENSE.md", "COPYING")


class DirtyWorkspaceError(RuntimeError):
    """Clone destination already exists and is not empty — refuse to mix."""


def count_code_lines(path: Path) -> int:
    """Code lines = non-blank, non-#-comment (same rule as our 150 gate)."""
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return sum(1 for line in lines if line.strip() and not line.strip().startswith("#"))


@dataclass(frozen=True)
class LocStats:
    """Python-only size snapshot of a repository tree."""

    files: int
    code_lines: int
    per_file: dict[str, int]

    def largest(self, n: int) -> list[tuple[str, int]]:
        ranked = sorted(self.per_file.items(), key=lambda item: -item[1])
        return ranked[:n]


@dataclass(frozen=True)
class RepoInfo:
    """Provenance record — the data behind docs/TARGET_REPO.md (FR-1)."""

    url: str
    path: Path
    commit_sha: str
    branch: str
    license_name: str
    loc: LocStats


class RepoService:
    """Clone, pin, and describe the target repository."""

    def __init__(self, config: Config, runner: ProcessRunner):
        self._workspace = Path(config.path("workspace"))
        self._default_dirname = str(config.get("repo.default_dirname"))
        self._runner = runner

    def clone(self, url: str, dest: Path | str | None = None, commit: str = "") -> RepoInfo:
        """Clone into the workspace and pin to a commit; refuse dirty dests."""
        dest = Path(dest) if dest else self._workspace / self._default_dirname
        if dest.exists() and any(dest.iterdir()):
            raise DirtyWorkspaceError(f"{dest} exists and is not empty — remove it first")
        self._runner.run_checked(["git", "clone", url, str(dest)])
        if commit:
            self.checkout(dest, commit)
        return self.provenance(dest, url=url)

    def checkout(self, repo_path: Path | str, commit: str) -> None:
        """Detached checkout — analysis never sits on a moving branch."""
        self._runner.run_checked(["git", "-C", str(repo_path), "checkout", "--detach", commit])

    def provenance(self, repo_path: Path | str, url: str = "") -> RepoInfo:
        """Assemble the full provenance record for an existing clone."""
        repo_path = Path(repo_path)
        return RepoInfo(
            url=url or self._git(repo_path, "remote", "get-url", "origin"),
            path=repo_path,
            commit_sha=self._git(repo_path, "rev-parse", "HEAD"),
            branch=self._git(repo_path, "rev-parse", "--abbrev-ref", "HEAD"),
            license_name=self._detect_license(repo_path),
            loc=self.loc_stats(repo_path),
        )

    def loc_stats(self, repo_path: Path | str) -> LocStats:
        """Per-file and total code lines over all tracked-tree .py files."""
        repo_path = Path(repo_path)
        per_file: dict[str, int] = {}
        for py in sorted(repo_path.rglob("*.py")):
            if ".git" in py.parts:
                continue
            per_file[py.relative_to(repo_path).as_posix()] = count_code_lines(py)
        return LocStats(files=len(per_file), code_lines=sum(per_file.values()), per_file=per_file)

    def _git(self, repo_path: Path, *args: str) -> str:
        result = self._runner.run(["git", "-C", str(repo_path), *args])
        return result.stdout.strip() if result.ok else ""

    def _detect_license(self, repo_path: Path) -> str:
        for name in LICENSE_CANDIDATES:
            candidate = repo_path / name
            if candidate.is_file():
                first_line = candidate.read_text(errors="replace").strip().splitlines()[0]
                return first_line.strip()
        return "UNKNOWN"

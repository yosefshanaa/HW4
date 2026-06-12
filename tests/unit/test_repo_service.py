"""Tests for hw4.services.repo_service — local-fixture clones, no network."""

import shutil
from pathlib import Path

import pytest

from hw4.services.repo_service import (
    DirtyWorkspaceError,
    RepoService,
    count_code_lines,
)
from hw4.shared.config import Config
from hw4.shared.process_runner import ProcessRunner

from .test_config import write_config_dir

MINI_REPO = Path(__file__).resolve().parents[1] / "fixtures" / "mini_repo"
GIT_ENV = ["-c", "user.email=test@hw4.local", "-c", "user.name=hw4-test"]


def make_service(tmp_path):
    setup = {
        "version": "1.00",
        "paths": {"workspace": str(tmp_path / "ws"), "results": "results"},
        "repo": {"timeout_seconds": 60, "default_dirname": "target"},
    }
    cfg = Config(write_config_dir(tmp_path / "cfg", setup=setup), environ={})
    runner = ProcessRunner(timeout_seconds=float(cfg.get("repo.timeout_seconds")))
    return RepoService(cfg, runner), runner


def make_git_fixture(tmp_path):
    """Copy mini_repo into tmp and turn it into a real local git repo."""
    src = tmp_path / "origin"
    shutil.copytree(MINI_REPO, src)
    (src / "LICENSE").write_text("MIT License\n\nCopyright (c) 2026 fixture\n")
    runner = ProcessRunner(timeout_seconds=60)
    runner.run_checked(["git", "init", "-q", "-b", "main", str(src)])
    runner.run_checked(["git", "-C", str(src), "add", "-A"])
    runner.run_checked(["git", "-C", str(src), *GIT_ENV, "commit", "-q", "-m", "fixture"])
    return src


class TestCountCodeLines:
    def test_blank_and_comment_lines_excluded(self, tmp_path):
        f = tmp_path / "x.py"
        f.write_text("# comment\n\nx = 1\n   \ny = 2  # trailing is code\n")
        assert count_code_lines(f) == 2


class TestLocStats:
    def test_counts_all_py_files_in_mini_repo(self, tmp_path):
        service, _ = make_service(tmp_path)
        stats = service.loc_stats(MINI_REPO)
        assert stats.files == 9
        assert "app/engine.py" in stats.per_file
        assert stats.code_lines == sum(stats.per_file.values()) > 0

    def test_largest_ranks_by_code_lines(self, tmp_path):
        service, _ = make_service(tmp_path)
        top = service.loc_stats(MINI_REPO).largest(1)
        assert top[0][0] == "app/engine.py"  # the god node is the biggest file


class TestCloneAndProvenance:
    def test_clone_pins_provenance(self, tmp_path):
        origin = make_git_fixture(tmp_path)
        service, _ = make_service(tmp_path)
        info = service.clone(str(origin))
        assert info.path == tmp_path / "ws" / "target"
        assert len(info.commit_sha) == 40
        assert info.url == str(origin)
        assert info.license_name == "MIT License"
        assert info.loc.files == 9

    def test_checkout_detaches_at_commit(self, tmp_path):
        origin = make_git_fixture(tmp_path)
        service, runner = make_service(tmp_path)
        first_sha = runner.run_checked(
            ["git", "-C", str(origin), "rev-parse", "HEAD"]
        ).stdout.strip()
        (origin / "extra.py").write_text("x = 1\n")
        runner.run_checked(["git", "-C", str(origin), "add", "-A"])
        runner.run_checked(["git", "-C", str(origin), *GIT_ENV, "commit", "-q", "-m", "second"])
        info = service.clone(str(origin), commit=first_sha)
        assert info.commit_sha == first_sha
        assert info.branch == "HEAD"  # detached — not riding a branch
        assert not (info.path / "extra.py").exists()

    def test_dirty_destination_refused(self, tmp_path):
        origin = make_git_fixture(tmp_path)
        service, _ = make_service(tmp_path)
        dest = tmp_path / "ws" / "target"
        dest.mkdir(parents=True)
        (dest / "leftover.txt").write_text("old run")
        with pytest.raises(DirtyWorkspaceError, match="not empty"):
            service.clone(str(origin))

    def test_missing_license_reported_unknown(self, tmp_path):
        origin = make_git_fixture(tmp_path)
        (origin / "LICENSE").unlink()
        runner = ProcessRunner(timeout_seconds=60)
        runner.run_checked(["git", "-C", str(origin), "add", "-A"])
        runner.run_checked(["git", "-C", str(origin), *GIT_ENV, "commit", "-q", "-m", "drop"])
        service, _ = make_service(tmp_path)
        assert service.clone(str(origin)).license_name == "UNKNOWN"

    def test_git_commands_audited_in_runner_history(self, tmp_path):
        origin = make_git_fixture(tmp_path)
        service, runner = make_service(tmp_path)
        service.clone(str(origin))
        commands = [r.command[:2] for r in runner.history]
        assert ["git", "clone"] in commands

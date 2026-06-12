"""Tests for fixloop.applier — branch isolation, exact apply, revert."""

import sys

import pytest

from hw4.services.fixloop.applier import (
    Applier,
    ApplyFailedError,
    apply_blocks,
    parse_blocks,
    parse_creates,
)
from hw4.services.fixloop.planner import FixPlan
from hw4.shared.config import Config
from hw4.shared.llm_client import LlmClient
from hw4.shared.process_runner import ProcessRunner

from .test_config import write_config_dir
from .test_gatekeeper import make_gatekeeper
from .test_llm_client import FakeTransport, response
from .test_repo_service import make_git_fixture

GOOD_EDIT = """FILE: app/utils.py
<<<<<<< SEARCH
def slugify(text):
    return "-".join(text.lower().split())
=======
def slugify(text):
    normalized = text.lower().split()
    return "-".join(normalized)
>>>>>>> REPLACE"""

BAD_EDIT = """FILE: app/utils.py
<<<<<<< SEARCH
def nonexistent():
    pass
=======
def nonexistent():
    return 1
>>>>>>> REPLACE"""

CHAR_TEST = """```python
from app.utils import clamp

def test_pin_clamp_bounds():
    assert clamp(5, 0, 10) == 5
    assert clamp(-1, 0, 10) == 0
```"""


def make_plan(needs_char=False):
    return FixPlan(
        finding_id="F-001", strategy="extract helpers",
        target_files=("app/utils.py",), steps=("apply", "test"),
        expected_metric_delta="degree drops", test_strategy="existing suite",
        needs_characterization=needs_char,
    )


def make_applier(tmp_path, script):
    setup = {
        "version": "1.00",
        "paths": {"results": "results"},
        "models": {"cheap": "model-cheap", "strong": "model-strong"},
        "llm": {"max_output_tokens": 64, "api_key_env": "K"},
        "fixloop": {"branch_prefix": "fix/", "max_edit_retries": 1,
                    "test_command": [sys.executable, "-m", "pytest", "-q", "tests"]},
    }
    cfg = Config(write_config_dir(tmp_path / "cfg", setup=setup), environ={})
    gate, ledger, _ = make_gatekeeper(tmp_path, rpm=1000)
    llm = LlmClient(cfg, gate, FakeTransport(script))
    repo = make_git_fixture(tmp_path)
    runner = ProcessRunner(timeout_seconds=120)
    return Applier(cfg, llm, runner, repo), repo, runner, ledger


def git_out(runner, repo, *args):
    return runner.run_checked(["git", "-C", str(repo), *args]).stdout.strip()


class TestParsing:
    def test_parse_blocks_extracts_fields(self):
        blocks = parse_blocks(GOOD_EDIT)
        assert len(blocks) == 1
        assert blocks[0].file == "app/utils.py"
        assert "slugify" in blocks[0].search

    def test_apply_rejects_non_target_files(self, tmp_path):
        with pytest.raises(ApplyFailedError, match="non-target"):
            apply_blocks(tmp_path, parse_blocks(GOOD_EDIT), [], allowed=("other.py",))


class TestApply:
    def test_successful_apply_on_isolated_branch(self, tmp_path):
        applier, repo, runner, ledger = make_applier(tmp_path, [response(text=GOOD_EDIT)])
        before_main = git_out(runner, repo, "rev-parse", "main")
        result = applier.apply(make_plan())
        assert result.branch == "fix/F-001"
        assert result.files_changed == ("app/utils.py",)
        assert "normalized" in (repo / "app/utils.py").read_text()
        assert git_out(runner, repo, "rev-parse", "main") == before_main  # main untouched
        assert ledger.entries()[0].purpose_tag == "fixloop.edit.F-001"

    def test_revert_restores_byte_identical_tree(self, tmp_path):
        applier, repo, runner, _ = make_applier(tmp_path, [response(text=GOOD_EDIT)])
        original = (repo / "app/utils.py").read_text()
        result = applier.apply(make_plan())
        applier.revert(result.base_sha)
        assert (repo / "app/utils.py").read_text() == original

    def test_bad_block_retried_with_feedback_then_succeeds(self, tmp_path):
        applier, repo, _, _ = make_applier(
            tmp_path, [response(text=BAD_EDIT), response(text=GOOD_EDIT)]
        )
        result = applier.apply(make_plan())
        assert result.files_changed == ("app/utils.py",)

    def test_persistently_bad_edits_fail_with_clean_tree(self, tmp_path):
        applier, repo, _, _ = make_applier(
            tmp_path, [response(text=BAD_EDIT), response(text=BAD_EDIT)]
        )
        original = (repo / "app/utils.py").read_text()
        with pytest.raises(ApplyFailedError, match="unappliable"):
            applier.apply(make_plan())
        assert (repo / "app/utils.py").read_text() == original


class TestCharacterization:
    def test_char_tests_written_and_green_before_edit(self, tmp_path):
        applier, repo, _, ledger = make_applier(
            tmp_path, [response(text=CHAR_TEST), response(text=GOOD_EDIT)]
        )
        result = applier.apply(make_plan(needs_char=True))
        assert result.characterization_test == "tests/test_characterization_F-001.py"
        assert (repo / result.characterization_test).exists()
        tags = [e.purpose_tag for e in ledger.entries()]
        assert tags[0] == "fixloop.chartest.F-001"

    def test_red_characterization_aborts_before_any_edit(self, tmp_path):
        broken_char = "def test_broken():\n    assert False\n"
        applier, repo, _, _ = make_applier(tmp_path, [response(text=broken_char)])
        original = (repo / "app/utils.py").read_text()
        with pytest.raises(ApplyFailedError, match="ORIGINAL"):
            applier.apply(make_plan(needs_char=True))
        assert (repo / "app/utils.py").read_text() == original

    def test_suite_runner_reports_green(self, tmp_path):
        applier, _, _, _ = make_applier(tmp_path, [])
        assert applier.run_tests() is True


CREATE_EDIT = """FILE: app/_helpers.py
<<<<<<< CREATE
def shared_helper():
    return "extracted"
>>>>>>> CREATE

FILE: app/utils.py
<<<<<<< SEARCH
def slugify(text):
    return "-".join(text.lower().split())
=======
from app._helpers import shared_helper


def slugify(text):
    return "-".join(text.lower().split())
>>>>>>> REPLACE"""

BROKEN_SYNTAX_EDIT = """FILE: app/utils.py
<<<<<<< SEARCH
def slugify(text):
    return "-".join(text.lower().split())
=======
def slugify(text)
    return "-".join(text.lower().split())
>>>>>>> REPLACE"""


class TestCreateBlocks:
    def test_new_sibling_module_created_and_edit_applied(self, tmp_path):
        applier, repo, _, _ = make_applier(tmp_path, [response(text=CREATE_EDIT)])
        result = applier.apply(make_plan())
        assert "app/_helpers.py" in result.files_changed
        assert (repo / "app/_helpers.py").read_text().startswith("def shared_helper")
        assert "shared_helper" in (repo / "app/utils.py").read_text()

    def test_create_outside_target_dirs_rejected(self, tmp_path):
        blocks = parse_creates("FILE: elsewhere/x.py\n<<<<<<< CREATE\nX = 1\n>>>>>>> CREATE")
        with pytest.raises(ApplyFailedError, match="outside the target"):
            apply_blocks(tmp_path, [], blocks, allowed=("app/utils.py",))

    def test_revert_removes_created_files(self, tmp_path):
        applier, repo, _, _ = make_applier(tmp_path, [response(text=CREATE_EDIT)])
        result = applier.apply(make_plan())
        applier.revert(result.base_sha)
        assert not (repo / "app/_helpers.py").exists()


class TestSyntaxGate:
    def test_unparseable_result_is_feedback_not_red_run(self, tmp_path):
        applier, repo, _, _ = make_applier(
            tmp_path, [response(text=BROKEN_SYNTAX_EDIT), response(text=GOOD_EDIT)]
        )
        result = applier.apply(make_plan())  # retry path recovers
        assert result.files_changed == ("app/utils.py",)
        assert "normalized" in (repo / "app/utils.py").read_text()


class TestAcceptCommit:
    def test_accepted_change_is_committed_on_branch(self, tmp_path):
        applier, repo, runner, _ = make_applier(tmp_path, [response(text=GOOD_EDIT)])
        result = applier.apply(make_plan())
        sha = applier.commit_accepted("F-001")
        assert sha != result.base_sha
        message = git_out(runner, repo, "log", "-1", "--format=%s")
        assert "accepted by improvement loop" in message

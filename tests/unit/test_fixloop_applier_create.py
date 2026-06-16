"""Tests for fixloop.applier — CREATE blocks, syntax gate, accept-commit.

Split out of test_fixloop_applier to stay within the 150-code-line limit
(guidelines §3.2/§6.1); reuses that suite's scaffolding (make_applier,
make_plan, git_out, GOOD_EDIT).
"""

import pytest

from hw4.services.fixloop.applier import ApplyFailedError, apply_blocks, parse_creates

from .test_fixloop_applier import GOOD_EDIT, git_out, make_applier, make_plan
from .test_llm_client import response

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

"""Tests for hw4.main — parsing, 1:1 dispatch, exit codes (thin-shell CLI)."""

import pytest

from hw4.main import EXIT_NOT_READY, build_parser, dispatch, main


class RecordingSdk:
    """Stands in for Hw4Sdk: records which method got which arguments."""

    def __init__(self):
        self.calls = []

    def _record(self, name, *args, **kwargs):
        self.calls.append((name, args, kwargs))
        return f"{name}-done"

    def build_graph(self, repo_path):
        return self._record("build_graph", repo_path)

    def build_vault(self, graph_path):
        return self._record("build_vault", graph_path)

    def analyze(self, graph_path):
        return self._record("analyze", graph_path)

    def ask(self, question, *, mode):
        return self._record("ask", question, mode=mode)

    def fix(self, finding_id):
        return self._record("fix", finding_id)

    def run_experiment(self):
        return self._record("run_experiment")

    def report(self):
        return self._record("report")


class TestParser:
    def test_version_flag_exits_zero(self, capsys):
        with pytest.raises(SystemExit) as excinfo:
            build_parser().parse_args(["--version"])
        assert excinfo.value.code == 0
        assert "hw4" in capsys.readouterr().out

    def test_command_is_required(self):
        with pytest.raises(SystemExit):
            build_parser().parse_args([])

    def test_ask_mode_restricted_to_known_values(self):
        with pytest.raises(SystemExit):
            build_parser().parse_args(["ask", "q", "--mode", "telepathy"])


class TestDispatch:
    @pytest.mark.parametrize(
        ("argv", "expected"),
        [
            (["graph", "repo/"], ("build_graph", ("repo/",), {})),
            (["vault", "g.json"], ("build_vault", ("g.json",), {})),
            (["analyze", "g.json"], ("analyze", ("g.json",), {})),
            (["ask", "why?"], ("ask", ("why?",), {"mode": "graph"})),
            (["ask", "why?", "--mode", "naive"], ("ask", ("why?",), {"mode": "naive"})),
            (["fix", "F-001"], ("fix", ("F-001",), {})),
            (["experiment"], ("run_experiment", (), {})),
            (["report"], ("report", (), {})),
        ],
    )
    def test_each_command_maps_to_one_sdk_call(self, argv, expected):
        sdk = RecordingSdk()
        dispatch(sdk, build_parser().parse_args(argv))
        assert sdk.calls == [expected]


class TestMain:
    def test_unwired_command_exits_not_ready(self, capsys):
        assert main(["report"]) == EXIT_NOT_READY
        assert "Phase 9" in capsys.readouterr().err

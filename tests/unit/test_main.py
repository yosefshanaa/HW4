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

    def build_graph(self, repo_path, *, iteration=None):
        return self._record("build_graph", repo_path, iteration=iteration)

    def build_vault(self, graph_path):
        return self._record("build_vault", graph_path)

    def analyze(self, graph_path):
        return self._record("analyze", graph_path)

    def analyze_with_agents(self):
        return self._record("analyze_with_agents")

    def ask(self, question, *, mode):
        return self._record("ask", question, mode=mode)

    def fix(self, finding_id, *, auto=False):
        return self._record("fix", finding_id, auto=auto)

    def evaluate(self, target_path, answer_key_path):
        return self._record("evaluate", target_path, answer_key_path)

    def debug(self, target_path):
        return self._record("debug", target_path)

    def run_experiment(self, *, condition="both"):
        return self._record("run_experiment", condition=condition)

    def report(self, *, dashboard=False):
        return self._record("report", dashboard=dashboard)


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
            (["graph", "repo/"], ("build_graph", ("repo/",), {"iteration": None})),
            (["graph", "repo/", "--iteration", "2"], ("build_graph", ("repo/",), {"iteration": 2})),
            (["vault", "g.json"], ("build_vault", ("g.json",), {})),
            (["analyze", "g.json"], ("analyze", ("g.json",), {})),
            (["analyze"], ("analyze", (None,), {})),
            (["analyze", "--agents"], ("analyze_with_agents", (), {})),
            (["ask", "why?"], ("ask", ("why?",), {"mode": "graph"})),
            (["ask", "why?", "--mode", "naive"], ("ask", ("why?",), {"mode": "naive"})),
            (["fix", "F-001"], ("fix", ("F-001",), {"auto": False})),
            (["fix", "--auto"], ("fix", ("",), {"auto": True})),
            (["evaluate"], ("evaluate", (None, None), {})),
            (["evaluate", "repo/", "--answer-key", "k.json"],
             ("evaluate", ("repo/", "k.json"), {})),
            (["debug"], ("debug", (None,), {})),
            (["debug", "case/"], ("debug", ("case/",), {})),
            (["experiment"], ("run_experiment", (), {"condition": "both"})),
            (["experiment", "--condition", "A"], ("run_experiment", (), {"condition": "A"})),
            (["report"], ("report", (), {"dashboard": False})),
            (["report", "--dashboard"], ("report", (), {"dashboard": True})),
        ],
    )
    def test_each_command_maps_to_one_sdk_call(self, argv, expected):
        sdk = RecordingSdk()
        dispatch(sdk, build_parser().parse_args(argv))
        assert sdk.calls == [expected]


class TestMain:
    def test_not_ready_capability_exits_2(self, capsys):
        assert main(["ask", "q", "--mode", "naive"]) == EXIT_NOT_READY
        assert "experiment" in capsys.readouterr().err

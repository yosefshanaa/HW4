"""Tests for hw4.services.graph_diff — set math, verdicts, rename guard."""

from hw4.services.graph_diff import IMPROVED, NEUTRAL, REGRESSED, GraphDelta, diff, judge
from hw4.services.graph_metrics import BottleneckEvidence, Metrics
from hw4.services.graph_models import Graph
from hw4.shared.config import Config

from .test_config import write_config_dir


def make_graph(node_ids, edge_pairs, iteration=0):
    return Graph.from_dict(
        {
            "version": "1.00",
            "iteration": iteration,
            "nodes": [{"id": n, "type": "module", "label": n} for n in node_ids],
            "edges": [
                {"src": s, "dst": d, "relation": "calls",
                 "evidence": "EXTRACTED", "confidence": 1.0}
                for s, d in edge_pairs
            ],
        }
    )


def make_metrics(score, isolated=0, communities=1, iteration=0):
    bottlenecks = []
    if score > 0:
        bottlenecks = [BottleneckEvidence(
            node_id="hub", betweenness=score, rank=1, mandatory_path_ratio=1.0,
            fan_in=1, fan_out=1, relation_profile={}, score=score,
        )]
    return Metrics(
        iteration=iteration, relations_considered=["calls"],
        community_count=communities,
        isolated_components=[[f"x{i}"] for i in range(isolated)],
        bottlenecks=bottlenecks,
    )


def make_delta(before_score, after_score, isolated=(0, 0)):
    return GraphDelta(
        iteration_before=0, iteration_after=1,
        nodes_added=[], nodes_removed=[], edges_added=[], edges_removed=[],
        top_bottleneck_before=before_score, top_bottleneck_after=after_score,
        isolated_before=isolated[0], isolated_after=isolated[1],
        community_before=2, community_after=2,
    )


def make_cfg(tmp_path, threshold=0.1):
    setup = {"version": "1.00", "paths": {"results": "results"},
             "loop": {"metric_improvement_threshold": threshold}}
    return Config(write_config_dir(tmp_path / "cfg", setup=setup), environ={})


class TestDiff:
    def test_node_and_edge_set_arithmetic(self):
        before = make_graph(["a", "b", "c"], [("a", "b"), ("b", "c")], iteration=0)
        after = make_graph(["a", "b", "d"], [("a", "b"), ("a", "d")], iteration=1)
        delta = diff(before, after, make_metrics(0.5), make_metrics(0.4, iteration=1))
        assert delta.nodes_added == ["d"] and delta.nodes_removed == ["c"]
        assert ("a", "d", "calls") in delta.edges_added
        assert ("b", "c", "calls") in delta.edges_removed

    def test_identical_graphs_empty_delta(self):
        g0 = make_graph(["a", "b"], [("a", "b")])
        g1 = make_graph(["a", "b"], [("a", "b")], iteration=1)
        delta = diff(g0, g1, make_metrics(0.5), make_metrics(0.5, iteration=1))
        assert not delta.nodes_added and not delta.edges_removed
        assert delta.bottleneck_improvement == 0.0

    def test_pure_rename_flagged_as_suspect(self):
        before = make_graph(["a", "hub", "b"], [("a", "hub"), ("hub", "b")])
        after = make_graph(["a", "core", "b"], [("a", "core"), ("core", "b")], iteration=1)
        delta = diff(before, after, make_metrics(0.5), make_metrics(0.5, iteration=1))
        assert ("hub", "core") in delta.possible_renames


class TestJudge:
    def test_score_drop_beyond_threshold_improves(self, tmp_path):
        assert judge(make_delta(1.0, 0.7), make_cfg(tmp_path)) == IMPROVED

    def test_score_rise_beyond_threshold_regresses(self, tmp_path):
        assert judge(make_delta(1.0, 1.3), make_cfg(tmp_path)) == REGRESSED

    def test_small_wiggle_is_neutral(self, tmp_path):
        assert judge(make_delta(1.0, 0.95), make_cfg(tmp_path)) == NEUTRAL

    def test_fewer_islands_improves_when_primary_not_worse(self, tmp_path):
        delta = make_delta(1.0, 1.0, isolated=(2, 1))
        assert judge(delta, make_cfg(tmp_path)) == IMPROVED

    def test_new_island_regresses(self, tmp_path):
        delta = make_delta(1.0, 0.99, isolated=(0, 1))
        assert judge(delta, make_cfg(tmp_path)) == REGRESSED

    def test_zero_baseline_score_is_neutral(self, tmp_path):
        assert judge(make_delta(0.0, 0.0), make_cfg(tmp_path)) == NEUTRAL

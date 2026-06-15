"""GRAPH_REPORT.md generation tests — Graphify-parity deliverable."""

from pathlib import Path

from hw4.sdk.sdk import Hw4Sdk
from hw4.services import graph_metrics, graph_report
from hw4.services.extractor import extract
from hw4.shared.config import Config

from .test_config import write_config_dir
from .test_operations import FAST_RATE_LIMITS, FULL_SETUP

MINI_REPO = Path(__file__).resolve().parents[1] / "fixtures" / "mini_repo"
CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"


class TestRender:
    def test_sections_and_counts_present(self):
        cfg = Config(CONFIG_DIR, environ={})
        graph = extract(MINI_REPO, cfg)
        metrics = graph_metrics.compute(graph, cfg)
        text = graph_report.render(graph, metrics)
        assert "## Nodes by type" in text
        assert "## Edges by relation" in text
        assert "## Evidence classes" in text
        assert f"{len(graph.nodes)} nodes" in text
        assert f"{len(graph.edges)} edges" in text


class TestBuildGraphEmitsReport:
    def test_report_written_beside_graph(self, tmp_path):
        write_config_dir(tmp_path / "config", setup=FULL_SETUP, rate_limits=FAST_RATE_LIMITS)
        sdk = Hw4Sdk(config_dir="config", environ={}, base_dir=tmp_path)
        record = sdk.build_graph(MINI_REPO)
        report = record.graph_path.parent / "GRAPH_REPORT.md"
        assert report.exists()
        assert "GRAPH_REPORT" in report.read_text(encoding="utf-8")

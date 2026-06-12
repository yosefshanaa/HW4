"""Tests for hw4.services.graph_runner — immutability and determinism."""

import json
from pathlib import Path

import pytest

from hw4.services.graph_runner import (
    EmptyGraphError,
    GraphRunner,
    IterationExistsError,
)
from hw4.shared.config import Config

from .test_config import write_config_dir

MINI_REPO = Path(__file__).resolve().parents[1] / "fixtures" / "mini_repo"


def make_runner(tmp_path):
    setup = {
        "version": "1.00",
        "paths": {"results": str(tmp_path / "results")},
        "graph": {
            "exclude_dirs": [".git", "__pycache__"],
            "doc_suffixes": [".md"],
            "max_mentions_per_doc": 50,
        },
    }
    cfg = Config(write_config_dir(tmp_path / "cfg", setup=setup), environ={})
    return GraphRunner(cfg)


class TestBuild:
    def test_artifacts_land_in_iteration_dir(self, tmp_path):
        runner = make_runner(tmp_path)
        record = runner.build(MINI_REPO, iteration=0)
        assert record.graph_path == tmp_path / "results" / "graphs" / "i00" / "graph.json"
        assert record.graph_path.exists() and record.manifest_path.exists()
        assert record.nodes > 0 and record.edges > 0

    def test_manifest_records_backend_scope_and_hash(self, tmp_path):
        runner = make_runner(tmp_path)
        record = runner.build(MINI_REPO, iteration=0)
        manifest = json.loads(record.manifest_path.read_text())
        assert manifest["backend"].startswith("ast_extractor/")
        assert manifest["content_hash"] == record.content_hash
        assert manifest["scan_scope"]["doc_suffixes"] == [".md"]

    def test_existing_iteration_never_overwritten(self, tmp_path):
        runner = make_runner(tmp_path)
        runner.build(MINI_REPO, iteration=0)
        with pytest.raises(IterationExistsError, match="already built"):
            runner.build(MINI_REPO, iteration=0)

    def test_identical_input_gives_identical_hash(self, tmp_path):
        runner = make_runner(tmp_path)
        first = runner.build(MINI_REPO, iteration=0)
        second = runner.build(MINI_REPO, iteration=1)
        first_doc = json.loads(first.graph_path.read_text())
        second_doc = json.loads(second.graph_path.read_text())
        first_doc.pop("iteration"), second_doc.pop("iteration")
        assert first_doc == second_doc  # only the iteration number differs

    def test_empty_scan_surfaces_cleanly(self, tmp_path):
        runner = make_runner(tmp_path)
        empty = tmp_path / "empty_repo"
        empty.mkdir()
        with pytest.raises(EmptyGraphError, match="no nodes"):
            runner.build(empty, iteration=0)


class TestLookup:
    def test_latest_iteration_none_before_any_build(self, tmp_path):
        assert make_runner(tmp_path).latest_iteration() is None

    def test_latest_iteration_tracks_builds(self, tmp_path):
        runner = make_runner(tmp_path)
        runner.build(MINI_REPO, iteration=0)
        runner.build(MINI_REPO, iteration=3)
        assert runner.latest_iteration() == 3
        assert runner.graph_path(3).exists()

"""Graph-guided debugging-case tests — reproduce, localize, verify (§5.3-5.4)."""

import importlib.util
from pathlib import Path

import pytest

from hw4.sdk.sdk import Hw4Sdk
from hw4.services.debug import run_debug_case
from hw4.shared.config import Config

from .test_config import write_config_dir
from .test_operations import FAST_RATE_LIMITS, FULL_SETUP

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "buggy_case"
CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"


def _load(name):
    path = FIXTURE / "httprange" / name
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestDebugCase:
    def result(self):
        return run_debug_case(FIXTURE, Config(CONFIG_DIR, environ={}))

    def test_bug_reproduced_and_fix_verified(self):
        r = self.result()
        assert r.buggy_value == 499 and r.expected == 500 and r.reproduced
        assert r.fixed_value == 500 and r.fixed

    def test_graph_localizes_implicated_module(self):
        assert self.result().located_module == "httprange.parser"

    def test_graph_guided_saves_tokens(self):
        r = self.result()
        assert 0 < r.graph_tokens < r.naive_tokens
        assert r.savings > 0


class TestPlantedFix:
    def test_fixed_parser_passes_full_spec(self):
        parse = _load("parser.py").parse_byte_range
        assert parse("bytes=0-499", 1000) == (0, 499, 500)
        assert parse("bytes=500-", 1000) == (500, 999, 500)
        assert parse("bytes=0-0", 1000) == (0, 0, 1)
        with pytest.raises(ValueError):
            parse("bytes=0-2000", 1000)

    def test_buggy_parser_drops_the_last_byte(self):
        assert _load("parser_buggy.py").parse_byte_range("bytes=0-499", 1000)[2] == 499


class TestDebugOp:
    def test_writes_bug_analysis_report(self, tmp_path):
        write_config_dir(tmp_path / "config", setup=FULL_SETUP, rate_limits=FAST_RATE_LIMITS)
        sdk = Hw4Sdk(config_dir="config", environ={}, base_dir=tmp_path)
        report = sdk.debug(FIXTURE)
        assert report.report_path.exists()
        text = report.report_path.read_text(encoding="utf-8")
        assert "Root cause" in text and "tested_by" in text and "fix verified" in text
        assert "reproduced" in str(report)

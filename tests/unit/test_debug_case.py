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


class TestTokenSubPoints:
    def test_files_read_counted(self):
        r = run_debug_case(FIXTURE, Config(CONFIG_DIR, environ={}))
        assert r.naive_files >= 3 and r.graph_files == 1  # whole package vs one module

    def test_report_has_all_four_dimensions(self, tmp_path):
        write_config_dir(tmp_path / "config", setup=FULL_SETUP, rate_limits=FAST_RATE_LIMITS)
        sdk = Hw4Sdk(config_dir="config", environ={}, base_dir=tmp_path)
        text = sdk.debug(FIXTURE).report_path.read_text(encoding="utf-8")
        for dimension in ("Tokens consumed", "Files / textual units", "Research rounds",
                          "Speed/quality to root cause"):
            assert dimension in text


class TestDebugOp:
    def test_writes_bug_analysis_report(self, tmp_path):
        write_config_dir(tmp_path / "config", setup=FULL_SETUP, rate_limits=FAST_RATE_LIMITS)
        sdk = Hw4Sdk(config_dir="config", environ={}, base_dir=tmp_path)
        report = sdk.debug(FIXTURE)
        assert report.report_path.exists()
        text = report.report_path.read_text(encoding="utf-8")
        assert "Root cause" in text and "tested_by" in text and "fix verified" in text
        assert "reproduced" in str(report)


class TestDebugVaultPages:
    def test_bug_focused_hot_and_knowledge_pages_written(self, tmp_path):
        write_config_dir(tmp_path / "config", setup=FULL_SETUP, rate_limits=FAST_RATE_LIMITS)
        sdk = Hw4Sdk(config_dir="config", environ={}, base_dir=tmp_path)
        sdk.debug(FIXTURE)
        project = tmp_path / "vault" / "20_Projects" / "range-debug"
        hot = (project / "hot.md").read_text(encoding="utf-8")
        assert "byte-range" in hot and "httprange.parser" in hot  # bug-focused, localized
        knowledge = (project / "knowledge-before-after.md").read_text(encoding="utf-8")
        assert "Before research" in knowledge and "After fix" in knowledge
        assert (project / "index.md").exists() and (project / "bug.md").exists()


class TestDebugAgent:
    def test_agent_narrates_from_localized_snippet_only(self, tmp_path):
        from .test_llm_client import FakeTransport, response
        write_config_dir(tmp_path / "config", setup=FULL_SETUP, rate_limits=FAST_RATE_LIMITS)
        transport = FakeTransport([], fill=response(text="Root cause: end-start drops a byte."))
        sdk = Hw4Sdk(config_dir="config", environ={}, base_dir=tmp_path, transport=transport)
        report = sdk.debug(FIXTURE, agent=True)
        assert report.narrative_path and Path(report.narrative_path).exists()
        narrative = Path(report.narrative_path).read_text(encoding="utf-8")
        assert "httprange.parser" in narrative  # graph-localized module named
        assert sdk.ledger.entries()[-1].purpose_tag == "agent.analyst"  # gated + tagged

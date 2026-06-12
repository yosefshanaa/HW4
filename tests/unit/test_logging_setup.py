"""Tests for hw4.shared.logging_setup — JSONL records, idempotency."""

import json

from hw4.shared.config import Config
from hw4.shared.logging_setup import get_logger, log_event, setup_logging

from .test_config import write_config_dir


def make_config(tmp_path, console=False):
    logging_cfg = {"version": "1.00", "level": "INFO", "console": console, "directory": "logs"}
    return Config(write_config_dir(tmp_path / "cfg", logging_cfg=logging_cfg), environ={})


class TestSetupLogging:
    def test_creates_run_file_with_json_records(self, tmp_path):
        cfg = make_config(tmp_path)
        logger = setup_logging(cfg, run_id="run1", base_dir=tmp_path)
        logger.info("hello")
        for handler in logger.handlers:
            handler.flush()
        lines = (tmp_path / "logs" / "run1.jsonl").read_text().splitlines()
        record = json.loads(lines[0])
        assert record["message"] == "hello"
        assert record["level"] == "INFO"
        assert "ts" in record

    def test_repeated_setup_does_not_duplicate_handlers(self, tmp_path):
        cfg = make_config(tmp_path)
        setup_logging(cfg, run_id="a", base_dir=tmp_path)
        logger = setup_logging(cfg, run_id="b", base_dir=tmp_path)
        assert len(logger.handlers) == 1  # console off => exactly one file handler

    def test_console_handler_added_when_enabled(self, tmp_path):
        cfg = make_config(tmp_path, console=True)
        logger = setup_logging(cfg, run_id="c", base_dir=tmp_path)
        assert len(logger.handlers) == 2

    def test_level_filtering(self, tmp_path):
        cfg = make_config(tmp_path)
        logger = setup_logging(cfg, run_id="d", base_dir=tmp_path)
        logger.debug("invisible")
        for handler in logger.handlers:
            handler.flush()
        assert (tmp_path / "logs" / "d.jsonl").read_text() == ""


class TestStructuredFields:
    def test_log_event_fields_land_as_json_keys(self, tmp_path):
        cfg = make_config(tmp_path)
        logger = setup_logging(cfg, run_id="e", base_dir=tmp_path)
        log_event(logger, "graph built", iteration=2, nodes=10)
        for handler in logger.handlers:
            handler.flush()
        record = json.loads((tmp_path / "logs" / "e.jsonl").read_text().splitlines()[0])
        assert record["iteration"] == 2
        assert record["nodes"] == 10


class TestGetLogger:
    def test_child_logger_namespaced_under_root(self):
        assert get_logger("graph").name == "hw4.graph"

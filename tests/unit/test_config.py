"""Tests for hw4.shared.config — loading, validation, overrides, secrets."""

import json
from pathlib import Path

import pytest

from hw4.shared.config import Config, ConfigKeyError, MissingSecretError
from hw4.shared.version import ConfigVersionError

REPO_CONFIG = Path(__file__).resolve().parents[2] / "config"


def write_config_dir(tmp_path, setup=None, rate_limits=None, logging_cfg=None):
    """Create a valid config dir, with optional overrides per file."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    setup = setup or {"version": "1.00", "paths": {"results": "results"}, "budget": {"max_usd": 5}}
    rate_limits = rate_limits or {
        "rate_limits": {"version": "1.00", "services": {"default": {"requests_per_minute": 3}}}
    }
    logging_cfg = logging_cfg or {"version": "1.00", "level": "INFO"}
    (tmp_path / "setup.json").write_text(json.dumps(setup))
    (tmp_path / "rate_limits.json").write_text(json.dumps(rate_limits))
    (tmp_path / "logging_config.json").write_text(json.dumps(logging_cfg))
    return tmp_path


class TestLoading:
    def test_loads_valid_directory(self, tmp_path):
        cfg = Config(write_config_dir(tmp_path), environ={})
        assert cfg.get("budget.max_usd") == 5

    def test_repo_config_directory_is_valid(self):
        """The committed config/ must always load — it ships with the tool."""
        cfg = Config(REPO_CONFIG, environ={})
        assert cfg.get("loop.max_iterations") >= 1
        assert cfg.service_limits()["requests_per_minute"] > 0

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="setup.json"):
            Config(tmp_path, environ={})

    def test_version_mismatch_raises(self, tmp_path):
        bad = {"version": "2.00", "paths": {}}
        with pytest.raises(ConfigVersionError, match="setup.json"):
            Config(write_config_dir(tmp_path, setup=bad), environ={})

    def test_rate_limits_version_checked_in_nested_block(self, tmp_path):
        bad = {"rate_limits": {"version": "9.00", "services": {}}}
        with pytest.raises(ConfigVersionError, match="rate_limits.json"):
            Config(write_config_dir(tmp_path, rate_limits=bad), environ={})


class TestGet:
    def test_dotted_path_resolution(self, tmp_path):
        cfg = Config(write_config_dir(tmp_path), environ={})
        assert cfg.get("paths.results") == "results"

    def test_missing_key_raises_without_default(self, tmp_path):
        cfg = Config(write_config_dir(tmp_path), environ={})
        with pytest.raises(ConfigKeyError, match="no.such.key"):
            cfg.get("no.such.key")

    def test_missing_key_returns_default(self, tmp_path):
        cfg = Config(write_config_dir(tmp_path), environ={})
        assert cfg.get("no.such.key", default=42) == 42

    def test_env_override_wins_and_parses_json(self, tmp_path):
        env = {"HW4__budget__max_usd": "9.5"}
        cfg = Config(write_config_dir(tmp_path), environ=env)
        assert cfg.get("budget.max_usd") == 9.5

    def test_env_override_non_json_stays_string(self, tmp_path):
        env = {"HW4__paths__results": "elsewhere"}
        cfg = Config(write_config_dir(tmp_path), environ=env)
        assert cfg.get("paths.results") == "elsewhere"

    def test_path_helper_returns_pathlib(self, tmp_path):
        cfg = Config(write_config_dir(tmp_path), environ={})
        assert cfg.path("results") == Path("results")


class TestServiceLimits:
    def test_unknown_service_falls_back_to_default(self, tmp_path):
        cfg = Config(write_config_dir(tmp_path), environ={})
        assert cfg.service_limits("nonexistent")["requests_per_minute"] == 3

    def test_no_default_raises(self, tmp_path):
        rl = {"rate_limits": {"version": "1.00", "services": {}}}
        cfg = Config(write_config_dir(tmp_path, rate_limits=rl), environ={})
        with pytest.raises(ConfigKeyError):
            cfg.service_limits("anything")


class TestSecrets:
    def test_secret_read_from_environment(self, tmp_path):
        cfg = Config(write_config_dir(tmp_path), environ={"MY_KEY": "shh"})
        assert cfg.get_secret("MY_KEY") == "shh"

    def test_missing_secret_raises_with_guidance(self, tmp_path):
        cfg = Config(write_config_dir(tmp_path), environ={})
        with pytest.raises(MissingSecretError, match=".env-example"):
            cfg.get_secret("ABSENT_KEY")

    def test_empty_secret_treated_as_missing(self, tmp_path):
        cfg = Config(write_config_dir(tmp_path), environ={"K": ""})
        with pytest.raises(MissingSecretError):
            cfg.get_secret("K")

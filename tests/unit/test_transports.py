"""Tests for hw4.shared.transports — provider dispatch, no network."""

import pytest

from hw4.shared.config import Config, MissingSecretError
from hw4.shared.transports import AnthropicTransport, OpenAITransport, make_transport

from .test_config import write_config_dir


def make_config(tmp_path, provider, environ):
    setup = {
        "version": "1.00",
        "paths": {"results": "results"},
        "models": {"cheap": "m-cheap", "strong": "m-strong"},
        "llm": {"max_output_tokens": 64, "provider": provider,
                "api_key_env": "OPENAI_API_KEY" if provider == "openai"
                else "ANTHROPIC_API_KEY"},
    }
    return Config(write_config_dir(tmp_path / "cfg", setup=setup), environ=environ)


class TestFactory:
    def test_openai_provider_dispatch(self, tmp_path):
        cfg = make_config(tmp_path, "openai", {"OPENAI_API_KEY": "sk-test-dummy"})
        assert isinstance(make_transport(cfg), OpenAITransport)

    def test_anthropic_provider_dispatch(self, tmp_path):
        cfg = make_config(tmp_path, "anthropic", {"ANTHROPIC_API_KEY": "sk-test-dummy"})
        assert isinstance(make_transport(cfg), AnthropicTransport)

    def test_unknown_provider_fails_loud(self, tmp_path):
        cfg = make_config(tmp_path, "skynet", {"OPENAI_API_KEY": "x"})
        with pytest.raises(ValueError, match="skynet"):
            make_transport(cfg)

    def test_missing_key_names_the_env_var(self, tmp_path):
        cfg = make_config(tmp_path, "openai", {})
        with pytest.raises(MissingSecretError, match="OPENAI_API_KEY"):
            make_transport(cfg)

    def test_repo_config_builds_a_transport_with_dummy_key(self, tmp_path):
        """The committed config must dispatch cleanly (provider wiring check)."""
        from pathlib import Path

        repo_cfg = Config(Path(__file__).resolve().parents[2] / "config",
                          environ={"OPENAI_API_KEY": "sk-test-dummy"})
        assert isinstance(make_transport(repo_cfg), OpenAITransport)

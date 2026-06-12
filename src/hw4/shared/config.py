"""Layered configuration loader — the only legal source of tunable values.

Hierarchy (guidelines §7.3): versioned JSON files in config/, environment
overrides (HW4__dotted__path), and process environment for secrets. Code
never embeds URLs, limits, model ids, or timeouts (§7.2) — it asks Config.

Secrets are deliberately separate: they come ONLY from the environment
(.env loaded by the shell / runner), never from JSON files, so a committed
config can never leak a key (§7.4).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from hw4.shared.version import assert_config_compatible

_MISSING = object()
ENV_PREFIX = "HW4__"


class ConfigKeyError(KeyError):
    """Raised when a required configuration key is absent."""


class MissingSecretError(RuntimeError):
    """Raised when a required secret is not present in the environment."""


def _read_json(path: Path) -> dict[str, Any]:
    """Load one JSON config file; absence is a hard error (fail fast)."""
    if not path.is_file():
        raise FileNotFoundError(f"required config file missing: {path}")
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _parse_env_value(raw: str) -> Any:
    """Env overrides arrive as strings; interpret JSON scalars when possible."""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


class Config:
    """Typed access to setup/rate-limit/logging configuration."""

    def __init__(self, config_dir: Path | str, environ: dict[str, str] | None = None):
        self._dir = Path(config_dir)
        self._env = os.environ if environ is None else environ
        self.setup = _read_json(self._dir / "setup.json")
        self.rate_limits = _read_json(self._dir / "rate_limits.json")
        self.logging = _read_json(self._dir / "logging_config.json")
        self._validate_versions()

    def _validate_versions(self) -> None:
        """Startup gate: every config file must be version-compatible (NFR-6)."""
        assert_config_compatible(self.setup.get("version", ""), "setup.json")
        nested = self.rate_limits.get("rate_limits", {})
        assert_config_compatible(nested.get("version", ""), "rate_limits.json")
        assert_config_compatible(self.logging.get("version", ""), "logging_config.json")

    def get(self, dotted_path: str, default: Any = _MISSING) -> Any:
        """Resolve a dotted path against setup.json with env-var override.

        Override convention: HW4__budget__max_usd beats setup.json's
        {"budget": {"max_usd": ...}} — exact path, double-underscore joined.
        """
        env_key = ENV_PREFIX + dotted_path.replace(".", "__")
        if env_key in self._env:
            return _parse_env_value(self._env[env_key])
        node: Any = self.setup
        for part in dotted_path.split("."):
            if not isinstance(node, dict) or part not in node:
                if default is _MISSING:
                    raise ConfigKeyError(f"missing config key: {dotted_path}")
                return default
            node = node[part]
        return node

    def service_limits(self, service: str = "default") -> dict[str, Any]:
        """Rate-limit block for a service; unknown services fall back to default."""
        services = self.rate_limits["rate_limits"]["services"]
        if service in services:
            return services[service]
        if "default" in services:
            return services["default"]
        raise ConfigKeyError(f"no rate limits for service {service!r} and no default")

    def get_secret(self, name: str) -> str:
        """Secrets come from the environment only — never from JSON (§7.4)."""
        value = self._env.get(name, "")
        if not value:
            raise MissingSecretError(
                f"secret {name!r} not set; copy .env-example to .env and fill it in"
            )
        return value

    def path(self, key: str) -> Path:
        """Project-relative path from setup.json's paths block."""
        return Path(self.get(f"paths.{key}"))

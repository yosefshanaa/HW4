"""Code version + configuration compatibility validation (guidelines §8.1).

Versions follow the course convention: start at "1.00", bump on meaningful
change. Every JSON config carries a "version" key; the application must
validate compatibility at startup so a stale config fails loudly instead of
producing silently-wrong behavior (NFR-6).
"""

from __future__ import annotations

__version__ = "1.00"


class ConfigVersionError(RuntimeError):
    """Raised when a configuration file's version is incompatible."""


def _major(version: str) -> str:
    """Return the major part of an 'X.YY' version string."""
    return version.split(".", 1)[0]


def assert_config_compatible(config_version: str, source: str = "config") -> None:
    """Fail fast unless the config's major version matches the code's.

    Minor drift (1.00 vs 1.01) is tolerated — additive config changes are
    expected during development. Major drift (1.x vs 2.x) means the schema
    changed and silent acceptance would be a correctness bug.
    """
    if not isinstance(config_version, str) or not config_version:
        raise ConfigVersionError(f"{source}: missing or non-string 'version' key")
    if _major(config_version) != _major(__version__):
        raise ConfigVersionError(
            f"{source}: version {config_version!r} incompatible with code {__version__!r}"
        )

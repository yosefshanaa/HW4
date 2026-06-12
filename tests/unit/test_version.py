"""Tests for hw4.shared.version — startup config-version validation."""

import pytest

from hw4.shared.version import ConfigVersionError, __version__, assert_config_compatible


class TestVersionConstant:
    def test_starts_at_course_convention(self):
        assert __version__ == "1.00"


class TestAssertConfigCompatible:
    def test_exact_match_passes(self):
        assert_config_compatible("1.00")

    def test_minor_drift_tolerated(self):
        assert_config_compatible("1.01")

    def test_major_mismatch_raises(self):
        with pytest.raises(ConfigVersionError, match="incompatible"):
            assert_config_compatible("2.00")

    def test_missing_version_raises(self):
        with pytest.raises(ConfigVersionError, match="missing"):
            assert_config_compatible("")

    def test_non_string_version_raises(self):
        with pytest.raises(ConfigVersionError):
            assert_config_compatible(1.0)  # type: ignore[arg-type]

    def test_source_appears_in_error_message(self):
        with pytest.raises(ConfigVersionError, match="rate_limits.json"):
            assert_config_compatible("9.99", source="rate_limits.json")

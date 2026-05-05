"""Tests for the configuration singleton module."""

import os
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from bookdl.core.config import (
    Config,
    DEFAULTS,
    coerce_bool,
    coerce_int,
    config,
)


class TestCoerceBool:
    """Tests for boolean coercion."""

    def test_true_values(self):
        """True-like values are coerced to True."""
        assert coerce_bool("true") is True
        assert coerce_bool("TRUE") is True
        assert coerce_bool("True") is True
        assert coerce_bool("1") is True
        assert coerce_bool("yes") is True
        assert coerce_bool("YES") is True
        assert coerce_bool("on") is True
        assert coerce_bool(True) is True

    def test_false_values(self):
        """False-like values are coerced to False."""
        assert coerce_bool("false") is False
        assert coerce_bool("FALSE") is False
        assert coerce_bool("0") is False
        assert coerce_bool("no") is False
        assert coerce_bool("off") is False
        assert coerce_bool(False) is False
        assert coerce_bool("") is False

    def test_non_string_values(self):
        """Non-string values are coerced via bool()."""
        assert coerce_bool(1) is True
        assert coerce_bool(0) is False
        assert coerce_bool([]) is False
        assert coerce_bool([1]) is True


class TestCoerceInt:
    """Tests for integer coercion."""

    def test_integer_input(self):
        """Integer input is returned as-is."""
        assert coerce_int(42) == 42
        assert coerce_int(-10) == -10
        assert coerce_int(0) == 0

    def test_string_integer(self):
        """String integers are parsed."""
        assert coerce_int("123") == 123
        assert coerce_int("-456") == -456
        assert coerce_int("  789  ") == 789

    def test_invalid_string_returns_default(self):
        """Invalid strings return default."""
        assert coerce_int("abc", default=99) == 99
        assert coerce_int("12.5", default=99) == 99
        assert coerce_int("", default=99) == 99

    def test_bool_returns_default(self):
        """Boolean input returns default (not 0/1)."""
        assert coerce_int(True, default=42) == 42
        assert coerce_int(False, default=42) == 42


class TestConfig:
    """Tests for Config singleton."""

    def setup_method(self):
        """Clear config and environment between tests."""
        config.refresh()
        # Remove any test environment variables
        for key in list(os.environ.keys()):
            if key.startswith("TEST_"):
                del os.environ[key]

    def test_get_returns_default_when_not_set(self):
        """get() returns provided default when key not found."""
        result = config.get("NONEXISTENT_KEY", "my_default")
        assert result == "my_default"

    def test_get_returns_defaults_dict_value(self):
        """get() returns value from DEFAULTS when available."""
        assert config.get("FLASK_PORT") == 8084
        assert config.get("SEARCH_MODE") == "universal"

    def test_get_reads_from_environment(self, monkeypatch):
        """get() reads from environment variables first."""
        monkeypatch.setenv("TEST_VAR", "env_value")
        result = config.get("TEST_VAR", "default_value")
        assert result == "env_value"

    def test_get_coerces_bool_from_env(self, monkeypatch):
        """get() coerces boolean from environment when default is bool."""
        # Set an env var for a key that has bool default
        monkeypatch.setenv("DEBUG", "true")
        result = config.get("DEBUG")
        assert result is True

    def test_get_coerces_int_from_env(self, monkeypatch):
        """get() coerces integer from environment when default is int."""
        monkeypatch.setenv("FLASK_PORT", "9000")
        result = config.get("FLASK_PORT")
        assert result == 9000

    def test_set_stores_value(self):
        """set() stores configuration values."""
        config.set("CUSTOM_KEY", "custom_value")
        assert config.get("CUSTOM_KEY") == "custom_value"

    def test_set_value_overridden_by_env(self, monkeypatch):
        """Environment variables take precedence over set values."""
        config.set("OVERRIDE_TEST", "set_value")
        monkeypatch.setenv("OVERRIDE_TEST", "env_value")
        result = config.get("OVERRIDE_TEST")
        assert result == "env_value"

    def test_refresh_clears_cached_values(self):
        """refresh() clears cached values."""
        config.set("REFRESH_TEST", "cached")
        assert config.get("REFRESH_TEST") == "cached"

        config.refresh()
        assert config.get("REFRESH_TEST") is None

    def test_singleton_pattern(self):
        """Config is a singleton - same instance returned."""
        config1 = Config()
        config2 = Config()
        assert config1 is config2

    def test_get_bool_helper(self, monkeypatch):
        """get_bool() returns boolean value."""
        config.set("BOOL_TEST", "yes")
        assert config.get_bool("BOOL_TEST") is True

        config.set("BOOL_TEST2", "no")
        assert config.get_bool("BOOL_TEST2") is False

    def test_get_int_helper(self):
        """get_int() returns integer value."""
        config.set("INT_TEST", "123")
        assert config.get_int("INT_TEST") == 123

        assert config.get_int("MISSING_INT", default=99) == 99

    def test_thread_safety(self):
        """Config is thread-safe for concurrent access."""
        errors = []

        def writer(i):
            try:
                for j in range(100):
                    config.set(f"thread_{i}_key_{j}", f"value_{j}")
            except Exception as e:
                errors.append(e)

        def reader(i):
            try:
                for j in range(100):
                    config.get(f"thread_{i}_key_{j}", "default")
            except Exception as e:
                errors.append(e)

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for i in range(5):
                futures.append(executor.submit(writer, i))
                futures.append(executor.submit(reader, i))

            for future in futures:
                future.result()

        assert len(errors) == 0

    def test_all_returns_complete_config(self):
        """all() returns all configuration including defaults."""
        config.set("CUSTOM", "value")
        result = config.all()

        # Should include defaults
        assert "FLASK_PORT" in result
        # Should include custom values
        assert result.get("CUSTOM") == "value"


class TestDefaults:
    """Tests for default configuration values."""

    def test_sensible_defaults_exist(self):
        """Sensible defaults are defined."""
        assert DEFAULTS["FLASK_PORT"] == 8084
        assert DEFAULTS["FLASK_HOST"] == "0.0.0.0"
        assert DEFAULTS["SEARCH_MODE"] == "universal"
        assert DEFAULTS["DEBUG"] is False
        assert DEFAULTS["LOG_LEVEL"] == "INFO"

    def test_default_paths(self):
        """Default paths are defined."""
        assert DEFAULTS["INGEST_DIR"] == "/books"
        assert DEFAULTS["CONFIG_DIR"] == "/config"


class TestGlobalConfigInstance:
    """Tests for the global config instance."""

    def test_config_is_singleton_instance(self):
        """Global config is a Config instance."""
        assert isinstance(config, Config)

    def test_config_is_same_as_new_instance(self):
        """Global config is the same as creating a new Config()."""
        assert config is Config()

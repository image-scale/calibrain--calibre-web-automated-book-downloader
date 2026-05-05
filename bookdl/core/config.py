"""Configuration singleton with environment variable resolution.

Provides a Config class that resolves settings from environment variables
with type coercion and default fallbacks.
"""

import os
from threading import Lock
from typing import Any, Self


# Default settings
DEFAULTS: dict[str, Any] = {
    "FLASK_PORT": 8084,
    "FLASK_HOST": "0.0.0.0",
    "INGEST_DIR": "/books",
    "CONFIG_DIR": "/config",
    "TMP_DIR": "/tmp",
    "TZ": "UTC",
    "SEARCH_MODE": "universal",
    "LOG_LEVEL": "INFO",
    "DEBUG": False,
    "STATUS_TIMEOUT": 3600,
    "METADATA_CACHE_ENABLED": True,
    "METADATA_CACHE_TTL": 300,
}


def coerce_bool(value: Any) -> bool:
    """Coerce a value to boolean.

    Recognizes strings like "true", "1", "yes", "on" as True,
    and "false", "0", "no", "off" as False.

    Args:
        value: Value to coerce

    Returns:
        Boolean value
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def coerce_int(value: Any, default: int = 0) -> int:
    """Coerce a value to integer.

    Args:
        value: Value to coerce
        default: Default value if coercion fails

    Returns:
        Integer value
    """
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.lstrip("-").isdigit():
            return int(stripped)
    return default


class Config:
    """Configuration singleton with environment variable resolution.

    Settings are resolved with priority: environment variable > set value > default.
    Thread-safe singleton pattern ensures only one instance exists.
    """

    _instance: Self | None = None
    _lock = Lock()

    def __new__(cls) -> Self:
        """Return the shared configuration singleton instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        instance = cls._instance
        if instance is None:
            msg = "Config singleton failed to initialize"
            raise RuntimeError(msg)
        return instance

    def __init__(self) -> None:
        """Initialize configuration state."""
        if self._initialized:
            return
        self._values: dict[str, Any] = {}
        self._values_lock = Lock()
        self._initialized = True

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value.

        Resolution order:
        1. Environment variable (with type coercion)
        2. Previously set value
        3. Default from DEFAULTS
        4. Provided default parameter

        Args:
            key: Configuration key
            default: Default value if not found anywhere

        Returns:
            Configuration value
        """
        # Check environment variable first
        env_value = os.environ.get(key)
        if env_value is not None:
            # Apply type coercion based on default value type
            expected_default = DEFAULTS.get(key, default)
            if isinstance(expected_default, bool):
                return coerce_bool(env_value)
            if isinstance(expected_default, int):
                return coerce_int(env_value, expected_default if isinstance(expected_default, int) else 0)
            return env_value

        # Check previously set value
        with self._values_lock:
            if key in self._values:
                return self._values[key]

        # Check defaults
        if key in DEFAULTS:
            return DEFAULTS[key]

        return default

    def set(self, key: str, value: Any) -> None:
        """Set configuration value.

        Args:
            key: Configuration key
            value: Value to set
        """
        with self._values_lock:
            self._values[key] = value

    def refresh(self) -> None:
        """Refresh configuration by clearing cached values.

        This forces re-reading from environment variables on next get().
        """
        with self._values_lock:
            self._values.clear()

    def get_bool(self, key: str, default: bool = False) -> bool:
        """Get configuration value as boolean.

        Args:
            key: Configuration key
            default: Default value

        Returns:
            Boolean value
        """
        value = self.get(key, default)
        return coerce_bool(value)

    def get_int(self, key: str, default: int = 0) -> int:
        """Get configuration value as integer.

        Args:
            key: Configuration key
            default: Default value

        Returns:
            Integer value
        """
        value = self.get(key, default)
        return coerce_int(value, default)

    def all(self) -> dict[str, Any]:
        """Get all configuration values including defaults.

        Returns:
            Dictionary of all configuration values
        """
        result = dict(DEFAULTS)
        with self._values_lock:
            result.update(self._values)
        # Override with environment variables
        for key in result:
            env_value = os.environ.get(key)
            if env_value is not None:
                expected_default = DEFAULTS.get(key)
                if isinstance(expected_default, bool):
                    result[key] = coerce_bool(env_value)
                elif isinstance(expected_default, int):
                    result[key] = coerce_int(env_value, expected_default if isinstance(expected_default, int) else 0)
                else:
                    result[key] = env_value
        return result


# Global singleton instance
config = Config()

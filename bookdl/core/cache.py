"""Thread-safe in-memory cache with TTL support.

Provides a CacheService class for caching values with time-to-live expiration,
along with a @cacheable decorator for memoizing function results.
"""

import threading
import time
from dataclasses import dataclass
from functools import wraps
from typing import TYPE_CHECKING, Any, ParamSpec, TypeVar, cast

if TYPE_CHECKING:
    from collections.abc import Callable

P = ParamSpec("P")
R = TypeVar("R")


@dataclass
class CacheEntry:
    """A cached value with expiration time."""

    value: object
    expires_at: float


class CacheService:
    """Thread-safe in-memory cache with TTL support.

    Provides get/set operations with automatic expiration, capacity limits,
    and prefix-based invalidation.
    """

    def __init__(self, max_size: int = 1000) -> None:
        """Initialize cache with maximum entry limit.

        Args:
            max_size: Maximum number of entries before eviction starts
        """
        self._cache: dict[str, CacheEntry] = {}
        self._lock = threading.Lock()
        self._max_size = max_size

    def get(self, key: str) -> object | None:
        """Get cached value if not expired.

        If the entry exists but is expired, it is removed and None is returned.

        Args:
            key: Cache key to retrieve

        Returns:
            Cached value, or None if not found or expired
        """
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None

            if time.time() > entry.expires_at:
                del self._cache[key]
                return None

            return entry.value

    def set(self, key: str, value: object, ttl: int) -> None:
        """Cache value with TTL in seconds.

        If the cache is at capacity, the oldest entries are evicted first.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds
        """
        with self._lock:
            # Evict oldest entries if at capacity
            if len(self._cache) >= self._max_size:
                self._evict_oldest()

            self._cache[key] = CacheEntry(value=value, expires_at=time.time() + ttl)

    def invalidate(self, key: str) -> bool:
        """Remove specific cache entry.

        Args:
            key: Cache key to remove

        Returns:
            True if entry was found and removed, False otherwise
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def invalidate_prefix(self, prefix: str) -> int:
        """Remove all cache entries whose keys start with prefix.

        Args:
            prefix: Key prefix to match

        Returns:
            Number of entries removed
        """
        with self._lock:
            matching_keys = [key for key in self._cache if key.startswith(prefix)]
            for key in matching_keys:
                del self._cache[key]
            return len(matching_keys)

    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()

    def cleanup_expired(self) -> int:
        """Remove all expired entries.

        Returns:
            Number of entries removed
        """
        with self._lock:
            now = time.time()
            expired_keys = [
                key for key, entry in self._cache.items() if entry.expires_at < now
            ]
            for key in expired_keys:
                del self._cache[key]
            return len(expired_keys)

    def _evict_oldest(self) -> None:
        """Evict ~10% of oldest entries. Called with lock held."""
        if not self._cache:
            return

        # Remove ~10% of entries, oldest first by expiration time
        entries_to_remove = max(1, len(self._cache) // 10)
        sorted_entries = sorted(self._cache.items(), key=lambda x: x[1].expires_at)

        for key, _ in sorted_entries[:entries_to_remove]:
            del self._cache[key]

    def stats(self) -> dict[str, int]:
        """Get cache statistics.

        Returns:
            Dictionary with 'size' and 'max_size' keys
        """
        with self._lock:
            return {"size": len(self._cache), "max_size": self._max_size}


# Global cache instance for general use
_global_cache = CacheService(max_size=1000)


def get_global_cache() -> CacheService:
    """Get the global cache instance."""
    return _global_cache


def cache_key(*args: object, **kwargs: object) -> str:
    """Generate cache key from arguments.

    Creates a unique string key from positional and keyword arguments.

    Args:
        *args: Positional arguments to include in key
        **kwargs: Keyword arguments to include in key

    Returns:
        Cache key string
    """
    parts = [str(arg) for arg in args]
    parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
    return ":".join(parts)


def _coerce_ttl_seconds(value: object, *, default: int) -> int:
    """Normalize cache TTL values.

    Args:
        value: TTL value to coerce
        default: Default value if coercion fails

    Returns:
        TTL in seconds as integer
    """
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value if value > 0 else default
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.isdigit():
            parsed = int(stripped)
            return parsed if parsed > 0 else default
    return default


def cacheable(
    ttl: int | None = None,
    ttl_default: int = 300,
    key_prefix: str = "",
    cache: CacheService | None = None,
) -> "Callable[[Callable[P, R]], Callable[P, R]]":
    """Cache function results with configurable TTL.

    Results are cached using a key generated from function name and arguments.
    None results are not cached.

    Args:
        ttl: Time-to-live in seconds (default: ttl_default)
        ttl_default: Default TTL if ttl is not specified
        key_prefix: Prefix for cache keys
        cache: CacheService instance to use (default: global cache)

    Returns:
        Decorator function
    """
    cache_instance = cache or _global_cache

    def decorator(func: "Callable[P, R]") -> "Callable[P, R]":
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            # Determine TTL
            effective_ttl = ttl if ttl is not None else ttl_default

            # Generate cache key from function name and arguments
            # Skip 'self' argument if present (first arg of method)
            cache_args = (
                args[1:] if args and hasattr(args[0], func.__name__) else args
            )

            key = cache_key(key_prefix or func.__name__, *cache_args, **kwargs)

            # Check cache
            cached = cache_instance.get(key)
            if cached is not None:
                return cast("R", cached)

            # Execute function and cache result
            result = func(*args, **kwargs)

            # Only cache non-None results
            if result is not None:
                cache_instance.set(key, result, effective_ttl)

            return result

        return wrapper

    return decorator

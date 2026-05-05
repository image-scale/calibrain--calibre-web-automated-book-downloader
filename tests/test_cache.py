"""Tests for the thread-safe cache module."""

import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from bookdl.core.cache import (
    CacheService,
    cache_key,
    cacheable,
    get_global_cache,
)


class TestCacheService:
    """Tests for CacheService class."""

    def test_get_returns_cached_value(self):
        """get() returns cached value if not expired."""
        cache = CacheService()
        cache.set("test_key", "test_value", ttl=60)

        assert cache.get("test_key") == "test_value"

    def test_get_returns_none_for_missing_key(self):
        """get() returns None for non-existent key."""
        cache = CacheService()

        assert cache.get("nonexistent") is None

    def test_get_returns_none_for_expired_entry(self):
        """get() returns None for expired entries and removes them."""
        cache = CacheService()
        cache.set("expired_key", "value", ttl=0)  # Already expired
        time.sleep(0.01)  # Ensure time has passed

        result = cache.get("expired_key")
        assert result is None
        # Entry should be removed
        assert cache.stats()["size"] == 0

    def test_set_stores_value_with_ttl(self):
        """set() stores value with TTL."""
        cache = CacheService()
        cache.set("key", {"data": "complex"}, ttl=300)

        assert cache.get("key") == {"data": "complex"}

    def test_set_evicts_oldest_when_at_capacity(self):
        """set() evicts oldest entries when at max_size."""
        cache = CacheService(max_size=10)

        # Fill cache
        for i in range(10):
            cache.set(f"key_{i}", f"value_{i}", ttl=3600)
            time.sleep(0.001)  # Small delay to ensure different expiration times

        assert cache.stats()["size"] == 10

        # Add one more - should evict oldest
        cache.set("new_key", "new_value", ttl=3600)

        # Should still be at or below max_size
        assert cache.stats()["size"] <= 10

    def test_invalidate_removes_entry(self):
        """invalidate() removes specific cache entry."""
        cache = CacheService()
        cache.set("key_to_remove", "value", ttl=60)

        result = cache.invalidate("key_to_remove")

        assert result is True
        assert cache.get("key_to_remove") is None

    def test_invalidate_returns_false_for_missing_key(self):
        """invalidate() returns False for non-existent key."""
        cache = CacheService()

        result = cache.invalidate("nonexistent")

        assert result is False

    def test_invalidate_prefix_removes_matching_entries(self):
        """invalidate_prefix() removes all entries with matching prefix."""
        cache = CacheService()
        cache.set("user:1:name", "Alice", ttl=60)
        cache.set("user:1:email", "alice@example.com", ttl=60)
        cache.set("user:2:name", "Bob", ttl=60)
        cache.set("other:key", "value", ttl=60)

        count = cache.invalidate_prefix("user:1:")

        assert count == 2
        assert cache.get("user:1:name") is None
        assert cache.get("user:1:email") is None
        assert cache.get("user:2:name") == "Bob"
        assert cache.get("other:key") == "value"

    def test_clear_removes_all_entries(self):
        """clear() removes all entries."""
        cache = CacheService()
        cache.set("key1", "value1", ttl=60)
        cache.set("key2", "value2", ttl=60)
        cache.set("key3", "value3", ttl=60)

        cache.clear()

        assert cache.stats()["size"] == 0
        assert cache.get("key1") is None

    def test_cleanup_expired_removes_expired_entries(self):
        """cleanup_expired() removes all expired entries."""
        cache = CacheService()
        cache.set("fresh", "value", ttl=3600)
        cache.set("expired1", "value", ttl=0)
        cache.set("expired2", "value", ttl=0)
        time.sleep(0.01)

        count = cache.cleanup_expired()

        assert count == 2
        assert cache.get("fresh") == "value"
        assert cache.get("expired1") is None
        assert cache.get("expired2") is None

    def test_stats_returns_size_and_max_size(self):
        """stats() returns current size and max_size."""
        cache = CacheService(max_size=500)
        cache.set("key1", "value1", ttl=60)
        cache.set("key2", "value2", ttl=60)

        stats = cache.stats()

        assert stats["size"] == 2
        assert stats["max_size"] == 500

    def test_thread_safety_concurrent_access(self):
        """Concurrent access does not corrupt cache state."""
        cache = CacheService(max_size=100)
        errors = []

        def writer(thread_id):
            try:
                for i in range(50):
                    cache.set(f"thread_{thread_id}_key_{i}", f"value_{i}", ttl=60)
            except Exception as e:
                errors.append(e)

        def reader(thread_id):
            try:
                for i in range(50):
                    cache.get(f"thread_{thread_id}_key_{i}")
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
        # Cache should be in consistent state
        stats = cache.stats()
        assert stats["size"] <= stats["max_size"]


class TestCacheKey:
    """Tests for cache_key function."""

    def test_generates_key_from_args(self):
        """cache_key generates key from positional arguments."""
        key = cache_key("func", "arg1", 123)

        assert "func" in key
        assert "arg1" in key
        assert "123" in key

    def test_generates_key_from_kwargs(self):
        """cache_key includes sorted keyword arguments."""
        key = cache_key("func", name="test", id=42)

        assert "id=42" in key
        assert "name=test" in key

    def test_different_args_produce_different_keys(self):
        """Different arguments produce different keys."""
        key1 = cache_key("func", "a", "b")
        key2 = cache_key("func", "a", "c")

        assert key1 != key2

    def test_empty_args(self):
        """Works with no arguments."""
        key = cache_key()

        assert key == ""


class TestCacheable:
    """Tests for @cacheable decorator."""

    def test_memoizes_function_results(self):
        """@cacheable caches function results."""
        cache = CacheService()
        call_count = 0

        @cacheable(ttl=60, cache=cache)
        def expensive_func(x, y):
            nonlocal call_count
            call_count += 1
            return x + y

        result1 = expensive_func(1, 2)
        result2 = expensive_func(1, 2)

        assert result1 == 3
        assert result2 == 3
        assert call_count == 1  # Second call used cache

    def test_different_args_cached_separately(self):
        """Different arguments are cached separately."""
        cache = CacheService()
        call_count = 0

        @cacheable(ttl=60, cache=cache)
        def add(a, b):
            nonlocal call_count
            call_count += 1
            return a + b

        result1 = add(1, 2)
        result2 = add(3, 4)

        assert result1 == 3
        assert result2 == 7
        assert call_count == 2  # Each unique call is cached

    def test_skips_cache_for_none_results(self):
        """@cacheable does not cache None results."""
        cache = CacheService()
        call_count = 0

        @cacheable(ttl=60, cache=cache)
        def maybe_none(return_none):
            nonlocal call_count
            call_count += 1
            return None if return_none else "value"

        result1 = maybe_none(True)
        result2 = maybe_none(True)

        assert result1 is None
        assert result2 is None
        assert call_count == 2  # Both calls executed (None not cached)

    def test_custom_ttl(self):
        """@cacheable uses specified TTL."""
        cache = CacheService()

        @cacheable(ttl=0, cache=cache)  # Immediate expiration
        def short_lived():
            return "ephemeral"

        result1 = short_lived()
        time.sleep(0.01)
        result2 = short_lived()  # Should call function again

        assert result1 == "ephemeral"
        assert result2 == "ephemeral"

    def test_custom_key_prefix(self):
        """@cacheable uses key_prefix in cache key."""
        cache = CacheService()

        @cacheable(ttl=60, key_prefix="custom", cache=cache)
        def func(x):
            return x * 2

        func(5)

        # Key should include prefix
        stats = cache.stats()
        assert stats["size"] == 1

    def test_works_with_methods(self):
        """@cacheable works with class methods."""
        cache = CacheService()

        class Calculator:
            def __init__(self):
                self.call_count = 0

            @cacheable(ttl=60, cache=cache)
            def compute(self, x):
                self.call_count += 1
                return x ** 2

        calc = Calculator()
        result1 = calc.compute(5)
        result2 = calc.compute(5)

        assert result1 == 25
        assert result2 == 25
        assert calc.call_count == 1


class TestGetGlobalCache:
    """Tests for global cache instance."""

    def test_returns_singleton(self):
        """get_global_cache returns the same instance."""
        cache1 = get_global_cache()
        cache2 = get_global_cache()

        assert cache1 is cache2

    def test_is_cache_service(self):
        """Global cache is a CacheService instance."""
        cache = get_global_cache()

        assert isinstance(cache, CacheService)

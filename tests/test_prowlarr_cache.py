"""Tests for the Prowlarr release cache."""

import threading
import time
from unittest.mock import patch

import pytest

from bookdl.prowlarr.cache import (
    RELEASE_CACHE_TTL,
    cache_release,
    cleanup_expired,
    clear_cache,
    get_cache_stats,
    get_release,
    remove_release,
)


class TestCacheRelease:
    """Tests for cache_release function."""

    def setup_method(self):
        """Clear cache before each test."""
        clear_cache()

    def test_stores_release_data(self):
        """cache_release stores release data."""
        release_data = {"title": "Test Book", "format": "epub"}
        cache_release("abc123", release_data)

        result = get_release("abc123")
        assert result == release_data

    def test_stores_with_timestamp(self):
        """cache_release stores release with timestamp."""
        cache_release("abc123", {"title": "Test"})

        stats = get_cache_stats()
        assert "abc123" in stats["entries"]

    def test_overwrites_existing_entry(self):
        """cache_release overwrites existing entry."""
        cache_release("abc123", {"title": "Old"})
        cache_release("abc123", {"title": "New"})

        result = get_release("abc123")
        assert result["title"] == "New"


class TestGetRelease:
    """Tests for get_release function."""

    def setup_method(self):
        """Clear cache before each test."""
        clear_cache()

    def test_returns_cached_release(self):
        """get_release returns cached release if not expired."""
        release_data = {"title": "Test Book", "size": "1.5 MB"}
        cache_release("xyz789", release_data)

        result = get_release("xyz789")
        assert result == release_data

    def test_returns_none_for_nonexistent(self):
        """get_release returns None for non-existent entries."""
        result = get_release("nonexistent")
        assert result is None

    def test_returns_none_for_expired(self):
        """get_release returns None for expired entries."""
        # Mock time to simulate expiration
        with patch("bookdl.prowlarr.cache.time") as mock_time:
            # First call - cache the release
            mock_time.time.return_value = 1000.0
            cache_release("expired_id", {"title": "Old Release"})

            # Second call - retrieve after TTL has passed
            mock_time.time.return_value = 1000.0 + RELEASE_CACHE_TTL + 1

            result = get_release("expired_id")
            assert result is None

    def test_removes_expired_entry_from_cache(self):
        """get_release removes expired entry from cache."""
        with patch("bookdl.prowlarr.cache.time") as mock_time:
            mock_time.time.return_value = 1000.0
            cache_release("expired_id", {"title": "Old"})

            mock_time.time.return_value = 1000.0 + RELEASE_CACHE_TTL + 1
            get_release("expired_id")

            # Entry should be removed
            stats = get_cache_stats()
            assert "expired_id" not in stats["entries"]


class TestRemoveRelease:
    """Tests for remove_release function."""

    def setup_method(self):
        """Clear cache before each test."""
        clear_cache()

    def test_removes_entry_from_cache(self):
        """remove_release removes entry from cache."""
        cache_release("to_remove", {"title": "Test"})
        assert get_release("to_remove") is not None

        result = remove_release("to_remove")

        assert result is True
        assert get_release("to_remove") is None

    def test_returns_false_for_nonexistent(self):
        """remove_release returns False for non-existent entry."""
        result = remove_release("nonexistent")
        assert result is False


class TestCleanupExpired:
    """Tests for cleanup_expired function."""

    def setup_method(self):
        """Clear cache before each test."""
        clear_cache()

    def test_removes_expired_entries(self):
        """cleanup_expired removes all expired entries."""
        with patch("bookdl.prowlarr.cache.time") as mock_time:
            # Cache some entries at time 1000
            mock_time.time.return_value = 1000.0
            cache_release("old1", {"title": "Old 1"})
            cache_release("old2", {"title": "Old 2"})

            # Cache one entry at later time
            mock_time.time.return_value = 5000.0
            cache_release("new1", {"title": "New 1"})

            # Run cleanup after TTL has passed for old entries
            mock_time.time.return_value = 1000.0 + RELEASE_CACHE_TTL + 1

            removed = cleanup_expired()

            assert removed == 2
            stats = get_cache_stats()
            assert "old1" not in stats["entries"]
            assert "old2" not in stats["entries"]
            assert "new1" in stats["entries"]

    def test_returns_count_of_removed(self):
        """cleanup_expired returns count of removed entries."""
        with patch("bookdl.prowlarr.cache.time") as mock_time:
            mock_time.time.return_value = 1000.0
            cache_release("entry1", {"title": "1"})
            cache_release("entry2", {"title": "2"})
            cache_release("entry3", {"title": "3"})

            mock_time.time.return_value = 1000.0 + RELEASE_CACHE_TTL + 1

            removed = cleanup_expired()

            assert removed == 3

    def test_returns_zero_when_nothing_expired(self):
        """cleanup_expired returns 0 when nothing to remove."""
        cache_release("fresh", {"title": "Fresh"})

        removed = cleanup_expired()

        assert removed == 0


class TestGetCacheStats:
    """Tests for get_cache_stats function."""

    def setup_method(self):
        """Clear cache before each test."""
        clear_cache()

    def test_returns_size(self):
        """get_cache_stats returns cache size."""
        cache_release("a", {"title": "A"})
        cache_release("b", {"title": "B"})

        stats = get_cache_stats()

        assert stats["size"] == 2

    def test_returns_entries(self):
        """get_cache_stats returns entry keys."""
        cache_release("entry1", {"title": "1"})
        cache_release("entry2", {"title": "2"})

        stats = get_cache_stats()

        assert sorted(stats["entries"]) == ["entry1", "entry2"]

    def test_empty_cache_stats(self):
        """get_cache_stats works with empty cache."""
        stats = get_cache_stats()

        assert stats["size"] == 0
        assert stats["entries"] == []


class TestCacheTTL:
    """Tests for cache TTL constant."""

    def test_default_ttl_is_one_hour(self):
        """Default TTL is 3600 seconds (1 hour)."""
        assert RELEASE_CACHE_TTL == 3600


class TestThreadSafety:
    """Tests for thread-safety of cache operations."""

    def setup_method(self):
        """Clear cache before each test."""
        clear_cache()

    def test_concurrent_writes_do_not_corrupt(self):
        """Concurrent writes do not corrupt cache state."""
        errors = []

        def writer(thread_id: int):
            try:
                for i in range(100):
                    cache_release(f"thread{thread_id}_entry{i}", {"thread": thread_id, "i": i})
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer, args=(i,)) for i in range(5)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        stats = get_cache_stats()
        assert stats["size"] == 500  # 5 threads * 100 entries each

    def test_concurrent_reads_and_writes(self):
        """Concurrent reads and writes do not corrupt state."""
        errors = []
        results = []

        # Pre-populate cache
        for i in range(50):
            cache_release(f"preloaded_{i}", {"i": i})

        def reader():
            try:
                for i in range(50):
                    result = get_release(f"preloaded_{i}")
                    if result is not None:
                        results.append(result)
            except Exception as e:
                errors.append(e)

        def writer():
            try:
                for i in range(50):
                    cache_release(f"new_{i}", {"i": i})
            except Exception as e:
                errors.append(e)

        threads = []
        for _ in range(3):
            threads.append(threading.Thread(target=reader))
            threads.append(threading.Thread(target=writer))

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        # All preloaded entries should still be readable
        for i in range(50):
            assert get_release(f"preloaded_{i}") is not None

"""Prowlarr release cache.

Stores search results so the handler can look up releases by source_id.
This allows release data to persist between search and download operations.
"""

from __future__ import annotations

import time
from threading import Lock
from typing import Any

# Cache TTL in seconds (1 hour - releases should be downloaded within this time)
RELEASE_CACHE_TTL = 3600

# Internal cache storage: source_id -> (release_dict, timestamp)
_cache: dict[str, tuple[dict[str, Any], float]] = {}
_cache_lock = Lock()


def cache_release(source_id: str, release_data: dict[str, Any]) -> None:
    """Cache a release by its source_id.

    Args:
        source_id: The unique identifier for this release (GUID)
        release_data: The full API result dict to cache
    """
    with _cache_lock:
        _cache[source_id] = (release_data, time.time())


def get_release(source_id: str) -> dict[str, Any] | None:
    """Get a cached release by source_id.

    Args:
        source_id: The unique identifier for the release

    Returns:
        The cached release dict, or None if not found or expired
    """
    with _cache_lock:
        if source_id not in _cache:
            return None

        release_data, cached_at = _cache[source_id]
        age = time.time() - cached_at

        if age > RELEASE_CACHE_TTL:
            # Expired - remove from cache
            del _cache[source_id]
            return None

        return release_data


def remove_release(source_id: str) -> bool:
    """Remove a release from the cache.

    Args:
        source_id: The unique identifier for the release

    Returns:
        True if the entry was removed, False if it wasn't in the cache
    """
    with _cache_lock:
        if source_id in _cache:
            del _cache[source_id]
            return True
        return False


def cleanup_expired() -> int:
    """Remove all expired entries from the cache.

    Returns:
        Number of entries removed
    """
    current_time = time.time()
    removed = 0

    with _cache_lock:
        expired_ids = [
            source_id
            for source_id, (_, cached_at) in _cache.items()
            if current_time - cached_at > RELEASE_CACHE_TTL
        ]
        for source_id in expired_ids:
            del _cache[source_id]
            removed += 1

    return removed


def get_cache_stats() -> dict[str, Any]:
    """Get cache statistics for debugging.

    Returns:
        Dict with cache size and entry keys
    """
    with _cache_lock:
        return {
            "size": len(_cache),
            "entries": list(_cache.keys()),
        }


def clear_cache() -> None:
    """Clear all entries from the cache.

    Primarily for testing purposes.
    """
    with _cache_lock:
        _cache.clear()

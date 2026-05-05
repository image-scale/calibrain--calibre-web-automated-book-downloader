# Todo

## Plan
Start with core user-facing functionality (book metadata search, download queue, file naming), then add supporting infrastructure (configuration, caching, providers). Build the Flask web API last to integrate all components. Focus on delivering end-to-end book search and download capability.

## Tasks
- [>] Task 1: Implement core data models for download tasks, queue items, and search filters with proper status tracking and filename generation (models.py + test_models.py)
- [ ] Task 2: Implement template-based file naming system that parses templates with conditional placeholders, sanitizes filenames, and builds library paths from metadata (naming.py + test_naming.py)
- [ ] Task 3: Implement thread-safe in-memory cache with TTL support, expiration cleanup, and cacheable decorator for function memoization (cache.py + test_cache.py)
- [ ] Task 4: Implement configuration singleton that resolves settings from environment variables with type coercion and default fallbacks (config.py + test_config.py)
- [ ] Task 5: Implement thread-safe download queue with priority support, cancellation flags, and status tracking with timeout cleanup (queue.py + test_queue.py)
- [ ] Task 6: Implement metadata provider plugin system with BookMetadata dataclass, search interfaces, and provider registry for extensibility (metadata_providers/__init__.py + test_metadata_providers.py)
- [ ] Task 7: Implement Open Library metadata provider that searches books via API, parses responses into BookMetadata, and handles pagination (openlibrary.py + test_openlibrary.py)
- [ ] Task 8: Implement release source plugin system with Release dataclass, protocol types, source registry, and column schema for UI (release_sources/__init__.py + test_release_sources.py)
- [ ] Task 9: Implement Prowlarr release cache with TTL-based expiration for storing and retrieving release data between searches and downloads (prowlarr/cache.py + test_prowlarr_cache.py)
- [ ] Task 10: Implement Torznab XML parser that safely parses torrent/usenet search results from Prowlarr indexers with XXE protection (prowlarr/torznab.py + test_torznab.py)
- [ ] Task 11: Implement download client plugin system with base handler interface, client registry, and common torrent/usenet utilities (clients/__init__.py + test_clients.py)
- [ ] Task 12: Implement qBittorrent download client that adds torrents, monitors progress, and retrieves completed downloads with hardlink support (qbittorrent.py + test_qbittorrent.py)
- [ ] Task 13: Implement download orchestrator that processes the queue, resolves releases via sources, and coordinates with download clients (orchestrator.py + test_orchestrator.py)
- [ ] Task 14: Implement Flask web API with search endpoint, download endpoint, queue status, and WebSocket support for real-time updates (app.py + test_api.py)

# Acceptance Criteria

## Task 1: Core Data Models

### Acceptance Criteria
- [x] QueueStatus enum has values: QUEUED, RESOLVING, LOCATING, DOWNLOADING, COMPLETE, ERROR, CANCELLED
- [x] TERMINAL_QUEUE_STATUSES contains COMPLETE, ERROR, CANCELLED
- [x] ACTIVE_QUEUE_STATUSES contains QUEUED, RESOLVING, LOCATING, DOWNLOADING
- [x] SearchMode enum has DIRECT and UNIVERSAL values
- [x] QueueItem dataclass has book_id, priority, added_time fields and supports comparison for priority queue ordering
- [x] QueueItem with lower priority number takes precedence (priority 1 < priority 2)
- [x] QueueItem with same priority uses added_time for ordering (earlier time < later time)
- [x] DownloadTask dataclass has required fields: task_id, source, title
- [x] DownloadTask has optional fields: author, year, format, size, preview, status, progress, etc.
- [x] DownloadTask.get_filename() returns sanitized filename from metadata
- [x] DownloadTask supports priority queue comparison via __lt__
- [x] build_filename() generates "Author - Title (Year).format" pattern
- [x] build_filename() sanitizes invalid characters (\\/:*?"<>|) to underscores
- [x] build_filename() truncates to 245 characters max
- [x] SearchFilters dataclass has isbn, author, title, lang, sort, content, format fields

## Task 2: Template-based File Naming

### Acceptance Criteria
- [x] parse_naming_template() substitutes {Author}, {Title}, {Year}, {Series}, {SeriesPosition} placeholders
- [x] parse_naming_template() supports conditional placeholders like {Series/} that include suffix only when value exists
- [x] parse_naming_template() supports conditional prefix like { - Subtitle} that includes prefix only when value exists
- [x] sanitize_filename() replaces invalid characters (\\/:*?"<>|) with underscores
- [x] sanitize_filename() collapses multiple underscores and trims whitespace/dots
- [x] sanitize_filename() truncates to max_length (default 245)
- [x] format_series_position() formats float as integer when whole number (e.g., 2.0 -> "2")
- [x] derive_primary_title() extracts title without subtitle suffix when possible
- [x] natural_sort_key() pads numbers for correct sorting (Part 2 < Part 10)
- [x] assign_part_numbers() assigns sequential part numbers to sorted file list
- [x] build_library_path() combines base path, template, and metadata into a full path
- [x] build_library_path() prevents path traversal by removing ".." sequences

## Task 3: Thread-safe Cache with TTL

### Acceptance Criteria
- [ ] CacheService.get() returns cached value if not expired
- [ ] CacheService.get() returns None for expired entries and removes them
- [ ] CacheService.set() stores value with TTL in seconds
- [ ] CacheService.set() evicts oldest entries when at max_size capacity
- [ ] CacheService.invalidate() removes specific cache entry by key
- [ ] CacheService.invalidate_prefix() removes all entries with matching key prefix
- [ ] CacheService.clear() removes all entries
- [ ] CacheService.cleanup_expired() removes all expired entries and returns count
- [ ] CacheService.stats() returns current size and max_size
- [ ] cache_key() generates unique key from arguments and kwargs
- [ ] @cacheable decorator memoizes function results with configurable TTL
- [ ] @cacheable decorator skips cache for None results
- [ ] Thread-safety: concurrent access does not corrupt cache state

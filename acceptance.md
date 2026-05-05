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
- [x] CacheService.get() returns cached value if not expired
- [x] CacheService.get() returns None for expired entries and removes them
- [x] CacheService.set() stores value with TTL in seconds
- [x] CacheService.set() evicts oldest entries when at max_size capacity
- [x] CacheService.invalidate() removes specific cache entry by key
- [x] CacheService.invalidate_prefix() removes all entries with matching key prefix
- [x] CacheService.clear() removes all entries
- [x] CacheService.cleanup_expired() removes all expired entries and returns count
- [x] CacheService.stats() returns current size and max_size
- [x] cache_key() generates unique key from arguments and kwargs
- [x] @cacheable decorator memoizes function results with configurable TTL
- [x] @cacheable decorator skips cache for None results
- [x] Thread-safety: concurrent access does not corrupt cache state

## Task 4: Configuration Singleton

### Acceptance Criteria
- [x] Config.get() retrieves setting value with optional default
- [x] Config.get() reads from environment variables first
- [x] Config.get() falls back to default when env var not set
- [x] Config.set() stores configuration values
- [x] Boolean values are coerced from strings ("true", "1", "yes" -> True)
- [x] Integer values are coerced from strings
- [x] Config is a thread-safe singleton
- [x] Config.refresh() reloads settings from environment
- [x] Common settings have sensible defaults (FLASK_PORT=8084, etc.)

## Task 5: Download Queue

### Acceptance Criteria
- [ ] BookQueue.add() adds download task to queue, returns False if already exists
- [ ] BookQueue.get_next() returns next task_id with cancellation flag
- [ ] BookQueue respects priority ordering (lower priority number processed first)
- [ ] BookQueue.update_status() updates task status and timestamp
- [ ] BookQueue.cancel() sets cancellation flag for task
- [ ] BookQueue.get_status() returns current status of task
- [ ] BookQueue.get_task() returns task data by id
- [ ] BookQueue.get_all_statuses() returns dict of all task statuses
- [ ] Terminal statuses (COMPLETE, ERROR, CANCELLED) are tracked correctly
- [ ] Stale tasks are cleaned up after timeout
- [ ] Thread-safety: concurrent operations don't corrupt state

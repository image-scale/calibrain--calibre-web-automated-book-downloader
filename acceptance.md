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
- [ ] parse_naming_template() substitutes {Author}, {Title}, {Year}, {Series}, {SeriesPosition} placeholders
- [ ] parse_naming_template() supports conditional placeholders like {Series/} that include suffix only when value exists
- [ ] parse_naming_template() supports conditional prefix like { - Subtitle} that includes prefix only when value exists
- [ ] sanitize_filename() replaces invalid characters (\\/:*?"<>|) with underscores
- [ ] sanitize_filename() collapses multiple underscores and trims whitespace/dots
- [ ] sanitize_filename() truncates to max_length (default 245)
- [ ] format_series_position() formats float as integer when whole number (e.g., 2.0 -> "2")
- [ ] derive_primary_title() extracts title without subtitle suffix when possible
- [ ] natural_sort_key() pads numbers for correct sorting (Part 2 < Part 10)
- [ ] assign_part_numbers() assigns sequential part numbers to sorted file list
- [ ] build_library_path() combines base path, template, and metadata into a full path
- [ ] build_library_path() prevents path traversal attacks

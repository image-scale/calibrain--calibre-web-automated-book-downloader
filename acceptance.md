# Acceptance Criteria

## Task 1: Core Data Models

### Acceptance Criteria
- [ ] QueueStatus enum has values: QUEUED, RESOLVING, LOCATING, DOWNLOADING, COMPLETE, ERROR, CANCELLED
- [ ] TERMINAL_QUEUE_STATUSES contains COMPLETE, ERROR, CANCELLED
- [ ] ACTIVE_QUEUE_STATUSES contains QUEUED, RESOLVING, LOCATING, DOWNLOADING
- [ ] SearchMode enum has DIRECT and UNIVERSAL values
- [ ] QueueItem dataclass has book_id, priority, added_time fields and supports comparison for priority queue ordering
- [ ] QueueItem with lower priority number takes precedence (priority 1 < priority 2)
- [ ] QueueItem with same priority uses added_time for ordering (earlier time < later time)
- [ ] DownloadTask dataclass has required fields: task_id, source, title
- [ ] DownloadTask has optional fields: author, year, format, size, preview, status, progress, etc.
- [ ] DownloadTask.get_filename() returns sanitized filename from metadata
- [ ] DownloadTask supports priority queue comparison via __lt__
- [ ] build_filename() generates "Author - Title (Year).format" pattern
- [ ] build_filename() sanitizes invalid characters (\\/:*?"<>|) to underscores
- [ ] build_filename() truncates to 245 characters max
- [ ] SearchFilters dataclass has isbn, author, title, lang, sort, content, format fields

"""Tests for core data models."""

import time

import pytest

from bookdl.core.models import (
    ACTIVE_QUEUE_STATUSES,
    TERMINAL_QUEUE_STATUSES,
    DownloadTask,
    QueueItem,
    QueueStatus,
    SearchFilters,
    SearchMode,
    build_filename,
)


class TestQueueStatus:
    """Tests for QueueStatus enum."""

    def test_queue_status_has_all_values(self):
        """QueueStatus enum has all required status values."""
        assert QueueStatus.QUEUED == "queued"
        assert QueueStatus.RESOLVING == "resolving"
        assert QueueStatus.LOCATING == "locating"
        assert QueueStatus.DOWNLOADING == "downloading"
        assert QueueStatus.COMPLETE == "complete"
        assert QueueStatus.ERROR == "error"
        assert QueueStatus.CANCELLED == "cancelled"

    def test_terminal_statuses_contains_expected(self):
        """TERMINAL_QUEUE_STATUSES contains COMPLETE, ERROR, CANCELLED."""
        assert QueueStatus.COMPLETE in TERMINAL_QUEUE_STATUSES
        assert QueueStatus.ERROR in TERMINAL_QUEUE_STATUSES
        assert QueueStatus.CANCELLED in TERMINAL_QUEUE_STATUSES
        assert len(TERMINAL_QUEUE_STATUSES) == 3

    def test_active_statuses_contains_expected(self):
        """ACTIVE_QUEUE_STATUSES contains active statuses."""
        assert QueueStatus.QUEUED in ACTIVE_QUEUE_STATUSES
        assert QueueStatus.RESOLVING in ACTIVE_QUEUE_STATUSES
        assert QueueStatus.LOCATING in ACTIVE_QUEUE_STATUSES
        assert QueueStatus.DOWNLOADING in ACTIVE_QUEUE_STATUSES
        assert len(ACTIVE_QUEUE_STATUSES) == 4

    def test_terminal_and_active_are_disjoint(self):
        """Terminal and active status sets do not overlap."""
        assert TERMINAL_QUEUE_STATUSES.isdisjoint(ACTIVE_QUEUE_STATUSES)


class TestSearchMode:
    """Tests for SearchMode enum."""

    def test_search_mode_has_direct_and_universal(self):
        """SearchMode enum has DIRECT and UNIVERSAL values."""
        assert SearchMode.DIRECT == "direct"
        assert SearchMode.UNIVERSAL == "universal"


class TestQueueItem:
    """Tests for QueueItem dataclass."""

    def test_queue_item_fields(self):
        """QueueItem has book_id, priority, added_time fields."""
        item = QueueItem(book_id="abc123", priority=5, added_time=1234567890.0)
        assert item.book_id == "abc123"
        assert item.priority == 5
        assert item.added_time == 1234567890.0

    def test_lower_priority_number_takes_precedence(self):
        """QueueItem with lower priority number is 'less than' (higher precedence)."""
        high_priority = QueueItem(book_id="a", priority=1, added_time=100.0)
        low_priority = QueueItem(book_id="b", priority=10, added_time=100.0)

        assert high_priority < low_priority
        assert not low_priority < high_priority

    def test_same_priority_uses_added_time(self):
        """QueueItem with same priority uses added_time for ordering (earlier first)."""
        earlier = QueueItem(book_id="a", priority=5, added_time=100.0)
        later = QueueItem(book_id="b", priority=5, added_time=200.0)

        assert earlier < later
        assert not later < earlier

    def test_queue_item_sorting(self):
        """QueueItems sort correctly by priority then added_time."""
        items = [
            QueueItem("c", priority=5, added_time=300.0),
            QueueItem("a", priority=1, added_time=100.0),
            QueueItem("b", priority=1, added_time=200.0),
            QueueItem("d", priority=10, added_time=50.0),
        ]
        sorted_items = sorted(items)
        assert [i.book_id for i in sorted_items] == ["a", "b", "c", "d"]


class TestDownloadTask:
    """Tests for DownloadTask dataclass."""

    def test_required_fields(self):
        """DownloadTask requires task_id, source, title."""
        task = DownloadTask(task_id="task1", source="direct", title="My Book")
        assert task.task_id == "task1"
        assert task.source == "direct"
        assert task.title == "My Book"

    def test_optional_fields_have_defaults(self):
        """DownloadTask optional fields have appropriate defaults."""
        task = DownloadTask(task_id="task1", source="direct", title="My Book")
        assert task.author is None
        assert task.year is None
        assert task.format is None
        assert task.size is None
        assert task.preview is None
        assert task.status == QueueStatus.QUEUED
        assert task.progress == 0.0
        assert task.priority == 0
        assert isinstance(task.output_args, dict)
        assert len(task.output_args) == 0

    def test_download_task_comparison_by_priority(self):
        """DownloadTask comparison uses priority first."""
        high = DownloadTask("a", "src", "Book A", priority=1)
        low = DownloadTask("b", "src", "Book B", priority=10)

        assert high < low
        assert not low < high

    def test_download_task_comparison_by_added_time(self):
        """DownloadTask with same priority uses added_time."""
        # Use explicit added_time to ensure deterministic comparison
        earlier = DownloadTask("a", "src", "Book A", priority=5, added_time=100.0)
        later = DownloadTask("b", "src", "Book B", priority=5, added_time=200.0)

        assert earlier < later

    def test_get_filename_from_download_path(self):
        """get_filename() returns filename from download_path when set."""
        task = DownloadTask(
            task_id="task1",
            source="direct",
            title="Ignored Title",
            download_path="/path/to/actual_file.epub",
        )
        assert task.get_filename() == "actual_file.epub"

    def test_get_filename_builds_from_metadata(self):
        """get_filename() builds filename from metadata when no download_path."""
        task = DownloadTask(
            task_id="task1",
            source="direct",
            title="The Great Book",
            author="John Author",
            year="2023",
            format="epub",
        )
        assert task.get_filename() == "John Author - The Great Book (2023).epub"

    def test_get_filename_title_only(self):
        """get_filename() works with just title."""
        task = DownloadTask(task_id="task1", source="direct", title="Simple Title")
        assert task.get_filename() == "Simple Title"


class TestBuildFilename:
    """Tests for build_filename function."""

    def test_full_pattern(self):
        """build_filename generates 'Author - Title (Year).format' pattern."""
        result = build_filename("Great Book", author="John Doe", year="2023", fmt="epub")
        assert result == "John Doe - Great Book (2023).epub"

    def test_title_only(self):
        """build_filename works with just title."""
        result = build_filename("Simple Title")
        assert result == "Simple Title"

    def test_title_with_author(self):
        """build_filename works with title and author."""
        result = build_filename("My Book", author="Jane Writer")
        assert result == "Jane Writer - My Book"

    def test_title_with_year(self):
        """build_filename works with title and year."""
        result = build_filename("History", year="1990")
        assert result == "History (1990)"

    def test_sanitizes_invalid_characters(self):
        """build_filename replaces \\/:*?\"<>| with underscores."""
        result = build_filename("Book: A <Good> Story?")
        assert result == "Book_ A _Good_ Story_"

    def test_sanitizes_backslash_and_colon(self):
        """build_filename handles backslash and colon."""
        result = build_filename("C:\\path\\to\\book")
        assert result == "C__path_to_book"

    def test_sanitizes_quotes_and_pipes(self):
        """build_filename handles quotes and pipes."""
        result = build_filename('Book "With" Quotes | And Pipes')
        assert result == "Book _With_ Quotes _ And Pipes"

    def test_truncates_to_245_chars(self):
        """build_filename truncates to 245 characters (before extension)."""
        long_title = "A" * 300
        result = build_filename(long_title)
        assert len(result) == 245

    def test_truncates_before_adding_extension(self):
        """build_filename truncates title before adding extension."""
        long_title = "B" * 300
        result = build_filename(long_title, fmt="epub")
        # 245 chars + ".epub" = 250 total
        assert len(result) == 250
        assert result.endswith(".epub")

    def test_strips_leading_trailing_whitespace(self):
        """build_filename strips leading/trailing whitespace from result."""
        result = build_filename("  Title With Spaces  ")
        assert result == "Title With Spaces"


class TestSearchFilters:
    """Tests for SearchFilters dataclass."""

    def test_all_fields_default_to_none(self):
        """SearchFilters fields default to None."""
        filters = SearchFilters()
        assert filters.isbn is None
        assert filters.author is None
        assert filters.title is None
        assert filters.lang is None
        assert filters.sort is None
        assert filters.content is None
        assert filters.format is None

    def test_fields_can_be_set(self):
        """SearchFilters accepts all field values."""
        filters = SearchFilters(
            isbn=["978-0-13-468599-1"],
            author=["Brandon Sanderson"],
            title=["Mistborn"],
            lang=["en", "de"],
            sort="newest",
            content=["fiction"],
            format=["epub", "pdf"],
        )
        assert filters.isbn == ["978-0-13-468599-1"]
        assert filters.author == ["Brandon Sanderson"]
        assert filters.title == ["Mistborn"]
        assert filters.lang == ["en", "de"]
        assert filters.sort == "newest"
        assert filters.content == ["fiction"]
        assert filters.format == ["epub", "pdf"]

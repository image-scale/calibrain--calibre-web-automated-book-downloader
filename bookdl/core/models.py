"""Data structures and models used across the book downloader application."""

import re
import time
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any


def build_filename(
    title: str,
    author: str | None = None,
    year: str | None = None,
    fmt: str | None = None,
) -> str:
    """Build a filesystem-safe filename from book metadata.

    Pattern: "Author - Title (Year).format"
    Invalid characters are replaced with underscores.
    Result is truncated to 245 characters (before extension).

    Args:
        title: Book title (required)
        author: Author name (optional)
        year: Publication year (optional)
        fmt: File format/extension without dot (optional)

    Returns:
        Sanitized filename string
    """
    parts = []
    if author:
        parts.append(author)
        parts.append(" - ")
    parts.append(title)
    if year:
        parts.append(f" ({year})")

    filename = "".join(parts)
    # Replace invalid filesystem characters with underscores
    filename = re.sub(r'[\\/:*?"<>|]', "_", filename.strip())[:245]

    if fmt:
        filename = f"{filename}.{fmt}"

    return filename


class QueueStatus(StrEnum):
    """Enum for possible download queue statuses."""

    QUEUED = "queued"
    RESOLVING = "resolving"
    LOCATING = "locating"
    DOWNLOADING = "downloading"
    COMPLETE = "complete"
    ERROR = "error"
    CANCELLED = "cancelled"


# Statuses that indicate the download is finished (successfully or not)
TERMINAL_QUEUE_STATUSES: frozenset[QueueStatus] = frozenset(
    {
        QueueStatus.COMPLETE,
        QueueStatus.ERROR,
        QueueStatus.CANCELLED,
    }
)

# Statuses that indicate the download is active/in-progress
ACTIVE_QUEUE_STATUSES: frozenset[QueueStatus] = frozenset(
    {
        QueueStatus.QUEUED,
        QueueStatus.RESOLVING,
        QueueStatus.LOCATING,
        QueueStatus.DOWNLOADING,
    }
)


class SearchMode(StrEnum):
    """Search modes supported by the application."""

    DIRECT = "direct"  # Query configured sources directly
    UNIVERSAL = "universal"  # Search via metadata providers for richer results


@dataclass
class QueueItem:
    """Queue item with priority and metadata for ordering in priority queue."""

    book_id: str
    priority: int
    added_time: float

    def __lt__(self, other: "QueueItem") -> bool:
        """Compare items for priority queue (lower priority number = higher precedence).

        When priorities are equal, earlier added_time takes precedence (FIFO).
        """
        if self.priority != other.priority:
            return self.priority < other.priority
        return self.added_time < other.added_time


@dataclass
class DownloadTask:
    """Mutable download task state tracked throughout the download pipeline.

    Contains all metadata and state needed to process a book download from
    queue through completion.
    """

    task_id: str  # Unique ID (e.g., hash, GUID)
    source: str  # Handler name ("direct_download", "prowlarr", etc.)
    title: str  # Display title for queue

    # Display info for queue sidebar
    author: str | None = None
    year: str | None = None
    format: str | None = None
    size: str | None = None
    preview: str | None = None
    content_type: str | None = None  # "ebook", "audiobook", etc.
    source_url: str | None = None  # Original release URL

    # Retry support
    retry_download_url: str | None = None
    retry_download_protocol: str | None = None
    retry_release_name: str | None = None
    retry_expected_hash: str | None = None
    retry_ratio_limit: float | None = None
    retry_seeding_time_limit_minutes: int | None = None
    can_retry_without_staged_source: bool = True

    # Series info (for library naming templates)
    series_name: str | None = None
    series_position: float | None = None
    subtitle: str | None = None

    # Hardlinking support
    original_download_path: str | None = None

    # Search mode for post-download processing behavior
    search_mode: SearchMode | None = None

    # Output selection for post-processing
    output_mode: str | None = None
    output_args: dict[str, Any] = field(default_factory=dict)

    # User association (multi-user support)
    user_id: int | None = None
    username: str | None = None
    request_id: int | None = None

    # Runtime state
    priority: int = 0
    added_time: float = field(default_factory=time.time)
    progress: float = 0.0
    status: QueueStatus = QueueStatus.QUEUED
    status_message: str | None = None
    download_path: str | None = None
    last_error_message: str | None = None
    last_error_type: str | None = None
    staged_path: str | None = None

    def __lt__(self, other: "DownloadTask") -> bool:
        """Compare tasks for priority queue (lower priority number = higher precedence)."""
        if self.priority != other.priority:
            return self.priority < other.priority
        return self.added_time < other.added_time

    def get_filename(self) -> str:
        """Build sanitized filename from task metadata.

        If download_path is set, returns just the filename from that path.
        Otherwise builds filename from title, author, year, and format.
        """
        if self.download_path:
            return Path(self.download_path).name
        return build_filename(self.title, self.author, self.year, self.format)


@dataclass
class SearchFilters:
    """Filters for book search queries."""

    isbn: list[str] | None = None
    author: list[str] | None = None
    title: list[str] | None = None
    lang: list[str] | None = None
    sort: str | None = None
    content: list[str] | None = None
    format: list[str] | None = None

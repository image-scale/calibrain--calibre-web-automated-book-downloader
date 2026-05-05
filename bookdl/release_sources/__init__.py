"""Release source plugin system.

Provides base classes, dataclasses, and registry for extensible release sources
that search for downloadable releases (torrents, direct downloads, etc.).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from collections.abc import Callable

    from bookdl.metadata_providers import BookMetadata


class ReleaseProtocol(StrEnum):
    """Protocol for downloading a release."""

    HTTP = "http"  # Direct HTTP download
    TORRENT = "torrent"  # BitTorrent
    NZB = "nzb"  # Usenet NZB


@dataclass
class Release:
    """A downloadable release from a release source.

    This is the common structure returned by all release sources,
    regardless of their internal representation.
    """

    source: str  # Source name (e.g., "direct", "prowlarr")
    source_id: str  # ID within that source
    title: str

    # Optional metadata
    format: str | None = None  # File format (e.g., "epub", "pdf", "mobi")
    language: str | None = None  # ISO 639-1 code (e.g., "en", "de")
    size: str | None = None  # Human-readable size (e.g., "1.5 MB")
    size_bytes: int | None = None  # Size in bytes for sorting
    download_url: str | None = None  # Direct download URL
    info_url: str | None = None  # Link to release info page
    protocol: ReleaseProtocol | None = None  # Download protocol

    # Source-specific metadata
    indexer: str | None = None  # Indexer name for display
    seeders: int | None = None  # For torrents
    peers: str | None = None  # For torrents: "seeders/leechers"
    content_type: str | None = None  # "ebook" or "audiobook"

    # Additional metadata
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchFilters:
    """Filters for release search."""

    format: str | None = None  # Filter by format (e.g., "epub")
    language: str | None = None  # Filter by language
    content_type: str = "ebook"  # "ebook" or "audiobook"


class ReleaseSource(ABC):
    """Abstract base class for release sources.

    Release sources search for downloadable releases of books.
    """

    # Subclasses should define these as class attributes
    supported_content_types: ClassVar[list[str]] = ["ebook", "audiobook"]

    @property
    @abstractmethod
    def name(self) -> str:
        """Internal identifier for this source (e.g., 'prowlarr')."""
        ...

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable name (e.g., 'Prowlarr')."""
        ...

    @abstractmethod
    def search(
        self,
        book: "BookMetadata",
        filters: SearchFilters | None = None,
    ) -> list[Release]:
        """Search for releases of a book.

        Args:
            book: Book metadata to search for
            filters: Optional filters (format, language, content_type)

        Returns:
            List of matching releases
        """
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this source is configured and reachable.

        Returns:
            True if source can be used, False otherwise
        """
        ...

    def get_column_config(self) -> "ReleaseColumnConfig":
        """Get column configuration for release list UI.

        Override this method to customize column layout.

        Returns:
            Column configuration for this source
        """
        return default_column_config()


# --- Column Schema for UI ---


class ColumnRenderType(StrEnum):
    """How the frontend should render the column value."""

    TEXT = "text"  # Plain text
    BADGE = "badge"  # Colored badge (format, language)
    SIZE = "size"  # File size formatting
    NUMBER = "number"  # Numeric value
    PEERS = "peers"  # Peers display: "S/L" format


class ColumnAlign(StrEnum):
    """Column alignment options."""

    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"


@dataclass
class ColumnColorHint:
    """Color hint for badge-type columns."""

    type: str  # "map" or "static"
    value: str  # Map name or CSS class


@dataclass
class ColumnSchema:
    """Definition for a single column in the release list."""

    key: str  # Data path (e.g., "format", "extra.language")
    label: str  # Accessibility label

    render_type: ColumnRenderType = ColumnRenderType.TEXT
    align: ColumnAlign = ColumnAlign.LEFT
    width: str = "auto"  # CSS width
    hide_mobile: bool = False  # Hide on small screens
    color_hint: ColumnColorHint | None = None  # For BADGE render type
    fallback: str = "-"  # Value when data is missing
    uppercase: bool = False  # Force uppercase display
    sortable: bool = False  # Show in sort dropdown
    sort_key: str | None = None  # Field to sort by


@dataclass
class ReleaseColumnConfig:
    """Complete column configuration for a release source."""

    columns: list[ColumnSchema]
    grid_template: str = "minmax(0,2fr) 60px 80px 80px"  # CSS grid-template-columns
    supported_filters: list[str] | None = None  # ["format", "language"]


def serialize_column_config(config: ReleaseColumnConfig) -> dict[str, Any]:
    """Serialize column configuration for API response.

    Args:
        config: Column configuration to serialize

    Returns:
        Dictionary suitable for JSON serialization
    """
    return {
        "columns": [
            {
                "key": col.key,
                "label": col.label,
                "render_type": col.render_type.value,
                "align": col.align.value,
                "width": col.width,
                "hide_mobile": col.hide_mobile,
                "color_hint": {
                    "type": col.color_hint.type,
                    "value": col.color_hint.value,
                }
                if col.color_hint
                else None,
                "fallback": col.fallback,
                "uppercase": col.uppercase,
                "sortable": col.sortable,
                "sort_key": col.sort_key,
            }
            for col in config.columns
        ],
        "grid_template": config.grid_template,
        "supported_filters": config.supported_filters,
    }


def default_column_config() -> ReleaseColumnConfig:
    """Get the default column configuration.

    Returns:
        Default column configuration for release lists
    """
    return ReleaseColumnConfig(
        columns=[
            ColumnSchema(
                key="language",
                label="Language",
                render_type=ColumnRenderType.BADGE,
                align=ColumnAlign.CENTER,
                width="60px",
                color_hint=ColumnColorHint(type="map", value="language"),
                uppercase=True,
            ),
            ColumnSchema(
                key="format",
                label="Format",
                render_type=ColumnRenderType.BADGE,
                align=ColumnAlign.CENTER,
                width="80px",
                color_hint=ColumnColorHint(type="map", value="format"),
                uppercase=True,
            ),
            ColumnSchema(
                key="size",
                label="Size",
                render_type=ColumnRenderType.SIZE,
                align=ColumnAlign.CENTER,
                width="80px",
            ),
        ],
        grid_template="minmax(0,2fr) 60px 80px 80px",
        supported_filters=["format", "language"],
    )


# --- Source Registry ---


class SourceRegistry:
    """Registry for release sources.

    Manages source instances and provides lookup functionality.
    """

    def __init__(self) -> None:
        """Initialize empty registry."""
        self._sources: dict[str, ReleaseSource] = {}

    def register(self, source: ReleaseSource) -> None:
        """Register a source by its name.

        Args:
            source: ReleaseSource instance to register
        """
        self._sources[source.name] = source

    def get(self, name: str) -> ReleaseSource | None:
        """Get a source by name.

        Args:
            name: Source name

        Returns:
            Source instance, or None if not found
        """
        return self._sources.get(name)

    def list_names(self) -> list[str]:
        """List all registered source names.

        Returns:
            List of source names
        """
        return list(self._sources.keys())

    def list_sources(self) -> list[dict[str, Any]]:
        """List all registered sources with their availability info.

        Returns:
            List of dicts with name, display_name, enabled, supported_content_types
        """
        result = []
        for name, source in self._sources.items():
            result.append(
                {
                    "name": name,
                    "display_name": source.display_name,
                    "enabled": source.is_available(),
                    "supported_content_types": getattr(
                        source, "supported_content_types", ["ebook", "audiobook"]
                    ),
                }
            )
        return result

    def clear(self) -> None:
        """Remove all registered sources."""
        self._sources.clear()


# Global registry instance
_global_registry = SourceRegistry()


def get_registry() -> SourceRegistry:
    """Get the global source registry.

    Returns:
        Global SourceRegistry instance
    """
    return _global_registry


def register_source(source: ReleaseSource) -> None:
    """Register a source in the global registry.

    Args:
        source: Source to register
    """
    _global_registry.register(source)


def get_source(name: str) -> ReleaseSource | None:
    """Get a source from the global registry.

    Args:
        name: Source name

    Returns:
        Source instance, or None if not found
    """
    return _global_registry.get(name)

"""Metadata provider plugin system for book search.

Provides base classes, dataclasses, and registry for extensible book metadata providers.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass
class BookMetadata:
    """Book metadata from a provider.

    Contains all information about a book from a metadata provider,
    suitable for display in search results and driving downloads.
    """

    provider: str  # Internal provider name (e.g., "openlibrary")
    provider_id: str  # ID in the provider's system
    title: str

    # Optional fields - not all providers have all data
    authors: list[str] = field(default_factory=list)
    isbn_10: str | None = None
    isbn_13: str | None = None
    cover_url: str | None = None
    description: str | None = None
    publisher: str | None = None
    publish_year: int | None = None
    language: str | None = None
    genres: list[str] = field(default_factory=list)
    source_url: str | None = None  # Link to book on provider's site
    subtitle: str | None = None
    page_count: int | None = None

    # Series information
    series_name: str | None = None
    series_position: float | None = None

    # Search optimization
    search_title: str | None = None  # Clean title for searching releases
    search_author: str | None = None  # Clean author for searching releases


@dataclass
class SearchOptions:
    """Options for metadata search queries."""

    query: str
    language: str | None = None
    limit: int = 20
    page: int = 1


@dataclass
class SearchResult:
    """Result from a metadata search with pagination info."""

    books: list[BookMetadata] = field(default_factory=list)
    page: int = 1
    total_found: int = 0
    has_more: bool = False


class MetadataProvider(ABC):
    """Abstract base class for metadata providers.

    All metadata providers must implement this interface.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Internal identifier for this provider (e.g., 'openlibrary')."""
        ...

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable name (e.g., 'Open Library')."""
        ...

    @property
    def requires_auth(self) -> bool:
        """Whether this provider requires authentication."""
        return False

    @abstractmethod
    def search(self, options: SearchOptions) -> SearchResult:
        """Search for books matching the query.

        Args:
            options: Search options (query, language, limit, page)

        Returns:
            SearchResult with matching books and pagination info
        """
        ...

    def get_by_id(self, provider_id: str) -> BookMetadata | None:
        """Get a specific book by provider ID.

        Override this for providers that support direct ID lookup.

        Args:
            provider_id: ID in the provider's system

        Returns:
            BookMetadata if found, None otherwise
        """
        return None


class ProviderRegistry:
    """Registry for metadata providers.

    Manages provider instances and provides search-all functionality.
    """

    def __init__(self) -> None:
        """Initialize empty registry."""
        self._providers: dict[str, MetadataProvider] = {}

    def register(self, provider: MetadataProvider) -> None:
        """Register a provider by its name.

        Args:
            provider: MetadataProvider instance to register
        """
        self._providers[provider.name] = provider

    def get(self, name: str) -> MetadataProvider | None:
        """Get a provider by name.

        Args:
            name: Provider name

        Returns:
            Provider instance, or None if not found
        """
        return self._providers.get(name)

    def list_names(self) -> list[str]:
        """List all registered provider names.

        Returns:
            List of provider names
        """
        return list(self._providers.keys())

    def list_providers(self) -> list[MetadataProvider]:
        """List all registered provider instances.

        Returns:
            List of provider instances
        """
        return list(self._providers.values())

    def search_all(
        self,
        options: SearchOptions,
        *,
        providers: list[str] | None = None,
    ) -> dict[str, SearchResult]:
        """Search across all (or specified) providers.

        Args:
            options: Search options
            providers: Optional list of provider names to search (default: all)

        Returns:
            Dictionary mapping provider name to SearchResult
        """
        results: dict[str, SearchResult] = {}

        target_providers = providers or list(self._providers.keys())

        for provider_name in target_providers:
            provider = self._providers.get(provider_name)
            if provider is None:
                continue

            try:
                results[provider_name] = provider.search(options)
            except Exception:
                # Log error but continue with other providers
                results[provider_name] = SearchResult(
                    books=[],
                    page=options.page,
                    total_found=0,
                    has_more=False,
                )

        return results

    def clear(self) -> None:
        """Remove all registered providers."""
        self._providers.clear()


# Global registry instance
_global_registry = ProviderRegistry()


def get_registry() -> ProviderRegistry:
    """Get the global provider registry.

    Returns:
        Global ProviderRegistry instance
    """
    return _global_registry


def register_provider(provider: MetadataProvider) -> None:
    """Register a provider in the global registry.

    Args:
        provider: Provider to register
    """
    _global_registry.register(provider)


def search_providers(
    options: SearchOptions,
    *,
    providers: list[str] | None = None,
) -> dict[str, SearchResult]:
    """Search across providers using the global registry.

    Args:
        options: Search options
        providers: Optional list of provider names

    Returns:
        Dictionary mapping provider name to SearchResult
    """
    return _global_registry.search_all(options, providers=providers)

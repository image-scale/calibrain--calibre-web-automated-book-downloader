"""Tests for the metadata provider plugin system."""

import pytest

from bookdl.metadata_providers import (
    BookMetadata,
    MetadataProvider,
    ProviderRegistry,
    SearchOptions,
    SearchResult,
    get_registry,
    register_provider,
    search_providers,
)


class MockProvider(MetadataProvider):
    """Mock provider for testing."""

    def __init__(self, name: str = "mock", display_name: str = "Mock Provider"):
        self._name = name
        self._display_name = display_name
        self._books: list[BookMetadata] = []

    @property
    def name(self) -> str:
        return self._name

    @property
    def display_name(self) -> str:
        return self._display_name

    def add_book(self, book: BookMetadata) -> None:
        """Add a book to the mock provider."""
        self._books.append(book)

    def search(self, options: SearchOptions) -> SearchResult:
        """Return matching books."""
        query_lower = options.query.lower()
        matching = [
            book for book in self._books if query_lower in book.title.lower()
        ]
        return SearchResult(
            books=matching[: options.limit],
            page=options.page,
            total_found=len(matching),
            has_more=len(matching) > options.limit,
        )


class FailingProvider(MetadataProvider):
    """Provider that always raises an exception."""

    @property
    def name(self) -> str:
        return "failing"

    @property
    def display_name(self) -> str:
        return "Failing Provider"

    def search(self, options: SearchOptions) -> SearchResult:
        raise RuntimeError("Provider error")


class TestBookMetadata:
    """Tests for BookMetadata dataclass."""

    def test_required_fields(self):
        """BookMetadata requires provider, provider_id, title."""
        book = BookMetadata(
            provider="test",
            provider_id="123",
            title="Test Book",
        )
        assert book.provider == "test"
        assert book.provider_id == "123"
        assert book.title == "Test Book"

    def test_optional_fields_default(self):
        """Optional fields have appropriate defaults."""
        book = BookMetadata(
            provider="test",
            provider_id="123",
            title="Test Book",
        )
        assert book.authors == []
        assert book.isbn_10 is None
        assert book.isbn_13 is None
        assert book.cover_url is None
        assert book.description is None
        assert book.publisher is None
        assert book.publish_year is None
        assert book.language is None
        assert book.genres == []
        assert book.series_name is None
        assert book.series_position is None

    def test_all_fields_can_be_set(self):
        """All BookMetadata fields can be set."""
        book = BookMetadata(
            provider="openlibrary",
            provider_id="OL123W",
            title="The Way of Kings",
            authors=["Brandon Sanderson"],
            isbn_10="0765326353",
            isbn_13="9780765326355",
            cover_url="https://example.com/cover.jpg",
            description="Epic fantasy novel",
            publisher="Tor Books",
            publish_year=2010,
            language="en",
            genres=["Fantasy", "Epic Fantasy"],
            source_url="https://openlibrary.org/works/OL123W",
            subtitle="Book One of the Stormlight Archive",
            page_count=1007,
            series_name="Stormlight Archive",
            series_position=1.0,
            search_title="The Way of Kings",
            search_author="Brandon Sanderson",
        )
        assert book.authors == ["Brandon Sanderson"]
        assert book.isbn_13 == "9780765326355"
        assert book.series_name == "Stormlight Archive"
        assert book.series_position == 1.0


class TestSearchOptions:
    """Tests for SearchOptions dataclass."""

    def test_required_query(self):
        """SearchOptions requires query."""
        options = SearchOptions(query="test query")
        assert options.query == "test query"

    def test_default_values(self):
        """SearchOptions has sensible defaults."""
        options = SearchOptions(query="test")
        assert options.language is None
        assert options.limit == 20
        assert options.page == 1

    def test_all_fields_can_be_set(self):
        """All SearchOptions fields can be set."""
        options = SearchOptions(
            query="mistborn",
            language="en",
            limit=50,
            page=2,
        )
        assert options.query == "mistborn"
        assert options.language == "en"
        assert options.limit == 50
        assert options.page == 2


class TestSearchResult:
    """Tests for SearchResult dataclass."""

    def test_default_values(self):
        """SearchResult has appropriate defaults."""
        result = SearchResult()
        assert result.books == []
        assert result.page == 1
        assert result.total_found == 0
        assert result.has_more is False

    def test_with_books(self):
        """SearchResult holds list of books."""
        book = BookMetadata(provider="test", provider_id="1", title="Book 1")
        result = SearchResult(
            books=[book],
            page=1,
            total_found=100,
            has_more=True,
        )
        assert len(result.books) == 1
        assert result.total_found == 100
        assert result.has_more is True


class TestMetadataProvider:
    """Tests for MetadataProvider abstract class."""

    def test_requires_name_property(self):
        """Provider must implement name property."""
        provider = MockProvider(name="test_provider")
        assert provider.name == "test_provider"

    def test_requires_display_name_property(self):
        """Provider must implement display_name property."""
        provider = MockProvider(display_name="Test Provider")
        assert provider.display_name == "Test Provider"

    def test_requires_auth_defaults_false(self):
        """requires_auth defaults to False."""
        provider = MockProvider()
        assert provider.requires_auth is False

    def test_requires_search_method(self):
        """Provider must implement search method."""
        provider = MockProvider()
        provider.add_book(
            BookMetadata(provider="mock", provider_id="1", title="Test Book")
        )

        result = provider.search(SearchOptions(query="test"))

        assert isinstance(result, SearchResult)
        assert len(result.books) == 1

    def test_get_by_id_returns_none_by_default(self):
        """get_by_id returns None by default."""
        provider = MockProvider()
        assert provider.get_by_id("some_id") is None


class TestProviderRegistry:
    """Tests for ProviderRegistry class."""

    def test_register_adds_provider(self):
        """register() adds provider by name."""
        registry = ProviderRegistry()
        provider = MockProvider(name="test_provider")

        registry.register(provider)

        assert registry.get("test_provider") is provider

    def test_get_returns_provider_by_name(self):
        """get() retrieves provider by name."""
        registry = ProviderRegistry()
        provider = MockProvider(name="my_provider")
        registry.register(provider)

        result = registry.get("my_provider")

        assert result is provider

    def test_get_returns_none_for_unknown(self):
        """get() returns None for unknown provider."""
        registry = ProviderRegistry()

        result = registry.get("nonexistent")

        assert result is None

    def test_list_names_returns_all_provider_names(self):
        """list_names() returns all registered provider names."""
        registry = ProviderRegistry()
        registry.register(MockProvider(name="provider1"))
        registry.register(MockProvider(name="provider2"))

        names = registry.list_names()

        assert sorted(names) == ["provider1", "provider2"]

    def test_list_providers_returns_instances(self):
        """list_providers() returns all provider instances."""
        registry = ProviderRegistry()
        p1 = MockProvider(name="provider1")
        p2 = MockProvider(name="provider2")
        registry.register(p1)
        registry.register(p2)

        providers = registry.list_providers()

        assert len(providers) == 2
        assert p1 in providers
        assert p2 in providers

    def test_search_all_searches_all_providers(self):
        """search_all() searches across all providers."""
        registry = ProviderRegistry()

        p1 = MockProvider(name="provider1")
        p1.add_book(BookMetadata(provider="provider1", provider_id="1", title="Test Book 1"))

        p2 = MockProvider(name="provider2")
        p2.add_book(BookMetadata(provider="provider2", provider_id="2", title="Test Book 2"))

        registry.register(p1)
        registry.register(p2)

        results = registry.search_all(SearchOptions(query="test"))

        assert "provider1" in results
        assert "provider2" in results
        assert len(results["provider1"].books) == 1
        assert len(results["provider2"].books) == 1

    def test_search_all_filters_by_provider_list(self):
        """search_all() can filter to specific providers."""
        registry = ProviderRegistry()
        registry.register(MockProvider(name="include"))
        registry.register(MockProvider(name="exclude"))

        results = registry.search_all(
            SearchOptions(query="test"),
            providers=["include"],
        )

        assert "include" in results
        assert "exclude" not in results

    def test_search_all_handles_provider_errors(self):
        """search_all() handles provider errors gracefully."""
        registry = ProviderRegistry()
        registry.register(FailingProvider())
        registry.register(MockProvider(name="working"))

        results = registry.search_all(SearchOptions(query="test"))

        # Both providers should have results (failing one has empty result)
        assert "failing" in results
        assert "working" in results
        assert results["failing"].total_found == 0

    def test_clear_removes_all_providers(self):
        """clear() removes all registered providers."""
        registry = ProviderRegistry()
        registry.register(MockProvider(name="provider1"))
        registry.register(MockProvider(name="provider2"))

        registry.clear()

        assert registry.list_names() == []


class TestGlobalRegistry:
    """Tests for global registry functions."""

    def setup_method(self):
        """Clear global registry before each test."""
        get_registry().clear()

    def test_get_registry_returns_singleton(self):
        """get_registry() returns the same instance."""
        r1 = get_registry()
        r2 = get_registry()
        assert r1 is r2

    def test_register_provider_adds_to_global(self):
        """register_provider() adds to global registry."""
        provider = MockProvider(name="global_test")
        register_provider(provider)

        assert get_registry().get("global_test") is provider

    def test_search_providers_uses_global_registry(self):
        """search_providers() searches global registry."""
        provider = MockProvider(name="search_test")
        provider.add_book(
            BookMetadata(provider="search_test", provider_id="1", title="Global Book")
        )
        register_provider(provider)

        results = search_providers(SearchOptions(query="global"))

        assert "search_test" in results
        assert len(results["search_test"].books) == 1

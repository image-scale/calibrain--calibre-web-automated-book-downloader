"""Tests for the release source plugin system."""

import pytest

from bookdl.metadata_providers import BookMetadata
from bookdl.release_sources import (
    ColumnAlign,
    ColumnColorHint,
    ColumnRenderType,
    ColumnSchema,
    Release,
    ReleaseColumnConfig,
    ReleaseProtocol,
    ReleaseSource,
    SearchFilters,
    SourceRegistry,
    default_column_config,
    get_registry,
    get_source,
    register_source,
    serialize_column_config,
)


class MockSource(ReleaseSource):
    """Mock release source for testing."""

    def __init__(
        self,
        name: str = "mock",
        display_name: str = "Mock Source",
        *,
        available: bool = True,
    ):
        self._name = name
        self._display_name = display_name
        self._available = available
        self._releases: list[Release] = []

    @property
    def name(self) -> str:
        return self._name

    @property
    def display_name(self) -> str:
        return self._display_name

    def add_release(self, release: Release) -> None:
        """Add a release for testing."""
        self._releases.append(release)

    def search(
        self,
        book: BookMetadata,
        filters: SearchFilters | None = None,
    ) -> list[Release]:
        """Return mock releases."""
        return self._releases

    def is_available(self) -> bool:
        return self._available


class UnavailableSource(ReleaseSource):
    """Source that is never available."""

    @property
    def name(self) -> str:
        return "unavailable"

    @property
    def display_name(self) -> str:
        return "Unavailable Source"

    def search(
        self,
        book: BookMetadata,
        filters: SearchFilters | None = None,
    ) -> list[Release]:
        return []

    def is_available(self) -> bool:
        return False


class TestReleaseProtocol:
    """Tests for ReleaseProtocol enum."""

    def test_http_protocol(self):
        """ReleaseProtocol has HTTP value."""
        assert ReleaseProtocol.HTTP == "http"

    def test_torrent_protocol(self):
        """ReleaseProtocol has TORRENT value."""
        assert ReleaseProtocol.TORRENT == "torrent"

    def test_nzb_protocol(self):
        """ReleaseProtocol has NZB value."""
        assert ReleaseProtocol.NZB == "nzb"


class TestRelease:
    """Tests for Release dataclass."""

    def test_required_fields(self):
        """Release requires source, source_id, title."""
        release = Release(
            source="test",
            source_id="123",
            title="Test Book",
        )
        assert release.source == "test"
        assert release.source_id == "123"
        assert release.title == "Test Book"

    def test_optional_fields_default(self):
        """Optional fields have appropriate defaults."""
        release = Release(
            source="test",
            source_id="123",
            title="Test Book",
        )
        assert release.format is None
        assert release.language is None
        assert release.size is None
        assert release.size_bytes is None
        assert release.download_url is None
        assert release.info_url is None
        assert release.protocol is None
        assert release.indexer is None
        assert release.seeders is None
        assert release.peers is None
        assert release.content_type is None
        assert release.extra == {}

    def test_all_fields_can_be_set(self):
        """All Release fields can be set."""
        release = Release(
            source="prowlarr",
            source_id="abc123",
            title="The Way of Kings",
            format="epub",
            language="en",
            size="2.5 MB",
            size_bytes=2621440,
            download_url="https://example.com/download",
            info_url="https://example.com/info",
            protocol=ReleaseProtocol.TORRENT,
            indexer="MyIndexer",
            seeders=42,
            peers="42/10",
            content_type="ebook",
            extra={"custom": "data"},
        )
        assert release.format == "epub"
        assert release.language == "en"
        assert release.size_bytes == 2621440
        assert release.protocol == ReleaseProtocol.TORRENT
        assert release.seeders == 42
        assert release.extra == {"custom": "data"}


class TestSearchFilters:
    """Tests for SearchFilters dataclass."""

    def test_defaults(self):
        """SearchFilters has sensible defaults."""
        filters = SearchFilters()
        assert filters.format is None
        assert filters.language is None
        assert filters.content_type == "ebook"

    def test_all_fields_can_be_set(self):
        """All SearchFilters fields can be set."""
        filters = SearchFilters(
            format="epub",
            language="en",
            content_type="audiobook",
        )
        assert filters.format == "epub"
        assert filters.language == "en"
        assert filters.content_type == "audiobook"


class TestReleaseSource:
    """Tests for ReleaseSource abstract class."""

    def test_requires_name_property(self):
        """Source must implement name property."""
        source = MockSource(name="test_source")
        assert source.name == "test_source"

    def test_requires_display_name_property(self):
        """Source must implement display_name property."""
        source = MockSource(display_name="Test Source")
        assert source.display_name == "Test Source"

    def test_requires_search_method(self):
        """Source must implement search method."""
        source = MockSource()
        source.add_release(
            Release(source="mock", source_id="1", title="Test Release")
        )

        book = BookMetadata(provider="test", provider_id="123", title="Test Book")
        results = source.search(book)

        assert len(results) == 1
        assert results[0].title == "Test Release"

    def test_requires_is_available_method(self):
        """Source must implement is_available method."""
        available_source = MockSource(available=True)
        unavailable_source = MockSource(available=False)

        assert available_source.is_available() is True
        assert unavailable_source.is_available() is False

    def test_get_column_config_returns_default(self):
        """get_column_config returns default config."""
        source = MockSource()
        config = source.get_column_config()

        assert isinstance(config, ReleaseColumnConfig)
        assert len(config.columns) > 0


class TestColumnRenderType:
    """Tests for ColumnRenderType enum."""

    def test_text_type(self):
        """ColumnRenderType has TEXT value."""
        assert ColumnRenderType.TEXT == "text"

    def test_badge_type(self):
        """ColumnRenderType has BADGE value."""
        assert ColumnRenderType.BADGE == "badge"

    def test_size_type(self):
        """ColumnRenderType has SIZE value."""
        assert ColumnRenderType.SIZE == "size"

    def test_number_type(self):
        """ColumnRenderType has NUMBER value."""
        assert ColumnRenderType.NUMBER == "number"


class TestColumnSchema:
    """Tests for ColumnSchema dataclass."""

    def test_required_fields(self):
        """ColumnSchema requires key and label."""
        col = ColumnSchema(key="format", label="Format")
        assert col.key == "format"
        assert col.label == "Format"

    def test_default_values(self):
        """ColumnSchema has sensible defaults."""
        col = ColumnSchema(key="test", label="Test")
        assert col.render_type == ColumnRenderType.TEXT
        assert col.align == ColumnAlign.LEFT
        assert col.width == "auto"
        assert col.hide_mobile is False
        assert col.color_hint is None
        assert col.fallback == "-"
        assert col.uppercase is False
        assert col.sortable is False
        assert col.sort_key is None

    def test_all_fields_can_be_set(self):
        """All ColumnSchema fields can be set."""
        col = ColumnSchema(
            key="format",
            label="Format",
            render_type=ColumnRenderType.BADGE,
            align=ColumnAlign.CENTER,
            width="80px",
            hide_mobile=True,
            color_hint=ColumnColorHint(type="map", value="format"),
            fallback="N/A",
            uppercase=True,
            sortable=True,
            sort_key="format_sort",
        )
        assert col.render_type == ColumnRenderType.BADGE
        assert col.align == ColumnAlign.CENTER
        assert col.width == "80px"
        assert col.hide_mobile is True
        assert col.color_hint.type == "map"
        assert col.uppercase is True
        assert col.sortable is True


class TestReleaseColumnConfig:
    """Tests for ReleaseColumnConfig dataclass."""

    def test_required_columns(self):
        """ReleaseColumnConfig requires columns list."""
        config = ReleaseColumnConfig(columns=[])
        assert config.columns == []

    def test_default_grid_template(self):
        """ReleaseColumnConfig has default grid_template."""
        config = ReleaseColumnConfig(columns=[])
        assert "minmax" in config.grid_template

    def test_with_columns(self):
        """ReleaseColumnConfig can hold column schemas."""
        col = ColumnSchema(key="format", label="Format")
        config = ReleaseColumnConfig(
            columns=[col],
            grid_template="1fr 80px",
            supported_filters=["format"],
        )
        assert len(config.columns) == 1
        assert config.grid_template == "1fr 80px"
        assert config.supported_filters == ["format"]


class TestSerializeColumnConfig:
    """Tests for serialize_column_config function."""

    def test_serializes_columns(self):
        """serialize_column_config converts columns to dicts."""
        config = ReleaseColumnConfig(
            columns=[
                ColumnSchema(
                    key="format",
                    label="Format",
                    render_type=ColumnRenderType.BADGE,
                    align=ColumnAlign.CENTER,
                ),
            ],
        )

        result = serialize_column_config(config)

        assert "columns" in result
        assert len(result["columns"]) == 1
        assert result["columns"][0]["key"] == "format"
        assert result["columns"][0]["label"] == "Format"
        assert result["columns"][0]["render_type"] == "badge"
        assert result["columns"][0]["align"] == "center"

    def test_serializes_color_hint(self):
        """serialize_column_config serializes color hints."""
        config = ReleaseColumnConfig(
            columns=[
                ColumnSchema(
                    key="format",
                    label="Format",
                    color_hint=ColumnColorHint(type="map", value="format"),
                ),
            ],
        )

        result = serialize_column_config(config)

        col = result["columns"][0]
        assert col["color_hint"]["type"] == "map"
        assert col["color_hint"]["value"] == "format"

    def test_color_hint_none_when_not_set(self):
        """serialize_column_config sets color_hint to None when not set."""
        config = ReleaseColumnConfig(
            columns=[ColumnSchema(key="title", label="Title")],
        )

        result = serialize_column_config(config)

        assert result["columns"][0]["color_hint"] is None

    def test_includes_grid_template(self):
        """serialize_column_config includes grid_template."""
        config = ReleaseColumnConfig(
            columns=[],
            grid_template="1fr 2fr 80px",
        )

        result = serialize_column_config(config)

        assert result["grid_template"] == "1fr 2fr 80px"

    def test_includes_supported_filters(self):
        """serialize_column_config includes supported_filters."""
        config = ReleaseColumnConfig(
            columns=[],
            supported_filters=["format", "language"],
        )

        result = serialize_column_config(config)

        assert result["supported_filters"] == ["format", "language"]


class TestDefaultColumnConfig:
    """Tests for default_column_config function."""

    def test_returns_column_config(self):
        """default_column_config returns ReleaseColumnConfig."""
        config = default_column_config()
        assert isinstance(config, ReleaseColumnConfig)

    def test_has_language_column(self):
        """default_column_config includes language column."""
        config = default_column_config()
        keys = [col.key for col in config.columns]
        assert "language" in keys

    def test_has_format_column(self):
        """default_column_config includes format column."""
        config = default_column_config()
        keys = [col.key for col in config.columns]
        assert "format" in keys

    def test_has_size_column(self):
        """default_column_config includes size column."""
        config = default_column_config()
        keys = [col.key for col in config.columns]
        assert "size" in keys

    def test_has_supported_filters(self):
        """default_column_config includes supported filters."""
        config = default_column_config()
        assert config.supported_filters is not None
        assert "format" in config.supported_filters
        assert "language" in config.supported_filters


class TestSourceRegistry:
    """Tests for SourceRegistry class."""

    def test_register_adds_source(self):
        """register() adds source by name."""
        registry = SourceRegistry()
        source = MockSource(name="test_source")

        registry.register(source)

        assert registry.get("test_source") is source

    def test_get_returns_source_by_name(self):
        """get() retrieves source by name."""
        registry = SourceRegistry()
        source = MockSource(name="my_source")
        registry.register(source)

        result = registry.get("my_source")

        assert result is source

    def test_get_returns_none_for_unknown(self):
        """get() returns None for unknown source."""
        registry = SourceRegistry()

        result = registry.get("nonexistent")

        assert result is None

    def test_list_names_returns_all_source_names(self):
        """list_names() returns all registered source names."""
        registry = SourceRegistry()
        registry.register(MockSource(name="source1"))
        registry.register(MockSource(name="source2"))

        names = registry.list_names()

        assert sorted(names) == ["source1", "source2"]

    def test_list_sources_returns_source_info(self):
        """list_sources() returns all sources with availability info."""
        registry = SourceRegistry()
        registry.register(MockSource(name="available", display_name="Available", available=True))
        registry.register(MockSource(name="unavailable", display_name="Unavailable", available=False))

        sources = registry.list_sources()

        assert len(sources) == 2

        available = next(s for s in sources if s["name"] == "available")
        assert available["display_name"] == "Available"
        assert available["enabled"] is True

        unavailable = next(s for s in sources if s["name"] == "unavailable")
        assert unavailable["display_name"] == "Unavailable"
        assert unavailable["enabled"] is False

    def test_list_sources_includes_content_types(self):
        """list_sources() includes supported_content_types."""
        registry = SourceRegistry()
        registry.register(MockSource(name="test"))

        sources = registry.list_sources()

        assert "supported_content_types" in sources[0]

    def test_clear_removes_all_sources(self):
        """clear() removes all registered sources."""
        registry = SourceRegistry()
        registry.register(MockSource(name="source1"))
        registry.register(MockSource(name="source2"))

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

    def test_register_source_adds_to_global(self):
        """register_source() adds to global registry."""
        source = MockSource(name="global_test")
        register_source(source)

        assert get_registry().get("global_test") is source

    def test_get_source_retrieves_from_global(self):
        """get_source() retrieves from global registry."""
        source = MockSource(name="retrieve_test")
        register_source(source)

        result = get_source("retrieve_test")

        assert result is source

    def test_get_source_returns_none_for_unknown(self):
        """get_source() returns None for unknown source."""
        result = get_source("nonexistent")
        assert result is None

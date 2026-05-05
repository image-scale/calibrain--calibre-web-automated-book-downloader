"""Tests for the Open Library metadata provider."""

from unittest.mock import MagicMock, patch

import pytest
import requests

from bookdl.metadata_providers import SearchOptions
from bookdl.metadata_providers.openlibrary import (
    COVERS_BASE_URL,
    OPENLIBRARY_BASE_URL,
    OpenLibraryProvider,
)


class TestOpenLibraryProviderProperties:
    """Tests for OpenLibraryProvider basic properties."""

    def test_name_returns_openlibrary(self):
        """Provider name is 'openlibrary'."""
        provider = OpenLibraryProvider()
        assert provider.name == "openlibrary"

    def test_display_name_returns_open_library(self):
        """Display name is 'Open Library'."""
        provider = OpenLibraryProvider()
        assert provider.display_name == "Open Library"

    def test_requires_auth_is_false(self):
        """Open Library does not require authentication."""
        provider = OpenLibraryProvider()
        assert provider.requires_auth is False

    def test_accepts_custom_session(self):
        """Provider accepts a custom session for dependency injection."""
        mock_session = MagicMock()
        provider = OpenLibraryProvider(session=mock_session)
        assert provider._session is mock_session


class TestOpenLibrarySearch:
    """Tests for OpenLibraryProvider.search() method."""

    def test_search_queries_api_with_correct_params(self):
        """search() sends correct parameters to the API."""
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"docs": [], "numFound": 0}
        mock_session.get.return_value = mock_response

        provider = OpenLibraryProvider(session=mock_session)
        options = SearchOptions(query="mistborn", limit=10, page=2)
        provider.search(options)

        mock_session.get.assert_called_once()
        call_args = mock_session.get.call_args
        assert call_args[0][0] == f"{OPENLIBRARY_BASE_URL}/search.json"
        params = call_args[1]["params"]
        assert params["q"] == "mistborn"
        assert params["limit"] == 10
        assert params["page"] == 2

    def test_search_includes_language_when_specified(self):
        """search() includes language filter when provided."""
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"docs": [], "numFound": 0}
        mock_session.get.return_value = mock_response

        provider = OpenLibraryProvider(session=mock_session)
        options = SearchOptions(query="test", language="en")
        provider.search(options)

        params = mock_session.get.call_args[1]["params"]
        assert params["lang"] == "en"

    def test_search_parses_response_into_book_metadata(self):
        """search() correctly parses API response into BookMetadata."""
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "docs": [
                {
                    "key": "/works/OL12345W",
                    "title": "The Way of Kings",
                    "author_name": ["Brandon Sanderson"],
                    "first_publish_year": 2010,
                    "cover_i": 9876543,
                    "isbn": ["0765326353", "9780765326355"],
                    "publisher": ["Tor Books"],
                    "language": ["eng"],
                    "subject": ["Fantasy", "Epic Fantasy", "Fiction"],
                }
            ],
            "numFound": 1,
        }
        mock_session.get.return_value = mock_response

        provider = OpenLibraryProvider(session=mock_session)
        result = provider.search(SearchOptions(query="way of kings"))

        assert len(result.books) == 1
        book = result.books[0]
        assert book.provider == "openlibrary"
        assert book.provider_id == "OL12345W"
        assert book.title == "The Way of Kings"
        assert book.authors == ["Brandon Sanderson"]
        assert book.publish_year == 2010
        assert book.isbn_10 == "0765326353"
        assert book.isbn_13 == "9780765326355"
        assert book.publisher == "Tor Books"
        assert book.language == "eng"
        assert "Fantasy" in book.genres

    def test_search_constructs_cover_url_from_cover_i(self):
        """search() constructs cover URL from cover_i field."""
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "docs": [
                {
                    "key": "/works/OL123W",
                    "title": "Test Book",
                    "cover_i": 12345,
                }
            ],
            "numFound": 1,
        }
        mock_session.get.return_value = mock_response

        provider = OpenLibraryProvider(session=mock_session)
        result = provider.search(SearchOptions(query="test"))

        assert result.books[0].cover_url == f"{COVERS_BASE_URL}/b/id/12345-L.jpg"

    def test_search_no_cover_url_when_cover_i_missing(self):
        """search() sets cover_url to None when cover_i is missing."""
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "docs": [
                {
                    "key": "/works/OL123W",
                    "title": "Test Book",
                }
            ],
            "numFound": 1,
        }
        mock_session.get.return_value = mock_response

        provider = OpenLibraryProvider(session=mock_session)
        result = provider.search(SearchOptions(query="test"))

        assert result.books[0].cover_url is None

    def test_search_constructs_source_url(self):
        """search() constructs source_url for each book."""
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "docs": [
                {
                    "key": "/works/OL999W",
                    "title": "Test Book",
                }
            ],
            "numFound": 1,
        }
        mock_session.get.return_value = mock_response

        provider = OpenLibraryProvider(session=mock_session)
        result = provider.search(SearchOptions(query="test"))

        assert result.books[0].source_url == f"{OPENLIBRARY_BASE_URL}/works/OL999W"

    def test_search_respects_limit_parameter(self):
        """search() respects limit parameter for result count."""
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"docs": [], "numFound": 0}
        mock_session.get.return_value = mock_response

        provider = OpenLibraryProvider(session=mock_session)
        provider.search(SearchOptions(query="test", limit=50))

        params = mock_session.get.call_args[1]["params"]
        assert params["limit"] == 50

    def test_search_returns_pagination_info(self):
        """search() returns correct pagination info in result."""
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "docs": [{"key": "/works/OL1W", "title": "Book"}],
            "numFound": 100,
        }
        mock_session.get.return_value = mock_response

        provider = OpenLibraryProvider(session=mock_session)
        result = provider.search(SearchOptions(query="test", limit=20, page=2))

        assert result.page == 2
        assert result.total_found == 100
        assert result.has_more is True  # 2*20=40 < 100

    def test_search_has_more_false_when_no_more_results(self):
        """search() sets has_more=False when on last page."""
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "docs": [{"key": "/works/OL1W", "title": "Book"}],
            "numFound": 15,
        }
        mock_session.get.return_value = mock_response

        provider = OpenLibraryProvider(session=mock_session)
        result = provider.search(SearchOptions(query="test", limit=20, page=1))

        assert result.has_more is False  # 1*20=20 >= 15

    def test_search_handles_timeout_gracefully(self):
        """search() returns empty result on timeout."""
        mock_session = MagicMock()
        mock_session.get.side_effect = requests.Timeout()

        provider = OpenLibraryProvider(session=mock_session)
        result = provider.search(SearchOptions(query="test"))

        assert result.books == []
        assert result.total_found == 0

    def test_search_handles_http_error_gracefully(self):
        """search() returns empty result on HTTP error."""
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.HTTPError()
        mock_session.get.return_value = mock_response

        provider = OpenLibraryProvider(session=mock_session)
        result = provider.search(SearchOptions(query="test"))

        assert result.books == []
        assert result.total_found == 0

    def test_search_handles_connection_error_gracefully(self):
        """search() returns empty result on connection error."""
        mock_session = MagicMock()
        mock_session.get.side_effect = requests.ConnectionError()

        provider = OpenLibraryProvider(session=mock_session)
        result = provider.search(SearchOptions(query="test"))

        assert result.books == []

    def test_search_handles_malformed_json_gracefully(self):
        """search() returns empty result on malformed JSON."""
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_session.get.return_value = mock_response

        provider = OpenLibraryProvider(session=mock_session)
        result = provider.search(SearchOptions(query="test"))

        assert result.books == []

    def test_search_skips_docs_without_title(self):
        """search() skips documents without a title."""
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "docs": [
                {"key": "/works/OL1W"},  # No title
                {"key": "/works/OL2W", "title": "Valid Book"},
            ],
            "numFound": 2,
        }
        mock_session.get.return_value = mock_response

        provider = OpenLibraryProvider(session=mock_session)
        result = provider.search(SearchOptions(query="test"))

        assert len(result.books) == 1
        assert result.books[0].title == "Valid Book"

    def test_search_skips_docs_without_key(self):
        """search() skips documents without a key."""
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "docs": [
                {"title": "No Key Book"},  # No key
                {"key": "/works/OL2W", "title": "Valid Book"},
            ],
            "numFound": 2,
        }
        mock_session.get.return_value = mock_response

        provider = OpenLibraryProvider(session=mock_session)
        result = provider.search(SearchOptions(query="test"))

        assert len(result.books) == 1
        assert result.books[0].title == "Valid Book"

    def test_search_handles_missing_optional_fields(self):
        """search() handles documents with missing optional fields."""
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "docs": [
                {
                    "key": "/works/OL1W",
                    "title": "Minimal Book",
                    # No author_name, cover_i, isbn, publisher, language, subject
                }
            ],
            "numFound": 1,
        }
        mock_session.get.return_value = mock_response

        provider = OpenLibraryProvider(session=mock_session)
        result = provider.search(SearchOptions(query="test"))

        book = result.books[0]
        assert book.title == "Minimal Book"
        assert book.authors == []
        assert book.isbn_10 is None
        assert book.isbn_13 is None
        assert book.cover_url is None
        assert book.publisher is None
        assert book.language is None
        assert book.genres == []


class TestOpenLibraryGetById:
    """Tests for OpenLibraryProvider.get_by_id() method."""

    def test_get_by_id_fetches_work(self):
        """get_by_id() fetches work by ID."""
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "title": "Test Work",
            "description": "A test description",
            "covers": [12345],
            "subjects": ["Fiction", "Test"],
        }
        mock_session.get.return_value = mock_response

        provider = OpenLibraryProvider(session=mock_session)
        book = provider.get_by_id("OL12345W")

        assert book is not None
        assert book.title == "Test Work"
        assert book.description == "A test description"
        assert book.cover_url == f"{COVERS_BASE_URL}/b/id/12345-L.jpg"
        assert "Fiction" in book.genres

    def test_get_by_id_normalizes_id_format(self):
        """get_by_id() normalizes various ID formats."""
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"title": "Test"}
        mock_session.get.return_value = mock_response

        provider = OpenLibraryProvider(session=mock_session)

        # Test without OL prefix
        provider.get_by_id("12345")
        assert "/works/OL12345W.json" in mock_session.get.call_args[0][0]

        # Test without W suffix
        mock_session.reset_mock()
        provider.get_by_id("OL12345")
        assert "/works/OL12345W.json" in mock_session.get.call_args[0][0]

    def test_get_by_id_handles_description_as_dict(self):
        """get_by_id() handles description when it's a dict with value key."""
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "title": "Test Work",
            "description": {"type": "/type/text", "value": "Dict description"},
        }
        mock_session.get.return_value = mock_response

        provider = OpenLibraryProvider(session=mock_session)
        book = provider.get_by_id("OL12345W")

        assert book.description == "Dict description"

    def test_get_by_id_returns_none_on_timeout(self):
        """get_by_id() returns None on timeout."""
        mock_session = MagicMock()
        mock_session.get.side_effect = requests.Timeout()

        provider = OpenLibraryProvider(session=mock_session)
        result = provider.get_by_id("OL12345W")

        assert result is None

    def test_get_by_id_returns_none_on_http_error(self):
        """get_by_id() returns None on HTTP error."""
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.HTTPError()
        mock_session.get.return_value = mock_response

        provider = OpenLibraryProvider(session=mock_session)
        result = provider.get_by_id("OL12345W")

        assert result is None

    def test_get_by_id_returns_none_when_no_title(self):
        """get_by_id() returns None when work has no title."""
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"description": "No title here"}
        mock_session.get.return_value = mock_response

        provider = OpenLibraryProvider(session=mock_session)
        result = provider.get_by_id("OL12345W")

        assert result is None

    def test_get_by_id_constructs_source_url(self):
        """get_by_id() constructs correct source_url."""
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"title": "Test"}
        mock_session.get.return_value = mock_response

        provider = OpenLibraryProvider(session=mock_session)
        book = provider.get_by_id("OL99999W")

        assert book.source_url == f"{OPENLIBRARY_BASE_URL}/works/OL99999W"

    def test_get_by_id_handles_missing_covers(self):
        """get_by_id() handles work without covers array."""
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"title": "No Cover Book"}
        mock_session.get.return_value = mock_response

        provider = OpenLibraryProvider(session=mock_session)
        book = provider.get_by_id("OL12345W")

        assert book.cover_url is None

    def test_get_by_id_limits_genres_to_5(self):
        """get_by_id() limits genres to first 5 subjects."""
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "title": "Many Subjects",
            "subjects": ["A", "B", "C", "D", "E", "F", "G"],
        }
        mock_session.get.return_value = mock_response

        provider = OpenLibraryProvider(session=mock_session)
        book = provider.get_by_id("OL12345W")

        assert len(book.genres) == 5
        assert book.genres == ["A", "B", "C", "D", "E"]

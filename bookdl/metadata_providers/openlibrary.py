"""Open Library metadata provider.

Searches the Open Library API (no API key required) for book metadata.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import requests

from . import BookMetadata, MetadataProvider, SearchOptions, SearchResult

if TYPE_CHECKING:
    from requests import Session

OPENLIBRARY_BASE_URL = "https://openlibrary.org"
COVERS_BASE_URL = "https://covers.openlibrary.org"

# ISBN lengths for classification
ISBN_10_LENGTH = 10
ISBN_13_LENGTH = 13

# Default timeout for API requests
DEFAULT_TIMEOUT = 15


class OpenLibraryProvider(MetadataProvider):
    """Open Library metadata provider using REST API.

    Open Library is a free, open-source library catalog with millions of books.
    No API key is required.
    """

    def __init__(self, session: Session | None = None) -> None:
        """Initialize provider with optional session for testing.

        Args:
            session: Optional requests session (for dependency injection in tests)
        """
        self._session = session or requests.Session()

    @property
    def name(self) -> str:
        """Internal identifier for this provider."""
        return "openlibrary"

    @property
    def display_name(self) -> str:
        """Human-readable name."""
        return "Open Library"

    def search(self, options: SearchOptions) -> SearchResult:
        """Search for books using Open Library's search API.

        Args:
            options: Search options (query, language, limit, page)

        Returns:
            SearchResult with matching books and pagination info
        """
        params: dict[str, Any] = {
            "q": options.query,
            "limit": options.limit,
            "page": options.page,
            "fields": "key,title,author_name,first_publish_year,cover_i,isbn,publisher,language,subject",
        }

        # Add language filter if specified
        if options.language:
            params["lang"] = options.language

        try:
            response = self._session.get(
                f"{OPENLIBRARY_BASE_URL}/search.json",
                params=params,
                timeout=DEFAULT_TIMEOUT,
            )
            response.raise_for_status()
            data = response.json()

            books: list[BookMetadata] = []
            for doc in data.get("docs", []):
                book = self._parse_search_doc(doc)
                if book:
                    books.append(book)

            total_found = data.get("numFound", 0)
            # Calculate if there are more results
            has_more = (options.page * options.limit) < total_found

            return SearchResult(
                books=books,
                page=options.page,
                total_found=total_found,
                has_more=has_more,
            )

        except requests.Timeout:
            return SearchResult(page=options.page)
        except requests.HTTPError:
            return SearchResult(page=options.page)
        except requests.RequestException:
            return SearchResult(page=options.page)
        except (TypeError, ValueError, KeyError):
            return SearchResult(page=options.page)

    def get_by_id(self, provider_id: str) -> BookMetadata | None:
        """Get book details by Open Library work ID.

        Args:
            provider_id: Open Library work ID (e.g., 'OL12345W')

        Returns:
            BookMetadata if found, None otherwise
        """
        # Normalize the ID format
        work_id = provider_id
        if not work_id.startswith("OL"):
            work_id = f"OL{work_id}"
        if not work_id.endswith("W"):
            work_id = f"{work_id}W"

        try:
            response = self._session.get(
                f"{OPENLIBRARY_BASE_URL}/works/{work_id}.json",
                timeout=DEFAULT_TIMEOUT,
            )
            response.raise_for_status()
            work = response.json()

            return self._parse_work(work, work_id)

        except requests.Timeout:
            return None
        except requests.HTTPError:
            return None
        except requests.RequestException:
            return None
        except (TypeError, ValueError, KeyError):
            return None

    def _parse_search_doc(self, doc: dict[str, Any]) -> BookMetadata | None:
        """Parse a search document into BookMetadata.

        Args:
            doc: Document from Open Library search response

        Returns:
            BookMetadata if valid, None otherwise
        """
        try:
            # Extract work ID from key
            key = doc.get("key", "")
            work_id = key.split("/")[-1] if key else None

            title = doc.get("title")
            if not work_id or not title:
                return None

            # Get authors (may be list or single value)
            authors = doc.get("author_name", [])
            if not isinstance(authors, list):
                authors = [authors] if authors else []

            # Get ISBNs - find first ISBN-10 and ISBN-13
            isbns = doc.get("isbn", [])
            isbn_10 = next((i for i in isbns if len(i) == ISBN_10_LENGTH), None)
            isbn_13 = next((i for i in isbns if len(i) == ISBN_13_LENGTH), None)

            # Get cover URL from cover_i field
            cover_id = doc.get("cover_i")
            cover_url = f"{COVERS_BASE_URL}/b/id/{cover_id}-L.jpg" if cover_id else None

            # Get publisher (first one)
            publishers = doc.get("publisher", [])
            publisher = publishers[0] if publishers else None

            # Get language (first one)
            languages = doc.get("language", [])
            language = languages[0] if languages else None

            # Get subjects as genres (first 5)
            subjects = doc.get("subject", [])
            genres = subjects[:5] if subjects else []

            return BookMetadata(
                provider="openlibrary",
                provider_id=work_id,
                title=title,
                authors=authors,
                isbn_10=isbn_10,
                isbn_13=isbn_13,
                cover_url=cover_url,
                publisher=publisher,
                publish_year=doc.get("first_publish_year"),
                language=language,
                genres=genres,
                source_url=f"{OPENLIBRARY_BASE_URL}/works/{work_id}",
            )

        except (TypeError, ValueError, AttributeError, KeyError):
            return None

    def _parse_work(self, work: dict[str, Any], work_id: str) -> BookMetadata | None:
        """Parse a work object into BookMetadata.

        Args:
            work: Work data from Open Library API
            work_id: The work ID

        Returns:
            BookMetadata if valid, None otherwise
        """
        try:
            title = work.get("title")
            if not title:
                return None

            # Get description (may be string or dict with value key)
            description = work.get("description")
            if isinstance(description, dict):
                description = description.get("value")

            # Get cover URL from covers array
            cover_url = None
            covers = work.get("covers", [])
            if covers:
                cover_id = covers[0]
                cover_url = f"{COVERS_BASE_URL}/b/id/{cover_id}-L.jpg"

            # Get subjects as genres (first 5)
            subjects = work.get("subjects", [])
            genres = subjects[:5] if subjects else []

            return BookMetadata(
                provider="openlibrary",
                provider_id=work_id,
                title=title,
                description=description,
                cover_url=cover_url,
                genres=genres,
                source_url=f"{OPENLIBRARY_BASE_URL}/works/{work_id}",
            )

        except (TypeError, ValueError, AttributeError, KeyError):
            return None

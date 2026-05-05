"""Download client plugin system.

Provides base classes and registry for external download clients
(torrent clients like qBittorrent, usenet clients like NZBGet).
"""

from __future__ import annotations

import random
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum
from functools import wraps
from typing import TYPE_CHECKING, TypeVar

import requests

if TYPE_CHECKING:
    from collections.abc import Callable

# Type variable for generic return type
T = TypeVar("T")

# Exceptions that should trigger a retry
RETRYABLE_EXCEPTIONS = (
    requests.exceptions.ConnectionError,
    requests.exceptions.Timeout,
)
_MIN_RETRYABLE_STATUS = 500
_RNG = random.SystemRandom()


def with_retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 10.0,
    jitter: float = 0.5,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Retry API calls with exponential backoff.

    Args:
        max_attempts: Maximum number of attempts (default 3)
        base_delay: Initial delay in seconds (default 1.0)
        max_delay: Maximum delay cap in seconds (default 10.0)
        jitter: Random jitter factor 0-1 to add to delay (default 0.5)

    Retries on:
        - Connection errors
        - Timeouts
        - HTTP 5xx server errors

    Does NOT retry on:
        - HTTP 4xx client errors (bad request, auth failures)
        - Other exceptions (programming errors)
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: object, **kwargs: object) -> T:
            last_exception: Exception | None = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except requests.exceptions.HTTPError as e:
                    # Only retry on server errors (5xx), not client errors (4xx)
                    if e.response is not None and e.response.status_code < _MIN_RETRYABLE_STATUS:
                        raise
                    last_exception = e
                except RETRYABLE_EXCEPTIONS as e:
                    last_exception = e

                if attempt < max_attempts:
                    # Calculate delay with exponential backoff
                    delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
                    # Add jitter to prevent thundering herd
                    delay += _RNG.uniform(0, delay * jitter)
                    time.sleep(delay)

            # All retries exhausted
            if last_exception is None:
                msg = "Retry failed without exception"
                raise RuntimeError(msg)
            raise last_exception

        return wrapper

    return decorator


class DownloadState(StrEnum):
    """Valid states for a download."""

    DOWNLOADING = "downloading"
    COMPLETE = "complete"
    ERROR = "error"
    SEEDING = "seeding"
    PAUSED = "paused"
    QUEUED = "queued"
    CHECKING = "checking"
    PROCESSING = "processing"
    UNKNOWN = "unknown"


@dataclass
class DownloadStatus:
    """Status of an external download."""

    progress: float  # 0-100
    state: DownloadState  # Current state
    message: str | None  # Status message
    complete: bool  # True when download finished
    file_path: str | None  # Path when complete
    download_speed: int | None = None  # Bytes per second
    eta: int | None = None  # Seconds remaining

    def __post_init__(self) -> None:
        """Validate and normalize progress."""
        # Clamp progress to valid range
        if self.progress < 0:
            self.progress = 0
        elif self.progress > 100:
            self.progress = 100

    @classmethod
    def error(cls, message: str) -> DownloadStatus:
        """Create an error status.

        Args:
            message: Error message

        Returns:
            DownloadStatus with ERROR state
        """
        return cls(
            progress=0,
            state=DownloadState.ERROR,
            message=message,
            complete=False,
            file_path=None,
        )


class DownloadClient(ABC):
    """Abstract base class for external download clients.

    Subclasses implement protocol-specific download management:
    - Torrent clients: qBittorrent, Transmission, Deluge
    - Usenet clients: NZBGet, SABnzbd

    Subclasses must define:
    - protocol: "torrent" or "usenet"
    - name: Unique client identifier
    """

    # Class attributes that subclasses must define
    protocol: str
    name: str

    @staticmethod
    @abstractmethod
    def is_configured() -> bool:
        """Check if this client is configured.

        Returns:
            True if required settings (URL, etc.) are present
        """
        ...

    @abstractmethod
    def test_connection(self) -> tuple[bool, str]:
        """Test connectivity to the client.

        Returns:
            Tuple of (success, message)
        """
        ...

    @abstractmethod
    def add_download(
        self,
        url: str,
        name: str,
        category: str | None = None,
    ) -> str:
        """Add a download to the client.

        Args:
            url: Download URL (magnet link, .torrent URL, or NZB URL)
            name: Display name for the download
            category: Category/label for organization

        Returns:
            Client-specific download ID

        Raises:
            Exception: If adding fails
        """
        ...

    @abstractmethod
    def get_status(self, download_id: str) -> DownloadStatus:
        """Get status of a download.

        Args:
            download_id: The ID returned by add_download()

        Returns:
            Current download status
        """
        ...

    @abstractmethod
    def remove(self, download_id: str, *, delete_files: bool = False) -> bool:
        """Remove a download from the client.

        Args:
            download_id: The ID returned by add_download()
            delete_files: Whether to also delete downloaded files

        Returns:
            True if removal succeeded
        """
        ...

    @abstractmethod
    def get_download_path(self, download_id: str) -> str | None:
        """Get the path where files were downloaded.

        Args:
            download_id: The ID returned by add_download()

        Returns:
            File or directory path, or None if not available
        """
        ...


# --- Client Registry ---


class ClientRegistry:
    """Registry for download clients.

    Manages client instances by protocol.
    """

    def __init__(self) -> None:
        """Initialize empty registry."""
        self._clients: dict[str, list[type[DownloadClient]]] = {}

    def register(self, protocol: str, client_cls: type[DownloadClient]) -> None:
        """Register a client class for a protocol.

        Multiple clients can be registered for the same protocol.

        Args:
            protocol: Protocol name ("torrent" or "usenet")
            client_cls: Download client class
        """
        if protocol not in self._clients:
            self._clients[protocol] = []
        self._clients[protocol].append(client_cls)

    def get_client(self, protocol: str) -> DownloadClient | None:
        """Get a configured client instance for a protocol.

        Args:
            protocol: Protocol name

        Returns:
            First configured client for the protocol, or None
        """
        if protocol not in self._clients:
            return None

        for client_cls in self._clients[protocol]:
            if client_cls.is_configured():
                return client_cls()

        return None

    def list_protocols(self) -> list[str]:
        """List protocols that have configured clients.

        Returns:
            List of protocol names with at least one configured client
        """
        result = []
        for protocol, client_classes in self._clients.items():
            for cls in client_classes:
                if cls.is_configured():
                    result.append(protocol)
                    break
        return result

    def list_all_clients(self) -> dict[str, list[type[DownloadClient]]]:
        """Get all registered client classes.

        Returns:
            Dict of protocol -> list of client classes
        """
        return dict(self._clients)

    def clear(self) -> None:
        """Remove all registered clients."""
        self._clients.clear()


# Global registry instance
_global_registry = ClientRegistry()


def get_registry() -> ClientRegistry:
    """Get the global client registry.

    Returns:
        Global ClientRegistry instance
    """
    return _global_registry


def register_client(protocol: str) -> Callable[[type[DownloadClient]], type[DownloadClient]]:
    """Decorator to register a download client.

    Args:
        protocol: Protocol this client handles ("torrent" or "usenet")

    Returns:
        Decorator function
    """
    def decorator(cls: type[DownloadClient]) -> type[DownloadClient]:
        _global_registry.register(protocol, cls)
        return cls

    return decorator


def get_client(protocol: str) -> DownloadClient | None:
    """Get a configured client for a protocol from global registry.

    Args:
        protocol: Protocol name

    Returns:
        Configured client instance, or None
    """
    return _global_registry.get_client(protocol)

"""Tests for the download client plugin system."""

import time
from unittest.mock import MagicMock, patch

import pytest
import requests

from bookdl.clients import (
    ClientRegistry,
    DownloadClient,
    DownloadState,
    DownloadStatus,
    get_client,
    get_registry,
    register_client,
    with_retry,
)


class MockConfiguredClient(DownloadClient):
    """Mock client that is configured."""

    protocol = "torrent"
    name = "mock_configured"

    @staticmethod
    def is_configured() -> bool:
        return True

    def test_connection(self) -> tuple[bool, str]:
        return True, "Connected"

    def add_download(self, url: str, name: str, category: str | None = None) -> str:
        return "mock_id_123"

    def get_status(self, download_id: str) -> DownloadStatus:
        return DownloadStatus(
            progress=50.0,
            state=DownloadState.DOWNLOADING,
            message="Downloading...",
            complete=False,
            file_path=None,
        )

    def remove(self, download_id: str, *, delete_files: bool = False) -> bool:
        return True

    def get_download_path(self, download_id: str) -> str | None:
        return "/downloads/test"


class MockUnconfiguredClient(DownloadClient):
    """Mock client that is not configured."""

    protocol = "torrent"
    name = "mock_unconfigured"

    @staticmethod
    def is_configured() -> bool:
        return False

    def test_connection(self) -> tuple[bool, str]:
        return False, "Not configured"

    def add_download(self, url: str, name: str, category: str | None = None) -> str:
        raise RuntimeError("Not configured")

    def get_status(self, download_id: str) -> DownloadStatus:
        return DownloadStatus.error("Not configured")

    def remove(self, download_id: str, *, delete_files: bool = False) -> bool:
        return False

    def get_download_path(self, download_id: str) -> str | None:
        return None


class TestDownloadState:
    """Tests for DownloadState enum."""

    def test_downloading_state(self):
        """DownloadState has DOWNLOADING value."""
        assert DownloadState.DOWNLOADING == "downloading"

    def test_complete_state(self):
        """DownloadState has COMPLETE value."""
        assert DownloadState.COMPLETE == "complete"

    def test_error_state(self):
        """DownloadState has ERROR value."""
        assert DownloadState.ERROR == "error"

    def test_seeding_state(self):
        """DownloadState has SEEDING value."""
        assert DownloadState.SEEDING == "seeding"

    def test_paused_state(self):
        """DownloadState has PAUSED value."""
        assert DownloadState.PAUSED == "paused"

    def test_queued_state(self):
        """DownloadState has QUEUED value."""
        assert DownloadState.QUEUED == "queued"


class TestDownloadStatus:
    """Tests for DownloadStatus dataclass."""

    def test_required_fields(self):
        """DownloadStatus holds required fields."""
        status = DownloadStatus(
            progress=50.0,
            state=DownloadState.DOWNLOADING,
            message="Test",
            complete=False,
            file_path=None,
        )
        assert status.progress == 50.0
        assert status.state == DownloadState.DOWNLOADING
        assert status.message == "Test"
        assert status.complete is False
        assert status.file_path is None

    def test_optional_fields(self):
        """DownloadStatus has optional speed and eta."""
        status = DownloadStatus(
            progress=75.0,
            state=DownloadState.DOWNLOADING,
            message=None,
            complete=False,
            file_path=None,
            download_speed=1024000,
            eta=300,
        )
        assert status.download_speed == 1024000
        assert status.eta == 300

    def test_progress_clamped_to_zero(self):
        """DownloadStatus clamps negative progress to 0."""
        status = DownloadStatus(
            progress=-10.0,
            state=DownloadState.QUEUED,
            message=None,
            complete=False,
            file_path=None,
        )
        assert status.progress == 0

    def test_progress_clamped_to_hundred(self):
        """DownloadStatus clamps progress over 100 to 100."""
        status = DownloadStatus(
            progress=150.0,
            state=DownloadState.COMPLETE,
            message=None,
            complete=True,
            file_path="/path",
        )
        assert status.progress == 100

    def test_error_factory_method(self):
        """DownloadStatus.error() creates error status."""
        status = DownloadStatus.error("Connection failed")

        assert status.progress == 0
        assert status.state == DownloadState.ERROR
        assert status.message == "Connection failed"
        assert status.complete is False
        assert status.file_path is None


class TestDownloadClient:
    """Tests for DownloadClient abstract class."""

    def test_requires_protocol(self):
        """Client must have protocol attribute."""
        client = MockConfiguredClient()
        assert client.protocol == "torrent"

    def test_requires_name(self):
        """Client must have name attribute."""
        client = MockConfiguredClient()
        assert client.name == "mock_configured"

    def test_is_configured_method(self):
        """Client implements is_configured static method."""
        assert MockConfiguredClient.is_configured() is True
        assert MockUnconfiguredClient.is_configured() is False

    def test_test_connection_method(self):
        """Client implements test_connection method."""
        client = MockConfiguredClient()
        success, message = client.test_connection()
        assert success is True
        assert message == "Connected"

    def test_add_download_method(self):
        """Client implements add_download method."""
        client = MockConfiguredClient()
        download_id = client.add_download("magnet:?xt=...", "Test Download")
        assert download_id == "mock_id_123"

    def test_get_status_method(self):
        """Client implements get_status method."""
        client = MockConfiguredClient()
        status = client.get_status("mock_id_123")
        assert isinstance(status, DownloadStatus)
        assert status.state == DownloadState.DOWNLOADING

    def test_remove_method(self):
        """Client implements remove method."""
        client = MockConfiguredClient()
        result = client.remove("mock_id_123")
        assert result is True

    def test_get_download_path_method(self):
        """Client implements get_download_path method."""
        client = MockConfiguredClient()
        path = client.get_download_path("mock_id_123")
        assert path == "/downloads/test"


class TestClientRegistry:
    """Tests for ClientRegistry class."""

    def test_register_adds_client(self):
        """register() adds client for protocol."""
        registry = ClientRegistry()
        registry.register("torrent", MockConfiguredClient)

        clients = registry.list_all_clients()
        assert "torrent" in clients
        assert MockConfiguredClient in clients["torrent"]

    def test_register_multiple_clients(self):
        """register() can add multiple clients for same protocol."""
        registry = ClientRegistry()
        registry.register("torrent", MockConfiguredClient)
        registry.register("torrent", MockUnconfiguredClient)

        clients = registry.list_all_clients()
        assert len(clients["torrent"]) == 2

    def test_get_client_returns_configured(self):
        """get_client() returns first configured client."""
        registry = ClientRegistry()
        registry.register("torrent", MockUnconfiguredClient)
        registry.register("torrent", MockConfiguredClient)

        client = registry.get_client("torrent")

        assert client is not None
        assert isinstance(client, MockConfiguredClient)

    def test_get_client_returns_none_for_unknown_protocol(self):
        """get_client() returns None for unknown protocol."""
        registry = ClientRegistry()

        client = registry.get_client("unknown")

        assert client is None

    def test_get_client_returns_none_when_none_configured(self):
        """get_client() returns None when no clients configured."""
        registry = ClientRegistry()
        registry.register("torrent", MockUnconfiguredClient)

        client = registry.get_client("torrent")

        assert client is None

    def test_list_protocols_returns_configured(self):
        """list_protocols() returns protocols with configured clients."""
        registry = ClientRegistry()
        registry.register("torrent", MockConfiguredClient)
        registry.register("usenet", MockUnconfiguredClient)

        protocols = registry.list_protocols()

        assert "torrent" in protocols
        assert "usenet" not in protocols

    def test_list_all_clients(self):
        """list_all_clients() returns all registered clients."""
        registry = ClientRegistry()
        registry.register("torrent", MockConfiguredClient)

        clients = registry.list_all_clients()

        assert isinstance(clients, dict)
        assert "torrent" in clients

    def test_clear_removes_all_clients(self):
        """clear() removes all registered clients."""
        registry = ClientRegistry()
        registry.register("torrent", MockConfiguredClient)
        registry.register("usenet", MockUnconfiguredClient)

        registry.clear()

        assert registry.list_all_clients() == {}


class TestGlobalRegistry:
    """Tests for global registry functions."""

    def setup_method(self):
        """Clear global registry before each test."""
        get_registry().clear()

    def test_get_registry_returns_singleton(self):
        """get_registry() returns same instance."""
        r1 = get_registry()
        r2 = get_registry()
        assert r1 is r2

    def test_register_client_decorator(self):
        """register_client decorator adds to global registry."""
        @register_client("test_protocol")
        class TestClient(MockConfiguredClient):
            protocol = "test_protocol"
            name = "test_client"

        assert "test_protocol" in get_registry().list_all_clients()

    def test_get_client_uses_global_registry(self):
        """get_client() uses global registry."""
        get_registry().register("torrent", MockConfiguredClient)

        client = get_client("torrent")

        assert client is not None
        assert isinstance(client, MockConfiguredClient)


class TestWithRetry:
    """Tests for with_retry decorator."""

    def test_returns_on_success(self):
        """with_retry returns result on success."""
        @with_retry(max_attempts=3)
        def successful_func():
            return "success"

        result = successful_func()
        assert result == "success"

    def test_retries_on_connection_error(self):
        """with_retry retries on ConnectionError."""
        call_count = 0

        @with_retry(max_attempts=3, base_delay=0.01)
        def failing_then_succeeding():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise requests.exceptions.ConnectionError()
            return "success"

        result = failing_then_succeeding()
        assert result == "success"
        assert call_count == 3

    def test_retries_on_timeout(self):
        """with_retry retries on Timeout."""
        call_count = 0

        @with_retry(max_attempts=3, base_delay=0.01)
        def timeout_then_succeeding():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise requests.exceptions.Timeout()
            return "success"

        result = timeout_then_succeeding()
        assert result == "success"
        assert call_count == 2

    def test_raises_after_max_attempts(self):
        """with_retry raises after exhausting attempts."""
        @with_retry(max_attempts=2, base_delay=0.01)
        def always_failing():
            raise requests.exceptions.ConnectionError()

        with pytest.raises(requests.exceptions.ConnectionError):
            always_failing()

    def test_does_not_retry_on_4xx_error(self):
        """with_retry does not retry on HTTP 4xx errors."""
        call_count = 0

        @with_retry(max_attempts=3, base_delay=0.01)
        def client_error():
            nonlocal call_count
            call_count += 1
            response = MagicMock()
            response.status_code = 401
            raise requests.exceptions.HTTPError(response=response)

        with pytest.raises(requests.exceptions.HTTPError):
            client_error()

        assert call_count == 1  # Should not retry

    def test_retries_on_5xx_error(self):
        """with_retry retries on HTTP 5xx errors."""
        call_count = 0

        @with_retry(max_attempts=3, base_delay=0.01)
        def server_error_then_success():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                response = MagicMock()
                response.status_code = 503
                raise requests.exceptions.HTTPError(response=response)
            return "success"

        result = server_error_then_success()
        assert result == "success"
        assert call_count == 2

    def test_exponential_backoff(self):
        """with_retry uses exponential backoff."""
        delays = []

        def mock_sleep(seconds):
            delays.append(seconds)

        call_count = 0

        @with_retry(max_attempts=4, base_delay=0.1, max_delay=10.0, jitter=0)
        def failing_func():
            nonlocal call_count
            call_count += 1
            if call_count < 4:
                raise requests.exceptions.ConnectionError()
            return "success"

        with patch('bookdl.clients.time.sleep', mock_sleep):
            failing_func()

        # Should have delays of approximately 0.1, 0.2, 0.4 (without jitter)
        assert len(delays) == 3
        assert delays[0] == pytest.approx(0.1, rel=0.1)
        assert delays[1] == pytest.approx(0.2, rel=0.1)
        assert delays[2] == pytest.approx(0.4, rel=0.1)

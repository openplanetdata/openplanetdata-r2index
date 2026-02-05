"""Tests for download functionality."""

from pathlib import Path
from unittest.mock import patch

import pytest
from pytest_httpx import HTTPXMock

from elaunira.r2index import (
    R2IndexClient,
    RemoteTuple,
)
from elaunira.r2index.client import _parse_object_id
from elaunira.r2index.storage import R2Config, R2TransferConfig


class TestParseObjectId:
    """Tests for _parse_object_id function."""

    def test_parse_simple_path(self):
        """Test parsing a simple object ID."""
        result = _parse_object_id("/releases/myapp/v1/myapp.zip")
        assert result.remote_path == "/releases/myapp"
        assert result.remote_version == "v1"
        assert result.remote_filename == "myapp.zip"

    def test_parse_deep_path(self):
        """Test parsing a deeply nested object ID."""
        result = _parse_object_id("/software/tools/releases/myapp/v2/tool.tar.gz")
        assert result.remote_path == "/software/tools/releases/myapp"
        assert result.remote_version == "v2"
        assert result.remote_filename == "tool.tar.gz"

    def test_parse_minimal_path(self):
        """Test parsing minimum required components."""
        result = _parse_object_id("/path/version/file.txt")
        assert result.remote_path == "/path"
        assert result.remote_version == "version"
        assert result.remote_filename == "file.txt"

    def test_parse_without_leading_slash(self):
        """Test parsing object ID without leading slash."""
        result = _parse_object_id("releases/myapp/v1/myapp.zip")
        assert result.remote_path == "/releases/myapp"
        assert result.remote_version == "v1"
        assert result.remote_filename == "myapp.zip"

    def test_parse_with_trailing_slash(self):
        """Test parsing object ID with trailing slash."""
        result = _parse_object_id("/releases/myapp/v1/myapp.zip/")
        assert result.remote_path == "/releases/myapp"
        assert result.remote_version == "v1"
        assert result.remote_filename == "myapp.zip"

    def test_parse_too_few_components(self):
        """Test error when object ID has too few components."""
        with pytest.raises(ValueError) as exc_info:
            _parse_object_id("/path/file.txt")
        assert "at least 3 components" in str(exc_info.value)

    def test_parse_single_component(self):
        """Test error with single component."""
        with pytest.raises(ValueError):
            _parse_object_id("/file.txt")

    def test_parse_empty_string(self):
        """Test error with empty string."""
        with pytest.raises(ValueError):
            _parse_object_id("")


class TestGetFileByTuple:
    """Tests for get_file_by_tuple method."""

    @pytest.fixture
    def client(self):
        """Create a test client."""
        return R2IndexClient(
            api_url="https://api.example.com",
            api_token="test-token",
        )

    def test_get_file_by_tuple(self, client: R2IndexClient, httpx_mock: HTTPXMock):
        """Test getting a file by remote tuple."""
        httpx_mock.add_response(
            url="https://api.example.com/files/by-tuple?remotePath=%2Freleases%2Fmyapp&remoteFilename=myapp.zip&remoteVersion=v1",
            json={
                "id": "file123",
                "category": "software",
                "entity": "myapp",
                "remote_path": "/releases/myapp",
                "remote_filename": "myapp.zip",
                "remote_version": "v1",
                "tags": [],
                "size": 1024,
                "md5": "abc",
                "sha1": "def",
                "sha256": "ghi",
                "sha512": "jkl",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
            },
        )

        remote_tuple = RemoteTuple(
            remote_path="/releases/myapp",
            remote_filename="myapp.zip",
            remote_version="v1",
        )
        record = client.get_file_by_tuple(remote_tuple)

        assert record.id == "file123"
        assert record.remote_path == "/releases/myapp"
        assert record.remote_filename == "myapp.zip"
        assert record.remote_version == "v1"


class TestDownloadAndRecord:
    """Tests for download_and_record method."""

    @pytest.fixture
    def client_with_r2(self):
        """Create a test client with R2 config."""
        r2_config = R2Config(
            access_key_id="test-key",
            secret_access_key="test-secret",
            endpoint_url="https://r2.example.com",
            bucket="test-bucket",
        )
        return R2IndexClient(
            api_url="https://api.example.com",
            api_token="test-token",
            r2_config=r2_config,
        )

    def test_download_and_record_with_defaults(
        self, client_with_r2: R2IndexClient, httpx_mock: HTTPXMock, tmp_path: Path
    ):
        """Test download_and_record with default IP and user agent."""
        # Mock checkip.amazonaws.com
        httpx_mock.add_response(
            url="https://checkip.amazonaws.com",
            text="203.0.113.1\n",
        )

        # Mock get_file_by_tuple
        httpx_mock.add_response(
            url="https://api.example.com/files/by-tuple?remotePath=%2Freleases%2Fmyapp&remoteFilename=myapp.zip&remoteVersion=v1",
            json={
                "id": "file123",
                "category": "software",
                "entity": "myapp",
                "remote_path": "/releases/myapp",
                "remote_filename": "myapp.zip",
                "remote_version": "v1",
                "tags": [],
                "size": 1024,
                "md5": "abc",
                "sha1": "def",
                "sha256": "ghi",
                "sha512": "jkl",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
            },
        )

        # Mock record_download
        httpx_mock.add_response(
            url="https://api.example.com/downloads",
            method="POST",
            status_code=201,
            json={
                "id": "download123",
                "fileId": "file123",
                "ipAddress": "203.0.113.1",
                "userAgent": "elaunira-r2index/0.1.0",
                "downloadedAt": "2024-01-01T00:00:00Z",
            },
        )

        destination = tmp_path / "myapp.zip"

        # Mock the R2 uploader download
        with patch.object(
            client_with_r2._get_uploader(),
            "download_file",
            return_value=destination,
        ) as mock_download:
            downloaded_path, file_record = client_with_r2.download_and_record(
                object_id="/releases/myapp/v1/myapp.zip",
                destination=str(destination),
            )

            mock_download.assert_called_once()
            assert downloaded_path == destination
            assert file_record.id == "file123"

    def test_download_and_record_with_explicit_ip_and_user_agent(
        self, client_with_r2: R2IndexClient, httpx_mock: HTTPXMock, tmp_path: Path
    ):
        """Test download_and_record with explicit IP and user agent."""
        # Mock get_file_by_tuple
        httpx_mock.add_response(
            url="https://api.example.com/files/by-tuple?remotePath=%2Freleases%2Fmyapp&remoteFilename=myapp.zip&remoteVersion=v1",
            json={
                "id": "file123",
                "category": "software",
                "entity": "myapp",
                "remote_path": "/releases/myapp",
                "remote_filename": "myapp.zip",
                "remote_version": "v1",
                "tags": [],
                "size": 1024,
                "md5": "abc",
                "sha1": "def",
                "sha256": "ghi",
                "sha512": "jkl",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
            },
        )

        # Mock record_download
        httpx_mock.add_response(
            url="https://api.example.com/downloads",
            method="POST",
            status_code=201,
            json={
                "id": "download123",
                "fileId": "file123",
                "ipAddress": "10.0.0.1",
                "userAgent": "custom-agent/1.0",
                "downloadedAt": "2024-01-01T00:00:00Z",
            },
        )

        destination = tmp_path / "myapp.zip"

        # Mock the R2 uploader download
        with patch.object(
            client_with_r2._get_uploader(),
            "download_file",
            return_value=destination,
        ):
            downloaded_path, file_record = client_with_r2.download_and_record(
                object_id="/releases/myapp/v1/myapp.zip",
                destination=str(destination),
                ip_address="10.0.0.1",
                user_agent="custom-agent/1.0",
            )

            assert downloaded_path == destination
            assert file_record.id == "file123"

    def test_download_and_record_invalid_object_id(
        self, client_with_r2: R2IndexClient, tmp_path: Path
    ):
        """Test download_and_record with invalid object ID."""
        destination = tmp_path / "file.zip"

        with pytest.raises(ValueError) as exc_info:
            client_with_r2.download_and_record(
                object_id="/invalid/path",
                destination=str(destination),
                ip_address="10.0.0.1",
            )

        assert "at least 3 components" in str(exc_info.value)


class TestR2TransferConfig:
    """Tests for R2TransferConfig."""

    def test_default_values(self):
        """Test default transfer config values."""
        config = R2TransferConfig()
        assert config.multipart_threshold == 100 * 1024 * 1024  # 100MB
        assert config.multipart_chunksize == 100 * 1024 * 1024  # 100MB
        assert config.max_concurrency >= 4  # At least 4
        assert config.use_threads is True

    def test_custom_values(self):
        """Test custom transfer config values."""
        config = R2TransferConfig(
            multipart_threshold=50 * 1024 * 1024,
            multipart_chunksize=25 * 1024 * 1024,
            max_concurrency=8,
            use_threads=False,
        )
        assert config.multipart_threshold == 50 * 1024 * 1024
        assert config.multipart_chunksize == 25 * 1024 * 1024
        assert config.max_concurrency == 8
        assert config.use_threads is False

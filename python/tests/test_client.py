"""Tests for the R2IndexClient."""

import pytest
from pytest_httpx import HTTPXMock

from elaunira.r2index import (
    AuthenticationError,
    FileCreateRequest,
    NotFoundError,
    R2IndexClient,
    ValidationError,
)


@pytest.fixture
def client():
    """Create a test client."""
    return R2IndexClient(
        index_api_url="https://api.example.com",
        index_api_token="test-token",
    )


def test_client_initialization(client: R2IndexClient):
    """Test client initialization."""
    assert client.api_url == "https://api.example.com"


def test_client_context_manager():
    """Test client as context manager."""
    with R2IndexClient(
        index_api_url="https://api.example.com",
        index_api_token="test-token",
    ) as client:
        assert client is not None


def test_list(client: R2IndexClient, httpx_mock: HTTPXMock):
    """Test listing files."""
    httpx_mock.add_response(
        url="https://api.example.com/files",
        json={
            "files": [
                {
                    "id": "file1",
                    "bucket": "test-bucket",
                    "category": "test",
                    "entity": "entity1",
                    "extension": "txt",
                    "media_type": "text/plain",
                    "remote_path": "/path",
                    "remote_filename": "file.txt",
                    "remote_version": "v1",
                    "tags": [],
                    "size": 100,
                    "checksum_md5": "abc",
                    "checksum_sha1": "def",
                    "checksum_sha256": "ghi",
                    "checksum_sha512": "jkl",
                    "created": 1704067200,
                    "updated": 1704067200,
                }
            ],
            "total": 1,
        },
    )

    response = client.list()
    assert len(response.files) == 1
    assert response.files[0].id == "file1"


def test_list_with_filters(client: R2IndexClient, httpx_mock: HTTPXMock):
    """Test listing files with filters."""
    httpx_mock.add_response(
        url="https://api.example.com/files?category=software&entity=myapp&tags=release%2Cstable",
        json={"files": [], "total": 0},
    )

    response = client.list(
        category="software",
        entity="myapp",
        tags=["release", "stable"],
    )
    assert response.total == 0


def test_create(client: R2IndexClient, httpx_mock: HTTPXMock):
    """Test creating a file record."""
    httpx_mock.add_response(
        url="https://api.example.com/files",
        method="POST",
        status_code=201,
        json={
            "id": "new-file",
            "bucket": "test-bucket",
            "category": "test",
            "entity": "entity1",
            "extension": "txt",
            "media_type": "text/plain",
            "remote_path": "/path",
            "remote_filename": "file.txt",
            "remote_version": "v1",
            "tags": [],
            "size": 100,
            "checksum_md5": "abc",
            "checksum_sha1": "def",
            "checksum_sha256": "ghi",
            "checksum_sha512": "jkl",
            "created": 1704067200,
            "updated": 1704067200,
        },
    )

    request = FileCreateRequest(
        bucket="test-bucket",
        category="test",
        entity="entity1",
        extension="txt",
        media_type="text/plain",
        remote_path="/path",
        remote_filename="file.txt",
        remote_version="v1",
        size=100,
        checksum_md5="abc",
        checksum_sha1="def",
        checksum_sha256="ghi",
        checksum_sha512="jkl",
    )
    record = client.create(request)
    assert record.id == "new-file"


def test_get(client: R2IndexClient, httpx_mock: HTTPXMock):
    """Test getting a file by ID."""
    httpx_mock.add_response(
        url="https://api.example.com/files/file123",
        json={
            "id": "file123",
            "bucket": "test-bucket",
            "category": "test",
            "entity": "entity1",
            "extension": "txt",
            "media_type": "text/plain",
            "remote_path": "/path",
            "remote_filename": "file.txt",
            "remote_version": "v1",
            "tags": [],
            "size": 100,
            "checksum_md5": "abc",
            "checksum_sha1": "def",
            "checksum_sha256": "ghi",
            "checksum_sha512": "jkl",
            "created": 1704067200,
            "updated": 1704067200,
        },
    )

    record = client.get("file123")
    assert record.id == "file123"


def test_get_not_found(client: R2IndexClient, httpx_mock: HTTPXMock):
    """Test 404 error handling."""
    httpx_mock.add_response(
        url="https://api.example.com/files/notfound",
        status_code=404,
        json={"error": "File not found"},
    )

    with pytest.raises(NotFoundError) as exc_info:
        client.get("notfound")

    assert exc_info.value.status_code == 404


def test_authentication_error(client: R2IndexClient, httpx_mock: HTTPXMock):
    """Test 401 error handling."""
    httpx_mock.add_response(
        url="https://api.example.com/files",
        status_code=401,
        json={"error": "Unauthorized"},
    )

    with pytest.raises(AuthenticationError) as exc_info:
        client.list()

    assert exc_info.value.status_code == 401


def test_validation_error(client: R2IndexClient, httpx_mock: HTTPXMock):
    """Test 400 error handling."""
    httpx_mock.add_response(
        url="https://api.example.com/files",
        method="POST",
        status_code=400,
        json={"error": "Invalid request"},
    )

    request = FileCreateRequest(
        bucket="test-bucket",
        category="test",
        entity="entity1",
        extension="txt",
        media_type="text/plain",
        remote_path="/path",
        remote_filename="file.txt",
        remote_version="v1",
        size=100,
        checksum_md5="abc",
        checksum_sha1="def",
        checksum_sha256="ghi",
        checksum_sha512="jkl",
    )

    with pytest.raises(ValidationError) as exc_info:
        client.create(request)

    assert exc_info.value.status_code == 400


def test_health_check(client: R2IndexClient, httpx_mock: HTTPXMock):
    """Test health check endpoint."""
    httpx_mock.add_response(
        url="https://api.example.com/health",
        json={
            "status": "ok",
        },
    )

    health = client.health()
    assert health.status == "ok"

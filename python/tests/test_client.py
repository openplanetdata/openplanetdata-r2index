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
        api_url="https://api.example.com",
        api_token="test-token",
    )


def test_client_initialization(client: R2IndexClient):
    """Test client initialization."""
    assert client.api_url == "https://api.example.com"


def test_client_context_manager():
    """Test client as context manager."""
    with R2IndexClient(
        api_url="https://api.example.com",
        api_token="test-token",
    ) as client:
        assert client is not None


def test_list_files(client: R2IndexClient, httpx_mock: HTTPXMock):
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
                    "remote_path": "/path",
                    "remote_filename": "file.txt",
                    "remote_version": "v1",
                    "tags": [],
                    "size": 100,
                    "md5": "abc",
                    "sha1": "def",
                    "sha256": "ghi",
                    "sha512": "jkl",
                    "created_at": "2024-01-01T00:00:00Z",
                    "updated_at": "2024-01-01T00:00:00Z",
                }
            ],
            "total": 1,
            "page": 1,
            "pageSize": 20,
        },
    )

    response = client.list_files()
    assert len(response.files) == 1
    assert response.files[0].id == "file1"


def test_list_files_with_filters(client: R2IndexClient, httpx_mock: HTTPXMock):
    """Test listing files with filters."""
    httpx_mock.add_response(
        url="https://api.example.com/files?category=software&entity=myapp&tags=release%2Cstable",
        json={"files": [], "total": 0, "page": 1, "pageSize": 20},
    )

    response = client.list_files(
        category="software",
        entity="myapp",
        tags=["release", "stable"],
    )
    assert response.total == 0


def test_create_file(client: R2IndexClient, httpx_mock: HTTPXMock):
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
            "remote_path": "/path",
            "remote_filename": "file.txt",
            "remote_version": "v1",
            "tags": [],
            "size": 100,
            "md5": "abc",
            "sha1": "def",
            "sha256": "ghi",
            "sha512": "jkl",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        },
    )

    request = FileCreateRequest(
        bucket="test-bucket",
        category="test",
        entity="entity1",
        remote_path="/path",
        remote_filename="file.txt",
        remote_version="v1",
        size=100,
        md5="abc",
        sha1="def",
        sha256="ghi",
        sha512="jkl",
    )
    record = client.create_file(request)
    assert record.id == "new-file"


def test_get_file(client: R2IndexClient, httpx_mock: HTTPXMock):
    """Test getting a file by ID."""
    httpx_mock.add_response(
        url="https://api.example.com/files/file123",
        json={
            "id": "file123",
            "bucket": "test-bucket",
            "category": "test",
            "entity": "entity1",
            "remote_path": "/path",
            "remote_filename": "file.txt",
            "remote_version": "v1",
            "tags": [],
            "size": 100,
            "md5": "abc",
            "sha1": "def",
            "sha256": "ghi",
            "sha512": "jkl",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        },
    )

    record = client.get_file("file123")
    assert record.id == "file123"


def test_get_file_not_found(client: R2IndexClient, httpx_mock: HTTPXMock):
    """Test 404 error handling."""
    httpx_mock.add_response(
        url="https://api.example.com/files/notfound",
        status_code=404,
        json={"error": "File not found"},
    )

    with pytest.raises(NotFoundError) as exc_info:
        client.get_file("notfound")

    assert exc_info.value.status_code == 404


def test_authentication_error(client: R2IndexClient, httpx_mock: HTTPXMock):
    """Test 401 error handling."""
    httpx_mock.add_response(
        url="https://api.example.com/files",
        status_code=401,
        json={"error": "Unauthorized"},
    )

    with pytest.raises(AuthenticationError) as exc_info:
        client.list_files()

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
        remote_path="/path",
        remote_filename="file.txt",
        remote_version="v1",
        size=100,
        md5="abc",
        sha1="def",
        sha256="ghi",
        sha512="jkl",
    )

    with pytest.raises(ValidationError) as exc_info:
        client.create_file(request)

    assert exc_info.value.status_code == 400


def test_health_check(client: R2IndexClient, httpx_mock: HTTPXMock):
    """Test health check endpoint."""
    httpx_mock.add_response(
        url="https://api.example.com/health",
        json={
            "status": "ok",
            "timestamp": "2024-01-01T00:00:00Z",
        },
    )

    health = client.health()
    assert health.status == "ok"

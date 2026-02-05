"""Tests for the AsyncR2IndexClient."""

import pytest
from pytest_httpx import HTTPXMock

from elaunira.r2index import AsyncR2IndexClient, FileCreateRequest


@pytest.fixture
def async_client():
    """Create a test async client."""
    return AsyncR2IndexClient(
        api_url="https://api.example.com",
        api_token="test-token",
    )


@pytest.mark.asyncio
async def test_async_client_context_manager():
    """Test async client as context manager."""
    async with AsyncR2IndexClient(
        api_url="https://api.example.com",
        api_token="test-token",
    ) as client:
        assert client is not None


@pytest.mark.asyncio
async def test_async_list_files(async_client: AsyncR2IndexClient, httpx_mock: HTTPXMock):
    """Test async listing files."""
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

    response = await async_client.list_files()
    assert len(response.files) == 1
    await async_client.close()


@pytest.mark.asyncio
async def test_async_create_file(async_client: AsyncR2IndexClient, httpx_mock: HTTPXMock):
    """Test async creating a file record."""
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
    record = await async_client.create_file(request)
    assert record.id == "new-file"
    await async_client.close()


@pytest.mark.asyncio
async def test_async_health_check(async_client: AsyncR2IndexClient, httpx_mock: HTTPXMock):
    """Test async health check endpoint."""
    httpx_mock.add_response(
        url="https://api.example.com/health",
        json={
            "status": "ok",
            "timestamp": "2024-01-01T00:00:00Z",
        },
    )

    health = await async_client.health()
    assert health.status == "ok"
    await async_client.close()

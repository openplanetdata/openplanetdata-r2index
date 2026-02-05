"""Tests for the AsyncR2IndexClient."""

import pytest
from pytest_httpx import HTTPXMock

from elaunira.r2index import AsyncR2IndexClient, FileCreateRequest


@pytest.fixture
def async_client():
    """Create a test async client."""
    return AsyncR2IndexClient(
        index_api_url="https://api.example.com",
        index_api_token="test-token",
    )


@pytest.mark.asyncio
async def test_async_client_context_manager():
    """Test async client as context manager."""
    async with AsyncR2IndexClient(
        index_api_url="https://api.example.com",
        index_api_token="test-token",
    ) as client:
        assert client is not None


@pytest.mark.asyncio
async def test_async_list(async_client: AsyncR2IndexClient, httpx_mock: HTTPXMock):
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

    response = await async_client.list()
    assert len(response.files) == 1
    await async_client.close()


@pytest.mark.asyncio
async def test_async_create(async_client: AsyncR2IndexClient, httpx_mock: HTTPXMock):
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
    record = await async_client.create(request)
    assert record.id == "new-file"
    await async_client.close()


@pytest.mark.asyncio
async def test_async_health_check(async_client: AsyncR2IndexClient, httpx_mock: HTTPXMock):
    """Test async health check endpoint."""
    httpx_mock.add_response(
        url="https://api.example.com/health",
        json={
            "status": "ok",
        },
    )

    health = await async_client.health()
    assert health.status == "ok"
    await async_client.close()

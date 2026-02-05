"""Tests for Pydantic models."""

from datetime import datetime

from elaunira.r2index import (
    DownloadRecordRequest,
    FileCreateRequest,
    FileListResponse,
    FileRecord,
    FileUpdateRequest,
    RemoteTuple,
)


def test_file_create_request():
    """Test FileCreateRequest model."""
    request = FileCreateRequest(
        bucket="my-bucket",
        category="software",
        entity="myapp",
        remote_path="/releases",
        remote_filename="myapp-1.0.0.zip",
        remote_version="1.0.0",
        name="My App Release",
        tags=["release", "stable"],
        size=1024,
        md5="abc123",
        sha1="def456",
        sha256="ghi789",
        sha512="jkl012",
    )

    assert request.bucket == "my-bucket"
    assert request.category == "software"
    assert request.tags == ["release", "stable"]
    data = request.model_dump()
    assert data["remote_path"] == "/releases"


def test_file_update_request_partial():
    """Test FileUpdateRequest with partial data."""
    request = FileUpdateRequest(
        name="Updated Name",
        tags=["updated"],
    )

    data = request.model_dump(exclude_none=True)
    assert "name" in data
    assert "tags" in data
    assert "category" not in data


def test_file_record_from_api():
    """Test FileRecord validation from API response."""
    api_response = {
        "id": "file123",
        "bucket": "my-bucket",
        "category": "software",
        "entity": "myapp",
        "remote_path": "/releases",
        "remote_filename": "myapp-1.0.0.zip",
        "remote_version": "1.0.0",
        "name": "My App",
        "tags": ["release"],
        "size": 1024,
        "md5": "abc",
        "sha1": "def",
        "sha256": "ghi",
        "sha512": "jkl",
        "created_at": "2024-01-15T10:30:00Z",
        "updated_at": "2024-01-15T10:30:00Z",
    }

    record = FileRecord.model_validate(api_response)
    assert record.id == "file123"
    assert record.bucket == "my-bucket"
    assert isinstance(record.created_at, datetime)


def test_file_list_response_with_alias():
    """Test FileListResponse with camelCase alias."""
    api_response = {
        "files": [],
        "total": 0,
        "page": 1,
        "pageSize": 20,
    }

    response = FileListResponse.model_validate(api_response)
    assert response.page_size == 20


def test_remote_tuple():
    """Test RemoteTuple model."""
    remote = RemoteTuple(
        bucket="my-bucket",
        remote_path="/data",
        remote_filename="file.txt",
        remote_version="v1",
    )

    assert remote.bucket == "my-bucket"
    assert remote.remote_path == "/data"


def test_download_record_request_alias():
    """Test DownloadRecordRequest with aliases."""
    request = DownloadRecordRequest(
        file_id="file123",
        ip_address="192.168.1.1",
        user_agent="Mozilla/5.0",
    )

    data = request.model_dump(by_alias=True)
    assert data["fileId"] == "file123"
    assert data["ipAddress"] == "192.168.1.1"

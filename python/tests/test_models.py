"""Tests for Pydantic models."""

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
        extension="zip",
        media_type="application/zip",
        remote_path="/releases",
        remote_filename="myapp-1.0.0.zip",
        remote_version="1.0.0",
        name="My App Release",
        tags=["release", "stable"],
        size=1024,
        checksum_md5="abc123",
        checksum_sha1="def456",
        checksum_sha256="ghi789",
        checksum_sha512="jkl012",
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
        "extension": "zip",
        "media_type": "application/zip",
        "remote_path": "/releases",
        "remote_filename": "myapp-1.0.0.zip",
        "remote_version": "1.0.0",
        "name": "My App",
        "tags": ["release"],
        "size": 1024,
        "checksum_md5": "abc",
        "checksum_sha1": "def",
        "checksum_sha256": "ghi",
        "checksum_sha512": "jkl",
        "created": 1705315800,
        "updated": 1705315800,
    }

    record = FileRecord.model_validate(api_response)
    assert record.id == "file123"
    assert record.bucket == "my-bucket"
    assert record.created == 1705315800


def test_file_list_response():
    """Test FileListResponse."""
    api_response = {
        "files": [],
        "total": 0,
    }

    response = FileListResponse.model_validate(api_response)
    assert response.total == 0


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


def test_download_record_request():
    """Test DownloadRecordRequest with remote tuple fields."""
    request = DownloadRecordRequest(
        bucket="my-bucket",
        remote_path="/data",
        remote_filename="file.txt",
        remote_version="v1",
        ip_address="192.168.1.1",
        user_agent="Mozilla/5.0",
    )

    data = request.model_dump()
    assert data["bucket"] == "my-bucket"
    assert data["ip_address"] == "192.168.1.1"

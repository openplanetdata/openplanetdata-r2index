"""Pydantic models for r2index API requests and responses."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class RemoteTuple(BaseModel):
    """Remote file identifier tuple."""

    bucket: str
    remote_path: str
    remote_filename: str
    remote_version: str


class FileCreateRequest(BaseModel):
    """Request payload for creating/upserting a file record."""

    bucket: str
    category: str
    entity: str
    remote_path: str
    remote_filename: str
    remote_version: str
    name: str | None = None
    tags: list[str] | None = None
    extra: dict[str, Any] | None = None
    size: int
    md5: str
    sha1: str
    sha256: str
    sha512: str


class FileUpdateRequest(BaseModel):
    """Request payload for updating a file record."""

    bucket: str | None = None
    category: str | None = None
    entity: str | None = None
    remote_path: str | None = None
    remote_filename: str | None = None
    remote_version: str | None = None
    name: str | None = None
    tags: list[str] | None = None
    extra: dict[str, Any] | None = None
    size: int | None = None
    md5: str | None = None
    sha1: str | None = None
    sha256: str | None = None
    sha512: str | None = None


class FileRecord(BaseModel):
    """File record as returned by the API."""

    id: str
    bucket: str
    category: str
    entity: str
    remote_path: str
    remote_filename: str
    remote_version: str
    name: str | None = None
    tags: list[str] = Field(default_factory=list)
    extra: dict[str, Any] | None = None
    size: int
    md5: str
    sha1: str
    sha256: str
    sha512: str
    created_at: datetime
    updated_at: datetime


class FileListResponse(BaseModel):
    """Response for listing files."""

    files: list[FileRecord]
    total: int
    page: int
    page_size: int = Field(alias="pageSize")

    model_config = {"populate_by_name": True}


class IndexEntry(BaseModel):
    """Single entry in the index response."""

    id: str
    bucket: str
    category: str
    entity: str
    remote_path: str
    remote_filename: str
    remote_version: str
    name: str | None = None
    tags: list[str] = Field(default_factory=list)
    size: int
    md5: str
    sha1: str
    sha256: str
    sha512: str


class DownloadRecordRequest(BaseModel):
    """Request payload for recording a download."""

    file_id: str = Field(alias="fileId")
    ip_address: str = Field(alias="ipAddress")
    user_agent: str | None = Field(default=None, alias="userAgent")

    model_config = {"populate_by_name": True}


class DownloadRecord(BaseModel):
    """Download record as returned by the API."""

    id: str
    file_id: str = Field(alias="fileId")
    ip_address: str = Field(alias="ipAddress")
    user_agent: str | None = Field(default=None, alias="userAgent")
    downloaded_at: datetime = Field(alias="downloadedAt")

    model_config = {"populate_by_name": True}


class TimeseriesDataPoint(BaseModel):
    """Single data point in timeseries analytics."""

    timestamp: datetime
    count: int


class TimeseriesResponse(BaseModel):
    """Response for timeseries analytics."""

    data: list[TimeseriesDataPoint]
    start: datetime
    end: datetime
    granularity: str


class SummaryResponse(BaseModel):
    """Response for summary analytics."""

    total_downloads: int = Field(alias="totalDownloads")
    unique_ips: int = Field(alias="uniqueIps")
    unique_files: int = Field(alias="uniqueFiles")
    start: datetime
    end: datetime

    model_config = {"populate_by_name": True}


class DownloadByIpEntry(BaseModel):
    """Single download entry for by-IP analytics."""

    file_id: str = Field(alias="fileId")
    downloaded_at: datetime = Field(alias="downloadedAt")
    user_agent: str | None = Field(default=None, alias="userAgent")

    model_config = {"populate_by_name": True}


class DownloadsByIpResponse(BaseModel):
    """Response for downloads by IP analytics."""

    ip_address: str = Field(alias="ipAddress")
    downloads: list[DownloadByIpEntry]
    total: int

    model_config = {"populate_by_name": True}


class UserAgentEntry(BaseModel):
    """Single user agent entry in analytics."""

    user_agent: str = Field(alias="userAgent")
    count: int

    model_config = {"populate_by_name": True}


class UserAgentsResponse(BaseModel):
    """Response for user agents analytics."""

    user_agents: list[UserAgentEntry] = Field(alias="userAgents")
    start: datetime
    end: datetime

    model_config = {"populate_by_name": True}


class CleanupResponse(BaseModel):
    """Response for cleanup operations."""

    deleted_count: int = Field(alias="deletedCount")

    model_config = {"populate_by_name": True}


class HealthResponse(BaseModel):
    """Response for health check."""

    status: str
    timestamp: datetime

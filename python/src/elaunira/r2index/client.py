"""Synchronous R2Index API client."""

from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

from .checksums import compute_checksums
from .exceptions import (
    AuthenticationError,
    ConflictError,
    NotFoundError,
    R2IndexError,
    ValidationError,
)
from .models import (
    CleanupResponse,
    DownloadRecord,
    DownloadRecordRequest,
    DownloadsByIpResponse,
    FileCreateRequest,
    FileListResponse,
    FileRecord,
    FileUpdateRequest,
    HealthResponse,
    IndexEntry,
    RemoteTuple,
    SummaryResponse,
    TimeseriesResponse,
    UserAgentsResponse,
)
from . import __version__
from .storage import R2Config, R2Storage, R2TransferConfig

CHECKIP_URL = "https://checkip.amazonaws.com"
DEFAULT_USER_AGENT = f"elaunira-r2index/{__version__}"


def _parse_object_id(object_id: str, bucket: str) -> RemoteTuple:
    """
    Parse an object_id into remote_path, remote_version, and remote_filename.

    Format: /path/to/object/version/filename.ext
    - remote_filename: last component (filename.ext)
    - remote_version: second-to-last component (version)
    - remote_path: everything before that (/path/to/object)

    Args:
        object_id: Full object path like /releases/myapp/v1/myapp.zip
        bucket: The S3/R2 bucket name.

    Returns:
        RemoteTuple with parsed components including bucket.

    Raises:
        ValueError: If object_id doesn't have enough components.
    """
    parts = object_id.strip("/").split("/")
    if len(parts) < 3:
        raise ValueError(
            f"object_id must have at least 3 components (path/version/filename), got: {object_id}"
        )

    remote_filename = parts[-1]
    remote_version = parts[-2]
    remote_path = "/" + "/".join(parts[:-2])

    return RemoteTuple(
        bucket=bucket,
        remote_path=remote_path,
        remote_filename=remote_filename,
        remote_version=remote_version,
    )


class R2IndexClient:
    """Synchronous client for the r2index API."""

    def __init__(
        self,
        index_api_url: str,
        index_api_token: str,
        r2_access_key_id: str | None = None,
        r2_secret_access_key: str | None = None,
        r2_endpoint_url: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        """
        Initialize the R2Index client.

        Args:
            index_api_url: Base URL of the r2index API.
            index_api_token: Bearer token for authentication.
            r2_access_key_id: R2 access key ID for storage operations.
            r2_secret_access_key: R2 secret access key for storage operations.
            r2_endpoint_url: R2 endpoint URL for storage operations.
            timeout: Request timeout in seconds.
        """
        self.api_url = index_api_url.rstrip("/")
        self._token = index_api_token
        self._timeout = timeout
        self._storage: R2Storage | None = None

        # Build R2 config if credentials provided
        if r2_access_key_id and r2_secret_access_key and r2_endpoint_url:
            self._r2_config: R2Config | None = R2Config(
                access_key_id=r2_access_key_id,
                secret_access_key=r2_secret_access_key,
                endpoint_url=r2_endpoint_url,
            )
        else:
            self._r2_config = None

        self._client = httpx.Client(
            base_url=self.api_url,
            headers={"Authorization": f"Bearer {index_api_token}"},
            timeout=timeout,
        )

    def __enter__(self) -> "R2IndexClient":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()

    def _get_storage(self) -> R2Storage:
        """Get or create the R2 uploader."""
        if self._r2_config is None:
            raise R2IndexError("R2 configuration required for upload operations")
        if self._storage is None:
            self._storage = R2Storage(self._r2_config)
        return self._storage

    def _handle_response(self, response: httpx.Response) -> Any:
        """Handle API response and raise appropriate exceptions."""
        if response.status_code == 200 or response.status_code == 201:
            return response.json()

        status = response.status_code
        try:
            error_data = response.json()
            message = error_data.get("error", response.text)
        except Exception:
            message = response.text

        if status == 401 or status == 403:
            raise AuthenticationError(message, status)
        elif status == 404:
            raise NotFoundError(message, status)
        elif status == 400:
            raise ValidationError(message, status)
        elif status == 409:
            raise ConflictError(message, status)
        else:
            raise R2IndexError(message, status)

    # File Operations

    def list_files(
        self,
        bucket: str | None = None,
        category: str | None = None,
        entity: str | None = None,
        tags: list[str] | None = None,
        page: int | None = None,
        page_size: int | None = None,
    ) -> FileListResponse:
        """
        List files with optional filters.

        Args:
            bucket: Filter by bucket.
            category: Filter by category.
            entity: Filter by entity.
            tags: Filter by tags.
            page: Page number (1-indexed).
            page_size: Number of items per page.

        Returns:
            FileListResponse with files and pagination info.
        """
        params: dict[str, Any] = {}
        if bucket:
            params["bucket"] = bucket
        if category:
            params["category"] = category
        if entity:
            params["entity"] = entity
        if tags:
            params["tags"] = ",".join(tags)
        if page:
            params["page"] = page
        if page_size:
            params["pageSize"] = page_size

        response = self._client.get("/files", params=params)
        data = self._handle_response(response)
        return FileListResponse.model_validate(data)

    def create_file(self, data: FileCreateRequest) -> FileRecord:
        """
        Create or upsert a file record.

        Args:
            data: File creation request data.

        Returns:
            The created or updated FileRecord.
        """
        response = self._client.post("/files", json=data.model_dump(by_alias=True))
        result = self._handle_response(response)
        return FileRecord.model_validate(result)

    def get_file(self, file_id: str) -> FileRecord:
        """
        Get a file by ID.

        Args:
            file_id: The file ID.

        Returns:
            The FileRecord.

        Raises:
            NotFoundError: If the file is not found.
        """
        response = self._client.get(f"/files/{file_id}")
        data = self._handle_response(response)
        return FileRecord.model_validate(data)

    def update_file(self, file_id: str, data: FileUpdateRequest) -> FileRecord:
        """
        Update a file record.

        Args:
            file_id: The file ID to update.
            data: Fields to update.

        Returns:
            The updated FileRecord.
        """
        response = self._client.put(
            f"/files/{file_id}",
            json=data.model_dump(exclude_none=True, by_alias=True),
        )
        result = self._handle_response(response)
        return FileRecord.model_validate(result)

    def delete_file(self, file_id: str) -> None:
        """
        Delete a file by ID.

        Args:
            file_id: The file ID to delete.

        Raises:
            NotFoundError: If the file is not found.
        """
        response = self._client.delete(f"/files/{file_id}")
        self._handle_response(response)

    def delete_file_by_tuple(self, remote_tuple: RemoteTuple) -> None:
        """
        Delete a file by remote tuple.

        Args:
            remote_tuple: The bucket, remote path, filename, and version.

        Raises:
            NotFoundError: If the file is not found.
        """
        params = {
            "bucket": remote_tuple.bucket,
            "remotePath": remote_tuple.remote_path,
            "remoteFilename": remote_tuple.remote_filename,
            "remoteVersion": remote_tuple.remote_version,
        }
        response = self._client.delete("/files", params=params)
        self._handle_response(response)

    def get_file_by_tuple(self, remote_tuple: RemoteTuple) -> FileRecord:
        """
        Get a file by remote tuple.

        Args:
            remote_tuple: The bucket, remote path, filename, and version.

        Returns:
            The FileRecord.

        Raises:
            NotFoundError: If the file is not found.
        """
        params = {
            "bucket": remote_tuple.bucket,
            "remotePath": remote_tuple.remote_path,
            "remoteFilename": remote_tuple.remote_filename,
            "remoteVersion": remote_tuple.remote_version,
        }
        response = self._client.get("/files/by-tuple", params=params)
        data = self._handle_response(response)
        return FileRecord.model_validate(data)

    def get_index(
        self,
        bucket: str | None = None,
        category: str | None = None,
        entity: str | None = None,
        tags: list[str] | None = None,
    ) -> list[IndexEntry]:
        """
        Get file index (lightweight listing).

        Args:
            bucket: Filter by bucket.
            category: Filter by category.
            entity: Filter by entity.
            tags: Filter by tags.

        Returns:
            List of IndexEntry objects.
        """
        params: dict[str, Any] = {}
        if bucket:
            params["bucket"] = bucket
        if category:
            params["category"] = category
        if entity:
            params["entity"] = entity
        if tags:
            params["tags"] = ",".join(tags)

        response = self._client.get("/files/index", params=params)
        data = self._handle_response(response)
        return [IndexEntry.model_validate(item) for item in data]

    # Download Tracking

    def record_download(self, data: DownloadRecordRequest) -> DownloadRecord:
        """
        Record a file download.

        Args:
            data: Download record data.

        Returns:
            The created DownloadRecord.
        """
        response = self._client.post("/downloads", json=data.model_dump(by_alias=True))
        result = self._handle_response(response)
        return DownloadRecord.model_validate(result)

    # Analytics

    def get_timeseries(
        self,
        start: datetime,
        end: datetime,
        granularity: str = "day",
        file_id: str | None = None,
        category: str | None = None,
        entity: str | None = None,
    ) -> TimeseriesResponse:
        """
        Get download timeseries analytics.

        Args:
            start: Start datetime.
            end: End datetime.
            granularity: Time granularity (hour, day, week, month).
            file_id: Optional file ID filter.
            category: Optional category filter.
            entity: Optional entity filter.

        Returns:
            TimeseriesResponse with data points.
        """
        params: dict[str, Any] = {
            "start": start.isoformat(),
            "end": end.isoformat(),
            "granularity": granularity,
        }
        if file_id:
            params["fileId"] = file_id
        if category:
            params["category"] = category
        if entity:
            params["entity"] = entity

        response = self._client.get("/analytics/timeseries", params=params)
        data = self._handle_response(response)
        return TimeseriesResponse.model_validate(data)

    def get_summary(
        self,
        start: datetime,
        end: datetime,
        file_id: str | None = None,
        category: str | None = None,
        entity: str | None = None,
    ) -> SummaryResponse:
        """
        Get download summary analytics.

        Args:
            start: Start datetime.
            end: End datetime.
            file_id: Optional file ID filter.
            category: Optional category filter.
            entity: Optional entity filter.

        Returns:
            SummaryResponse with aggregated statistics.
        """
        params: dict[str, Any] = {
            "start": start.isoformat(),
            "end": end.isoformat(),
        }
        if file_id:
            params["fileId"] = file_id
        if category:
            params["category"] = category
        if entity:
            params["entity"] = entity

        response = self._client.get("/analytics/summary", params=params)
        data = self._handle_response(response)
        return SummaryResponse.model_validate(data)

    def get_downloads_by_ip(
        self,
        ip_address: str,
        start: datetime,
        end: datetime,
    ) -> DownloadsByIpResponse:
        """
        Get downloads by IP address.

        Args:
            ip_address: The IP address to query.
            start: Start datetime.
            end: End datetime.

        Returns:
            DownloadsByIpResponse with download records.
        """
        params = {
            "start": start.isoformat(),
            "end": end.isoformat(),
        }
        response = self._client.get(f"/analytics/by-ip/{ip_address}", params=params)
        data = self._handle_response(response)
        return DownloadsByIpResponse.model_validate(data)

    def get_user_agents(
        self,
        start: datetime,
        end: datetime,
    ) -> UserAgentsResponse:
        """
        Get user agent analytics.

        Args:
            start: Start datetime.
            end: End datetime.

        Returns:
            UserAgentsResponse with user agent counts.
        """
        params = {
            "start": start.isoformat(),
            "end": end.isoformat(),
        }
        response = self._client.get("/analytics/user-agents", params=params)
        data = self._handle_response(response)
        return UserAgentsResponse.model_validate(data)

    # Maintenance

    def cleanup_downloads(self) -> CleanupResponse:
        """
        Clean up old download records.

        Returns:
            CleanupResponse with deleted count.
        """
        response = self._client.post("/maintenance/cleanup-downloads")
        data = self._handle_response(response)
        return CleanupResponse.model_validate(data)

    # Health

    def health(self) -> HealthResponse:
        """
        Check API health.

        Returns:
            HealthResponse with status and timestamp.
        """
        response = self._client.get("/health")
        data = self._handle_response(response)
        return HealthResponse.model_validate(data)

    # High-Level Pipeline

    def upload_and_register(
        self,
        bucket: str,
        local_path: str | Path,
        category: str,
        entity: str,
        remote_path: str,
        remote_filename: str,
        remote_version: str,
        name: str | None = None,
        tags: list[str] | None = None,
        extra: dict[str, Any] | None = None,
        content_type: str | None = None,
        progress_callback: Callable[[int], None] | None = None,
    ) -> FileRecord:
        """
        Upload a file to R2 and register it with the r2index API.

        This is a convenience method that performs the full pipeline:
        1. Compute checksums (streaming, memory efficient)
        2. Upload to R2 (multipart for large files)
        3. Register with r2index API

        Args:
            bucket: The S3/R2 bucket name.
            local_path: Local path to the file to upload.
            category: File category.
            entity: File entity.
            remote_path: Remote path in R2 (e.g., "/data/files").
            remote_filename: Remote filename in R2.
            remote_version: Version identifier.
            name: Optional display name.
            tags: Optional list of tags.
            extra: Optional extra metadata.
            content_type: Optional content type for R2.
            progress_callback: Optional callback for upload progress.

        Returns:
            The created FileRecord.

        Raises:
            R2IndexError: If R2 config is not provided.
            UploadError: If upload fails.
        """
        local_path = Path(local_path)
        uploader = self._get_storage()

        # Step 1: Compute checksums
        checksums = compute_checksums(local_path)

        # Step 2: Build R2 object key
        object_key = f"{remote_path.strip('/')}/{remote_filename}"

        # Step 3: Upload to R2
        uploader.upload_file(
            local_path,
            bucket,
            object_key,
            content_type=content_type,
            progress_callback=progress_callback,
        )

        # Step 4: Register with API
        create_request = FileCreateRequest(
            bucket=bucket,
            category=category,
            entity=entity,
            remote_path=remote_path,
            remote_filename=remote_filename,
            remote_version=remote_version,
            name=name,
            tags=tags,
            extra=extra,
            size=checksums.size,
            md5=checksums.md5,
            sha1=checksums.sha1,
            sha256=checksums.sha256,
            sha512=checksums.sha512,
        )

        return self.create_file(create_request)

    def _get_public_ip(self) -> str:
        """Fetch public IP address from checkip.amazonaws.com."""
        response = httpx.get(CHECKIP_URL, timeout=10.0)
        return response.text.strip()

    def download_and_record(
        self,
        bucket: str,
        object_id: str,
        destination: str | Path,
        ip_address: str | None = None,
        user_agent: str | None = None,
        progress_callback: Callable[[int], None] | None = None,
        transfer_config: R2TransferConfig | None = None,
    ) -> tuple[Path, FileRecord]:
        """
        Download a file from R2 and record the download in the index.

        This is a convenience method that performs:
        1. Parse object_id into remote_path, remote_version, remote_filename
        2. Fetch file record from the API using these components
        3. Download the file from R2
        4. Record the download in the index for analytics

        Args:
            bucket: The S3/R2 bucket name.
            object_id: Full S3 object path in format: /path/to/object/version/filename
                Example: /releases/myapp/v1/myapp.zip
                - remote_path: /releases/myapp
                - remote_version: v1
                - remote_filename: myapp.zip
            destination: Local path where the file will be saved.
            ip_address: IP address of the downloader. If not provided, fetched
                from checkip.amazonaws.com.
            user_agent: User agent string. Defaults to "elaunira-r2index/<version>".
            progress_callback: Optional callback for download progress.
            transfer_config: Optional transfer configuration for multipart/threading.

        Returns:
            A tuple of (downloaded file path, file record).

        Raises:
            R2IndexError: If R2 config is not provided.
            ValueError: If object_id format is invalid.
            NotFoundError: If the file is not found in the index.
            DownloadError: If download fails.
        """
        storage = self._get_storage()

        # Resolve defaults
        if ip_address is None:
            ip_address = self._get_public_ip()
        if user_agent is None:
            user_agent = DEFAULT_USER_AGENT

        # Step 1: Parse object_id into components
        remote_tuple = _parse_object_id(object_id, bucket)

        # Step 2: Get file record by tuple
        file_record = self.get_file_by_tuple(remote_tuple)

        # Step 3: Build R2 object key and download
        object_key = object_id.strip("/")
        downloaded_path = storage.download_file(
            bucket,
            object_key,
            destination,
            progress_callback=progress_callback,
            transfer_config=transfer_config,
        )

        # Step 4: Record the download
        download_request = DownloadRecordRequest(
            file_id=file_record.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.record_download(download_request)

        return downloaded_path, file_record

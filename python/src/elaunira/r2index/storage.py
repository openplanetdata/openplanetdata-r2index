"""Synchronous R2 storage operations using boto3."""

import os
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import boto3
from boto3.s3.transfer import TransferConfig

from .exceptions import DownloadError, UploadError

# Default thresholds and part sizes for multipart transfers
DEFAULT_MULTIPART_CHUNKSIZE = 100 * 1024 * 1024  # 100MB
DEFAULT_MULTIPART_THRESHOLD = 100 * 1024 * 1024  # 100MB


def _default_max_concurrency() -> int:
    """Return default max concurrency: 2x CPU cores, minimum 4."""
    cpu_count = os.cpu_count() or 2
    return max(4, cpu_count * 2)


@dataclass
class R2TransferConfig:
    """Configuration for R2 transfer operations (uploads/downloads)."""

    multipart_threshold: int = DEFAULT_MULTIPART_THRESHOLD
    """Size threshold (bytes) to trigger multipart transfer. Default 100MB."""

    multipart_chunksize: int = DEFAULT_MULTIPART_CHUNKSIZE
    """Size of each part (bytes) in multipart transfer. Default 100MB."""

    max_concurrency: int = field(default_factory=_default_max_concurrency)
    """Number of parallel threads for multipart transfer. Default 2x CPU cores."""

    use_threads: bool = True
    """Whether to use threads for parallel transfer. Default True."""


@dataclass
class R2Config:
    """Configuration for R2 storage."""

    access_key_id: str
    secret_access_key: str
    endpoint_url: str
    bucket: str
    region: str = "auto"


class R2Storage:
    """Synchronous R2 storage client using boto3."""

    def __init__(self, config: R2Config) -> None:
        """
        Initialize the R2 storage client.

        Args:
            config: R2 configuration with credentials and endpoint.
        """
        self.config = config
        self._client = boto3.client(
            "s3",
            aws_access_key_id=config.access_key_id,
            aws_secret_access_key=config.secret_access_key,
            endpoint_url=config.endpoint_url,
            region_name=config.region,
        )

    def upload_file(
        self,
        file_path: str | Path,
        object_key: str,
        content_type: str | None = None,
        progress_callback: Callable[[int], None] | None = None,
        transfer_config: R2TransferConfig | None = None,
    ) -> str:
        """
        Upload a file to R2.

        Uses multipart upload for files larger than the configured threshold.

        Args:
            file_path: Path to the file to upload.
            object_key: The key (path) to store the object under in R2.
            content_type: Optional content type for the object.
            progress_callback: Optional callback called with bytes uploaded so far.
            transfer_config: Optional transfer configuration for multipart/threading.

        Returns:
            The object key of the uploaded file.

        Raises:
            UploadError: If the upload fails.
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise UploadError(f"File not found: {file_path}")

        tc = transfer_config or R2TransferConfig()
        boto_transfer_config = TransferConfig(
            multipart_threshold=tc.multipart_threshold,
            multipart_chunksize=tc.multipart_chunksize,
            max_concurrency=tc.max_concurrency,
            use_threads=tc.use_threads,
        )

        extra_args = {}
        if content_type:
            extra_args["ContentType"] = content_type

        callback = None
        if progress_callback:
            callback = _ProgressCallback(progress_callback)

        try:
            self._client.upload_file(
                str(file_path),
                self.config.bucket,
                object_key,
                Config=boto_transfer_config,
                ExtraArgs=extra_args if extra_args else None,
                Callback=callback,
            )
        except Exception as e:
            raise UploadError(f"Failed to upload file to R2: {e}") from e

        return object_key

    def delete_object(self, object_key: str) -> None:
        """
        Delete an object from R2.

        Args:
            object_key: The key of the object to delete.

        Raises:
            UploadError: If the deletion fails.
        """
        try:
            self._client.delete_object(Bucket=self.config.bucket, Key=object_key)
        except Exception as e:
            raise UploadError(f"Failed to delete object from R2: {e}") from e

    def object_exists(self, object_key: str) -> bool:
        """
        Check if an object exists in R2.

        Args:
            object_key: The key of the object to check.

        Returns:
            True if the object exists, False otherwise.
        """
        try:
            self._client.head_object(Bucket=self.config.bucket, Key=object_key)
            return True
        except self._client.exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            raise UploadError(f"Failed to check object existence: {e}") from e

    def download_file(
        self,
        object_key: str,
        file_path: str | Path,
        progress_callback: Callable[[int], None] | None = None,
        transfer_config: R2TransferConfig | None = None,
    ) -> Path:
        """
        Download a file from R2.

        Args:
            object_key: The key (path) of the object in R2.
            file_path: Local path where the file will be saved.
            progress_callback: Optional callback called with bytes downloaded so far.
            transfer_config: Optional transfer configuration for multipart/threading.

        Returns:
            The path to the downloaded file.

        Raises:
            DownloadError: If the download fails.
        """
        file_path = Path(file_path)

        # Ensure parent directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)

        tc = transfer_config or R2TransferConfig()
        boto_transfer_config = TransferConfig(
            multipart_threshold=tc.multipart_threshold,
            multipart_chunksize=tc.multipart_chunksize,
            max_concurrency=tc.max_concurrency,
            use_threads=tc.use_threads,
        )

        callback = None
        if progress_callback:
            callback = _ProgressCallback(progress_callback)

        try:
            self._client.download_file(
                self.config.bucket,
                object_key,
                str(file_path),
                Config=boto_transfer_config,
                Callback=callback,
            )
        except Exception as e:
            raise DownloadError(f"Failed to download file from R2: {e}") from e

        return file_path


class _ProgressCallback:
    """Wrapper to track cumulative progress for boto3 callback."""

    def __init__(self, callback: Callable[[int], None]) -> None:
        self._callback = callback
        self._bytes_transferred = 0

    def __call__(self, bytes_amount: int) -> None:
        self._bytes_transferred += bytes_amount
        self._callback(self._bytes_transferred)

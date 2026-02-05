"""Asynchronous R2 storage operations using aioboto3."""

from collections.abc import Callable
from pathlib import Path

import aioboto3
from aiobotocore.config import AioConfig

from .exceptions import DownloadError, UploadError
from .storage import R2Config, R2TransferConfig


class AsyncR2Storage:
    """Asynchronous R2 storage client using aioboto3."""

    def __init__(self, config: R2Config) -> None:
        """
        Initialize the async R2 storage client.

        Args:
            config: R2 configuration with credentials and endpoint.
        """
        self.config = config
        self._session = aioboto3.Session()

    async def upload_file(
        self,
        file_path: str | Path,
        object_key: str,
        content_type: str | None = None,
        progress_callback: Callable[[int], None] | None = None,
        transfer_config: R2TransferConfig | None = None,
    ) -> str:
        """
        Upload a file to R2 asynchronously.

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
        aio_config = AioConfig(
            max_pool_connections=tc.max_concurrency,
        )

        extra_args = {}
        if content_type:
            extra_args["ContentType"] = content_type

        try:
            async with self._session.client(
                "s3",
                aws_access_key_id=self.config.access_key_id,
                aws_secret_access_key=self.config.secret_access_key,
                endpoint_url=self.config.endpoint_url,
                region_name=self.config.region,
                config=aio_config,
            ) as client:
                callback = None
                if progress_callback:
                    callback = _AsyncProgressCallback(progress_callback)

                await client.upload_file(
                    str(file_path),
                    self.config.bucket,
                    object_key,
                    ExtraArgs=extra_args if extra_args else None,
                    Callback=callback,
                )
        except Exception as e:
            raise UploadError(f"Failed to upload file to R2: {e}") from e

        return object_key

    async def delete_object(self, object_key: str) -> None:
        """
        Delete an object from R2 asynchronously.

        Args:
            object_key: The key of the object to delete.

        Raises:
            UploadError: If the deletion fails.
        """
        try:
            async with self._session.client(
                "s3",
                aws_access_key_id=self.config.access_key_id,
                aws_secret_access_key=self.config.secret_access_key,
                endpoint_url=self.config.endpoint_url,
                region_name=self.config.region,
            ) as client:
                await client.delete_object(Bucket=self.config.bucket, Key=object_key)
        except Exception as e:
            raise UploadError(f"Failed to delete object from R2: {e}") from e

    async def object_exists(self, object_key: str) -> bool:
        """
        Check if an object exists in R2 asynchronously.

        Args:
            object_key: The key of the object to check.

        Returns:
            True if the object exists, False otherwise.
        """
        try:
            async with self._session.client(
                "s3",
                aws_access_key_id=self.config.access_key_id,
                aws_secret_access_key=self.config.secret_access_key,
                endpoint_url=self.config.endpoint_url,
                region_name=self.config.region,
            ) as client:
                await client.head_object(Bucket=self.config.bucket, Key=object_key)
                return True
        except client.exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            raise UploadError(f"Failed to check object existence: {e}") from e

    async def download_file(
        self,
        object_key: str,
        file_path: str | Path,
        progress_callback: Callable[[int], None] | None = None,
        transfer_config: R2TransferConfig | None = None,
    ) -> Path:
        """
        Download a file from R2 asynchronously.

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
        aio_config = AioConfig(
            max_pool_connections=tc.max_concurrency,
        )

        try:
            async with self._session.client(
                "s3",
                aws_access_key_id=self.config.access_key_id,
                aws_secret_access_key=self.config.secret_access_key,
                endpoint_url=self.config.endpoint_url,
                region_name=self.config.region,
                config=aio_config,
            ) as client:
                callback = None
                if progress_callback:
                    callback = _AsyncProgressCallback(progress_callback)

                await client.download_file(
                    self.config.bucket,
                    object_key,
                    str(file_path),
                    Callback=callback,
                )
        except Exception as e:
            raise DownloadError(f"Failed to download file from R2: {e}") from e

        return file_path


class _AsyncProgressCallback:
    """Wrapper to track cumulative progress for aioboto3 callback."""

    def __init__(self, callback: Callable[[int], None]) -> None:
        self._callback = callback
        self._bytes_transferred = 0

    def __call__(self, bytes_amount: int) -> None:
        self._bytes_transferred += bytes_amount
        self._callback(self._bytes_transferred)

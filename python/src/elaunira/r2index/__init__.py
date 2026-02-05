"""Python library for uploading and downloading files to/from Cloudflare R2 with the r2index API."""

from .async_client import AsyncR2IndexClient
from .async_storage import AsyncR2Storage
from .checksums import (
    ChecksumResult,
    compute_checksums,
    compute_checksums_async,
    compute_checksums_from_file_object,
)
from .client import R2IndexClient
from .exceptions import (
    AuthenticationError,
    ConflictError,
    DownloadError,
    NotFoundError,
    R2IndexError,
    UploadError,
    ValidationError,
)
from .models import (
    CleanupResponse,
    DownloadByIpEntry,
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
    TimeseriesDataPoint,
    TimeseriesResponse,
    UserAgentEntry,
    UserAgentsResponse,
)
from .storage import R2Config, R2Storage, R2TransferConfig

__all__ = [
    # Clients
    "AsyncR2IndexClient",
    "R2IndexClient",
    # Storage
    "AsyncR2Storage",
    "R2Config",
    "R2Storage",
    "R2TransferConfig",
    # Checksums
    "ChecksumResult",
    "compute_checksums",
    "compute_checksums_async",
    "compute_checksums_from_file_object",
    # Exceptions
    "AuthenticationError",
    "ConflictError",
    "DownloadError",
    "NotFoundError",
    "R2IndexError",
    "UploadError",
    "ValidationError",
    # Models - File operations
    "FileCreateRequest",
    "FileListResponse",
    "FileRecord",
    "FileUpdateRequest",
    "IndexEntry",
    "RemoteTuple",
    # Models - Downloads
    "DownloadRecord",
    "DownloadRecordRequest",
    # Models - Analytics
    "DownloadByIpEntry",
    "DownloadsByIpResponse",
    "SummaryResponse",
    "TimeseriesDataPoint",
    "TimeseriesResponse",
    "UserAgentEntry",
    "UserAgentsResponse",
    # Models - Other
    "CleanupResponse",
    "HealthResponse",
]

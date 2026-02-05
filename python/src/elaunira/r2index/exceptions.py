"""Custom exceptions for the r2index library."""


class R2IndexError(Exception):
    """Base exception for r2index library errors."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class AuthenticationError(R2IndexError):
    """Raised for 401/403 authentication/authorization errors."""

    pass


class NotFoundError(R2IndexError):
    """Raised for 404 not found errors."""

    pass


class ValidationError(R2IndexError):
    """Raised for 400 validation errors."""

    pass


class ConflictError(R2IndexError):
    """Raised for 409 conflict errors."""

    pass


class UploadError(R2IndexError):
    """Raised for R2 upload failures."""

    pass


class DownloadError(R2IndexError):
    """Raised for R2 download failures."""

    pass


class ChecksumVerificationError(DownloadError):
    """Raised when checksum verification fails after download."""

    def __init__(
        self,
        message: str,
        expected: str | None = None,
        actual: str | None = None,
    ) -> None:
        super().__init__(message)
        self.expected = expected
        self.actual = actual

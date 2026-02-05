# elaunira-r2index

Python library for uploading and downloading files to/from Cloudflare R2 with the r2index API.

## Installation

```bash
pip install elaunira-r2index
```

## Usage

### Sync Client

```python
from elaunira.r2index import R2IndexClient

client = R2IndexClient(
    index_api_url="https://r2index.example.com",
    index_api_token="your-bearer-token",
    r2_access_key_id="your-r2-access-key-id",
    r2_secret_access_key="your-r2-secret-access-key",
    r2_endpoint_url="https://your-account-id.r2.cloudflarestorage.com",
)

# Upload and register a file
record = client.upload(
    bucket="my-bucket",
    source="./myfile.zip",
    category="software",
    entity="myapp",
    extension="zip",
    media_type="application/zip",
    destination_path="/releases/myapp",
    destination_filename="myapp.zip",
    destination_version="v1",
    tags=["release", "stable"],
    create_checksum_files=True,  # Creates .md5, .sha1, .sha256, .sha512 files
)

# Download a file and record the download
# IP address is auto-detected, user agent defaults to "elaunira-r2index/<version>"
path, record = client.download(
    bucket="my-bucket",
    source_path="/releases/myapp",
    source_filename="myapp.zip",
    source_version="v1",
    destination="./downloads/myfile.zip",
    verify_checksum=True,  # Verify SHA-256 checksum after download
)
```

### Async Client

```python
from elaunira.r2index import AsyncR2IndexClient

async with AsyncR2IndexClient(
    index_api_url="https://r2index.example.com",
    index_api_token="your-bearer-token",
    r2_access_key_id="your-r2-access-key-id",
    r2_secret_access_key="your-r2-secret-access-key",
    r2_endpoint_url="https://your-account-id.r2.cloudflarestorage.com",
) as client:
    # Upload
    record = await client.upload(
        bucket="my-bucket",
        source="./myfile.zip",
        category="software",
        entity="myapp",
        extension="zip",
        media_type="application/zip",
        destination_path="/releases/myapp",
        destination_filename="myapp.zip",
        destination_version="v1",
        tags=["release", "stable"],
    )

    # Download
    path, record = await client.download(
        bucket="my-bucket",
        source_path="/releases/myapp",
        source_filename="myapp.zip",
        source_version="v1",
        destination="./downloads/myfile.zip",
    )
```

### Transfer Configuration

Control multipart transfer settings with `R2TransferConfig` for both uploads and downloads:

```python
from elaunira.r2index import R2IndexClient, R2TransferConfig

client = R2IndexClient(
    index_api_url="https://r2index.example.com",
    index_api_token="your-bearer-token",
    r2_access_key_id="your-r2-access-key-id",
    r2_secret_access_key="your-r2-secret-access-key",
    r2_endpoint_url="https://your-account-id.r2.cloudflarestorage.com",
)

# Custom transfer settings
transfer_config = R2TransferConfig(
    multipart_threshold=100 * 1024 * 1024,  # 100MB (default)
    multipart_chunksize=32 * 1024 * 1024,   # 32MB chunks
    max_concurrency=64,                      # 64 parallel threads
    use_threads=True,                        # Enable threading (default)
)

# Use with upload
record = client.upload(
    bucket="my-bucket",
    source="./largefile.zip",
    category="data",
    entity="archive",
    extension="zip",
    media_type="application/zip",
    destination_path="/data/files",
    destination_filename="largefile.zip",
    destination_version="v1",
    transfer_config=transfer_config,
)

# Use with download
path, record = client.download(
    bucket="my-bucket",
    source_path="/data/files",
    source_filename="largefile.zip",
    source_version="v1",
    destination="./downloads/largefile.zip",
    transfer_config=transfer_config,
)
```

Default `max_concurrency` is 2x the number of CPU cores (minimum 4).

### Progress Tracking

```python
def on_progress(bytes_transferred: int) -> None:
    print(f"Downloaded: {bytes_transferred / 1024 / 1024:.1f} MB")

path, record = client.download(
    bucket="my-bucket",
    source_path="/releases/myapp",
    source_filename="myapp.zip",
    source_version="v1",
    destination="./downloads/myfile.zip",
    progress_callback=on_progress,
)
```

### Deleting Files

```python
# Delete from R2 storage (including checksum sidecar files if they exist)
client.delete_from_r2(
    bucket="my-bucket",
    path="/releases/myapp",
    filename="myapp.zip",
    version="v1",
    delete_checksum_files=True,  # Also delete .md5, .sha1, .sha256, .sha512 files
)

# Delete from index (metadata only)
client.delete(file_id)

# Or delete by remote tuple
client.delete_by_tuple(RemoteTuple(
    bucket="my-bucket",
    remote_path="/releases/myapp",
    remote_filename="myapp.zip",
    remote_version="v1",
))
```

## License

MIT

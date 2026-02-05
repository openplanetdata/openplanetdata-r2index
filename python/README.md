# elaunira-r2index

Python library for uploading and downloading files to/from Cloudflare R2 with the r2index API.

## Installation

```bash
pip install elaunira-r2index
```

## Usage

### Sync Client

```python
from elaunira.r2index import R2IndexClient, R2Config

client = R2IndexClient(
    api_url="https://r2index.example.com",
    api_token="your-bearer-token",
    r2_config=R2Config(
        access_key_id="your-r2-access-key-id",
        secret_access_key="your-r2-secret-access-key",
        endpoint_url="https://your-account-id.r2.cloudflarestorage.com",
        bucket="your-bucket-name",
    ),
)

# Upload and register a file
record = client.upload_and_register(
    local_path="./myfile.zip",
    bucket="my-bucket",
    category="software",
    entity="myapp",
    remote_path="/releases/myapp",
    remote_filename="myapp.zip",
    remote_version="v1",
    tags=["release", "stable"],
)

# Download a file and record the download
# IP address is auto-detected, user agent defaults to "elaunira-r2index/0.1.0"
path, record = client.download_and_record(
    bucket="my-bucket",
    object_id="/releases/myapp/v1/myapp.zip",
    destination="./downloads/myfile.zip",
)
```

### Async Client

```python
from elaunira.r2index import AsyncR2IndexClient, R2Config

async with AsyncR2IndexClient(
    api_url="https://r2index.example.com",
    api_token="your-bearer-token",
    r2_config=R2Config(
        access_key_id="your-r2-access-key-id",
        secret_access_key="your-r2-secret-access-key",
        endpoint_url="https://your-account-id.r2.cloudflarestorage.com",
        bucket="your-bucket-name",
    ),
) as client:
    # Upload
    record = await client.upload_and_register(
        local_path="./myfile.zip",
        bucket="my-bucket",
        category="software",
        entity="myapp",
        remote_path="/releases/myapp",
        remote_filename="myapp.zip",
        remote_version="v1",
        tags=["release", "stable"],
    )

    # Download
    path, record = await client.download_and_record(
        bucket="my-bucket",
        object_id="/releases/myapp/v1/myapp.zip",
        destination="./downloads/myfile.zip",
    )
```

### Transfer Configuration

Control multipart transfer settings with `R2TransferConfig`:

```python
from elaunira.r2index import R2IndexClient, R2Config, R2TransferConfig

client = R2IndexClient(
    api_url="https://r2index.example.com",
    api_token="your-bearer-token",
    r2_config=R2Config(...),
)

# Custom transfer settings
transfer_config = R2TransferConfig(
    multipart_threshold=100 * 1024 * 1024,  # 100MB (default)
    multipart_chunksize=32 * 1024 * 1024,   # 32MB chunks
    max_concurrency=64,                      # 64 parallel threads
    use_threads=True,                        # Enable threading (default)
)

path, record = client.download_and_record(
    bucket="my-bucket",
    object_id="/data/files/v2/largefile.zip",
    destination="./downloads/largefile.zip",
    transfer_config=transfer_config,
)
```

Default `max_concurrency` is 2x the number of CPU cores (minimum 4).

### Progress Tracking

```python
def on_progress(bytes_transferred: int) -> None:
    print(f"Downloaded: {bytes_transferred / 1024 / 1024:.1f} MB")

path, record = client.download_and_record(
    bucket="my-bucket",
    object_id="/releases/myapp/v1/myapp.zip",
    destination="./downloads/myfile.zip",
    progress_callback=on_progress,
)
```

## License

MIT

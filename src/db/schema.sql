CREATE TABLE IF NOT EXISTS files (
    id TEXT PRIMARY KEY,
    name TEXT,
    category TEXT NOT NULL,
    entity TEXT NOT NULL,
    extension TEXT NOT NULL,
    media_type TEXT NOT NULL,
    remote_path TEXT NOT NULL,
    remote_filename TEXT NOT NULL,
    remote_version TEXT NOT NULL,
    metadata_path TEXT,
    size INTEGER,
    checksum_md5 TEXT,
    checksum_sha1 TEXT,
    checksum_sha256 TEXT,
    checksum_sha512 TEXT,
    extra TEXT,
    deprecated INTEGER DEFAULT 0,
    deprecation_reason TEXT DEFAULT '',
    created INTEGER NOT NULL,
    updated INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS file_tags (
    file_id TEXT NOT NULL,
    tag TEXT NOT NULL,
    PRIMARY KEY (file_id, tag),
    FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_files_category ON files(category);
CREATE INDEX IF NOT EXISTS idx_files_entity ON files(entity);
CREATE INDEX IF NOT EXISTS idx_files_extension ON files(extension);
CREATE INDEX IF NOT EXISTS idx_files_media_type ON files(media_type);
CREATE INDEX IF NOT EXISTS idx_files_deprecated ON files(deprecated);
CREATE UNIQUE INDEX IF NOT EXISTS idx_files_remote_unique ON files(remote_path, remote_filename, remote_version);
CREATE INDEX IF NOT EXISTS idx_file_tags_tag ON file_tags(tag);

-- Downloads tracking
CREATE TABLE IF NOT EXISTS file_downloads (
    id TEXT PRIMARY KEY,
    remote_path TEXT NOT NULL,
    remote_filename TEXT NOT NULL,
    remote_version TEXT NOT NULL,
    ip_address TEXT NOT NULL,
    user_agent TEXT,
    downloaded_at INTEGER NOT NULL,
    hour_bucket INTEGER NOT NULL,
    day_bucket INTEGER NOT NULL,
    month_bucket INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_downloads_hour ON file_downloads(hour_bucket);
CREATE INDEX IF NOT EXISTS idx_downloads_day ON file_downloads(day_bucket);
CREATE INDEX IF NOT EXISTS idx_downloads_month ON file_downloads(month_bucket);
CREATE INDEX IF NOT EXISTS idx_downloads_file_day ON file_downloads(remote_path, remote_filename, remote_version, day_bucket);
CREATE INDEX IF NOT EXISTS idx_downloads_ip_day ON file_downloads(ip_address, day_bucket);

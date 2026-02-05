import type {
  CreateDownloadInput,
  DownloadRecord,
  AnalyticsScale,
  TimeSeriesBucket,
  FileDownloadStats,
  AnalyticsSummary,
  DownloadsByIpResult,
  UserAgentStats,
} from '../types';

// ============================================================================
// Cleanup / TTL
// ============================================================================

export async function cleanupOldDownloads(db: D1Database, retentionDays: number): Promise<number> {
  const cutoff = Date.now() - (retentionDays * 24 * 60 * 60 * 1000);
  const result = await db.prepare('DELETE FROM file_downloads WHERE downloaded_at < ?').bind(cutoff).run();
  return result.meta.changes;
}

// ============================================================================
// Helpers
// ============================================================================

function computeBuckets(downloadedAt: number) {
  const date = new Date(downloadedAt);
  return {
    hour_bucket: Math.floor(downloadedAt / 3600000) * 3600000,
    day_bucket: Math.floor(downloadedAt / 86400000) * 86400000,
    month_bucket: date.getUTCFullYear() * 100 + (date.getUTCMonth() + 1),
  };
}

function getBucketColumn(scale: AnalyticsScale): string {
  switch (scale) {
    case 'hour': return 'hour_bucket';
    case 'day': return 'day_bucket';
    case 'month': return 'month_bucket';
  }
}

interface FileFilter {
  bucket?: string;
  remote_path?: string;
  remote_filename?: string;
  remote_version?: string;
}

function buildFileConditions(filter: FileFilter): { conditions: string[]; values: unknown[] } {
  const conditions: string[] = [];
  const values: unknown[] = [];

  if (filter.bucket) {
    conditions.push('bucket = ?');
    values.push(filter.bucket);
  }
  if (filter.remote_path) {
    conditions.push('remote_path = ?');
    values.push(filter.remote_path);
  }
  if (filter.remote_filename) {
    conditions.push('remote_filename = ?');
    values.push(filter.remote_filename);
  }
  if (filter.remote_version) {
    conditions.push('remote_version = ?');
    values.push(filter.remote_version);
  }

  return { conditions, values };
}

// ============================================================================
// Create Download
// ============================================================================

export async function createDownload(db: D1Database, input: CreateDownloadInput): Promise<DownloadRecord> {
  const id = crypto.randomUUID();
  const downloadedAt = Date.now();
  const timeBuckets = computeBuckets(downloadedAt);

  await db.prepare(`
    INSERT INTO file_downloads (id, bucket, remote_path, remote_filename, remote_version, ip_address, user_agent, downloaded_at, hour_bucket, day_bucket, month_bucket)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  `).bind(
    id,
    input.bucket,
    input.remote_path,
    input.remote_filename,
    input.remote_version,
    input.ip_address,
    input.user_agent ?? null,
    downloadedAt,
    timeBuckets.hour_bucket,
    timeBuckets.day_bucket,
    timeBuckets.month_bucket
  ).run();

  return {
    id,
    bucket: input.bucket,
    remote_path: input.remote_path,
    remote_filename: input.remote_filename,
    remote_version: input.remote_version,
    ip_address: input.ip_address,
    user_agent: input.user_agent ?? null,
    downloaded_at: downloadedAt,
    ...timeBuckets,
  };
}

// ============================================================================
// Time Series
// ============================================================================

export async function getTimeSeries(
  db: D1Database,
  start: number,
  end: number,
  scale: AnalyticsScale,
  filter: FileFilter,
  filesLimit: number = 100
): Promise<TimeSeriesBucket[]> {
  const bucketCol = getBucketColumn(scale);
  const { conditions, values } = buildFileConditions(filter);

  // Add time range condition based on scale
  conditions.push(`${bucketCol} >= ?`);
  conditions.push(`${bucketCol} <= ?`);

  // Convert start/end to bucket values for the scale
  const startBucket = scale === 'month'
    ? new Date(start).getUTCFullYear() * 100 + (new Date(start).getUTCMonth() + 1)
    : scale === 'hour'
      ? Math.floor(start / 3600000) * 3600000
      : Math.floor(start / 86400000) * 86400000;

  const endBucket = scale === 'month'
    ? new Date(end).getUTCFullYear() * 100 + (new Date(end).getUTCMonth() + 1)
    : scale === 'hour'
      ? Math.floor(end / 3600000) * 3600000
      : Math.floor(end / 86400000) * 86400000;

  values.push(startBucket, endBucket);

  const whereClause = conditions.length > 0 ? `WHERE ${conditions.join(' AND ')}` : '';

  // Query per-file stats grouped by time bucket, joined with files to get id
  const query = `
    SELECT
      d.${bucketCol} as time_bucket,
      f.id as file_id,
      d.bucket,
      d.remote_path,
      d.remote_filename,
      d.remote_version,
      COUNT(*) as downloads,
      COUNT(DISTINCT d.ip_address) as unique_downloads
    FROM file_downloads d
    LEFT JOIN files f ON f.bucket = d.bucket
      AND f.remote_path = d.remote_path
      AND f.remote_filename = d.remote_filename
      AND f.remote_version = d.remote_version
    ${whereClause.replace(/\b(bucket|remote_path|remote_filename|remote_version)\b/g, 'd.$1').replace(/\b(hour_bucket|day_bucket|month_bucket)\b/g, 'd.$1')}
    GROUP BY d.${bucketCol}, d.bucket, d.remote_path, d.remote_filename, d.remote_version
    ORDER BY d.${bucketCol}, downloads DESC
  `;

  const result = await db.prepare(query).bind(...values).all<{
    time_bucket: number;
    file_id: string | null;
    bucket: string;
    remote_path: string;
    remote_filename: string;
    remote_version: string;
    downloads: number;
    unique_downloads: number;
  }>();

  // Group results by time bucket (already sorted by downloads DESC within each bucket)
  const timeBucketMap = new Map<number, { files: FileDownloadStats[]; total: number; unique: number }>();

  for (const row of result.results) {
    if (!timeBucketMap.has(row.time_bucket)) {
      timeBucketMap.set(row.time_bucket, { files: [], total: 0, unique: 0 });
    }
    const timeBucket = timeBucketMap.get(row.time_bucket)!;
    // Always count total downloads, but only keep top N files per bucket
    timeBucket.total += row.downloads;
    if (timeBucket.files.length < filesLimit) {
      timeBucket.files.push({
        id: row.file_id,
        bucket: row.bucket,
        remote_path: row.remote_path,
        remote_filename: row.remote_filename,
        remote_version: row.remote_version,
        downloads: row.downloads,
        unique_downloads: row.unique_downloads,
      });
    }
  }

  // Calculate unique downloads per bucket (need separate query since DISTINCT spans files)
  const uniqueQuery = `
    SELECT ${bucketCol} as bucket, COUNT(DISTINCT ip_address) as unique_downloads
    FROM file_downloads
    ${whereClause}
    GROUP BY ${bucketCol}
    ORDER BY ${bucketCol}
  `;
  const uniqueResult = await db.prepare(uniqueQuery).bind(...values).all<{ bucket: number; unique_downloads: number }>();

  for (const row of uniqueResult.results) {
    if (timeBucketMap.has(row.bucket)) {
      timeBucketMap.get(row.bucket)!.unique = row.unique_downloads;
    }
  }

  // Convert to array
  return Array.from(timeBucketMap.entries())
    .sort(([a], [b]) => a - b)
    .map(([timestamp, data]) => ({
      timestamp,
      files: data.files,
      total_downloads: data.total,
      total_unique_downloads: data.unique,
    }));
}

// ============================================================================
// Summary
// ============================================================================

export async function getSummary(
  db: D1Database,
  start: number,
  end: number,
  filter: FileFilter
): Promise<AnalyticsSummary> {
  const { conditions, values } = buildFileConditions(filter);

  conditions.push('downloaded_at >= ?');
  conditions.push('downloaded_at <= ?');
  values.push(start, end);

  const whereClause = `WHERE ${conditions.join(' AND ')}`;

  // Get totals
  const totalsQuery = `
    SELECT COUNT(*) as total, COUNT(DISTINCT ip_address) as unique_total
    FROM file_downloads
    ${whereClause}
  `;
  const totals = await db.prepare(totalsQuery).bind(...values).first<{ total: number; unique_total: number }>();

  // Get top user agents
  const uaQuery = `
    SELECT user_agent, COUNT(*) as downloads
    FROM file_downloads
    ${whereClause}
    GROUP BY user_agent
    ORDER BY downloads DESC
    LIMIT 10
  `;
  const userAgents = await db.prepare(uaQuery).bind(...values).all<{ user_agent: string | null; downloads: number }>();

  return {
    total_downloads: totals?.total ?? 0,
    unique_downloads: totals?.unique_total ?? 0,
    top_user_agents: userAgents.results
      .filter(ua => ua.user_agent)
      .map(ua => ({ user_agent: ua.user_agent!, downloads: ua.downloads })),
    period: { start, end },
  };
}

// ============================================================================
// By IP
// ============================================================================

export async function getDownloadsByIp(
  db: D1Database,
  ip: string,
  start: number,
  end: number,
  limit: number,
  offset: number
): Promise<DownloadsByIpResult> {
  const conditions = ['ip_address = ?', 'downloaded_at >= ?', 'downloaded_at <= ?'];
  const values: unknown[] = [ip, start, end];

  const whereClause = `WHERE ${conditions.join(' AND ')}`;

  // Get total count
  const countQuery = `SELECT COUNT(*) as total FROM file_downloads ${whereClause}`;
  const countResult = await db.prepare(countQuery).bind(...values).first<{ total: number }>();

  // Get downloads
  const query = `
    SELECT bucket, remote_path, remote_filename, remote_version, downloaded_at, user_agent
    FROM file_downloads
    ${whereClause}
    ORDER BY downloaded_at DESC
    LIMIT ? OFFSET ?
  `;
  const result = await db.prepare(query).bind(...values, limit, offset).all<{
    bucket: string;
    remote_path: string;
    remote_filename: string;
    remote_version: string;
    downloaded_at: number;
    user_agent: string | null;
  }>();

  return {
    downloads: result.results,
    total: countResult?.total ?? 0,
  };
}

// ============================================================================
// User Agents
// ============================================================================

export async function getUserAgentStats(
  db: D1Database,
  start: number,
  end: number,
  filter: FileFilter,
  limit: number
): Promise<UserAgentStats[]> {
  const { conditions, values } = buildFileConditions(filter);

  conditions.push('downloaded_at >= ?');
  conditions.push('downloaded_at <= ?');
  values.push(start, end);

  const whereClause = `WHERE ${conditions.join(' AND ')}`;

  const query = `
    SELECT user_agent, COUNT(*) as downloads, COUNT(DISTINCT ip_address) as unique_ips
    FROM file_downloads
    ${whereClause}
    GROUP BY user_agent
    ORDER BY downloads DESC
    LIMIT ?
  `;

  const result = await db.prepare(query).bind(...values, limit).all<{
    user_agent: string | null;
    downloads: number;
    unique_ips: number;
  }>();

  return result.results
    .filter(r => r.user_agent)
    .map(r => ({
      user_agent: r.user_agent!,
      downloads: r.downloads,
      unique_ips: r.unique_ips,
    }));
}

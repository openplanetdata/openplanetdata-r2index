import { describe, it, expect, beforeAll, beforeEach } from 'vitest';
import { env, SELF } from 'cloudflare:test';
import { setupDatabase } from './setup';

const API_TOKEN = 'test-token';

const createAuthHeaders = () => ({
  Authorization: `Bearer ${API_TOKEN}`,
  'Content-Type': 'application/json',
});

const validDownloadInput = {
  remote_path: '/uploads/documents',
  remote_filename: 'report.pdf',
  remote_version: 'v1',
  ip_address: '192.168.1.1',
  user_agent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0',
};

beforeAll(async () => {
  await setupDatabase();
});

describe('POST /downloads - Record download', () => {
  beforeEach(async () => {
    await env.DB.prepare('DELETE FROM file_downloads').run();
  });

  it('records a download with all fields', async () => {
    const response = await SELF.fetch('http://localhost/downloads', {
      method: 'POST',
      headers: createAuthHeaders(),
      body: JSON.stringify(validDownloadInput),
    });
    expect(response.status).toBe(201);
    const data = await response.json() as {
      id: string;
      remote_path: string;
      ip_address: string;
      downloaded_at: number;
      hour_bucket: number;
      day_bucket: number;
      month_bucket: number;
    };
    expect(data.id).toBeTruthy();
    expect(data.remote_path).toBe('/uploads/documents');
    expect(data.ip_address).toBe('192.168.1.1');
    expect(data.downloaded_at).toBeGreaterThan(0);
    expect(data.hour_bucket).toBeGreaterThan(0);
    expect(data.day_bucket).toBeGreaterThan(0);
    expect(data.month_bucket).toBeGreaterThan(0);
  });

  it('records a download without user_agent', async () => {
    const { user_agent, ...input } = validDownloadInput;
    const response = await SELF.fetch('http://localhost/downloads', {
      method: 'POST',
      headers: createAuthHeaders(),
      body: JSON.stringify(input),
    });
    expect(response.status).toBe(201);
  });

  it('rejects missing required fields', async () => {
    const response = await SELF.fetch('http://localhost/downloads', {
      method: 'POST',
      headers: createAuthHeaders(),
      body: JSON.stringify({ ip_address: '192.168.1.1' }),
    });
    expect(response.status).toBe(400);
  });

  it('computes correct time buckets', async () => {
    const response = await SELF.fetch('http://localhost/downloads', {
      method: 'POST',
      headers: createAuthHeaders(),
      body: JSON.stringify(validDownloadInput),
    });
    const data = await response.json() as {
      downloaded_at: number;
      hour_bucket: number;
      day_bucket: number;
      month_bucket: number;
    };

    // hour_bucket should be start of the hour
    expect(data.hour_bucket % 3600000).toBe(0);
    expect(data.hour_bucket).toBeLessThanOrEqual(data.downloaded_at);
    expect(data.hour_bucket + 3600000).toBeGreaterThan(data.downloaded_at);

    // day_bucket should be start of the day
    expect(data.day_bucket % 86400000).toBe(0);

    // month_bucket should be YYYYMM format
    const date = new Date(data.downloaded_at);
    const expectedMonth = date.getUTCFullYear() * 100 + (date.getUTCMonth() + 1);
    expect(data.month_bucket).toBe(expectedMonth);
  });
});

describe('GET /analytics/timeseries', () => {
  beforeEach(async () => {
    await env.DB.prepare('DELETE FROM file_downloads').run();

    // Create test downloads
    for (let i = 0; i < 5; i++) {
      await SELF.fetch('http://localhost/downloads', {
        method: 'POST',
        headers: createAuthHeaders(),
        body: JSON.stringify({
          ...validDownloadInput,
          ip_address: `192.168.1.${i + 1}`,
        }),
      });
    }
  });

  it('returns time series with daily scale', async () => {
    const now = Date.now();
    const start = now - 86400000;
    const end = now + 86400000;

    const response = await SELF.fetch(
      `http://localhost/analytics/timeseries?start=${start}&end=${end}&scale=day`,
      { headers: createAuthHeaders() }
    );
    expect(response.status).toBe(200);
    const data = await response.json() as { scale: string; data: { bucket: number; downloads: number; unique_downloads: number }[] };
    expect(data.scale).toBe('day');
    expect(data.data.length).toBeGreaterThan(0);
    expect(data.data[0].downloads).toBe(5);
    expect(data.data[0].unique_downloads).toBe(5);
  });

  it('returns time series with hourly scale', async () => {
    const now = Date.now();
    const start = now - 3600000;
    const end = now + 3600000;

    const response = await SELF.fetch(
      `http://localhost/analytics/timeseries?start=${start}&end=${end}&scale=hour`,
      { headers: createAuthHeaders() }
    );
    expect(response.status).toBe(200);
    const data = await response.json() as { scale: string; data: unknown[] };
    expect(data.scale).toBe('hour');
  });

  it('filters by file', async () => {
    // Add downloads for another file
    await SELF.fetch('http://localhost/downloads', {
      method: 'POST',
      headers: createAuthHeaders(),
      body: JSON.stringify({ ...validDownloadInput, remote_filename: 'other.pdf', ip_address: '10.0.0.1' }),
    });

    const now = Date.now();
    const response = await SELF.fetch(
      `http://localhost/analytics/timeseries?start=${now - 86400000}&end=${now + 86400000}&scale=day&remote_filename=report.pdf`,
      { headers: createAuthHeaders() }
    );
    const data = await response.json() as { data: { downloads: number }[] };
    expect(data.data[0].downloads).toBe(5); // Only original file
  });

  it('includes Cache-Control header', async () => {
    const now = Date.now();
    const response = await SELF.fetch(
      `http://localhost/analytics/timeseries?start=${now - 86400000}&end=${now + 86400000}`,
      { headers: createAuthHeaders() }
    );
    expect(response.headers.get('Cache-Control')).toBe('public, max-age=60');
  });
});

describe('GET /analytics/summary', () => {
  beforeEach(async () => {
    await env.DB.prepare('DELETE FROM file_downloads').run();

    for (let i = 0; i < 3; i++) {
      await SELF.fetch('http://localhost/downloads', {
        method: 'POST',
        headers: createAuthHeaders(),
        body: JSON.stringify({
          ...validDownloadInput,
          ip_address: `192.168.1.${i + 1}`,
          user_agent: i < 2 ? 'Chrome/120' : 'Safari/17',
        }),
      });
    }
  });

  it('returns summary with totals', async () => {
    const now = Date.now();
    const response = await SELF.fetch(
      `http://localhost/analytics/summary?start=${now - 86400000}&end=${now + 86400000}`,
      { headers: createAuthHeaders() }
    );
    expect(response.status).toBe(200);
    const data = await response.json() as {
      total_downloads: number;
      unique_downloads: number;
      top_user_agents: { user_agent: string; downloads: number }[];
      period: { start: number; end: number };
    };
    expect(data.total_downloads).toBe(3);
    expect(data.unique_downloads).toBe(3);
    expect(data.top_user_agents.length).toBe(2);
    expect(data.top_user_agents[0].downloads).toBe(2); // Chrome
    expect(data.period.start).toBeLessThan(data.period.end);
  });
});

describe('GET /analytics/by-ip', () => {
  beforeEach(async () => {
    await env.DB.prepare('DELETE FROM file_downloads').run();

    for (let i = 0; i < 3; i++) {
      await SELF.fetch('http://localhost/downloads', {
        method: 'POST',
        headers: createAuthHeaders(),
        body: JSON.stringify({
          ...validDownloadInput,
          remote_filename: `file${i}.pdf`,
        }),
      });
    }
  });

  it('returns downloads for IP', async () => {
    const now = Date.now();
    const response = await SELF.fetch(
      `http://localhost/analytics/by-ip?ip=192.168.1.1&start=${now - 86400000}&end=${now + 86400000}`,
      { headers: createAuthHeaders() }
    );
    expect(response.status).toBe(200);
    const data = await response.json() as { downloads: unknown[]; total: number };
    expect(data.total).toBe(3);
    expect(data.downloads.length).toBe(3);
  });

  it('requires ip parameter', async () => {
    const now = Date.now();
    const response = await SELF.fetch(
      `http://localhost/analytics/by-ip?start=${now - 86400000}&end=${now + 86400000}`,
      { headers: createAuthHeaders() }
    );
    expect(response.status).toBe(400);
  });

  it('supports pagination', async () => {
    const now = Date.now();
    const response = await SELF.fetch(
      `http://localhost/analytics/by-ip?ip=192.168.1.1&start=${now - 86400000}&end=${now + 86400000}&limit=2`,
      { headers: createAuthHeaders() }
    );
    const data = await response.json() as { downloads: unknown[]; total: number };
    expect(data.total).toBe(3);
    expect(data.downloads.length).toBe(2);
  });
});

describe('GET /analytics/user-agents', () => {
  beforeEach(async () => {
    await env.DB.prepare('DELETE FROM file_downloads').run();

    const userAgents = ['Chrome/120', 'Chrome/120', 'Safari/17', 'Firefox/121'];
    for (let i = 0; i < userAgents.length; i++) {
      await SELF.fetch('http://localhost/downloads', {
        method: 'POST',
        headers: createAuthHeaders(),
        body: JSON.stringify({
          ...validDownloadInput,
          ip_address: `192.168.1.${i + 1}`,
          user_agent: userAgents[i],
        }),
      });
    }
  });

  it('returns user agent stats', async () => {
    const now = Date.now();
    const response = await SELF.fetch(
      `http://localhost/analytics/user-agents?start=${now - 86400000}&end=${now + 86400000}`,
      { headers: createAuthHeaders() }
    );
    expect(response.status).toBe(200);
    const data = await response.json() as { data: { user_agent: string; downloads: number; unique_ips: number }[] };
    expect(data.data.length).toBe(3);
    expect(data.data[0].user_agent).toBe('Chrome/120');
    expect(data.data[0].downloads).toBe(2);
    expect(data.data[0].unique_ips).toBe(2);
  });
});

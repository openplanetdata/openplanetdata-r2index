import { Context, Hono } from 'hono';
import type { AnalyticsScale, Env } from '../types';
import { getTimeSeries, getSummary, getDownloadsByIp, getUserAgentStats } from '../db/downloads';
import { validationError } from '../errors';
import { analyticsParamsSchema } from '../validation';

const app = new Hono<{ Bindings: Env }>();

function getAnalyticsParams(c: Context) {
  return {
    start: c.req.query('start'),
    end: c.req.query('end'),
    scale: c.req.query('scale'),
    bucket: c.req.query('bucket'),
    remote_path: c.req.query('remote_path'),
    remote_filename: c.req.query('remote_filename'),
    remote_version: c.req.query('remote_version'),
    ip: c.req.query('ip'),
    limit: c.req.query('limit'),
    offset: c.req.query('offset'),
  };
}

function getCacheMaxAge(c: Context<{ Bindings: Env }>): number {
  return parseInt(c.env.CACHE_MAX_AGE || '60', 10);
}

// Get time series data
app.get('/timeseries', async (c) => {
  const params = getAnalyticsParams(c);
  const parsed = analyticsParamsSchema.safeParse(params);

  if (!parsed.success) {
    return c.json(validationError(parsed.error.flatten().fieldErrors), 400);
  }

  const { start, end, scale, bucket, remote_path, remote_filename, remote_version, limit } = parsed.data;
  const filesLimit = Math.min(parseInt(limit || '100', 10), 1000);
  const data = await getTimeSeries(
    c.env.DB,
    parseInt(start, 10),
    parseInt(end, 10),
    (scale || 'day') as AnalyticsScale,
    { bucket, remote_path, remote_filename, remote_version },
    filesLimit
  );

  c.header('Cache-Control', `public, max-age=${getCacheMaxAge(c)}`);
  return c.json({ scale: scale || 'day', data });
});

// Get summary stats
app.get('/summary', async (c) => {
  const params = getAnalyticsParams(c);
  const parsed = analyticsParamsSchema.safeParse(params);

  if (!parsed.success) {
    return c.json(validationError(parsed.error.flatten().fieldErrors), 400);
  }

  const { start, end, bucket, remote_path, remote_filename, remote_version } = parsed.data;
  const summary = await getSummary(
    c.env.DB,
    parseInt(start, 10),
    parseInt(end, 10),
    { bucket, remote_path, remote_filename, remote_version }
  );

  c.header('Cache-Control', `public, max-age=${getCacheMaxAge(c)}`);
  return c.json(summary);
});

// Get downloads by IP
app.get('/by-ip', async (c) => {
  const params = getAnalyticsParams(c);
  const parsed = analyticsParamsSchema.safeParse(params);

  if (!parsed.success) {
    return c.json(validationError(parsed.error.flatten().fieldErrors), 400);
  }

  const { start, end, ip, limit, offset } = parsed.data;

  if (!ip) {
    return c.json(validationError({ ip: ['ip parameter is required'] }), 400);
  }

  const result = await getDownloadsByIp(
    c.env.DB,
    ip,
    parseInt(start, 10),
    parseInt(end, 10),
    Math.min(parseInt(limit || '100', 10), 1000),
    parseInt(offset || '0', 10)
  );

  c.header('Cache-Control', `public, max-age=${getCacheMaxAge(c)}`);
  return c.json(result);
});

// Get user agent stats
app.get('/user-agents', async (c) => {
  const params = getAnalyticsParams(c);
  const parsed = analyticsParamsSchema.safeParse(params);

  if (!parsed.success) {
    return c.json(validationError(parsed.error.flatten().fieldErrors), 400);
  }

  const { start, end, bucket, remote_path, remote_filename, remote_version, limit } = parsed.data;
  const data = await getUserAgentStats(
    c.env.DB,
    parseInt(start, 10),
    parseInt(end, 10),
    { bucket, remote_path, remote_filename, remote_version },
    Math.min(parseInt(limit || '20', 10), 100)
  );

  c.header('Cache-Control', `public, max-age=${getCacheMaxAge(c)}`);
  return c.json({ data });
});

export default app;

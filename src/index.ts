import { Hono } from 'hono';
import { cors } from 'hono/cors';
import type { Env, Variables } from './types';
import { authMiddleware } from './middleware/auth';
import { requestIdMiddleware } from './middleware/request-id';
import filesRoutes from './routes/files';
import downloadsRoutes from './routes/downloads';
import analyticsRoutes from './routes/analytics';
import { cleanupOldDownloads } from './db/downloads';
import { Errors } from './errors';

const app = new Hono<{ Bindings: Env; Variables: Variables }>();

// Global error handler - always return JSON
app.onError((err, c) => {
  const requestId = c.get('requestId');
  console.error(`[${requestId}] Error:`, err);

  if (err.message?.includes('JSON')) {
    return c.json(Errors.INVALID_JSON, 400);
  }
  return c.json(Errors.INTERNAL_ERROR, 500);
});

// 404 handler - always return JSON
app.notFound((c) => {
  return c.json(Errors.NOT_FOUND, 404);
});

// Request ID middleware (first, so all requests get an ID)
app.use('*', requestIdMiddleware);

// CORS configuration
app.use('*', cors({
  origin: '*',
  allowMethods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
  allowHeaders: ['Content-Type', 'Authorization', 'X-Request-ID'],
  exposeHeaders: ['X-Request-ID'],
  maxAge: 86400,
}));

// Health check (no auth required)
app.get('/health', (c) => c.json({ status: 'ok' }));

// Apply auth middleware to all other routes
app.use('/*', authMiddleware);

// Mount routes
app.route('/files', filesRoutes);
app.route('/downloads', downloadsRoutes);
app.route('/analytics', analyticsRoutes);

// Maintenance: cleanup old downloads (respects DOWNLOADS_RETENTION_DAYS, default 365)
app.post('/maintenance/cleanup-downloads', async (c) => {
  const retentionDays = parseInt(c.env.DOWNLOADS_RETENTION_DAYS || '365', 10);

  if (retentionDays <= 0) {
    return c.json({ error: 'DOWNLOADS_RETENTION_DAYS must be positive' }, 400);
  }

  const deleted = await cleanupOldDownloads(c.env.D1, retentionDays);
  return c.json({ deleted, retention_days: retentionDays });
});

export default app;

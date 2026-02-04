import { Hono } from 'hono';
import type { Env } from '../types';
import { createDownload } from '../db/downloads';
import { validationError } from '../errors';
import { createDownloadSchema } from '../validation';

const app = new Hono<{ Bindings: Env }>();

// Record a download
app.post('/', async (c) => {
  const body = await c.req.json();
  const parsed = createDownloadSchema.safeParse(body);

  if (!parsed.success) {
    return c.json(validationError(parsed.error.flatten().fieldErrors), 400);
  }

  const download = await createDownload(c.env.DB, parsed.data);
  return c.json(download, 201);
});

export default app;

import { defineWorkersConfig } from '@cloudflare/vitest-pool-workers/config';

export default defineWorkersConfig({
  test: {
    poolOptions: {
      workers: {
        wrangler: { configPath: './wrangler.toml' },
        miniflare: {
          bindings: {
            API_TOKEN: 'test-token',
            CACHE_MAX_AGE: '60',
          },
        },
      },
    },
  },
});

import { defineConfig, devices } from '@playwright/test';

/**
 * End-to-end tests: the real SPA against the real backend, in a browser.
 *
 * They never touch the dev data. Playwright starts its own backend on :8100 against its
 * own database, `component_repository_e2e`, recreated empty before every run and migrated
 * on startup - next to the dev database in the Compose Postgres. And its own Vite dev
 * server on :5180, pointed at that backend. What they share with development is only
 * infrastructure: `make docker-infra` (Postgres :5433, Mailhog :8025 for the login codes,
 * the format service :8001) has to be running.
 *
 *   npm run e2e            headless
 *   npm run e2e -- --ui    Playwright's UI mode
 */

export const BACKEND_URL = 'http://localhost:8100';
const FRONTEND_URL = 'http://localhost:5180';

export default defineConfig({
  testDir: './e2e',
  testMatch: '**/*.e2e.ts',
  // every test signs up its own users, so they don't see each other's drafts - but they
  // do share one backend, and a single worker keeps its logs readable
  workers: 1,
  timeout: 60_000,
  expect: { timeout: 10_000 },
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: FRONTEND_URL,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: [
    {
      command: 'uv run python -m scripts.recreate_e2e_database && uv run uvicorn app.main:app --port 8100',
      cwd: '../backend-python',
      url: `${BACKEND_URL}/health`,
      // a fresh database every run - never attach to a backend someone else started
      reuseExistingServer: false,
      timeout: 120_000,
      env: {
        DATABASE_NAME: 'component_repository_e2e',
        AUTO_MIGRATE: 'true',
        CORS_ORIGIN: FRONTEND_URL,
        EMAIL_PROVIDER: 'smtp',
        SMTP_HOST: 'localhost',
        SMTP_PORT: '1025',
        // a test logging the same user in twice needn't wait out a minute
        OTP_REQUEST_COOLDOWN: '1',
      },
    },
    {
      command: 'npx vite --port 5180 --strictPort',
      url: FRONTEND_URL,
      reuseExistingServer: false,
      timeout: 60_000,
      env: { VITE_API_BASE_URL: BACKEND_URL },
    },
  ],
});

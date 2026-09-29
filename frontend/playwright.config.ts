import { defineConfig } from "@playwright/test";

const BACKEND_PORT = 8111;
const FRONTEND_PORT = 5177;

// Windows venvs live at .venv\Scripts\, POSIX at .venv/bin/
const PYTHON = process.platform === "win32" ? ".venv\\Scripts\\python.exe" : ".venv/bin/python";

export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  expect: { timeout: 7_000 },
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: `http://127.0.0.1:${FRONTEND_PORT}`,
    trace: "retain-on-failure",
  },
  globalSetup: "./e2e/global-setup.ts",
  globalTeardown: "./e2e/global-teardown.ts",
  webServer: [
    {
      command: `${PYTHON} -m uvicorn app.main:app --port ${BACKEND_PORT} --log-level warning`,
      cwd: "../backend",
      port: BACKEND_PORT,
      // Always start fresh servers: reusing a stale process makes test data
      // nondeterministic. Set SHOPSTOCK_E2E_REUSE=1 to opt back in.
      reuseExistingServer: process.env.SHOPSTOCK_E2E_REUSE === "1",
      timeout: 30_000,
      env: {
        DATABASE_URL: "sqlite:///./e2e.db",
        APP_ENV: "dev",
      },
    },
    {
      command: "npx vite --port 5177 --strictPort --host 127.0.0.1",
      cwd: ".",
      port: FRONTEND_PORT,
      reuseExistingServer: process.env.SHOPSTOCK_E2E_REUSE === "1",
      timeout: 30_000,
      env: {
        BACKEND_URL: `http://127.0.0.1:${BACKEND_PORT}`,
      },
    },
  ],
});

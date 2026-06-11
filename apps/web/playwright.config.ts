import { defineConfig, devices } from "@playwright/test";

const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";
const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:3000";
const pythonExecutable = process.env.PYTHON_EXECUTABLE ?? "python";
const managedServers = process.env.PLAYWRIGHT_MANAGED_SERVERS !== "0";

export default defineConfig({
  testDir: "./e2e",
  timeout: 180_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  reporter: [["list"], ["html", { outputFolder: "../../artefacts/playwright-report", open: "never" }]],
  use: {
    baseURL,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "off",
    actionTimeout: 15_000,
  },
  outputDir: "../../artefacts/playwright-results",
  webServer: managedServers
    ? [
        {
          command: `"${pythonExecutable}" -m uvicorn app.main:app --host 127.0.0.1 --port 8000`,
          cwd: "../api",
          url: `${apiBase}/api/v1/demo/briefing`,
          reuseExistingServer: true,
          timeout: 120_000,
          env: {
            DATABASE_URL: process.env.PLAYWRIGHT_DATABASE_URL ?? "sqlite:///../../markets_strategy_copilot_e2e.db",
          },
        },
        {
          command: `"${process.execPath}" node_modules/next/dist/bin/next start --hostname 127.0.0.1 --port 3000`,
          cwd: ".",
          url: baseURL,
          reuseExistingServer: true,
          timeout: 180_000,
          env: {
            NEXT_PUBLIC_API_BASE_URL: apiBase,
          },
        },
      ]
    : undefined,
  projects: [
    {
      name: "chromium-desktop",
      use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 1000 } },
    },
    {
      name: "chromium-mobile",
      use: { ...devices["Pixel 5"] },
    },
  ],
});

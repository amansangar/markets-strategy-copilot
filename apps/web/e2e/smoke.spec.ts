import { expect, test } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

const screenshotsDir = process.env.MARKETS_SCREENSHOTS_DIR ?? path.resolve(__dirname, "../../../artefacts/screenshots");
const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";
const captureRouteScreenshots = process.env.MARKETS_CAPTURE_SCREENSHOTS === "1";

fs.mkdirSync(screenshotsDir, { recursive: true });

const routes = [
  { path: "/", title: "Market Overview", shot: "dashboard", waitText: "What to look at now" },
  { path: "/demo", title: "Demo Guide", shot: "demo-guide", waitText: "Ready-to-demo" },
  { path: "/pro-terminal", title: "Professional Research Toolkit", shot: "pro-terminal", waitText: "Research Modules" },
  { path: "/quality", title: "Signal Quality", shot: "signal-quality", waitText: "Action distribution" },
  { path: "/governance", title: "Signal Comparison", shot: "governance", waitText: "What changed" },
  { path: "/universe", title: "Universe Builder", shot: "universe", waitText: "Universe presets" },
  { path: "/coverage", title: "Data Coverage", shot: "data-coverage", waitText: "Coverage matrix" },
  { path: "/terminal", title: "Multi-Chart Workspace", shot: "terminal", waitText: "Auto drawings" },
  { path: "/opportunities", title: "Ranked Research Opportunities", shot: "opportunities", waitText: "Methodology" },
  { path: "/asset/SPY", title: "SPY Detail", shot: "asset-detail", waitText: "Market replay" },
  { path: "/scanner", title: "Find Opportunities", shot: "scanner", waitText: "Why" },
  { path: "/strategy-builder", title: "Pine-Lite Strategy Lab", shot: "strategy-builder", waitText: "Evaluation" },
  { path: "/strategy-tester", title: "Strategy Tester", shot: "strategy-tester", waitText: "Run backtest" },
  { path: "/strategy-matrix", title: "Strategy Matrix", shot: "strategy-matrix", waitText: "Best current preset" },
  { path: "/replay-lab", title: "Replay Lab", shot: "replay-lab", waitText: "Signal timeline" },
  { path: "/assistant", title: "Ask for a market brief", shot: "research-assistant", waitText: "What do you want to understand" },
  { path: "/tear-sheet", title: "Fundamental Tear Sheet", shot: "tear-sheet", waitText: "Macro sensitivity" },
  { path: "/events", title: "Economic, Earnings, News and Filing Calendar", shot: "events-calendar", waitText: "FRED" },
  { path: "/alerts", title: "Alerts", shot: "alerts", waitText: "Delivery channels" },
  { path: "/alert-builder", title: "Advanced Alert Builder", shot: "alert-builder", waitText: "Templates" },
  { path: "/reports", title: "Reports", shot: "reports", waitText: "Recent exports" },
  { path: "/settings", title: "Settings", shot: "settings-provider-status", waitText: "Provider configuration" },
  { path: "/portfolio", title: "Portfolio", shot: "portfolio", waitText: "paper" },
  { path: "/workspace", title: "Research Workspace", shot: "workspace", waitText: "Saved watchlists" },
  { path: "/setup", title: "Setup Guide", shot: "setup-guide", waitText: "First-run tutorial" },
];

test.describe("Markets Strategy Copilot route smoke", () => {
  test.describe.configure({ mode: "parallel" });

  for (const route of routes) {
    test(`${route.path} renders without fatal errors`, async ({ page }, testInfo) => {
      const consoleErrors: string[] = [];
      const networkErrors: string[] = [];
      page.on("console", (message) => {
        if (message.type() === "error") {
          consoleErrors.push(message.text());
        }
      });
      page.on("response", (response) => {
        if (response.status() >= 500) {
          networkErrors.push(`${response.status()} ${response.url()}`);
        }
      });

      await page.goto(route.path);
      await expect(page.getByRole("heading", { name: route.title, exact: false })).toBeVisible({ timeout: 45_000 });
      await expect(page.locator("main")).toContainText(/[A-Za-z]{4,}/, { timeout: 45_000 });
      if (captureRouteScreenshots) {
        await page.screenshot({ path: `${screenshotsDir}/${route.shot}-${testInfo.project.name}.png`, fullPage: true, timeout: 60_000 });
      }
      if (route.path === "/") {
        const dashboardMain = page.locator("main");
        await expect(dashboardMain.getByText("What to look at now")).toBeVisible({ timeout: 30_000 });
        await expect(dashboardMain.getByText("Price chart")).toBeVisible({ timeout: 30_000 });
        await expect(dashboardMain.getByText(/Signal:/i).first()).toBeVisible({ timeout: 30_000 });
        await expect(dashboardMain.getByText("Open research")).toBeVisible({ timeout: 30_000 });
        await dashboardMain.getByRole("button", { name: "Indicators" }).click();
        await expect(dashboardMain.getByText("rsi", { exact: true }).first()).toBeVisible({ timeout: 30_000 });
        await dashboardMain.getByRole("button", { name: "Backtest" }).click();
        await expect(dashboardMain.getByText(/total|not precomputed|Run Strategy Tester/i).first()).toBeVisible({ timeout: 30_000 });
        await dashboardMain.getByRole("button", { name: "Live data" }).click();
        await expect(dashboardMain.getByText("What to look at now")).toBeVisible({ timeout: 30_000 });
        await expect(dashboardMain.getByRole("button", { name: "Live data" })).toBeVisible({ timeout: 30_000 });
        await dashboardMain.getByRole("button", { name: "Demo data" }).click();
        const firstAssetLink = dashboardMain.locator('a[href^="/asset/"]').first();
        await expect(firstAssetLink).toBeVisible({ timeout: 30_000 });
      }
      if (route.path === "/portfolio") {
        await expect(page.getByText("Portfolio risk heatmap")).toBeVisible({ timeout: 30_000 });
      }
      if (route.path === "/settings") {
        await expect(page.getByText("Live data")).toBeVisible({ timeout: 30_000 });
        await expect(page.getByText("Provider configuration")).toBeVisible({ timeout: 30_000 });
      }

      expect(networkErrors, "No fatal 5xx network errors").toEqual([]);
      expect(consoleErrors.filter((item) => !item.includes("favicon")), "No fatal console errors").toEqual([]);
    });
  }
});

test.describe("Core interactions", () => {
  test("dashboard market selection updates the active chart context", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByText(/Showing .* on the chart/i).first()).toBeVisible({ timeout: 45_000 });
    await page.getByRole("button", { name: /Select AAPL/i }).first().click();
    await expect(page.getByText("Showing AAPL on the chart")).toBeVisible({ timeout: 45_000 });
    await page.getByRole("button", { name: /Select BTCUSD/i }).first().click();
    await expect(page.getByText("Showing BTCUSD on the chart")).toBeVisible({ timeout: 45_000 });
  });

  test("asset replay and filing panels render", async ({ page }) => {
    await page.goto("/asset/SPY");
    await expect(page.getByText("Market replay", { exact: false })).toBeVisible({ timeout: 75_000 });
    await page.locator("main").getByRole("button", { name: "Demo" }).click();
    await expect(page.getByText("Breakout watch")).toBeVisible({ timeout: 75_000 });
    await page.getByLabel("Replay scenario: Risk-off check").dispatchEvent("click");
    await page.getByLabel("Replay cursor").press("ArrowRight");
    await expect(page.getByText("SEC filings", { exact: false })).toBeVisible({ timeout: 75_000 });
  });

  test("command palette opens and navigates", async ({ page }) => {
    await page.goto("/");
    await page.keyboard.press("Control+K");
    await expect(page.getByPlaceholder("Search screens, symbols, reports, alerts...")).toBeVisible();
    await page.getByPlaceholder("Search screens, symbols, reports, alerts...").fill("portfolio");
    await Promise.all([
      page.waitForURL(/\/portfolio/),
      page.locator('a[href="/portfolio"]').filter({ hasText: "/portfolio" }).click(),
    ]);
    await expect(page.getByRole("heading", { name: /Portfolio/i })).toBeVisible();
  });

  test("live mode persists or visibly falls back across main routes", async ({ page }) => {
    await page.goto("/");
    await page.locator("main").getByRole("button", { name: "Live data" }).click();
    await expect(page.getByText("What to look at now")).toBeVisible({ timeout: 90_000 });
    await page.goto("/scanner");
    await expect(page.locator("main").getByRole("button", { name: "Live data" })).toBeVisible();
    await page.goto("/asset/SPY");
    await expect(page.locator("main").getByRole("button", { name: "Live" })).toBeVisible();
  });

  test("live API failure falls back to demo mode", async ({ page }) => {
    await page.route("**/api/v1/dashboard**", async (route) => {
      if (route.request().url().includes("mode=live")) {
        await route.fulfill({
          status: 503,
          contentType: "application/json",
          body: JSON.stringify({ detail: "simulated provider outage" }),
        });
        return;
      }
      await route.continue();
    });

    await page.goto("/");
    await page.locator("main").getByRole("button", { name: "Demo data" }).click();
    await page.locator("main").getByRole("button", { name: "Live data" }).click();
    await expect(page.getByText(/Live data unavailable|Live fallback active|Live data degraded/)).toBeVisible({ timeout: 30_000 });
    await expect(page.locator("main").getByRole("button", { name: "Demo data" })).toBeVisible();
    await expect(page.getByText("What to look at now")).toBeVisible({ timeout: 60_000 });
  });

  test("scanner filters and strategy tester run path work", async ({ page }) => {
    await page.goto("/scanner");
    if ((page.viewportSize()?.width ?? 0) < 700) {
      await expect(page.locator("main").getByText(/why matched|confidence|regime/i).first()).toBeVisible({ timeout: 30_000 });
    } else {
      await expect(page.getByRole("columnheader", { name: "Why" })).toBeVisible();
    }
    const firstAssetLink = page.locator('main a[href^="/asset/"]:visible').first();
    await expect(firstAssetLink).toBeVisible({ timeout: 120_000 });
    await Promise.all([
      page.waitForURL(/\/asset\//),
      firstAssetLink.click({ noWaitAfter: true }),
    ]);
    await expect(page.getByText("Market replay", { exact: false })).toBeVisible({ timeout: 75_000 });
    await page.goto("/strategy-tester");
    const runButton = page.getByRole("button", { name: /run backtest/i });
    if (await runButton.isEnabled().catch(() => false)) {
      await runButton.click();
    }
    await expect(page.getByText(/sharpe/i).first()).toBeVisible({ timeout: 75_000 });
    await expect(page.getByText("Backtest robustness")).toBeVisible({ timeout: 75_000 });
  });

  test("alerts can toggle and report export button works", async ({ page }) => {
    await page.goto("/alerts");
    const alertToggle = page.getByRole("button", { name: /enable alert|disable alert/i }).first();
    if (await alertToggle.isVisible().catch(() => false)) {
      await alertToggle.click();
    }
    await expect(page.getByText("Delivery log").first()).toBeVisible({ timeout: 30_000 });
    await page.goto("/reports");
    await page.getByRole("button", { name: /export/i }).click();
    await expect(page.getByText("Latest export", { exact: false })).toBeVisible({ timeout: 75_000 });
  });

  test("strategy builder and multi-chart terminal support core interactions", async ({ page }) => {
    await page.goto("/strategy-builder");
    await expect(page.getByRole("heading", { name: /Pine-Lite Strategy Lab/i })).toBeVisible({ timeout: 75_000 });
    await page.getByRole("button", { name: /Evaluate rule/i }).click();
    await expect(page.getByText(/rule fit/i)).toBeVisible({ timeout: 30_000 });

    await page.goto("/terminal");
    await expect(page.getByRole("heading", { name: /Multi-Chart Workspace/i })).toBeVisible({ timeout: 75_000 });
    await page.getByRole("button", { name: "BTCUSD" }).click();
    await expect(page.getByText(/Correlation watch/i)).toBeVisible({ timeout: 30_000 });
  });

  test("replay lab, opportunity ranking, and alert builder support core interactions", async ({ page }) => {
    await page.goto("/replay-lab");
    await page.getByRole("slider").press("ArrowRight");
    await expect(page.getByText(/no lookahead/i).first()).toBeVisible({ timeout: 30_000 });

    await page.goto("/opportunities");
    await expect(page.getByText("Methodology")).toBeVisible({ timeout: 75_000 });
    await page.getByRole("button", { name: "volumeRatio" }).click();
    await expect(page.getByRole("columnheader", { name: "volumeRatio" })).toBeVisible({ timeout: 30_000 });

    await page.goto("/alert-builder");
    await page.getByRole("button", { name: /Provider outage/i }).click();
    await expect(page.getByText(/Provider Status|provider\.status/i)).toBeVisible({ timeout: 30_000 });
  });

  test("professional research toolkit supports category filtering", async ({ page }) => {
    await page.goto("/pro-terminal");
    await expect(page.getByText("Professional Research Toolkit")).toBeVisible({ timeout: 75_000 });
    await page.getByRole("button", { name: /risk/i }).click();
    await expect(page.getByText(/Risk Navigator/i).first()).toBeVisible({ timeout: 30_000 });
  });
});

test.describe("Live provider smoke", () => {
  test.skip(process.env.MARKETS_TEST_MODE !== "live", "Run with MARKETS_TEST_MODE=live through smoke:live.");

  test("provider health endpoint returns non-secret integration statuses", async ({ request }) => {
    const response = await request.get(`${apiBase}/api/v1/providers/checks`);
    expect(response.ok()).toBeTruthy();
    const payload = await response.json();
    expect(payload).toHaveProperty("checks");
    expect(JSON.stringify(payload)).not.toContain("sk-");
    expect(JSON.stringify(payload)).not.toContain("Bearer ");
  });

  test("settings provider diagnostics button renders safe statuses", async ({ page }) => {
    await page.goto("/settings");
    await page.getByRole("button", { name: /check connections/i }).click();
    await expect(page.getByText(/healthy:/i).first()).toBeVisible({ timeout: 45_000 });
    await expect(page.getByText(/configured|not configured/i).first()).toBeVisible();
  });
});

import { chromium } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

const repoRoot = path.resolve(process.cwd(), "..", "..");
const timestamp = new Date().toISOString().replace(/[-:]/g, "").replace(/\..+/, "").replace("T", "-");
const outputDir = path.join(repoRoot, "artefacts", "screenshots", `final-current-fullpages-${timestamp}`);
const baseUrl = process.env.FRONTEND_URL ?? "http://127.0.0.1:3000";

const forbiddenPhrases = [
  "temporarily unavailable",
  "request failed",
  "could not be loaded",
  "API request timed out",
  "Running",
  "Loading",
  "Opening",
  "Preparing",
  "Calculating",
  "Building",
  "fallback rows could not be loaded",
];

const routes = [
  { name: "dashboard", path: "/", success: /Watchlist|Price chart|Current view/i },
  { name: "asset-spy", path: "/asset/SPY", success: /News timeline|Audit trail|Market replay/i },
  { name: "scanner", path: "/scanner", success: /Why matched|confidence|Scanner/i },
  { name: "strategy-tester", path: "/strategy-tester", success: /Sharpe|Total return|Walk-forward|Trade list/i, action: "runBacktest" },
  { name: "alerts", path: "/alerts", success: /Delivery log|Alert|enabled/i },
  { name: "reports", path: "/reports", success: /Recent exports|Investment note|Export/i },
  { name: "settings", path: "/settings", success: /Provider configuration|Provider health|Check live connections/i },
  { name: "portfolio", path: "/portfolio", success: /Open positions|Portfolio|P&L/i },
  { name: "workspace", path: "/workspace", success: /Saved watchlists|Saved scanners|Symbol notes/i },
  { name: "assistant", path: "/assistant?symbol=SPY", success: /Ask for a market brief|Ask AI Copilot/i },
  { name: "demo", path: "/demo", success: /Demo|walkthrough|readiness/i },
  { name: "setup", path: "/setup", success: /Setup|beginner|Start/i },
  { name: "quality", path: "/quality", success: /Signal quality|Audit|coverage/i },
  { name: "governance", path: "/governance", success: /Governance|Policy|model/i },
  { name: "coverage", path: "/coverage", success: /Coverage|Data|universe/i },
  { name: "universe", path: "/universe", success: /Universe|Watchlist|assets/i },
  { name: "terminal", path: "/terminal", success: /Terminal|Chart|workspace/i },
  { name: "opportunities", path: "/opportunities", success: /Methodology|volumeRatio|whyMatched|STRONG_BUY_WATCH/i },
  { name: "strategy-builder", path: "/strategy-builder", success: /Strategy Builder|Rule|strategy/i },
  { name: "strategy-matrix", path: "/strategy-matrix", success: /Strategy Matrix|preset|robustness/i },
  { name: "replay-lab", path: "/replay-lab", success: /Replay|cursor|timeline/i },
  { name: "tear-sheet", path: "/tear-sheet", success: /Tear Sheet|profile|macro/i },
  { name: "events", path: "/events", success: /Events|calendar|filing/i },
  { name: "alert-builder", path: "/alert-builder", success: /Alert Builder|template|cooldown/i },
  { name: "pro-terminal", path: "/pro-terminal", success: /Professional Research Toolkit|Research Modules/i },
];

const viewports = [
  { suffix: "desktop", width: 1440, height: 1200 },
  { suffix: "mobile", width: 390, height: 1000 },
];

function assertNoForbidden(text, label) {
  const lower = text.toLowerCase();
  const found = forbiddenPhrases.find((phrase) => lower.includes(phrase.toLowerCase()));
  if (found) {
    throw new Error(`${label} still contains forbidden final-screenshot text: ${found}`);
  }
}

async function waitForSuccess(page, route) {
  await page.waitForLoadState("domcontentloaded");
  await page.waitForTimeout(1200);
  if (route.action === "runBacktest") {
    const metricsAlreadyVisible = await page.getByText(/Total return/i).first().isVisible().catch(() => false);
    const button = page.getByRole("button", { name: /run backtest/i });
    const canRun =
      !metricsAlreadyVisible &&
      (await button.isVisible().catch(() => false)) &&
      (await button.isEnabled().catch(() => false));
    if (canRun) {
      await button.click();
    }
    await page.waitForFunction(() => !document.body.innerText.includes("Running..."), null, { timeout: 45000 });
  }
  await page.waitForFunction(
    (patternSource) => new RegExp(patternSource, "i").test(document.body.innerText),
    route.success.source,
    { timeout: 30000 },
  );
  await page.waitForTimeout(900);
}

fs.mkdirSync(outputDir, { recursive: true });

const browser = await chromium.launch({ headless: true });
const manifest = [];
const failures = [];

for (const viewport of viewports) {
  const context = await browser.newContext({
    viewport: { width: viewport.width, height: viewport.height },
    deviceScaleFactor: viewport.suffix === "mobile" ? 2 : 1,
    colorScheme: "dark",
    reducedMotion: "reduce",
  });
  await context.addInitScript(() => {
    window.sessionStorage.setItem("markets-strategy-copilot:mode:v2", "demo");
  });
  const page = await context.newPage();

  for (const route of routes) {
    const url = new URL(route.path, baseUrl);
    url.searchParams.set("final-screenshot", timestamp);
    const label = `${route.name}-${viewport.suffix}`;
    try {
      await page.goto(url.toString(), { waitUntil: "domcontentloaded", timeout: 45000 });
      await waitForSuccess(page, route);
      const text = await page.locator("body").innerText({ timeout: 10000 });
      assertNoForbidden(text, label);
      const file = `${label}.jpg`;
      const fullPath = path.join(outputDir, file);
      await page.screenshot({ path: fullPath, fullPage: true, type: "jpeg", quality: 82 });
      manifest.push({ route: route.path, viewport: viewport.suffix, file });
    } catch (error) {
      failures.push({ route: route.path, viewport: viewport.suffix, error: String(error?.message ?? error) });
    }
  }

  await context.close();
}

await browser.close();

fs.writeFileSync(path.join(outputDir, "manifest.json"), JSON.stringify({ generatedAt: new Date().toISOString(), baseUrl, screenshots: manifest, failures }, null, 2));
fs.writeFileSync(path.join(repoRoot, "artefacts", "screenshot-validation.json"), JSON.stringify({ generatedAt: new Date().toISOString(), outputDir, screenshotCount: manifest.length, failures }, null, 2));

if (failures.length) {
  console.error(JSON.stringify(failures, null, 2));
  process.exit(1);
}

console.log(outputDir);

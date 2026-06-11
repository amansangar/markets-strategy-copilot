const fs = require("node:fs");
const path = require("node:path");
const { chromium } = require("../apps/web/node_modules/playwright");

const baseUrl = process.env.MARKETS_BASE_URL || "http://127.0.0.1:3000";
const outputName = process.env.MARKETS_INTERACTION_SCREENSHOT_DIR || "exhaustive-ui-clicks-20260503";
const outDir = path.resolve(__dirname, "../artefacts/screenshots", outputName);
const manifest = [];
const requestedRoutes = (process.env.MARKETS_CAPTURE_ROUTES || "")
  .split(",")
  .map((item) => item.trim())
  .filter(Boolean);

const routes = [
  { path: "/", name: "dashboard", waitText: "What to look at now" },
  { path: "/asset/SPY", name: "asset-spy", waitText: "Market replay" },
  { path: "/scanner", name: "scanner", waitText: "Why" },
  { path: "/strategy-tester", name: "strategy-tester", waitText: "Run backtest" },
  { path: "/alerts", name: "alerts", waitText: "Delivery channels" },
  { path: "/reports", name: "reports", waitText: "Recent exports" },
  { path: "/settings", name: "settings", waitText: "Connected services" },
  { path: "/portfolio", name: "portfolio", waitText: "paper" },
  { path: "/workspace", name: "workspace", waitText: "Saved watchlists" },
  { path: "/assistant", name: "assistant", waitText: "What do you want to understand" },
  { path: "/demo", name: "demo-guide", waitText: "Ready-to-demo" },
  { path: "/setup", name: "setup-guide", waitText: "First-run tutorial" },
  { path: "/terminal", name: "terminal", waitText: "Auto drawings" },
  { path: "/opportunities", name: "opportunities", waitText: "Methodology" },
  { path: "/strategy-builder", name: "strategy-builder", waitText: "Evaluation" },
  { path: "/strategy-matrix", name: "strategy-matrix", waitText: "Best current preset" },
  { path: "/replay-lab", name: "replay-lab", waitText: "Signal timeline" },
  { path: "/tear-sheet", name: "tear-sheet", waitText: "Macro sensitivity" },
  { path: "/events", name: "events", waitText: "FRED" },
  { path: "/alert-builder", name: "alert-builder", waitText: "Templates" },
  { path: "/pro-terminal", name: "pro-terminal", waitText: "All 75 Feature Modules" },
  { path: "/quality", name: "signal-quality", waitText: "Action distribution" },
  { path: "/governance", name: "governance", waitText: "What changed" },
  { path: "/coverage", name: "data-coverage", waitText: "Coverage matrix" },
  { path: "/universe", name: "universe", waitText: "Universe presets" },
];

const unsafeText = [
  "delete",
  "remove",
  "send email",
  "email report",
  "sign in",
  "sign out",
  "log in",
  "logout",
  "open clerk",
  "external",
];

if (process.env.MARKETS_CAPTURE_APPEND !== "1") {
  fs.rmSync(outDir, { recursive: true, force: true });
}
fs.mkdirSync(outDir, { recursive: true });

function slugify(value) {
  const slug = String(value || "control")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 70);
  return slug || "control";
}

async function waitForApp(page, route) {
  await page.goto(`${baseUrl}${route.path}`, { waitUntil: "domcontentloaded", timeout: 120_000 });
  if (route.path === "/setup") {
    await page.evaluate(() => {
      window.localStorage.removeItem("markets-strategy-copilot:first-run-tutorial-dismissed");
    }).catch(() => {});
    await page.reload({ waitUntil: "domcontentloaded", timeout: 120_000 }).catch(() => {});
  }
  if (route.waitText) {
    await page.getByText(route.waitText, { exact: false }).first().waitFor({ state: "visible", timeout: 120_000 }).catch(() => {});
  }
  if (route.path === "/universe") {
    await page.getByRole("button", { name: /All \(/ }).click({ timeout: 5_000 }).catch(() => {});
  }
  await page.waitForLoadState("domcontentloaded", { timeout: 30_000 }).catch(() => {});
  await page.waitForTimeout(650);
}

async function screenshot(page, file) {
  const target = path.join(outDir, file);
  await page.screenshot({ path: target, fullPage: true, timeout: 90_000 });
}

async function visibleControls(page) {
  return page.evaluate(() => {
    function isVisible(element) {
      const style = window.getComputedStyle(element);
      const rect = element.getBoundingClientRect();
      return (
        style &&
        style.visibility !== "hidden" &&
        style.display !== "none" &&
        rect.width > 2 &&
        rect.height > 2
      );
    }

    function textFor(element) {
      const aria = element.getAttribute("aria-label");
      const title = element.getAttribute("title");
      const placeholder = element.getAttribute("placeholder");
      const value = element.value;
      const text = element.innerText || element.textContent || "";
      return (aria || title || placeholder || text || value || element.tagName).trim().replace(/\s+/g, " ");
    }

    const selectors = [
      "button",
      '[role="button"]',
      '[role="tab"]',
      '[role="switch"]',
      '[role="slider"]',
      "select",
      "input:not([type='hidden'])",
      "textarea",
      "summary",
    ];

    const nodes = [];
    const seen = new Set();
    for (const selector of selectors) {
      document.querySelectorAll(selector).forEach((element) => {
        if (!(element instanceof HTMLElement) || seen.has(element) || !isVisible(element)) {
          return;
        }
        seen.add(element);
        nodes.push({
          selector,
          tag: element.tagName.toLowerCase(),
          role: element.getAttribute("role") || "",
          type: element.getAttribute("type") || "",
          text: textFor(element),
          disabled: Boolean(element.disabled || element.getAttribute("aria-disabled") === "true"),
        });
      });
    }
    return nodes;
  });
}

async function interact(page, controlIndex, control) {
  const locator = page.locator(control.selector).nth(controlIndex);
  await locator.scrollIntoViewIfNeeded({ timeout: 10_000 }).catch(() => {});

  if (control.tag === "input" || control.tag === "textarea") {
    const type = String(control.type || "").toLowerCase();
    if (type === "range") {
      await locator.press("ArrowRight", { timeout: 10_000 });
      return "moved range slider";
    }
    if (["checkbox", "radio"].includes(type) || control.role === "switch") {
      await locator.click({ timeout: 10_000 });
      return "clicked toggle input";
    }
    const value = type === "number" || control.role === "slider" ? "75" : "SPY";
    await locator.fill(value, { timeout: 10_000 });
    return `filled ${value}`;
  }

  if (control.tag === "select") {
    const options = await locator.locator("option").evaluateAll((items) => items.map((item) => item.value).filter(Boolean)).catch(() => []);
    if (options.length > 1) {
      await locator.selectOption(options[1], { timeout: 10_000 });
      return `selected ${options[1]}`;
    }
    await locator.click({ timeout: 10_000 });
    return "opened select";
  }

  if (control.role === "slider") {
    await locator.press("ArrowRight", { timeout: 10_000 });
    return "moved slider";
  }

  await locator.click({ timeout: 12_000 });
  return "clicked";
}

async function main() {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1440, height: 950 }, deviceScaleFactor: 1 });

  const selectedRoutes = requestedRoutes.length
    ? routes.filter((route) => requestedRoutes.includes(route.name) || requestedRoutes.includes(route.path))
    : routes;

  for (const route of selectedRoutes) {
    await waitForApp(page, route);
    const controls = await visibleControls(page);
    const selectorOffsets = {};
    const routeEntries = [];

    for (let index = 0; index < controls.length; index += 1) {
      const control = controls[index];
      const selectorIndex = selectorOffsets[control.selector] || 0;
      selectorOffsets[control.selector] = selectorIndex + 1;
      const label = control.text || `${control.tag} ${selectorIndex + 1}`;
      const lowered = label.toLowerCase();
      const safe = !control.disabled && !unsafeText.some((term) => lowered.includes(term));
      const base = `${route.name}-${String(index + 1).padStart(3, "0")}-${slugify(label)}`;
      const before = `${base}-before.png`;
      const after = `${base}-after.png`;

      await waitForApp(page, route);
      await screenshot(page, before);

      let status = "skipped";
      let note = "";
      if (!safe) {
        note = control.disabled ? "disabled control" : "skipped by safety policy";
        await screenshot(page, after);
      } else {
        try {
          const currentCount = await page.locator(control.selector).count();
          if (selectorIndex >= currentCount) {
            throw new Error(`control index ${selectorIndex} no longer exists for ${control.selector}`);
          }
          note = await interact(page, selectorIndex, control);
          await page.waitForLoadState("domcontentloaded", { timeout: 12_000 }).catch(() => {});
          await page.waitForTimeout(500);
          await screenshot(page, after);
          status = "captured";
        } catch (error) {
          note = error.message.split("\n")[0];
          await screenshot(page, after).catch(() => {});
          status = "failed";
        }
      }

      const entry = {
        route: route.path,
        routeName: route.name,
        controlNumber: index + 1,
        selector: control.selector,
        selectorIndex,
        tag: control.tag,
        role: control.role,
        label,
        status,
        note,
        before,
        after,
      };
      manifest.push(entry);
      routeEntries.push(entry);
      fs.writeFileSync(path.join(outDir, "manifest.json"), `${JSON.stringify(manifest, null, 2)}\n`);
      fs.writeFileSync(path.join(outDir, `${route.name}-manifest.json`), `${JSON.stringify(routeEntries, null, 2)}\n`);
      console.log(`${route.name} ${index + 1}/${controls.length}: ${status} ${label}`);
    }

    const routeManifest = path.join(outDir, `${route.name}-manifest.json`);
    fs.writeFileSync(routeManifest, `${JSON.stringify(routeEntries, null, 2)}\n`);
  }

  await browser.close();
  fs.writeFileSync(path.join(outDir, "manifest.json"), `${JSON.stringify(manifest, null, 2)}\n`);

  const summary = manifest.reduce(
    (acc, item) => {
      acc.total += 1;
      acc[item.status] = (acc[item.status] || 0) + 1;
      return acc;
    },
    { total: 0 },
  );
  fs.writeFileSync(path.join(outDir, "summary.json"), `${JSON.stringify(summary, null, 2)}\n`);
  console.log(JSON.stringify(summary, null, 2));
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});

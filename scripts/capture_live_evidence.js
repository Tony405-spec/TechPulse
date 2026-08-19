const { chromium } = require("playwright");
const path = require("path");

const root = process.cwd();
const screenshotPath = (...parts) => path.join(root, "assets", "screenshots", ...parts);

async function waitForApp(page) {
  await page.waitForLoadState("domcontentloaded").catch(() => {});
  await page.waitForFunction(
    () => document.body && document.body.innerText.includes("TECHPULSE"),
    null,
    { timeout: 60000 },
  );
  await page.waitForTimeout(2500);
}

async function clickText(page, text) {
  const exact = page.getByText(text, { exact: true }).first();
  if (await exact.count()) {
    await exact.click();
  } else {
    await page.getByText(text).first().click();
  }
  await waitForApp(page);
}

async function capture(page, filename) {
  await page.waitForTimeout(800);
  await page.screenshot({ path: screenshotPath(filename), fullPage: true });
  console.log(`captured ${filename}`);
}

(async () => {
  const baseUrl = process.env.TECHPULSE_URL || "http://127.0.0.1:8501/";
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({
    viewport: { width: 1440, height: 1150 },
    deviceScaleFactor: 1,
  });
  page.setDefaultTimeout(45000);
  page.on("pageerror", (error) => console.log("pageerror:", error.message));
  page.on("requestfailed", (request) => {
    console.log("requestfailed:", request.url(), request.failure()?.errorText);
  });

  await page.goto(baseUrl, { waitUntil: "commit", timeout: 60000 });
  await waitForApp(page);
  await capture(page, "01-command-center-overview.png");

  const search = page.getByPlaceholder("Search or filter by technology name").first();
  if (await search.count()) {
    await search.fill("amazon");
    await page.keyboard.press("Enter");
    await waitForApp(page);
  }
  await capture(page, "02-technology-search-amazon.png");

  await clickText(page, "Global Rankings");
  await capture(page, "03-global-rankings.png");

  await clickText(page, "Model Laboratory");
  await capture(page, "04-model-laboratory.png");

  await clickText(page, "About / Methodology");
  await capture(page, "05-about-methodology.png");

  await browser.close();
})();

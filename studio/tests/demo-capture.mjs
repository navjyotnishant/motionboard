// Capture the screens used in the README walkthrough and the overview video from a running Studio.
// Usage: node tests/demo-capture.mjs <outdir> <projectId> [shot]   Reads the token from $MB_HOME/studio.token.
import { chromium } from "@playwright/test";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const out = process.argv[2] || "/tmp/studio-demo";
const pid = process.argv[3];
const shot = process.argv[4] || "2";
const home = process.env.MB_HOME || path.join(os.homedir(), ".motionboard");
const token = fs.readFileSync(path.join(home, "studio.token"), "utf8").trim();
const base = `http://127.0.0.1:${process.env.PORT || 4317}`;
fs.mkdirSync(out, { recursive: true });

const browser = await chromium.launch({ channel: "chrome", headless: true });
const page = await browser.newPage({ viewport: { width: 1600, height: 900 }, deviceScaleFactor: 1.5 });
const snap = (name) => page.screenshot({ path: `${out}/${name}.png` });
await page.goto(`${base}/?session=${token}`);
await page.waitForTimeout(1500);
await snap("11-studio-projects");
await page.goto(`${base}/p/${pid}`);
await page.waitForTimeout(3500);
await snap("12-studio-board-clips");
await page.keyboard.press("s");
await page.waitForTimeout(1200);
await snap("13-studio-story-clips");
await page.keyboard.press("s");
await page.waitForTimeout(600);
const card = page.locator(`[data-shot='${shot}']`);
await card.scrollIntoViewIfNeeded();
await card.dblclick();
await page.waitForTimeout(2500);
await snap("14-studio-shot-takes");
await page.keyboard.press("Escape");
await page.waitForTimeout(400);
await page.keyboard.press("q");
await page.waitForTimeout(2500);
await snap("15-studio-queue");
console.log("captured");
await browser.close();

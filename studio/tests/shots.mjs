// Screenshot the running Studio with the installed Chrome (no browser download).
// Usage: node tests/shots.mjs <outdir> [projectId]   Reads the token from $MB_HOME/studio.token.
import { chromium } from "@playwright/test";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const out = process.argv[2] || "/tmp/studio-shots";
const pid = process.argv[3];
const home = process.env.MB_HOME || path.join(os.homedir(), ".motionboard");
const token = fs.readFileSync(path.join(home, "studio.token"), "utf8").trim();
const base = `http://127.0.0.1:${process.env.PORT || 4317}`;
fs.mkdirSync(out, { recursive: true });

const browser = await chromium.launch({ channel: "chrome", headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const errors = [];
page.on("pageerror", (e) => errors.push(String(e)));
page.on("console", (m) => { if (m.type() === "error") errors.push(m.text()); });
await page.goto(`${base}/?session=${token}`);
await page.waitForTimeout(1200);
await page.screenshot({ path: `${out}/bin.png` });
if (pid) {
  await page.goto(`${base}/p/${pid}`);
  await page.waitForTimeout(2000);
  await page.screenshot({ path: `${out}/board.png` });
  await page.keyboard.press("s");
  await page.waitForTimeout(600);
  await page.screenshot({ path: `${out}/story.png` });
  await page.keyboard.press("s");
  await page.waitForTimeout(400);
  await page.locator("[data-shot='2']").dblclick();
  await page.waitForTimeout(1200);
  await page.screenshot({ path: `${out}/panel.png` });
  await page.keyboard.press("q");
  await page.waitForTimeout(2500);
  await page.screenshot({ path: `${out}/queue.png` });
}
console.log(JSON.stringify({ errors }));
await browser.close();

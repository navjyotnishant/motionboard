// Check per-shot play: the song plays only that shot's slice, stops at the cut, and the clip runs in step.
// Usage: node tests/shot-play-check.mjs <projectId> [shotOrd]
import { chromium } from "@playwright/test";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const pid = process.argv[2];
const ord = process.argv[3] || "1";
const home = process.env.MB_HOME || path.join(os.homedir(), ".motionboard");
const token = fs.readFileSync(path.join(home, "studio.token"), "utf8").trim();
const base = `http://127.0.0.1:${process.env.PORT || 4317}`;
const browser = await chromium.launch({ channel: "chrome", headless: true, args: ["--autoplay-policy=no-user-gesture-required"] });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const errors = [];
page.on("pageerror", (e) => errors.push(String(e)));
await page.goto(`${base}/?session=${token}`);
await page.goto(`${base}/p/${pid}`);
await page.waitForSelector(`[data-shot='${ord}']`);
const card = page.locator(`[data-shot='${ord}']`);
await card.getByRole("button", { name: "Play shot" }).click();
await page.waitForTimeout(1200);
const mid = await page.evaluate((o) => {
  const a = document.querySelector("audio");
  const v = document.querySelector(`[data-shot='${o}'] video`);
  return { audio: a.currentTime, paused: a.paused, video: v ? { t: v.currentTime, paused: v.paused } : null };
}, ord);
await page.waitForTimeout(4500);
const end = await page.evaluate(() => { const a = document.querySelector("audio"); return { audio: a.currentTime, paused: a.paused }; });
console.log(JSON.stringify({ mid, end, errors }));
await browser.close();

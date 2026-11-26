// Check a clip take previews with the song in sync. Usage: node tests/take-check.mjs <projectId> <shotOrd> <takeNumber>
import { chromium } from "@playwright/test";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const [pid, ord = "6", take = "1"] = process.argv.slice(2);
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
await page.locator(`[data-shot='${ord}']`).dblclick();
await page.getByTitle(new RegExp(`^Take ${take} `)).click();
await page.waitForTimeout(1500);
const r = await page.evaluate(() => {
  const box = document.querySelector("video[controls]")?.parentElement;
  const v = box?.querySelector("video"), a = box?.querySelector("audio");
  return v && a ? { video: v.currentTime, audio: a.currentTime, vPaused: v.paused, aPaused: a.paused,
    button: box.parentElement?.innerText.match(/Use this take|In use/)?.[0] } : null;
});
await page.screenshot({ path: "/tmp/take-check.png" });
console.log(JSON.stringify({ r, errors }));
await browser.close();

// Check the board's Play button plays the song. Usage: node tests/play-check.mjs <projectId>
import { chromium } from "@playwright/test";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const pid = process.argv[2];
const home = process.env.MB_HOME || path.join(os.homedir(), ".motionboard");
const token = fs.readFileSync(path.join(home, "studio.token"), "utf8").trim();
const base = `http://127.0.0.1:${process.env.PORT || 4317}`;
const browser = await chromium.launch({ channel: "chrome", headless: true, args: ["--autoplay-policy=no-user-gesture-required"] });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const errors = [];
page.on("pageerror", (e) => errors.push(String(e)));
page.on("console", (m) => { if (m.type() === "error") errors.push(m.text()); });
await page.goto(`${base}/?session=${token}`);
await page.goto(`${base}/p/${pid}`);
await page.getByRole("button", { name: "Play" }).click();
await page.waitForTimeout(2500);
const t = await page.evaluate(() => { const a = document.querySelector("audio"); return a ? { time: a.currentTime, paused: a.paused, err: a.error?.code ?? null, ready: a.readyState } : null; });
const label = await page.getByRole("button", { name: /Play|Pause/ }).first().textContent();
console.log(JSON.stringify({ audio: t, button: label, errors }));
await browser.close();

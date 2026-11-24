import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import type { Page } from "@playwright/test";

export const E2E = process.env.MB_E2E_DIR || "/tmp/mb-e2e";
export const ENGINE = path.resolve(__dirname, "../../../engine");
export const project = () => fs.readFileSync(path.join(E2E, "project"), "utf8").trim();
export const folder = () => fs.readFileSync(path.join(E2E, "folder"), "utf8").trim();

/** Run mb as the chat would (actor chat), against the e2e database. */
export function mbChat(...args: string[]) {
  const out = execFileSync("uv", ["run", "mb", ...args, "--json"], {
    cwd: ENGINE, env: { ...process.env, MB_HOME: `${E2E}/home`, MB_PROJECTS: `${E2E}/projects`, MB_BACKEND: "stub", MB_ACTOR: "chat" },
  }).toString();
  return JSON.parse(out.trim().split("\n").pop()!);
}

export async function login(page: Page) {
  await page.goto("/?token=e2e-token");
}

export async function openBoard(page: Page) {
  await login(page);
  await page.goto(`/p/${project()}`);
  await page.locator("[data-shot='1']").waitFor();
}

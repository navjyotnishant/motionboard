// T046: the animatic opens over the song and steps shots; JSON export imports back as a new project.
import fs from "node:fs";
import { expect, test } from "@playwright/test";
import { folder, mbChat, openBoard } from "./helpers";

test("animatic and JSON round trip", async ({ page }) => {
  await openBoard(page);
  await page.keyboard.press("v");
  await expect(page.getByText(/shot 1/)).toBeVisible();
  await page.keyboard.press("l");
  await expect(page.getByText(/shot 2/)).toBeVisible({ timeout: 5_000 });
  await page.keyboard.press("Escape");

  await page.getByRole("button", { name: "Export" }).click();
  await page.getByRole("button", { name: "Project JSON with media" }).click();
  await expect.poll(() => fs.existsSync(`${folder()}/exports`) && fs.readdirSync(`${folder()}/exports`).length, { timeout: 20_000 })
    .toBeTruthy();
  const exp = fs.readdirSync(`${folder()}/exports`)[0];
  const imported = mbChat("import", "--file", `${folder()}/exports/${exp}`);
  expect(imported.ok).toBe(true);
  const original = JSON.parse(fs.readFileSync(`${folder()}/exports/${exp}/project.json`, "utf8"));
  const again = mbChat("export", "-p", imported.project, "--out", "/tmp/mb-e2e/again", "--no-media");
  expect(again.ok).toBe(true);
  const copy = JSON.parse(fs.readFileSync("/tmp/mb-e2e/again/project.json", "utf8"));
  expect(copy.shots.map((s: { visual: string }) => s.visual)).toEqual(original.shots.map((s: { visual: string }) => s.visual));
});

// T028: the template path drafts a board; brainstorm without the claude command says Claude is needed.
import { expect, test } from "@playwright/test";
import { ENGINE, login } from "./helpers";

test("start from a template, and brainstorm without Claude", async ({ page }) => {
  await login(page);
  await page.goto("/new");
  await page.getByPlaceholder("Paper Boats", { exact: true }).fill("From the Studio");
  await page.getByRole("button", { name: "Give a path on this Mac instead" }).click();
  await page.getByPlaceholder("/Users/you/Music/song.wav").fill(`${ENGINE}/tests/fixtures/song10s.wav`);
  await page.locator("textarea[name='lyrics']").fill("paper boats on a silver river\nfolding wishes into the night");
  await page.getByRole("button", { name: "Create and analyse" }).click();
  await expect(page.getByText("How do you want to start?")).toBeVisible({ timeout: 60_000 });

  await page.getByRole("button", { name: "Brainstorm three concepts" }).click();
  await expect(page.getByText(/needs Claude Code/)).toBeVisible({ timeout: 10_000 });

  await page.getByRole("button", { name: /Mood Loop/ }).click();
  await page.getByRole("button", { name: "Cosmic" }).click();
  await page.getByRole("button", { name: "Draft the board" }).click();
  await page.waitForURL(/\/p\//, { timeout: 30_000 });
  await expect(page.locator("[data-shot='1']")).toBeVisible();
});

// T034: approve the storyboard, request plates, reject with a note, upload, approve, approve the plates gate.
import { expect, test } from "@playwright/test";
import { E2E, openBoard } from "./helpers";

test("review flow with gates", async ({ page }) => {
  await openBoard(page);
  await page.getByRole("button", { name: /storyboard/i }).click();
  await expect(page.getByRole("button", { name: /request plates/i })).toBeVisible({ timeout: 15_000 });
  await page.getByRole("button", { name: /request plates/i }).click();
  await expect(page.locator("[data-shot='1'] img")).toBeVisible({ timeout: 20_000 });

  await page.locator("[data-shot='1']").dblclick();
  await page.getByRole("button", { name: /^Reject/ }).click();
  await page.getByPlaceholder("What should change? (required)").fill("too bright, make it night");
  await page.getByRole("button", { name: "Reject with note" }).click();
  await expect(page.locator("aside")).toContainText("Needs redo", { timeout: 15_000 });

  await page.getByPlaceholder(/Upload a plate/).fill(`${E2E}/upload.png`);
  await page.getByRole("button", { name: "Upload" }).click();
  await expect(page.locator("aside")).toContainText("Plate to review", { timeout: 15_000 });

  for (const n of [1, 2, 3, 4]) {
    await page.locator(`[data-shot='${n}']`).click();
    await page.keyboard.press("a");
    await expect(page.locator(`[data-shot='${n}'] [title='Plate approved']`)).toBeVisible({ timeout: 15_000 });
  }
  await page.getByRole("button", { name: /^plates$/i }).click();
  await expect(page.getByRole("button", { name: /render clips/i })).toBeVisible({ timeout: 15_000 });
});

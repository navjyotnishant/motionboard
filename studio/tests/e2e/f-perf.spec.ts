// T049: an 80 shot board loads and draws in under 5 seconds.
import fs from "node:fs";
import { expect, test } from "@playwright/test";
import { E2E, login } from "./helpers";

test("80 shot board loads under 5 s", async ({ page }) => {
  const pid = fs.readFileSync(`${E2E}/project80`, "utf8").trim();
  await login(page);
  const t0 = Date.now();
  await page.goto(`/p/${pid}`);
  await expect(page.locator("[data-shot]")).toHaveCount(80, { timeout: 5_000 });
  await page.locator("[data-shot='80']").scrollIntoViewIfNeeded();
  const ms = Date.now() - t0;
  console.log(`80 shot board ready in ${ms} ms`);
  expect(ms).toBeLessThan(5_000);
});

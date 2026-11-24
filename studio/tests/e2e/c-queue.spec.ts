// T041: render clips with the stub backend; queue pause, resume and stop from the drawer.
import { expect, test } from "@playwright/test";
import { mbChat, openBoard, project } from "./helpers";

test("queue controls", async ({ page }) => {
  await openBoard(page);
  await page.keyboard.press("q");
  await expect(page.getByText("Render queue")).toBeVisible();
  await page.getByRole("button", { name: "Pause after this shot" }).click();
  await expect(page.getByRole("button", { name: "Resume" })).toBeVisible({ timeout: 10_000 });
  // Queue while paused so nothing runs, then resume and let the worker render.
  const q = mbChat("clips", "-p", project());
  expect(q.ok).toBe(true);
  await page.getByRole("button", { name: "Resume" }).click();
  await page.getByRole("button", { name: /render clips|start worker/i }).first().click().catch(() => {});
  await expect.poll(async () => {
    const b = await (await page.request.get(`/api/projects/${project()}`)).json();
    return b.shots.filter((s: { state: string }) => s.state === "clip_ready").length;
  }, { timeout: 60_000 }).toBe(4);
  await page.getByRole("button", { name: "Stop" }).click();
  await expect(page.locator("text=done").first()).toBeVisible();
});

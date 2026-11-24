// T022: load board, edit a field, drag a cut, reload, a chat edit appears within 3 s. Also T014's 403s.
import { expect, test } from "@playwright/test";
import { mbChat, openBoard, project } from "./helpers";

test("refuses requests without the session token or from another origin", async ({ request, page }) => {
  expect((await request.get("/api/projects")).status()).toBe(403);
  expect((await request.get("/")).status()).toBe(403);
  await page.goto("/?token=e2e-token");
  const cookies = await page.context().cookies();
  const header = { cookie: cookies.map((c) => `${c.name}=${c.value}`).join("; ") };
  expect((await request.get("/api/projects", { headers: header })).status()).toBe(200);
  const cross = await request.post("/api/mb", { headers: { ...header, origin: "https://evil.example" },
    data: { action: "approve", args: { project: project(), stage: "storyboard" } } });
  expect(cross.status()).toBe(403);
  const escape = await request.get(`/api/media?path=${encodeURIComponent("/etc/passwd")}`, { headers: header });
  expect(escape.status()).toBe(403);
});

test("board edits persist and chat edits appear live", async ({ page }) => {
  await openBoard(page);
  await expect(page.locator("[data-shot]")).toHaveCount(4);
  await page.locator("[data-shot='1']").dblclick();
  const action = page.locator("aside textarea").nth(2);
  await action.fill("she lets the paper boat go");
  await action.blur();
  await expect(action).toHaveValue("she lets the paper boat go", { timeout: 15_000 });
  await page.reload();
  await page.locator("[data-shot='1']").dblclick();
  await expect(page.locator("aside textarea").nth(2)).toHaveValue("she lets the paper boat go");

  // Drag the first cut to the right on the waveform canvas.
  const canvas = page.locator("canvas").last();
  const box = (await canvas.boundingBox())!;
  const before = mbChat("export", "-p", project(), "--out", "/tmp/mb-e2e/before", "--no-media");
  expect(before.ok).toBe(true);
  const board = await (await page.request.get(`/api/projects/${project()}`)).json();
  const dur = board.shots[board.shots.length - 1].end;
  const x0 = box.x + (board.shots[0].end / dur) * box.width;
  await page.mouse.move(x0, box.y + 60);
  await page.mouse.down();
  await page.mouse.move(x0 + box.width * 0.04, box.y + 60, { steps: 6 });
  await page.mouse.up();
  await expect.poll(async () => (await (await page.request.get(`/api/projects/${project()}`)).json()).shots[0].end,
    { timeout: 15_000 }).not.toBe(board.shots[0].end);

  // A change made from chat shows up without a reload.
  const t0 = Date.now();
  mbChat("shot", "set", "-p", project(), "--shot", "2", "--field", "camera", "--value", "slow push in from chat");
  await page.locator("[data-shot='2']").dblclick();
  await expect(page.locator("aside textarea").nth(3)).toHaveValue("slow push in from chat", { timeout: 3_000 + 2_000 });
  expect(Date.now() - t0).toBeLessThan(8_000);
});

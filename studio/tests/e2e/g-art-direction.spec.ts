// 003: the Art view. The creator reviews and approves the Bible in the Studio, the chat sees the same state, chat
// changes (references, revisions, reviews) appear without a reload, and a shot carries its creative context.
import path from "node:path";
import { expect, test } from "@playwright/test";
import { E2E, mbChat, openBoard, project } from "./helpers";

const FIX = path.resolve(__dirname, "../../../engine/tests/fixtures/almost-yours");

test("art direction: review, approve, references, creative context, revisions", async ({ page }) => {
  const pid = project();
  expect(mbChat("art", "draft", "-p", pid, "--file", `${FIX}/bible.json`, "--profile", "full").ok).toBe(true);
  mbChat("shot", "set", "-p", pid, "--shot", "3", "--field", "motifs", "--value", "ruby thread: almost touching");

  await openBoard(page);
  await page.locator("[data-view='art']").click();
  await expect(page.locator("[data-art-status]")).toHaveText(/Draft/);
  await expect(page.locator("[data-swatch='#9B111E']")).toBeVisible();
  await expect(page.locator("[data-character='HER']")).toBeVisible();
  await expect(page.locator("[data-motif='ruby thread'] [data-motif-cell='3']")).toHaveAttribute("data-state", "almost touching");
  await expect(page.getByText("plates wait for approval")).toBeVisible(); // a full Bible holds plates

  // A reference added in chat shows up live.
  expect(mbChat("character", "ref", "add", "-p", pid, "--name", "HER", "--file", `${E2E}/upload.png`, "--purpose", "face").ok).toBe(true);
  await expect(page.locator("[data-character='HER'] [data-ref]")).toHaveCount(1, { timeout: 8_000 });

  // The creator submits and approves in the Studio; the chat reads the same approval.
  await page.getByRole("button", { name: "Submit for review" }).click();
  await expect(page.locator("[data-art-status]")).toHaveText(/Awaiting review/, { timeout: 15_000 });
  await page.locator("[data-art-approve]").click();
  await expect(page.locator("[data-art-status]")).toHaveText(/Approved v1/, { timeout: 15_000 });
  const shown = mbChat("art", "show", "-p", pid);
  expect(shown.data.status).toBe("approved");
  expect(shown.data.approved_via).toBe("studio");
  await expect(page.getByText("plates wait for approval")).toHaveCount(0);

  // A revision from chat is pending, with the approved version still in force.
  mbChat("art", "draft", "-p", pid, "--file", `${FIX}/bible-v2.json`, "--note", "HER deeper garnet");
  await expect(page.locator("[data-art-status]")).toHaveText(/Draft/, { timeout: 8_000 });
  await expect(page.locator("[data-art-pending]")).toContainText("characters");
  if (process.env.MB_SHOTS) await page.screenshot({ path: `${process.env.MB_SHOTS}/art-view.png`, fullPage: true });
  expect(mbChat("art", "show", "-p", pid).data.version).toBe(1);

  // Shot creative context from the panel reaches the composed prompt.
  await page.locator("[data-view='grid']").click();
  await page.locator("[data-shot='2']").dblclick();
  await page.locator("[data-creative] button").first().click();
  const motifs = page.locator("[data-creative-field='motifs']");
  await motifs.fill("ruby thread: taut toward HIM");
  await motifs.blur();
  await expect.poll(() => mbChat("shot", "prompts", "-p", pid, "--shot", "2").data.creative.motifs?.[0]?.state,
    { timeout: 15_000 }).toBe("taut toward HIM");
  expect(mbChat("shot", "prompts", "-p", pid, "--shot", "2").data.plate).toContain("a thin luminous ruby-red thread, taut toward HIM");

  // A prompt the creator writes in the panel is theirs: marked, kept through an approval, cleared only by them.
  const motion = page.locator("[data-field='motion_prompt']");
  await motion.fill("she turns once at the waist fold and stops");
  await motion.blur();
  await expect(page.locator("[data-authored='motion']")).toBeVisible({ timeout: 15_000 });
  expect(mbChat("art", "approve", "-p", pid).data.overrides.map((o: { shot: number; part: string }) => `${o.shot} ${o.part}`))
    .toEqual(["2 motion"]);
  expect(mbChat("shot", "prompts", "-p", pid, "--shot", "2").data.stored.motion).toBe("she turns once at the waist fold and stops");
  await expect(page.locator("[data-authored='motion']")).toBeVisible();
  if (process.env.MB_SHOTS) await page.screenshot({ path: `${process.env.MB_SHOTS}/shot-authored.png` });
  await page.locator("[data-use-generated='motion']").click();
  await expect(page.locator("[data-authored='motion']")).toHaveCount(0, { timeout: 15_000 });
  expect(mbChat("shot", "prompts", "-p", pid, "--shot", "2").data.authored.motion).toBe(false);

  // A review from chat about shot 2 shows in its panel.
  expect(mbChat("critique", "add", "-p", pid, "--stage", "plate", "--role", "editor", "--verdict", "revise",
    "--file", `${FIX}/critique-editor.json`).ok).toBe(true);
  await expect(page.locator("[data-findings]")).toContainText("1 review note", { timeout: 8_000 });
  await expect(page.locator("[data-finding]")).toContainText("decorative curl");
  if (process.env.MB_SHOTS) await page.screenshot({ path: `${process.env.MB_SHOTS}/shot-panel.png` });
});

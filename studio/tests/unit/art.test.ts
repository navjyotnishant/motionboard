// 003: the Art view's helpers and the bridge actions it uses. The helpers only arrange what the engine stored.
import { describe, expect, it } from "vitest";
import {
  affected, authoredParts, creativeCount, creativeText, directionChanged, findingsFor, motifGrid, motifsToText, palette,
  statusOf,
} from "@/lib/art";
import { build, MbBridgeError } from "@/lib/mb";
import type { ArtVersion, Board } from "@/components/board/types";

const v = (over: Partial<ArtVersion>): ArtVersion => ({
  id: "A1", version: 1, profile: "full", status: "approved", body: {}, note: "", impact: {}, created_at: "2026-11-27T00:00:00Z",
  approved_at: "2026-11-27T01:00:00Z", approved_via: "chat", ...over,
});

const board = (over: Partial<Board> = {}): Board => ({
  seq: 0, adapters: [], jobs: [], approvals: [], characters: [], critiques: [],
  project: { id: "P1", title: "Almost Yours", folder: "/x", aspect: "9:16", mode: "two-lovers", visual_look: "origami",
    segment_start: 0, segment_end: 10, synthetic_people: 0, theme: {} },
  analysis: null,
  shots: [1, 2, 3, 4].map((ord) => ({
    id: `S${ord}`, ord, start: ord - 1, end: ord, frames: 24, lyric: "", visual: "", action: "", camera: "", has_figure: true,
    lip_sync: false, plate_prompt: "", motion_prompt: "", state: "plate_approved", dirty: false, updated_at: "", cast: [],
    plate_authored: false, motion_authored: ord === 2, plate_base: "", motion_base: "generated",
    creative: ord === 1 ? {} : { motifs: [{ name: ord === 4 ? "Ruby Thread" : "ruby thread", state: `state ${ord}` }] },
  })),
  assets: [],
  artDirection: { approved: null, pending: null, required: false, versions: [] },
  ...over,
});

describe("art direction status", () => {
  it("says draft, awaiting review or approved with the version", () => {
    expect(statusOf(board().artDirection).label).toBe("No art direction");
    expect(statusOf({ approved: v({}), pending: null, required: false, versions: [] }).label).toBe("Approved v1");
    expect(statusOf({ approved: v({}), pending: v({ version: 2, status: "in_review" }), required: false, versions: [] }))
      .toEqual({ label: "Awaiting review", tone: "warn", version: 2 });
    expect(statusOf({ approved: null, pending: v({ status: "draft" }), required: true, versions: [] }).label).toBe("Draft");
  });
});

describe("palette and motifs", () => {
  it("keeps only valid hex swatches", () => {
    const body = { color: { palette: [{ name: "ruby", hex: "#9B111E", role: "accent" }, { name: "bad", hex: "red" }] } };
    expect(palette(body)).toEqual([{ name: "ruby", hex: "#9B111E", role: "accent" }]);
  });
  it("lays out the thread's state shot by shot, matching names without case", () => {
    const grid = motifGrid({ motifs: [{ name: "ruby thread", meaning: "the connection", payoff: "it snaps" }] }, board().shots);
    expect(grid).toHaveLength(1);
    expect(grid[0].cells.map((c) => c.state)).toEqual([null, "state 2", "state 3", "state 4"]);
    expect(grid[0].payoff).toBe("it snaps");
  });
  it("writes motifs back as name: state lines", () => {
    expect(motifsToText([{ name: "ruby thread", state: "taut" }, { name: "boat" }])).toBe("ruby thread: taut\nboat");
    expect(creativeCount({ intent: "x", motifs: [{ name: "a" }] })).toBe(2);
    expect(creativeCount({})).toBe(0);
  });
});

describe("affected shots", () => {
  const impact = { shots: [{ shot: 2, reasons: ["character HER changed"], assets: [{ id: "PL2", kind: "plate", created_at: "x" }] },
    { shot: 3, reasons: ["character HER changed"], assets: [{ id: "PL3", kind: "plate", created_at: "x" }] }] };
  it("maps a version's impact by shot", () => {
    expect([...affected(v({ impact })).keys()]).toEqual([2, 3]);
  });
  it("marks a shot only while it still uses an asset made under the earlier direction", () => {
    const b = board({
      artDirection: { approved: v({ version: 2, impact }), pending: null, required: false, versions: [] },
      assets: [
        { id: "PL2", shot_id: "S2", kind: "plate", path: "/a", text: null, source: "x", cost_usd: 0, active: true, created_at: "", notes: [] },
        { id: "PL3", shot_id: "S3", kind: "plate", path: "/b", text: null, source: "x", cost_usd: 0, active: false, created_at: "", notes: [] },
        { id: "PL3b", shot_id: "S3", kind: "plate", path: "/c", text: null, source: "x", cost_usd: 0, active: true, created_at: "", notes: [] },
      ],
    });
    expect([...directionChanged(b)]).toEqual(["S2"]);
  });
  it("finds open review findings for a shot", () => {
    const f = { observation: "o", audience_impact: "a", implication: "i", recommendation: "r", shots: [2] };
    const b = board({ critiques: [
      { id: "C1", stage: "plate", role: "editor", verdict: "revise", summary: "", findings: [f], checked: [], not_checked: [],
        created_at: "", resolved_at: null },
      { id: "C2", stage: "plate", role: "director", verdict: "revise", summary: "", findings: [f], checked: [], not_checked: [],
        created_at: "", resolved_at: "done" },
    ] });
    expect(findingsFor(b, 2).map((x) => x.role)).toEqual(["editor"]);
    expect(findingsFor(b, 3)).toEqual([]);
  });
});

describe("bridge actions for art direction", () => {
  it("builds exact argv and refuses bad input", () => {
    expect(build("art_approve", { project: "01ABCDEF" })).toEqual(["art", "approve", "-p", "01ABCDEF", "--via", "studio"]);
    expect(build("art_reject", { project: "01ABCDEF", note: "start slack" }))
      .toEqual(["art", "reject", "-p", "01ABCDEF", "--note", "start slack"]);
    expect(build("ref_add", { project: "01ABCDEF", name: "HER", file: "/tmp/her.png", purpose: "silhouette", primary: true }))
      .toEqual(["character", "ref", "add", "-p", "01ABCDEF", "--name", "HER", "--file", "/tmp/her.png", "--purpose", "silhouette", "--primary"]);
    expect(build("shot_set", { project: "01ABCDEF", shot: 2, field: "motifs", value: "ruby thread: taut" }))
      .toEqual(["shot", "set", "-p", "01ABCDEF", "--shot", "2", "--field", "motifs", "--value", "ruby thread: taut"]);
    expect(() => build("ref_add", { project: "01ABCDEF", name: "HER; rm", file: "/x" })).toThrow(MbBridgeError);
    expect(() => build("ref_add", { project: "01ABCDEF", name: "HER", file: "/x", purpose: "selfie" })).toThrow(MbBridgeError);
    expect(() => build("art_reject", { project: "01ABCDEF", note: "" })).toThrow(MbBridgeError);
    expect(() => build("shot_set", { project: "01ABCDEF", shot: 2, field: "creative", value: "{}" })).toThrow(MbBridgeError);
  });
});

describe("003 corrections: shot associations and authored prompts", () => {
  it("edits materials and objects as comma lists and counts them", () => {
    const c = { objects: ["display case", "paper boat"], materials: ["washi paper"], motifs: [{ name: "thread", state: "taut" }] };
    expect(creativeText(c, "objects")).toBe("display case, paper boat");
    expect(creativeText(c, "materials")).toBe("washi paper");
    expect(creativeText(c, "motifs")).toBe("thread: taut");
    expect(creativeText({}, "intent")).toBe("");
    expect(creativeCount(c)).toBe(3);
  });
  it("marks which prompts the creator wrote", () => {
    const shots = board().shots;
    expect(authoredParts(shots[0])).toEqual([]);
    expect(authoredParts(shots[1])).toEqual(["motion"]);
    expect(authoredParts({ plate_authored: true, motion_authored: true })).toEqual(["plate", "motion"]);
  });
  it("sends override decisions and the new shot fields through the whitelisted bridge", () => {
    expect(build("override_clear", { project: "P1ABCDEFGH", shot: 2, part: "motion" }))
      .toEqual(["shot", "override", "clear", "-p", "P1ABCDEFGH", "--shot", "2", "--part", "motion"]);
    expect(build("override_keep", { project: "P1ABCDEFGH", shot: 3, part: "both" }))
      .toEqual(["shot", "override", "keep", "-p", "P1ABCDEFGH", "--shot", "3", "--part", "both"]);
    expect(build("shot_set", { project: "P1ABCDEFGH", shot: 4, field: "objects", value: "paper boat" }).slice(-4))
      .toEqual(["--field", "objects", "--value", "paper boat"]);
    expect(() => build("override_clear", { project: "P1ABCDEFGH", shot: 2, part: "all" })).toThrow(MbBridgeError);
  });
});

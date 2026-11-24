// T014: token and origin rejection, media path escape rejected, mb bridge whitelist.
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { originOk, safeEqual, tokenOk } from "@/lib/token";
import { parseRange, resolveMedia, within } from "@/lib/media";
import { build, MbBridgeError } from "@/lib/mb";

const ORIGINS = ["http://127.0.0.1:4317", "http://localhost:4317"];

describe("session token", () => {
  beforeAll(() => { process.env.MB_STUDIO_TOKEN = "s3cret-token-value"; });
  afterAll(() => { delete process.env.MB_STUDIO_TOKEN; });
  it("accepts only the exact token", () => {
    expect(tokenOk("s3cret-token-value")).toBe(true);
    expect(tokenOk("s3cret-token-valuX")).toBe(false);
    expect(tokenOk(undefined)).toBe(false);
    expect(tokenOk("")).toBe(false);
  });
  it("refuses everything when no token is configured", () => {
    delete process.env.MB_STUDIO_TOKEN;
    expect(tokenOk("anything")).toBe(false);
    process.env.MB_STUDIO_TOKEN = "s3cret-token-value";
  });
  it("compares in constant shape", () => {
    expect(safeEqual("abc", "abc")).toBe(true);
    expect(safeEqual("abc", "abd")).toBe(false);
    expect(safeEqual("abc", "abcd")).toBe(false);
  });
});

describe("origin check", () => {
  it("lets reads through and blocks cross origin writes", () => {
    expect(originOk("GET", null, ORIGINS)).toBe(true);
    expect(originOk("POST", "http://127.0.0.1:4317", ORIGINS)).toBe(true);
    expect(originOk("POST", "https://evil.example", ORIGINS)).toBe(false);
    expect(originOk("PATCH", null, ORIGINS)).toBe(false);
    expect(originOk("DELETE", "http://127.0.0.1:9999", ORIGINS)).toBe(false);
  });
});

describe("media paths", () => {
  let root: string, outside: string;
  beforeAll(() => {
    const base = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), "mbsec-")));
    root = path.join(base, "projects");
    outside = path.join(base, "secret.txt");
    fs.mkdirSync(path.join(root, "p1"), { recursive: true });
    fs.writeFileSync(path.join(root, "p1", "plate.png"), "x");
    fs.writeFileSync(outside, "secret");
    fs.symlinkSync(outside, path.join(root, "p1", "link.png"));
  });
  it("serves files inside a project folder", () => {
    expect(resolveMedia(path.join(root, "p1", "plate.png"), [root])).toBe(path.join(root, "p1", "plate.png"));
  });
  it("rejects dot dot escapes, symlinks out, relative paths and directories", () => {
    expect(resolveMedia(path.join(root, "p1", "..", "..", "secret.txt"), [root])).toBeNull();
    expect(resolveMedia(path.join(root, "p1", "link.png"), [root])).toBeNull();
    expect(resolveMedia("p1/plate.png", [root])).toBeNull();
    expect(resolveMedia(path.join(root, "p1"), [root])).toBeNull();
    expect(resolveMedia(`${root}/p1/plate.png\0.txt`, [root])).toBeNull();
  });
  it("does not treat a sibling with a shared prefix as inside", () => {
    expect(within("/a/projects-evil/x", ["/a/projects"])).toBe(false);
    expect(within("/a/projects/x", ["/a/projects"])).toBe(true);
  });
  it("parses byte ranges", () => {
    expect(parseRange("bytes=0-99", 1000)).toEqual({ start: 0, end: 99 });
    expect(parseRange("bytes=900-", 1000)).toEqual({ start: 900, end: 999 });
    expect(parseRange("bytes=-100", 1000)).toEqual({ start: 900, end: 999 });
    expect(parseRange("bytes=2000-", 1000)).toBeNull();
  });
});

describe("mb bridge", () => {
  it("refuses unknown actions and bad arguments", () => {
    expect(() => build("rm", {})).toThrow(MbBridgeError);
    expect(() => build("approve", { project: "01ABC", stage: "everything" })).toThrow(MbBridgeError);
    expect(() => build("shot_set", { project: "01ABC", shot: 1, field: "state", value: "clip_approved" })).toThrow();
    expect(() => build("approve", { project: "../../x", stage: "plates" })).toThrow();
  });
  it("builds argv arrays, never a shell string", () => {
    expect(build("approve", { project: "01ABCDEF", stage: "plates" }))
      .toEqual(["approve", "-p", "01ABCDEF", "--stage", "plates", "--via", "studio"]);
    const a = build("review", { project: "01ABCDEF", shot: 2, kind: "clip", decision: "reject", note: "x; rm -rf ~" });
    expect(a).toContain("x; rm -rf ~");
  });
});

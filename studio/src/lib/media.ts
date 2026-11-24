// Media files are served only from inside a project folder (or the projects root), after resolving
// symlinks, so a path like /projects/x/../../etc/passwd or a planted link cannot escape.
import "server-only";
import fs from "node:fs";
import path from "node:path";
import { PROJECTS_ROOT } from "./config";
import { raw } from "./db";

export function allowedRoots(): string[] {
  const roots = new Set<string>();
  const add = (p: string) => {
    try {
      roots.add(fs.realpathSync(p));
    } catch {
      /* missing folders are simply not allowed */
    }
  };
  add(PROJECTS_ROOT);
  for (const r of raw().prepare("SELECT folder FROM project").all() as { folder: string }[]) add(r.folder);
  return [...roots];
}

export function within(file: string, roots: string[]): boolean {
  return roots.some((r) => file === r || file.startsWith(r.endsWith(path.sep) ? r : r + path.sep));
}

export function resolveMedia(requested: string, roots = allowedRoots()): string | null {
  if (!requested || !path.isAbsolute(requested) || requested.includes("\0")) return null;
  let real: string;
  try {
    real = fs.realpathSync(requested);
  } catch {
    return null;
  }
  if (!within(real, roots)) return null;
  if (!fs.statSync(real).isFile()) return null;
  return real;
}

const TYPES: Record<string, string> = {
  ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp",
  ".mp4": "video/mp4", ".mov": "video/quicktime", ".wav": "audio/wav", ".mp3": "audio/mpeg", ".m4a": "audio/mp4",
  ".json": "application/json", ".txt": "text/plain", ".md": "text/markdown",
};
export const contentType = (f: string) => TYPES[path.extname(f).toLowerCase()] || "application/octet-stream";

export function parseRange(h: string | null, size: number): { start: number; end: number } | null {
  if (!h) return null;
  const m = /^bytes=(\d*)-(\d*)$/.exec(h.trim());
  if (!m) return null;
  let start = m[1] ? Number(m[1]) : NaN;
  let end = m[2] ? Number(m[2]) : NaN;
  if (Number.isNaN(start)) {
    if (Number.isNaN(end)) return null;
    start = Math.max(0, size - end);
    end = size - 1;
  } else if (Number.isNaN(end) || end >= size) end = size - 1;
  if (start > end || start >= size) return null;
  return { start, end };
}

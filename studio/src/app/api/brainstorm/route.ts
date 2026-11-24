// Brainstorm three concepts with the creator's own Claude (`claude -p`). Without the CLI the Studio says so
// (CLAUDE_MISSING) and the creator can brainstorm in chat instead. Concepts are saved with `mb concepts add`.
import { execFile } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { connection, NextResponse } from "next/server";
import { z } from "zod";
import { parseJson, raw } from "@/lib/db";
import { build, runMb } from "@/lib/mb";
import { brainstormPrompt, extractJson } from "@/lib/prompts/brainstorm";

const Body = z.object({
  project_id: z.string().regex(/^[0-9A-Za-z]{4,40}$/),
  answers: z.object({ mood: z.string().max(400).optional(), world: z.string().max(400).optional(),
    characters: z.string().max(400).optional(), look: z.string().max(60).optional() }),
});

const Concept = z.object({
  title: z.string(), premise: z.string().default(""), hero_image_idea: z.string().default(""),
  mode: z.string(), look: z.string(), sample_shots: z.array(z.string()).default([]),
  shots: z.array(z.object({ visual: z.string().optional(), action: z.string(), camera: z.string().optional(),
    has_figure: z.boolean().optional(), lip_sync: z.boolean().optional() })).default([]),
});

function which(cmd: string): string | null {
  const forced = process.env.MB_CLAUDE_BIN;
  if (forced) return forced === "none" ? null : forced;
  for (const d of (process.env.PATH || "").split(path.delimiter).concat(["/opt/homebrew/bin", "/usr/local/bin",
    path.join(os.homedir(), ".claude", "local"), path.join(os.homedir(), ".local", "bin")])) {
    const p = path.join(d, cmd);
    if (fs.existsSync(p)) return p;
  }
  return null;
}

export async function POST(req: Request) {
  await connection();
  const parsed = Body.safeParse(await req.json().catch(() => null));
  if (!parsed.success) return NextResponse.json({ error: parsed.error.issues[0]?.message }, { status: 400 });
  const claude = which("claude");
  if (!claude) {
    return NextResponse.json({ error: "CLAUDE_MISSING",
      message: "Brainstorm needs Claude Code on this Mac (the claude command). Brainstorm in chat, or pick a template." },
    { status: 424 });
  }
  const p = raw().prepare("SELECT * FROM project WHERE id = ?").get(parsed.data.project_id) as Record<string, string> | undefined;
  if (!p) return NextResponse.json({ error: "NOT_FOUND" }, { status: 404 });
  const a = raw().prepare("SELECT tempo_bpm, beats, lines FROM song_analysis WHERE project_id = ?").get(p.id) as
    { tempo_bpm: number | null; beats: string; lines: string } | undefined;
  const lines = parseJson<{ text: string }[]>(a?.lines, []);
  const modesRep = await runMb(build("modes", {}));
  const modes = (modesRep.data.modes as { slug: string; name: string; summary: string }[]) || [];
  const looks = ((modesRep.data.looks as { slug: string }[]) || []).map((l) => l.slug);
  const shots = Math.max(4, Math.min(24, lines.length || 8));
  const prompt = brainstormPrompt({ title: p.title, lyrics: lines.map((l) => l.text).join("\n") || p.lyrics, idea: p.idea,
    aspect: p.aspect, tempo: a?.tempo_bpm ?? null, shots, modes, looks, answers: parsed.data.answers });

  const out = await new Promise<{ ok: boolean; text: string }>((resolve) => {
    execFile(claude, ["-p", prompt], { cwd: os.tmpdir(), timeout: 180_000, maxBuffer: 8 << 20 },
      (err, stdout, stderr) => resolve({ ok: !err, text: err ? (stderr || err.message) : stdout }));
  });
  if (!out.ok) return NextResponse.json({ error: "CLAUDE_FAILED", message: out.text.slice(-400) }, { status: 502 });
  let concepts;
  try {
    const j = extractJson(out.text) as { concepts: unknown[] };
    concepts = z.array(Concept).min(1).parse(j.concepts).slice(0, 3)
      .map((c) => ({ ...c, mode: modes.some((m) => m.slug === c.mode) ? c.mode : modes[0]?.slug,
        look: looks.includes(c.look) ? c.look : looks[0] }));
  } catch (e) {
    return NextResponse.json({ error: "BAD_ANSWER", message: `Claude's answer was not usable: ${String(e).slice(0, 200)}` },
      { status: 502 });
  }
  const dir = path.join(p.folder, "concepts");
  fs.mkdirSync(dir, { recursive: true });
  const file = path.join(dir, `brainstorm-${Date.now()}.json`);
  fs.writeFileSync(file, JSON.stringify({ concepts }, null, 2));
  const saved = await runMb(build("concepts_add", { project: p.id, file }));
  const ids = ((saved.data.concepts as { id: string }[]) || []).map((c) => c.id);
  concepts.forEach((c, i) => {
    const sf = path.join(dir, `shots-${ids[i] || i}.json`);
    fs.writeFileSync(sf, JSON.stringify({ shots: c.shots }, null, 2));
  });
  return NextResponse.json({ concepts: concepts.map((c, i) => ({ ...c, id: ids[i] || null,
    shots_file: path.join(dir, `shots-${ids[i] || i}.json`) })) });
}

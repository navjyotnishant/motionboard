// Edit a shot from the Studio. The engine owns the rules (prompts follow the look, finished work is marked
// for redo, boundaries snap to beats), so edits go through `mb shot set|move`. A stale updated_at is a 409.
import { connection, NextResponse } from "next/server";
import { z } from "zod";
import { raw } from "@/lib/db";
import { runMb } from "@/lib/mb";

const Body = z.object({
  updated_at: z.string(),
  fields: z.object({
    lyric: z.string().max(4000).optional(),
    visual: z.string().max(4000).optional(),
    action: z.string().max(4000).optional(),
    camera: z.string().max(4000).optional(),
    plate_prompt: z.string().max(4000).optional(),
    motion_prompt: z.string().max(4000).optional(),
    has_figure: z.boolean().optional(),
    lip_sync: z.boolean().optional(),
    end: z.number().optional(),
  }).refine((f) => Object.keys(f).length > 0, "no fields"),
});

type ShotRow = { id: string; project_id: string; ord: number; updated_at: string };

export async function PATCH(req: Request, ctx: { params: Promise<{ id: string }> }) {
  await connection();
  const { id } = await ctx.params;
  const parsed = Body.safeParse(await req.json().catch(() => null));
  if (!parsed.success) return NextResponse.json({ error: parsed.error.issues[0]?.message }, { status: 400 });
  const shot = raw().prepare("SELECT id, project_id, ord, updated_at FROM shot WHERE id = ?").get(id) as
    ShotRow | undefined;
  if (!shot) return NextResponse.json({ error: "NOT_FOUND" }, { status: 404 });
  if (shot.updated_at !== parsed.data.updated_at) {
    return NextResponse.json({ error: "CONFLICT", message: "shot changed elsewhere; reloaded" }, { status: 409 });
  }
  const reports = [];
  for (const [field, value] of Object.entries(parsed.data.fields)) {
    const args = field === "end"
      ? ["shot", "move", "-p", shot.project_id, "--shot", String(shot.ord), "--end", String(value)]
      : ["shot", "set", "-p", shot.project_id, "--shot", String(shot.ord), "--field", field, "--value", String(value)];
    const r = await runMb(args, 60_000);
    reports.push(r);
    if (!r.ok) return NextResponse.json(r, { status: 422 });
  }
  const updated = raw().prepare("SELECT * FROM shot WHERE id = ?").get(id);
  return NextResponse.json({ shot: updated, reports });
}

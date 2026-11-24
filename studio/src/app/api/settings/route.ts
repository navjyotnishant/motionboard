import { connection, NextResponse } from "next/server";
import { DB_PATH, ENGINE_ROOT, MB_HOME, PROJECTS_ROOT } from "@/lib/config";
import { parseJson, raw } from "@/lib/db";

export async function GET() {
  await connection();
  const db = raw();
  const guards = db.prepare("SELECT name, start_free_pct, kill_free_pct, swap_ceiling_mb, poll_seconds, builtin FROM guard_profile ORDER BY builtin DESC, name").all();
  const active = db.prepare("SELECT value FROM workspace_setting WHERE key = 'active_guard_profile'").get() as { value: string } | undefined;
  // Adapter configs may name a key file or variable; they never hold the key itself (the engine refuses that).
  const adapters = (db.prepare("SELECT name, kind, config, cost_per_image_usd, enabled FROM plate_adapter ORDER BY name").all() as
    { name: string; kind: string; config: string; cost_per_image_usd: number; enabled: number }[])
    .map((a) => ({ ...a, config: parseJson(a.config, {}) }));
  return NextResponse.json({
    guards, active: parseJson<string>(active?.value, "balanced"), adapters,
    paths: { home: MB_HOME, db: DB_PATH, projects: PROJECTS_ROOT, engine: ENGINE_ROOT },
  });
}

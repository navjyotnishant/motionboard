// Read models for the UI. Plain SQL against the shared database; shapes are what the client renders.
import "server-only";
import fs from "node:fs";
import path from "node:path";
import { parseJson, raw } from "./db";

const sibling = (p: string | null, ext: string) => {
  if (!p || !/\.mp4$/i.test(p)) return null;
  const q = path.join(path.dirname(p), ".previews", path.basename(p).replace(/\.mp4$/i, ext));
  return fs.existsSync(q) ? q : null;
};

export type ShotRow = {
  id: string; ord: number; start: number; end: number; frames: number; lyric: string; visual: string;
  action: string; camera: string; has_figure: number; lip_sync: number; plate_prompt: string; motion_prompt: string;
  state: string; dirty: number; updated_at: string;
};

export function listProjects() {
  const rows = raw().prepare(
    `SELECT p.id, p.title, p.aspect, p.mode, p.visual_look, p.folder, p.updated_at,
       (SELECT COUNT(*) FROM shot s WHERE s.project_id = p.id) AS shots,
       (SELECT a.path FROM asset_version a JOIN shot s ON s.id = a.shot_id
          WHERE s.project_id = p.id AND a.kind = 'plate' AND a.active = 1 ORDER BY s.ord LIMIT 1) AS hero
     FROM project p ORDER BY p.updated_at DESC`,
  ).all() as Record<string, unknown>[];
  const approvals = raw().prepare("SELECT project_id, stage FROM stage_approval WHERE approved_at IS NOT NULL").all() as
    { project_id: string; stage: string }[];
  return rows.map((r) => {
    const done = approvals.filter((a) => a.project_id === r.id).map((a) => a.stage);
    const stage = ["final", "clips", "plates", "storyboard"].find((s) => done.includes(s));
    return { ...r, stage: stage ? `${stage} approved` : (r.shots ? "storyboard" : "new") };
  });
}

export function board(projectId: string) {
  const db = raw();
  const project = db.prepare("SELECT * FROM project WHERE id = ? OR id LIKE ?").get(projectId, `%${projectId}`) as
    Record<string, unknown> | undefined;
  if (!project) return null;
  const pid = project.id as string;
  const analysis = db.prepare("SELECT * FROM song_analysis WHERE project_id = ?").get(pid) as
    Record<string, string | number | null> | undefined;
  const shots = db.prepare("SELECT * FROM shot WHERE project_id = ? ORDER BY ord").all(pid) as ShotRow[];
  const assets = db.prepare(
    `SELECT a.* FROM asset_version a JOIN shot s ON s.id = a.shot_id WHERE s.project_id = ? ORDER BY a.created_at`,
  ).all(pid) as { id: string; shot_id: string; kind: string; path: string | null; text: string | null;
    source: string; cost_usd: number; active: number; created_at: string }[];
  const notes = db.prepare(
    `SELECT n.* FROM review_note n JOIN asset_version a ON a.id = n.asset_version_id JOIN shot s ON s.id = a.shot_id
     WHERE s.project_id = ? ORDER BY n.at`,
  ).all(pid) as { id: string; asset_version_id: string; decision: string; text: string; at: string }[];
  const characters = db.prepare("SELECT * FROM character WHERE project_id = ? ORDER BY name").all(pid) as
    { id: string; name: string; reference_image: string | null; style_line: string }[];
  const cast = db.prepare(
    "SELECT sc.shot_id, sc.character_id FROM shot_character sc JOIN shot s ON s.id = sc.shot_id WHERE s.project_id = ?",
  ).all(pid) as { shot_id: string; character_id: string }[];
  const approvals = db.prepare("SELECT stage, approved_at, via FROM stage_approval WHERE project_id = ?").all(pid) as
    { stage: string; approved_at: string | null; via: string }[];
  const jobs = db.prepare(
    `SELECT j.*, s.ord FROM render_job j LEFT JOIN shot s ON s.id = j.shot_id WHERE j.project_id = ?
     ORDER BY j.created_at DESC LIMIT 200`,
  ).all(pid) as Record<string, unknown>[];
  const seq = (db.prepare("SELECT COALESCE(MAX(seq), 0) AS s FROM change_event").get() as { s: number }).s;
  const adapters = db.prepare(
    "SELECT name, kind, cost_per_image_usd FROM plate_adapter WHERE enabled = 1 ORDER BY name",
  ).all() as { name: string; kind: string; cost_per_image_usd: number }[];
  return {
    seq,
    adapters,
    project: { ...project, theme: parseJson(project.theme as string, {}) },
    analysis: analysis ? {
      tempo_bpm: analysis.tempo_bpm,
      beats: parseJson<number[]>(analysis.beats as string, []),
      lines: parseJson<{ start: number; end: number; text: string }[]>(analysis.lines as string, []),
      peaks: parseJson<number[]>(analysis.waveform_peaks as string, []),
      verified_vocal_alignment: !!analysis.verified_vocal_alignment,
    } : null,
    shots: shots.map((s) => ({
      ...s,
      has_figure: !!s.has_figure, lip_sync: !!s.lip_sync, dirty: !!s.dirty,
      cast: cast.filter((c) => c.shot_id === s.id).map((c) => c.character_id),
    })),
    assets: assets.map((a) => ({
      ...a, active: !!a.active, notes: notes.filter((n) => n.asset_version_id === a.id),
      proxy: a.kind === "clip" ? sibling(a.path, ".proxy.mp4") : null,
      poster: a.kind === "clip" ? sibling(a.path, ".poster.jpg") : null,
    })),
    characters,
    approvals,
    jobs,
  };
}

export function queue() {
  const db = raw();
  const jobs = db.prepare(
    `SELECT j.id, j.project_id, j.state, j.progress, j.sec_per_frame, j.stop_reason, j.suggestion, j.priority,
       j.settings, j.created_at, j.started_at, j.ended_at, s.ord, p.title
     FROM render_job j LEFT JOIN shot s ON s.id = j.shot_id LEFT JOIN project p ON p.id = j.project_id
     WHERE j.state IN ('queued','running','paused') OR j.ended_at > strftime('%Y-%m-%dT%H:%M:%fZ','now','-1 hour')
     ORDER BY CASE j.state WHEN 'running' THEN 0 WHEN 'paused' THEN 1 WHEN 'queued' THEN 2 ELSE 3 END,
       j.priority, j.created_at`,
  ).all() as Record<string, unknown>[];
  const active = db.prepare("SELECT value FROM workspace_setting WHERE key = 'active_guard_profile'").get() as
    { value: string } | undefined;
  const name = parseJson<string>(active?.value, "balanced");
  const guard = db.prepare("SELECT * FROM guard_profile WHERE name = ?").get(name);
  const running = jobs.find((j) => j.state === "running");
  const samples = running
    ? db.prepare("SELECT at, free_pct, swap_mb, rss_mb FROM memory_sample WHERE job_id = ? ORDER BY at DESC LIMIT 90")
      .all(running.id as string).reverse()
    : [];
  return { jobs: jobs.map((j) => ({ ...j, settings: parseJson(j.settings as string, {}) })), guard, samples };
}

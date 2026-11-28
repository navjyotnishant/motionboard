// Drizzle mirror of the engine schema (engine/src/motionboard/db/migrations). The engine owns migrations;
// this file only describes the tables so the Studio can read them with types. Keep in step with 0001 to 0003.
import { integer, real, sqliteTable, text, primaryKey } from "drizzle-orm/sqlite-core";

export const workspaceSetting = sqliteTable("workspace_setting", {
  key: text("key").primaryKey(),
  value: text("value").notNull(),
});

export const guardProfile = sqliteTable("guard_profile", {
  id: text("id").primaryKey(),
  name: text("name").notNull(),
  startFreePct: integer("start_free_pct").notNull(),
  killFreePct: integer("kill_free_pct").notNull(),
  swapCeilingMb: integer("swap_ceiling_mb").notNull(),
  pollSeconds: real("poll_seconds").notNull(),
  builtin: integer("builtin", { mode: "boolean" }).notNull(),
});

export const plateAdapter = sqliteTable("plate_adapter", {
  id: text("id").primaryKey(),
  name: text("name").notNull(),
  kind: text("kind", { enum: ["manual", "command", "http", "handoff"] }).notNull(),
  config: text("config").notNull(),
  costPerImageUsd: real("cost_per_image_usd").notNull(),
  enabled: integer("enabled", { mode: "boolean" }).notNull(),
});

export const template = sqliteTable("template", {
  id: text("id").primaryKey(),
  name: text("name").notNull(),
  source: text("source", { enum: ["builtin", "user"] }).notNull(),
  body: text("body").notNull(),
});

export const project = sqliteTable("project", {
  id: text("id").primaryKey(),
  title: text("title").notNull(),
  folder: text("folder").notNull(),
  songPath: text("song_path"),
  segmentStart: real("segment_start"),
  segmentEnd: real("segment_end"),
  lyrics: text("lyrics").notNull(),
  idea: text("idea").notNull(),
  aspect: text("aspect", { enum: ["9:16", "16:9"] }).notNull(),
  look: text("look", { enum: ["stylized", "realistic"] }).notNull(),
  theme: text("theme").notNull(),
  templateId: text("template_id"),
  conceptId: text("concept_id"),
  videoBackend: text("video_backend").notNull(),
  plateAdapterId: text("plate_adapter_id"),
  syntheticPeople: integer("synthetic_people", { mode: "boolean" }).notNull(),
  createdAt: text("created_at").notNull(),
  updatedAt: text("updated_at").notNull(),
  mode: text("mode"),
  visualLook: text("visual_look"),
});

export const songAnalysis = sqliteTable("song_analysis", {
  projectId: text("project_id").primaryKey(),
  tempoBpm: real("tempo_bpm"),
  beats: text("beats").notNull(),
  lines: text("lines").notNull(),
  loudness: text("loudness").notNull(),
  waveformPeaks: text("waveform_peaks").notNull(),
  verifiedVocalAlignment: integer("verified_vocal_alignment", { mode: "boolean" }).notNull(),
});

export const concept = sqliteTable("concept", {
  id: text("id").primaryKey(),
  projectId: text("project_id").notNull(),
  title: text("title").notNull(),
  premise: text("premise").notNull(),
  heroImageIdea: text("hero_image_idea").notNull(),
  sampleShots: text("sample_shots").notNull(),
  chosen: integer("chosen", { mode: "boolean" }).notNull(),
});

export const character = sqliteTable("character", {
  id: text("id").primaryKey(),
  projectId: text("project_id").notNull(),
  name: text("name").notNull(),
  referenceImage: text("reference_image"),
  styleLine: text("style_line").notNull(),
});

export const SHOT_STATES = [
  "draft", "plate_requested", "plate_ready", "plate_approved", "clip_queued", "clip_rendering",
  "clip_ready", "clip_approved", "clip_failed", "needs_redo",
] as const;

export const shot = sqliteTable("shot", {
  id: text("id").primaryKey(),
  projectId: text("project_id").notNull(),
  ord: integer("ord").notNull(),
  start: real("start").notNull(),
  end: real("end").notNull(),
  frames: integer("frames").notNull(),
  lyric: text("lyric").notNull(),
  visual: text("visual").notNull(),
  action: text("action").notNull(),
  camera: text("camera").notNull(),
  hasFigure: integer("has_figure", { mode: "boolean" }).notNull(),
  lipSync: integer("lip_sync", { mode: "boolean" }).notNull(),
  platePrompt: text("plate_prompt").notNull(),
  motionPrompt: text("motion_prompt").notNull(),
  state: text("state", { enum: SHOT_STATES }).notNull(),
  dirty: integer("dirty", { mode: "boolean" }).notNull(),
  updatedAt: text("updated_at").notNull(),
  creative: text("creative").notNull(), // 0003: JSON intent, audience, metaphor, motifs, continuity
});

export const shotCharacter = sqliteTable(
  "shot_character",
  { shotId: text("shot_id").notNull(), characterId: text("character_id").notNull() },
  (t) => [primaryKey({ columns: [t.shotId, t.characterId] })],
);

export const assetVersion = sqliteTable("asset_version", {
  id: text("id").primaryKey(),
  shotId: text("shot_id").notNull(),
  kind: text("kind", { enum: ["plate", "clip", "prompt"] }).notNull(),
  path: text("path"),
  text: text("text"),
  source: text("source").notNull(),
  costUsd: real("cost_usd").notNull(),
  active: integer("active", { mode: "boolean" }).notNull(),
  createdAt: text("created_at").notNull(),
});

export const plateRequest = sqliteTable("plate_request", {
  id: text("id").primaryKey(),
  shotId: text("shot_id").notNull(),
  adapterId: text("adapter_id").notNull(),
  prompt: text("prompt").notNull(),
  referenceImage: text("reference_image"),
  state: text("state", { enum: ["pending", "approved_cost", "running", "done", "failed"] }).notNull(),
  estCostUsd: real("est_cost_usd").notNull(),
  resultAssetId: text("result_asset_id"),
  createdAt: text("created_at").notNull(),
  refs: text("refs").notNull(), // 0003: JSON references sent
  refsDropped: text("refs_dropped").notNull(), // 0003: JSON references not sent, with a reason
});

export const renderJob = sqliteTable("render_job", {
  id: text("id").primaryKey(),
  projectId: text("project_id").notNull(),
  shotId: text("shot_id"),
  kind: text("kind", { enum: ["clip", "lipsync", "vocals", "finish", "plate"] }).notNull(),
  backend: text("backend").notNull(),
  settings: text("settings").notNull(),
  priority: integer("priority").notNull(),
  state: text("state", { enum: ["queued", "running", "paused", "done", "failed", "stopped"] }).notNull(),
  progress: real("progress").notNull(),
  secPerFrame: real("sec_per_frame"),
  stopReason: text("stop_reason"),
  suggestion: text("suggestion"),
  logPath: text("log_path"),
  createdAt: text("created_at").notNull(),
  startedAt: text("started_at"),
  endedAt: text("ended_at"),
});

export const memorySample = sqliteTable("memory_sample", {
  jobId: text("job_id").notNull(),
  at: text("at").notNull(),
  freePct: integer("free_pct").notNull(),
  swapMb: integer("swap_mb").notNull(),
  rssMb: integer("rss_mb").notNull(),
});

export const fitSample = sqliteTable("fit_sample", {
  backend: text("backend").notNull(),
  mode: text("mode").notNull(),
  width: integer("width").notNull(),
  height: integer("height").notNull(),
  frames: integer("frames").notNull(),
  peakUsedGb: real("peak_used_gb").notNull(),
  secPerFrame: real("sec_per_frame"),
  machine: text("machine").notNull(),
  at: text("at").notNull(),
});

export const stageApproval = sqliteTable(
  "stage_approval",
  {
    projectId: text("project_id").notNull(),
    stage: text("stage", { enum: ["storyboard", "plates", "clips", "final"] }).notNull(),
    approvedAt: text("approved_at"),
    via: text("via", { enum: ["chat", "studio"] }).notNull(),
  },
  (t) => [primaryKey({ columns: [t.projectId, t.stage] })],
);

export const reviewNote = sqliteTable("review_note", {
  id: text("id").primaryKey(),
  assetVersionId: text("asset_version_id").notNull(),
  decision: text("decision", { enum: ["approve", "reject", "comment"] }).notNull(),
  text: text("text").notNull(),
  at: text("at").notNull(),
});

export const delivery = sqliteTable("delivery", {
  projectId: text("project_id").primaryKey(),
  videoPath: text("video_path"),
  coverPath: text("cover_path"),
  metadataPath: text("metadata_path"),
  targetFolder: text("target_folder"),
  postTime: text("post_time"),
  verified: text("verified").notNull(),
});

export const changeEvent = sqliteTable("change_event", {
  seq: integer("seq").primaryKey({ autoIncrement: true }),
  at: text("at").notNull(),
  entity: text("entity").notNull(),
  entityId: text("entity_id").notNull(),
  kind: text("kind", { enum: ["insert", "update", "delete"] }).notNull(),
  actor: text("actor", { enum: ["chat", "studio", "worker"] }).notNull(),
});

// 0003 creative direction
export const artDirection = sqliteTable("art_direction", {
  id: text("id").primaryKey(),
  projectId: text("project_id").notNull(),
  version: integer("version").notNull(),
  profile: text("profile", { enum: ["compact", "full"] }).notNull(),
  status: text("status", { enum: ["draft", "in_review", "approved", "superseded"] }).notNull(),
  body: text("body").notNull(),
  note: text("note").notNull(),
  basedOn: text("based_on"),
  impact: text("impact").notNull(),
  createdAt: text("created_at").notNull(),
  updatedAt: text("updated_at").notNull(),
  createdVia: text("created_via", { enum: ["chat", "studio", "worker"] }).notNull(),
  approvedAt: text("approved_at"),
  approvedVia: text("approved_via", { enum: ["chat", "studio"] }),
});

export const characterReference = sqliteTable("character_reference", {
  id: text("id").primaryKey(),
  characterId: text("character_id").notNull(),
  path: text("path").notNull(),
  purpose: text("purpose", { enum: ["face", "silhouette", "costume", "material", "detail", "turnaround", "other"] }).notNull(),
  description: text("description").notNull(),
  isPrimary: integer("is_primary", { mode: "boolean" }).notNull(),
  ord: integer("ord").notNull(),
  meta: text("meta").notNull(),
  createdAt: text("created_at").notNull(),
});

export const critique = sqliteTable("critique", {
  id: text("id").primaryKey(),
  projectId: text("project_id").notNull(),
  stage: text("stage", { enum: ["concept", "art_direction", "plate", "rough_cut"] }).notNull(),
  role: text("role", { enum: ["director", "production_designer", "cinematographer", "editor", "emotion_editor", "creator"] }).notNull(),
  verdict: text("verdict", { enum: ["ready", "revise", "blocked"] }).notNull(),
  summary: text("summary").notNull(),
  findings: text("findings").notNull(),
  checked: text("checked").notNull(),
  notChecked: text("not_checked").notNull(),
  artDirectionId: text("art_direction_id"),
  createdAt: text("created_at").notNull(),
  resolvedAt: text("resolved_at"),
});

export type Project = typeof project.$inferSelect;
export type Shot = typeof shot.$inferSelect;
export type Character = typeof character.$inferSelect;
export type AssetVersion = typeof assetVersion.$inferSelect;
export type RenderJob = typeof renderJob.$inferSelect;

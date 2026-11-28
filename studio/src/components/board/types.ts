export type Shot = {
  id: string; ord: number; start: number; end: number; frames: number; lyric: string; visual: string;
  action: string; camera: string; has_figure: boolean; lip_sync: boolean; plate_prompt: string;
  motion_prompt: string; state: string; dirty: boolean; updated_at: string; cast: string[]; creative: Creative;
};
export type Motif = { name: string; state?: string };
export type Creative = { intent?: string; audience?: string; metaphor?: string; motifs?: Motif[]; continuity?: string };
export type Note = { id: string; asset_version_id: string; decision: string; text: string; at: string };
export type Asset = {
  id: string; shot_id: string; kind: "plate" | "clip" | "prompt"; path: string | null; text: string | null;
  source: string; cost_usd: number; active: boolean; created_at: string; notes: Note[];
  proxy?: string | null; poster?: string | null;
};
export type Reference = { id: string; path: string; purpose: string; description: string; is_primary: boolean; ord: number };
export type Character = {
  id: string; name: string; reference_image: string | null; style_line: string; references: Reference[];
};
export type Impact = {
  changed?: string[]; characters?: string[]; motifs?: string[]; review_only?: string[];
  shots?: { shot: number; reasons: string[]; assets: { id: string; kind: string; created_at: string }[] }[];
};
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type Bible = Record<string, any>;
export type ArtVersion = {
  id: string; version: number; profile: "compact" | "full"; status: "draft" | "in_review" | "approved" | "superseded";
  body: Bible; note: string; impact: Impact; created_at: string; approved_at: string | null; approved_via: string | null;
};
export type Finding = {
  observation: string; audience_impact: string; implication: string; recommendation: string; shots: number[]; motif?: string;
};
export type Critique = {
  id: string; stage: string; role: string; verdict: "ready" | "revise" | "blocked"; summary: string; findings: Finding[];
  checked: string[]; not_checked: string[]; created_at: string; resolved_at: string | null;
};
export type Job = {
  id: string; shot_id: string | null; ord: number | null; state: string; progress: number;
  sec_per_frame: number | null; stop_reason: string | null; suggestion: string | null; created_at: string;
  settings?: string | Record<string, unknown>;
};
export type Board = {
  seq: number;
  adapters: { name: string; kind: string; cost_per_image_usd: number }[];
  project: {
    id: string; title: string; folder: string; aspect: "9:16" | "16:9"; mode: string | null; visual_look: string | null;
    segment_start: number | null; segment_end: number | null; synthetic_people: number; theme: Record<string, unknown>;
  };
  analysis: { tempo_bpm: number | null; beats: number[]; lines: { start: number; end: number; text: string }[];
    peaks: number[]; verified_vocal_alignment: boolean } | null;
  shots: Shot[];
  assets: Asset[];
  characters: Character[];
  approvals: { stage: string; approved_at: string | null; via: string }[];
  jobs: Job[];
  artDirection: {
    approved: ArtVersion | null; pending: ArtVersion | null; required: boolean;
    versions: Omit<ArtVersion, "body" | "impact">[];
  };
  critiques: Critique[];
};

export const activeAsset = (b: Board, shotId: string, kind: "plate" | "clip") =>
  b.assets.find((a) => a.shot_id === shotId && a.kind === kind && a.active) || null;
export const versions = (b: Board, shotId: string, kind: "plate" | "clip") =>
  b.assets.filter((a) => a.shot_id === shotId && a.kind === kind);
export const lastJob = (b: Board, shotId: string) => b.jobs.find((j) => j.shot_id === shotId) || null;

// Bridge to the engine CLI. Only whitelisted actions run; arguments are validated and passed as an argv
// array (no shell). The engine records these changes with actor "studio".
import "server-only";
import { execFile } from "node:child_process";
import { z } from "zod";
import fs from "node:fs";
import path from "node:path";
import { ENGINE_ROOT } from "./config";

// The engine's own environment, run directly: "uv run" would re-sync it and drop the optional extras
// (demucs, mlx-whisper) that install.sh added.
const VENV_MB = path.join(ENGINE_ROOT, ".venv", "bin", "mb");
const mbCommand = (args: string[]): [string, string[]] =>
  fs.existsSync(VENV_MB) ? [VENV_MB, args] : ["uv", ["run", "--project", ENGINE_ROOT, "mb", ...args]];

export type Report = {
  ok: boolean;
  command: string;
  project: string | null;
  data: Record<string, unknown>;
  verified: string[];
  not_verified: string[];
  next: string | string[] | null;
  error?: { code: string; message: string; hint?: string };
};

const id = z.string().regex(/^[0-9A-Za-z]{4,40}$/);
const ord = z.number().int().min(0).max(999);
const word = z.string().regex(/^[a-z0-9-]{1,40}$/);
const text = z.string().max(4000);
const file = z.string().min(1).max(1000);
const shots = z.string().regex(/^[0-9, ]{1,200}$/).optional();

const ACTIONS = {
  draft: z.object({ project: id, mode: word, look: word, replace: z.boolean().optional(), shots_file: file.optional() }),
  project_new: z.object({ title: z.string().min(1).max(200), song: file, lyrics_file: file.optional(),
    idea: z.string().max(4000).optional(), aspect: z.enum(["9:16", "16:9"]), look: z.enum(["stylized", "realistic"]) }),
  analyze: z.object({ project: id }),
  modes: z.object({}),
  concepts_add: z.object({ project: id, file }),
  concepts_choose: z.object({ project: id, concept: id }),
  approve: z.object({ project: id, stage: z.enum(["storyboard", "plates", "clips", "final"]) }),
  revoke: z.object({ project: id, stage: z.enum(["storyboard", "plates", "clips", "final"]) }),
  review: z.object({ project: id, shot: ord, kind: z.enum(["plate", "clip"]), decision: z.enum(["approve", "reject"]),
    note: text.optional() }),
  plates: z.object({ project: id, adapter: z.string().max(60).optional(), shots, confirm_cost: z.boolean().optional() }),
  use_version: z.object({ project: id, asset: z.string().regex(/^[0-9A-Za-z]{10,40}$/) }),
  plate_upload: z.object({ project: id, shot: ord, file }),
  clips: z.object({ project: id, shots, redo: z.boolean().optional() }),
  worker_start: z.object({}),
  queue_pause: z.object({}),
  queue_resume: z.object({}),
  queue_stop: z.object({ project: id.optional() }),
  queue_move: z.object({ job: id, position: z.number().int().min(0).max(999) }),
  guard_set: z.object({ name: z.string().max(40) }),
  guard_create: z.object({ name: z.string().max(40), start: z.number().int(), kill: z.number().int(),
    swap: z.number().int(), poll: z.number().optional() }),
  adapter_add: z.object({ name: z.string().max(40), kind: z.enum(["manual", "command", "http", "handoff"]),
    config: z.record(z.string(), z.unknown()), cost: z.number().min(0).optional() }),
  shot_set: z.object({ project: id, shot: ord, field: z.enum(["lyric", "visual", "action", "camera", "plate_prompt", "motion_prompt", "has_figure", "lip_sync"]), value: text }),
  shot_move: z.object({ project: id, shot: ord, end: z.number() }),
  character_set: z.object({ project: id, name: z.string().max(40), field: z.enum(["style_line", "reference_image", "name"]),
    value: text }),
  character_link: z.object({ project: id, name: z.string().max(40), shots: z.string().regex(/^[0-9, ]{1,200}$/),
    on: z.boolean() }),
  export_json: z.object({ project: id, out: file, no_media: z.boolean().optional() }),
  export_pdf: z.object({ project: id, out: file }),
  export_html: z.object({ project: id, out: file, no_audio: z.boolean().optional() }),
  template_save: z.object({ project: id, name: z.string().min(1).max(60) }),
  import_json: z.object({ file }),
  sheet: z.object({ project: id, kind: z.enum(["storyboard", "plates", "clips"]).optional() }),
  finish: z.object({ project: id }),
  theme_set: z.object({ project: id, pairs: z.array(z.string().max(400)).max(30) }),
} as const;

export type Action = keyof typeof ACTIONS;
export const ACTION_NAMES = Object.keys(ACTIONS) as Action[];

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function argv(action: Action, a: any): string[] {
  const p = a.project ? ["-p", a.project] : [];
  switch (action) {
    case "draft": return ["draft", ...p, "--mode", a.mode, "--look", a.look, ...(a.replace ? ["--replace"] : []),
      ...(a.shots_file ? ["--shots-file", a.shots_file] : [])];
    case "project_new": return ["project", "new", "--title", a.title, "--song", a.song, "--aspect", a.aspect,
      "--look", a.look, ...(a.lyrics_file ? ["--lyrics-file", a.lyrics_file] : []), ...(a.idea ? ["--idea", a.idea] : [])];
    case "analyze": return ["analyze", ...p];
    case "modes": return ["modes"];
    case "concepts_add": return ["concepts", "add", ...p, "--file", a.file];
    case "concepts_choose": return ["concepts", "choose", ...p, "--concept", a.concept];
    case "approve": return ["approve", ...p, "--stage", a.stage, "--via", "studio"];
    case "revoke": return ["approve", ...p, "--stage", a.stage, "--revoke", "--via", "studio"];
    case "review": return ["review", ...p, "--shot", String(a.shot), "--kind", a.kind, "--decision", a.decision,
      ...(a.note ? ["--note", a.note] : [])];
    case "plates": return ["plates", ...p, ...(a.adapter ? ["--adapter", a.adapter] : []),
      ...(a.shots ? ["--shots", a.shots] : []), ...(a.confirm_cost ? ["--confirm-cost"] : [])];
    case "use_version": return ["use", ...p, "--asset", a.asset];
    case "plate_upload": return ["plate", "upload", ...p, "--shot", String(a.shot), "--file", a.file];
    case "clips": return ["clips", ...p, ...(a.shots ? ["--shots", a.shots] : []), ...(a.redo ? ["--redo"] : [])];
    case "worker_start": return ["worker", "--detach"];
    case "queue_pause": return ["queue", "--pause"];
    case "queue_resume": return ["queue", "--resume"];
    case "queue_stop": return ["queue", ...p, "--stop"];
    case "queue_move": return ["queue", "--move", `${a.job}:${a.position}`];
    case "guard_set": return ["guard", "--set", a.name];
    case "guard_create": return ["guard", "--create", a.name, "--start", String(a.start), "--kill", String(a.kill),
      "--swap", String(a.swap), ...(a.poll ? ["--poll", String(a.poll)] : [])];
    case "adapter_add": return ["adapter", "--add", a.name, "--kind", a.kind, "--config", JSON.stringify(a.config),
      ...(a.cost ? ["--cost", String(a.cost)] : [])];
    case "shot_set": return ["shot", "set", ...p, "--shot", String(a.shot), "--field", a.field, "--value", a.value];
    case "shot_move": return ["shot", "move", ...p, "--shot", String(a.shot), "--end", String(a.end)];
    case "character_set": return ["character", "set", ...p, "--name", a.name, "--field", a.field, "--value", a.value];
    case "character_link": return ["character", a.on ? "link" : "unlink", ...p, "--name", a.name, "--shots", a.shots];
    case "export_json": return ["export", ...p, "--out", a.out, ...(a.no_media ? ["--no-media"] : [])];
    case "export_pdf": return ["export", ...p, "--out", a.out, "--format", "pdf"];
    case "export_html": return ["export", ...p, "--out", a.out, "--format", "html", ...(a.no_audio ? ["--no-media"] : [])];
    case "template_save": return ["template", "save", ...p, "--name", a.name];
    case "import_json": return ["import", "--file", a.file];
    case "sheet": return ["sheet", ...p, ...(a.kind ? ["--kind", a.kind] : [])];
    case "finish": return ["finish", ...p];
    case "theme_set": return ["theme", ...p, ...a.pairs.flatMap((x: string) => ["--set", x])];
  }
}

export class MbBridgeError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

export function build(action: string, args: unknown): string[] {
  if (!(action in ACTIONS)) throw new MbBridgeError(400, `unknown action '${action}'`);
  const parsed = ACTIONS[action as Action].safeParse(args ?? {});
  if (!parsed.success) throw new MbBridgeError(400, `bad arguments for ${action}: ${parsed.error.issues[0]?.message}`);
  return argv(action as Action, parsed.data);
}

export function runMb(args: string[], timeoutMs = 600_000): Promise<Report> {
  return new Promise((resolve) => {
    const [cmd, argv] = mbCommand([...args, "--json"]);
    execFile(
      cmd,
      argv,
      { cwd: ENGINE_ROOT, env: { ...process.env, MB_ACTOR: "studio" }, timeout: timeoutMs, maxBuffer: 16 << 20 },
      (err, stdout, stderr) => {
        const line = stdout.trim().split("\n").filter(Boolean).pop() || "";
        try {
          resolve(JSON.parse(line) as Report);
        } catch {
          resolve({
            ok: false, command: `mb ${args[0]}`, project: null, data: {}, verified: [], not_verified: [], next: null,
            error: { code: "INTERNAL", message: (stderr || err?.message || "no output from mb").slice(-600) },
          });
        }
      },
    );
  });
}

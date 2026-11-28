// Paths the Studio shares with the engine. Same environment overrides as engine/src/motionboard/config.py.
import os from "node:os";
import path from "node:path";

const expand = (p: string) => (p.startsWith("~") ? path.join(os.homedir(), p.slice(1)) : p);

export const MB_HOME = expand(process.env.MB_HOME || "~/.motionboard");
export const DB_PATH = expand(process.env.MB_DB || path.join(MB_HOME, "motionboard.db"));
export const PROJECTS_ROOT = expand(process.env.MB_PROJECTS || "~/Motionboard/projects");
// studio/ sits next to engine/ in the repo.
export const REPO_ROOT = path.resolve(process.env.MB_REPO || path.join(process.cwd(), ".."));
export const ENGINE_ROOT = path.join(REPO_ROOT, "engine");
export const PORT = Number(process.env.PORT || 4317);
export const ORIGINS = [`http://127.0.0.1:${PORT}`, `http://localhost:${PORT}`];
export const MIN_SCHEMA = 4; // 0003: art direction, references, creative context, critiques; 0004: prompt overrides

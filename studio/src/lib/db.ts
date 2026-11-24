// One SQLite connection per server process. WAL lets the engine and the Studio read and write together.
import "server-only";
import Database from "better-sqlite3";
import { drizzle } from "drizzle-orm/better-sqlite3";
import fs from "node:fs";
import { DB_PATH, MIN_SCHEMA } from "./config";
import * as schema from "./schema";

type DB = Database.Database;
const g = globalThis as unknown as { __mbdb?: DB };

export class DbError extends Error {
  constructor(public code: "DB_MISSING" | "SCHEMA_OLD", message: string) {
    super(message);
  }
}

export function raw(): DB {
  if (g.__mbdb) return g.__mbdb;
  if (!fs.existsSync(DB_PATH)) {
    throw new DbError("DB_MISSING", `no Motionboard database at ${DB_PATH}; run: mb db migrate`);
  }
  const db = new Database(DB_PATH);
  db.pragma("journal_mode = WAL");
  db.pragma("busy_timeout = 5000");
  db.pragma("foreign_keys = ON");
  const v = (db.prepare("SELECT MAX(version) AS v FROM schema_version").get() as { v: number | null })?.v ?? 0;
  if (v < MIN_SCHEMA) {
    db.close();
    throw new DbError("SCHEMA_OLD", `database schema ${v} is older than ${MIN_SCHEMA}; run: mb db migrate`);
  }
  g.__mbdb = db;
  return db;
}

export function orm() {
  return drizzle(raw(), { schema });
}

export const now = () => new Date().toISOString().replace(/\.\d{3}Z$/, "Z");

export function emit(entity: string, entityId: string, kind: "insert" | "update" | "delete") {
  raw()
    .prepare("INSERT INTO change_event(at, entity, entity_id, kind, actor) VALUES (?, ?, ?, ?, 'studio')")
    .run(now(), entity, entityId, kind);
}

export function parseJson<T>(s: string | null | undefined, fallback: T): T {
  if (!s) return fallback;
  try {
    return JSON.parse(s) as T;
  } catch {
    return fallback;
  }
}

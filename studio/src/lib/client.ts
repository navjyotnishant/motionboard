"use client";
// Client helpers: API calls, media URLs, timecodes, and the live event subscription.
import { useEffect, useRef } from "react";

export type Report = {
  ok: boolean; command: string; data: Record<string, unknown>; verified: string[]; not_verified: string[];
  next: string | string[] | null; error?: { code: string; message: string; hint?: string };
};

export async function getJson<T>(url: string): Promise<T> {
  const r = await fetch(url, { cache: "no-store" });
  if (!r.ok) throw new Error(`${r.status} ${(await r.text()).slice(0, 200)}`);
  return r.json() as Promise<T>;
}

export async function mb(action: string, args: Record<string, unknown> = {}): Promise<Report> {
  const r = await fetch("/api/mb", {
    method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ action, args }),
  });
  const j = await r.json();
  if (!r.ok && !("ok" in j)) {
    return { ok: false, command: action, data: {}, verified: [], not_verified: [], next: null,
      error: { code: "BRIDGE", message: j.error || r.statusText } };
  }
  return j as Report;
}

export async function patchShot(id: string, updated_at: string, fields: Record<string, unknown>) {
  const r = await fetch(`/api/shots/${id}`, {
    method: "PATCH", headers: { "content-type": "application/json" }, body: JSON.stringify({ updated_at, fields }),
  });
  return { status: r.status, body: await r.json() };
}

export const media = (p: string | null | undefined, v?: string) =>
  p ? `/api/media?path=${encodeURIComponent(p)}${v ? `&v=${encodeURIComponent(v)}` : ""}` : "";

export function tc(sec: number, fps = 24): string {
  const s = Math.max(0, sec);
  const m = Math.floor(s / 60), r = Math.floor(s % 60), f = Math.floor((s - Math.floor(s)) * fps);
  return `${String(m).padStart(2, "0")}:${String(r).padStart(2, "0")}:${String(f).padStart(2, "0")}`;
}

export type ChangeEvent = { seq: number; entity: string; entity_id: string; kind: string; actor: string };

/** Subscribe to change events; `onBatch` is called at most every 250 ms with the events since the last call. */
export function useEvents(since: number | null, onBatch: (ev: ChangeEvent[]) => void) {
  const cb = useRef(onBatch);
  useEffect(() => { cb.current = onBatch; }, [onBatch]);
  useEffect(() => {
    if (since === null) return;
    const es = new EventSource(`/api/events?since=${since}`);
    let buf: ChangeEvent[] = [];
    let t: ReturnType<typeof setTimeout> | null = null;
    es.onmessage = (m) => {
      buf.push(JSON.parse(m.data));
      if (!t) t = setTimeout(() => { const b = buf; buf = []; t = null; cb.current(b); }, 250);
    };
    return () => { es.close(); if (t) clearTimeout(t); };
  }, [since]);
}

export const STATE_COLOR: Record<string, string> = {
  draft: "var(--idle)", plate_requested: "var(--info)", plate_ready: "var(--warn)", plate_approved: "var(--ok)",
  clip_queued: "var(--info)", clip_rendering: "var(--accent)", clip_ready: "var(--warn)", clip_approved: "var(--ok)",
  clip_failed: "var(--bad)", needs_redo: "var(--bad)",
};
export const STATE_LABEL: Record<string, string> = {
  draft: "Draft", plate_requested: "Plate requested", plate_ready: "Plate to review", plate_approved: "Plate approved",
  clip_queued: "Queued", clip_rendering: "Rendering", clip_ready: "Clip to review", clip_approved: "Clip approved",
  clip_failed: "Clip failed", needs_redo: "Needs redo",
};

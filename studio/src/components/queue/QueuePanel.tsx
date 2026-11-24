"use client";
// Render queue drawer: progress, time left, seconds per frame, reorder, pause, resume, stop, memory meter.
import { useCallback, useEffect, useState } from "react";
import { getJson, mb } from "@/lib/client";
import { useToast } from "@/components/ui/Toast";
import { MemoryMeter } from "./MemoryMeter";

type QJob = { id: string; state: string; progress: number; sec_per_frame: number | null; stop_reason: string | null;
  suggestion: string | null; ord: number | null; title: string | null; started_at: string | null;
  settings: { frames?: number; mode?: string } };
type Q = { jobs: QJob[]; guard: { name: string; start_free_pct: number; kill_free_pct: number; swap_ceiling_mb: number } | null;
  samples: { free_pct: number; swap_mb: number }[]; now: { free_pct: number | null; swap_mb: number | null; total_gb: number } };

function left(j: QJob): string {
  const frames = j.settings.frames ?? 0;
  if (j.state !== "running" || !j.started_at || j.progress <= 0.01) return "";
  const elapsed = (Date.now() - Date.parse(j.started_at)) / 1000;
  const s = Math.max(0, elapsed / j.progress - elapsed);
  return `${Math.floor(s / 60)}m ${Math.round(s % 60)}s left · ${frames}f`;
}

export function QueuePanel({ onClose, tick }: { onClose: () => void; tick: number }) {
  const toast = useToast();
  const [q, setQ] = useState<Q | null>(null);
  const [drag, setDrag] = useState<string | null>(null);
  const load = useCallback(() => { getJson<Q>("/api/queue").then(setQ).catch(() => {}); }, []);
  useEffect(() => { load(); const t = setInterval(load, 2000); return () => clearInterval(t); }, [load]);
  useEffect(load, [tick, load]);
  const act = async (action: string, args: Record<string, unknown> = {}) => { toast(await mb(action, args)); load(); };
  const queued = q?.jobs.filter((j) => j.state === "queued") ?? [];
  const running = q?.jobs.some((j) => j.state === "running");
  const paused = q?.jobs.some((j) => j.state === "paused");

  return (
    <div className="flex h-[300px] shrink-0 border-t border-line bg-s1">
      <div className="scroll-thin flex-1 overflow-y-auto p-3">
        <div className="mb-2 flex items-center gap-2">
          <span className="text-[13px] font-medium">Render queue</span>
          <span className="text-[12px] text-fg3">{queued.length} waiting</span>
          <div className="ml-auto flex gap-2">
            {!running && queued.length > 0 && <button className="rounded bg-accent px-2 py-0.5 text-[12px] text-accent-ink" onClick={() => act("worker_start")}>Start worker</button>}
            {paused
              ? <button className="rounded border border-line px-2 py-0.5 text-[12px]" onClick={() => act("queue_resume")}>Resume</button>
              : <button className="rounded border border-line px-2 py-0.5 text-[12px]" onClick={() => act("queue_pause")}>Pause after this shot</button>}
            <button className="rounded border border-line px-2 py-0.5 text-[12px] text-bad" onClick={() => act("queue_stop")}>Stop</button>
            <button className="px-1 text-fg3 hover:text-fg" onClick={onClose} aria-label="Close">×</button>
          </div>
        </div>
        {!q && <div className="text-fg3">Loading…</div>}
        {q && q.jobs.length === 0 && <div className="text-fg3">Nothing queued.</div>}
        <div className="space-y-1">
          {q?.jobs.map((j) => (
            <div key={j.id} draggable={j.state === "queued"}
              onDragStart={() => setDrag(j.id)}
              onDragOver={(e) => e.preventDefault()}
              onDrop={() => { if (drag && drag !== j.id) act("queue_move", { job: drag, position: queued.findIndex((x) => x.id === j.id) }); setDrag(null); }}
              className="flex items-center gap-3 rounded border border-line bg-s2 px-3 py-2 text-[12px]">
              <span className="w-10 font-medium">{j.ord ? `#${j.ord}` : "job"}</span>
              <span className="w-28 truncate text-fg3">{j.title}</span>
              <span className="w-12 uppercase text-fg3">{j.settings.mode}</span>
              <div className="h-1.5 flex-1 rounded bg-s3">
                <div className="h-full rounded" style={{ width: `${Math.round(j.progress * 100)}%`,
                  background: j.state === "failed" || j.state === "stopped" ? "var(--bad)" : j.state === "done" ? "var(--ok)" : "var(--accent)" }} />
              </div>
              <span className="tnum w-40 text-right font-mono text-fg3">
                {j.state === "running" ? left(j) : j.state}
                {j.sec_per_frame ? ` · ${j.sec_per_frame.toFixed(1)} s/f` : ""}
              </span>
              {j.stop_reason && <span className="w-56 truncate text-bad" title={`${j.stop_reason}${j.suggestion ? `. ${j.suggestion}` : ""}`}>{j.stop_reason}</span>}
            </div>
          ))}
        </div>
      </div>
      <div className="w-[300px] border-l border-line p-4">
        {q && <MemoryMeter freePct={q.now.free_pct} swapMb={q.now.swap_mb}
          swapAtStart={q.samples.length ? q.samples[0].swap_mb : null} guard={q.guard} totalGb={q.now.total_gb} />}
      </div>
    </div>
  );
}

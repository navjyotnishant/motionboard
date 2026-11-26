"use client";
// Always-on load strip for the top bar: CPU, GPU, free memory against the guard floors, and the render in progress.
// Polls the queue route; clicking it opens the queue drawer.
import { useEffect, useState } from "react";
import { getJson } from "@/lib/client";

type Now = { free_pct: number | null; swap_mb: number | null; total_gb: number; cpu_pct: number | null; gpu_pct: number | null };
type Q = {
  now: Now; paused: boolean;
  guard: { start_free_pct: number; kill_free_pct: number } | null;
  jobs: { state: string; progress: number; ord: number | null }[];
};

function Stat({ label, pct, color, title }: { label: string; pct: number | null; color: string; title: string }) {
  return (
    <span className="flex items-center gap-1" title={title}>
      <span className="h-1.5 w-1.5 rounded-full" style={{ background: color }} />
      <span className="text-fg3">{label}</span>
      <span className="tnum font-mono text-fg">{pct === null ? "–" : `${pct}%`}</span>
    </span>
  );
}

export function SystemLoad({ onOpen }: { onOpen: () => void }) {
  const [q, setQ] = useState<Q | null>(null);
  useEffect(() => {
    let on = true;
    const load = () => getJson<Q>("/api/queue").then((d) => { if (on) setQ(d); }).catch(() => {});
    load();
    const t = setInterval(load, 3000);
    return () => { on = false; clearInterval(t); };
  }, []);
  if (!q) return null;
  const { now, guard } = q;
  const kill = guard?.kill_free_pct ?? 8, start = guard?.start_free_pct ?? 35;
  const free = now.free_pct;
  const memColor = free === null ? "var(--line)" : free < kill + 5 ? "var(--bad)" : free < start ? "var(--warn)" : "var(--ok)";
  const busy = (p: number | null) => (p !== null && p > 90 ? "var(--warn)" : "var(--info)");
  const run = q.jobs.find((j) => j.state === "running");
  const waiting = q.jobs.filter((j) => j.state === "queued").length;
  const status = run
    ? `Rendering shot ${run.ord ?? "?"} · ${Math.round(run.progress * 100)}%${waiting ? ` · ${waiting} queued` : ""}`
    : q.paused ? `Paused${waiting ? ` · ${waiting} queued` : ""}`
    : waiting ? `${waiting} queued` : "Idle";
  const short = run ? `Shot ${run.ord ?? "?"} ${Math.round(run.progress * 100)}%` : q.paused ? "Paused" : waiting ? `${waiting} queued` : "Idle";
  return (
    <button onClick={onOpen} title="System load · open the render queue"
      className="flex shrink-0 items-center gap-2.5 whitespace-nowrap rounded border border-line px-2 py-1 text-[11px] hover:bg-s2">
      <Stat label="CPU" pct={now.cpu_pct} color={busy(now.cpu_pct)} title="CPU use across all cores" />
      <Stat label="GPU" pct={now.gpu_pct} color={busy(now.gpu_pct)} title="GPU busy share" />
      <Stat label="Free" pct={free} color={memColor}
        title={`Free memory of ${now.total_gb} GB. Guard stops renders below ${kill}%, starts them at ${start}%.`} />
      <span className={run ? "text-accent" : "text-fg3"} title={status}>{short}</span>
    </button>
  );
}

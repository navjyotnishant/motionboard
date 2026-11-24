"use client";
// Free memory against the guard's kill floor and start floor, and swap growth against its ceiling.
type Guard = { name: string; start_free_pct: number; kill_free_pct: number; swap_ceiling_mb: number } | null;

export function MemoryMeter({ freePct, swapMb, swapAtStart, guard, totalGb }: {
  freePct: number | null; swapMb: number | null; swapAtStart: number | null; guard: Guard; totalGb: number;
}) {
  const kill = guard?.kill_free_pct ?? 8, start = guard?.start_free_pct ?? 35;
  const f = freePct ?? 0;
  const color = f < kill + 5 ? "var(--bad)" : f < start ? "var(--warn)" : "var(--ok)";
  const growth = swapMb !== null && swapAtStart !== null ? Math.max(0, swapMb - swapAtStart) : null;
  const ceil = guard?.swap_ceiling_mb ?? 4096;
  return (
    <div className="space-y-3">
      <div>
        <div className="mb-1 flex text-[11px] text-fg3">
          <span>Free memory</span>
          <span className="tnum ml-auto font-mono text-fg">{freePct === null ? "?" : `${freePct}%`}</span>
          <span className="ml-2">of {totalGb} GB</span>
        </div>
        <div className="relative h-2 rounded bg-s3">
          <div className="absolute inset-y-0 left-0 rounded" style={{ width: `${f}%`, background: color }} />
          <div className="absolute inset-y-[-3px] w-px bg-bad" style={{ left: `${kill}%` }} title={`kill floor ${kill}%`} />
          <div className="absolute inset-y-[-3px] w-px bg-warn" style={{ left: `${start}%` }} title={`start floor ${start}%`} />
        </div>
        <div className="mt-1 flex text-[10px] text-fg3">
          <span>stop below {kill}%</span><span className="ml-auto">start at {start}%</span>
        </div>
      </div>
      <div>
        <div className="mb-1 flex text-[11px] text-fg3">
          <span>Swap growth this job</span>
          <span className="tnum ml-auto font-mono text-fg">{growth === null ? "–" : `${growth} MB`}</span>
          <span className="ml-2">ceiling {ceil} MB</span>
        </div>
        <div className="h-2 rounded bg-s3">
          <div className="h-full rounded" style={{ width: `${growth === null ? 0 : Math.min(100, (growth / Math.max(1, ceil)) * 100)}%`,
            background: growth !== null && growth > ceil * 0.8 ? "var(--bad)" : "var(--info)" }} />
        </div>
      </div>
      <div className="text-[11px] text-fg3">Guard: <span className="text-fg2">{guard?.name ?? "balanced"}</span></div>
    </div>
  );
}

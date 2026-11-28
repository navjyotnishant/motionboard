"use client";
// The four review gates. Each shows its state; the next one offers one action. A gate that cannot pass yet
// is disabled with the reason. Paid plates stop at a cost confirm modal.
import { useState } from "react";
import { mb, type Report } from "@/lib/client";
import { useToast } from "@/components/ui/Toast";
import type { Board } from "./types";

const STAGES = ["storyboard", "plates", "clips", "final"] as const;
type Stage = (typeof STAGES)[number];

function reasons(b: Board): Record<Stage, string | null> {
  const n = b.shots.length;
  const plates = b.shots.filter((s) => ["plate_approved", "clip_queued", "clip_rendering", "clip_ready", "clip_approved",
    "clip_failed"].includes(s.state)).length;
  const clips = b.shots.filter((s) => s.state === "clip_approved").length;
  const art = b.artDirection?.required ? "approve the art direction first (Art view)" : null;
  return {
    storyboard: n ? null : "draft the board first",
    plates: art ?? (plates === n && n ? null : `${n - plates} of ${n} plates not approved`),
    clips: clips === n && n ? null : `${n - clips} of ${n} clips not approved`,
    final: null,
  };
}

export function GateBar({ board, reload }: { board: Board; reload: () => void }) {
  const toast = useToast();
  const [busy, setBusy] = useState<string | null>(null);
  const [cost, setCost] = useState<{ est: number; adapter: string; shots: number[] } | null>(null);
  const [adapter, setAdapter] = useState(board.adapters[0]?.name || "manual");
  const approved = new Set(board.approvals.filter((a) => a.approved_at).map((a) => a.stage));
  const why = reasons(board);
  const next = STAGES.find((s) => !approved.has(s));
  const pid = board.project.id;

  async function act(name: string, action: string, args: Record<string, unknown> = {}): Promise<Report> {
    setBusy(name);
    const r = await mb(action, { project: pid, ...args });
    setBusy(null);
    if (r.error?.code === "COST_NOT_CONFIRMED") {
      const d = r.data as { est_cost_usd: number; adapter: string; shots: number[] };
      setCost({ est: d.est_cost_usd, adapter: d.adapter, shots: d.shots });
    } else toast(r);
    reload();
    return r;
  }

  const primary = "rounded bg-accent px-3 py-1 text-[12px] font-medium text-accent-ink";
  const quiet = "rounded border border-line px-3 py-1 text-[12px] text-fg2 hover:text-fg";

  return (
    <div className="flex items-center gap-3">
      <div className="flex items-center gap-1">
        {STAGES.map((s, i) => (
          <div key={s} className="flex items-center gap-1">
            {i > 0 && <span className="h-px w-3 bg-line" />}
            <button
              title={approved.has(s) ? `${s} approved (click to revoke)` : why[s] || `approve ${s}`}
              disabled={!!busy || (!approved.has(s) && (!!why[s] || s !== next))}
              onClick={() => act(s, approved.has(s) ? "revoke" : "approve", { stage: s })}
              className="flex items-center gap-1.5 rounded px-2 py-1 text-[12px] capitalize"
              style={{ background: s === next ? "var(--surface-3)" : "transparent",
                color: approved.has(s) ? "var(--ok)" : s === next ? "var(--text)" : "var(--text-3)" }}>
              <span className="h-1.5 w-1.5 rounded-full" style={{ background: approved.has(s) ? "var(--ok)" : "var(--idle)" }} />
              {s}
            </button>
          </div>
        ))}
      </div>
      {next === "plates" && board.artDirection?.required && (
        <span data-art-gate className="text-[12px] text-warn">Plates wait for the art direction</span>
      )}
      {next === "plates" && !board.artDirection?.required && (
        <div className="flex items-center gap-2">
          <select value={adapter} onChange={(e) => setAdapter(e.target.value)} className="w-auto py-0.5 text-[12px]">
            {board.adapters.map((a) => (
              <option key={a.name} value={a.name}>{a.name}{a.cost_per_image_usd ? ` · $${a.cost_per_image_usd}/image` : ""}</option>
            ))}
          </select>
          <button className={primary} disabled={!!busy} onClick={() => act("plates", "plates", { adapter })}>
            {busy === "plates" ? "Requesting…" : "Request plates"}
          </button>
        </div>
      )}
      {next === "clips" && (
        <button className={primary} disabled={!!busy} onClick={async () => {
          const r = await act("clips", "clips");
          if (r.ok) toast(await mb("worker_start"));
        }}>{busy === "clips" ? "Queueing…" : "Render clips"}</button>
      )}
      {next === "final" && (
        <button className={primary} disabled={!!busy} onClick={() => act("finish", "finish")}>
          {busy === "finish" ? "Finishing… (minutes)" : "Finish video"}
        </button>
      )}
      {cost && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
          <div className="w-[380px] rounded-md border border-line bg-s1 p-5">
            <div className="text-[15px] font-medium">Confirm cost</div>
            <p className="mt-2 text-fg2">
              {cost.shots.length} plate{cost.shots.length === 1 ? "" : "s"} with <b className="text-fg">{cost.adapter}</b> cost
              about <b className="text-fg">${cost.est.toFixed(2)}</b>. Nothing has been sent yet.
            </p>
            <div className="mt-4 flex justify-end gap-2">
              <button className={quiet} onClick={() => setCost(null)}>Cancel</button>
              <button className={primary} onClick={() => { setCost(null); act("plates", "plates", { adapter: cost.adapter, confirm_cost: true }); }}>
                Spend ${cost.est.toFixed(2)}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

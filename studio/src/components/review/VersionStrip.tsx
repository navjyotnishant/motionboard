"use client";
// Every plate and clip made for the shot, newest last, with the notes left on each.
import { useState } from "react";
import { media } from "@/lib/client";
import { versions, type Board, type Shot } from "@/components/board/types";

export function VersionStrip({ board, shot }: { board: Board; shot: Shot; reload: () => void }) {
  const [open, setOpen] = useState<string | null>(null);
  const all = [...versions(board, shot.id, "plate"), ...versions(board, shot.id, "clip")];
  if (all.length === 0) return null;
  const shown = all.find((a) => a.id === open);
  const ratio = board.project.aspect === "16:9" ? "16 / 9" : "9 / 16";
  return (
    <div className="border-b border-line px-4 py-3">
      <div className="mb-2 text-[11px] uppercase tracking-wider text-fg3">Versions</div>
      <div className="flex gap-2 overflow-x-auto pb-1">
        {all.map((a, i) => (
          <button key={a.id} onClick={() => setOpen(open === a.id ? null : a.id)}
            className="relative w-14 shrink-0 overflow-hidden rounded border"
            style={{ aspectRatio: ratio, borderColor: a.active ? "var(--accent)" : "var(--line)" }}
            title={`${a.kind} v${i + 1} · ${a.source}${a.active ? " · active" : ""}`}>
            {a.kind === "plate"
              ? <img src={media(a.path, a.id)} alt="" className="h-full w-full object-cover" />
              : a.poster ? <img src={media(a.poster, a.id)} alt="" className="h-full w-full object-cover" />
                : <video src={media(a.path, a.id)} muted preload="metadata" className="h-full w-full object-cover" />}
            <span className="absolute bottom-0 left-0 bg-black/70 px-1 text-[9px] uppercase">{a.kind}</span>
          </button>
        ))}
      </div>
      {shown && (
        <div className="mt-2 rounded border border-line bg-s2 p-2">
          {shown.kind === "plate"
            ? <img src={media(shown.path, shown.id)} alt="" className="w-full rounded" />
            : <video src={media(shown.path, shown.id)} controls autoPlay loop className="w-full rounded" />}
          <div className="mt-2 text-[11px] text-fg3">{shown.source}{shown.cost_usd ? ` · $${shown.cost_usd.toFixed(2)}` : ""}</div>
          {shown.notes.map((n) => (
            <div key={n.id} className="mt-1 text-[12px]">
              <span style={{ color: n.decision === "reject" ? "var(--bad)" : n.decision === "approve" ? "var(--ok)" : "var(--text-2)" }}>
                {n.decision}
              </span>
              {n.text && <span className="text-fg2"> · {n.text}</span>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

"use client";
// Approve or reject what the shot is waiting on (the clip if there is one, else the plate). A reject
// needs a note, so the next version can fix it. A and R on the keyboard do the same.
import { useEffect, useRef, useState } from "react";
import { mb } from "@/lib/client";
import { useToast } from "@/components/ui/Toast";
import { activeAsset, type Board, type Shot } from "@/components/board/types";

export function reviewKind(board: Board, shot: Shot): "plate" | "clip" | null {
  if (activeAsset(board, shot.id, "clip")) return "clip";
  if (activeAsset(board, shot.id, "plate")) return "plate";
  return null;
}

export function ApproveBar({ board, shot, reload, rejectSignal }: {
  board: Board; shot: Shot; reload: () => void; rejectSignal: number;
}) {
  const toast = useToast();
  const kind = reviewKind(board, shot);
  const [noting, setNoting] = useState(false);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [path, setPath] = useState("");
  const ref = useRef<HTMLTextAreaElement>(null);
  const first = useRef(rejectSignal);
  useEffect(() => {
    if (rejectSignal !== first.current && kind) { setNoting(true); setTimeout(() => ref.current?.focus(), 0); }
  }, [rejectSignal, kind]);
  useEffect(() => { setNoting(false); setNote(""); }, [shot.id]);

  async function review(decision: "approve" | "reject") {
    if (!kind) return;
    setBusy(true);
    const r = await mb("review", { project: board.project.id, shot: shot.ord, kind, decision, note: note || undefined });
    setBusy(false);
    toast(r);
    if (r.ok) { setNoting(false); setNote(""); }
    reload();
  }

  return (
    <div className="border-b border-line px-4 py-3">
      {kind ? (
        <div className="flex items-center gap-2">
          <span className="text-[12px] text-fg2">Review {kind}</span>
          <button disabled={busy} onClick={() => review("approve")}
            className="ml-auto rounded bg-accent px-3 py-1 text-[12px] font-medium text-accent-ink">Approve <kbd className="opacity-60">A</kbd></button>
          <button disabled={busy} onClick={() => { setNoting(true); setTimeout(() => ref.current?.focus(), 0); }}
            className="rounded border border-line px-3 py-1 text-[12px] text-fg2 hover:text-fg">Reject <kbd className="opacity-60">R</kbd></button>
        </div>
      ) : (
        <div className="text-[12px] text-fg3">No plate yet. Request plates from the gate bar, or upload one.</div>
      )}
      {noting && (
        <div className="mt-2">
          <textarea ref={ref} rows={2} value={note} placeholder="What should change? (required)"
            onChange={(e) => setNote(e.target.value)} />
          <div className="mt-1 flex justify-end gap-2">
            <button className="text-[12px] text-fg3" onClick={() => setNoting(false)}>Cancel</button>
            <button disabled={busy || !note.trim()} onClick={() => review("reject")}
              className="rounded bg-bad px-3 py-1 text-[12px] font-medium text-white">Reject with note</button>
          </div>
        </div>
      )}
      <div className="mt-2 flex gap-2">
        <input value={path} onChange={(e) => setPath(e.target.value)} placeholder="Upload a plate: /path/to/image.png"
          className="text-[12px]" />
        <button disabled={busy || !path.trim()} className="shrink-0 rounded border border-line px-2 text-[12px] text-fg2"
          onClick={async () => {
            setBusy(true);
            const r = await mb("plate_upload", { project: board.project.id, shot: shot.ord, file: path.trim() });
            setBusy(false); toast(r); if (r.ok) setPath(""); reload();
          }}>Upload</button>
      </div>
    </div>
  );
}

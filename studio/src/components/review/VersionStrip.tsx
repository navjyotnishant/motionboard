"use client";
// Every plate and clip made for the shot, newest last, with the notes left on each.
// Clip takes preview with the shot's slice of the song, in sync, and any take can be made the one the shot uses.
import { useEffect, useRef, useState } from "react";
import { media, mb } from "@/lib/client";
import { useToast } from "@/components/ui/Toast";
import { versions, type Asset, type Board, type Shot } from "@/components/board/types";

function TakePreview({ board, shot, take }: { board: Board; shot: Shot; take: Asset }) {
  const vid = useRef<HTMLVideoElement>(null);
  const aud = useRef<HTMLAudioElement>(null);
  const len = shot.end - shot.start;
  const segment = `${board.project.folder}/audio/segment.wav`;
  // Keep the song slice under the (muted) take: same position, same play state, looping at the cut.
  useEffect(() => {
    const v = vid.current, a = aud.current;
    if (!v || !a) return;
    const sync = () => { a.currentTime = shot.start + Math.min(v.currentTime, len); };
    const onPlay = () => { sync(); a.play().catch(() => {}); };
    const onPause = () => a.pause();
    const onTime = () => {
      if (v.currentTime >= len) { v.currentTime = 0; sync(); }
      else if (Math.abs(a.currentTime - (shot.start + v.currentTime)) > 0.12) sync();
    };
    v.addEventListener("play", onPlay); v.addEventListener("pause", onPause);
    v.addEventListener("seeked", sync); v.addEventListener("timeupdate", onTime);
    if (!v.paused) onPlay();
    return () => {
      a.pause();
      v.removeEventListener("play", onPlay); v.removeEventListener("pause", onPause);
      v.removeEventListener("seeked", sync); v.removeEventListener("timeupdate", onTime);
    };
  }, [take.id, shot.start, len]);
  return (
    <>
      <video ref={vid} src={media(take.path, take.id)} controls autoPlay muted playsInline className="w-full rounded" />
      <audio ref={aud} src={media(segment)} preload="auto" />
    </>
  );
}

export function VersionStrip({ board, shot, reload }: { board: Board; shot: Shot; reload: () => void }) {
  const toast = useToast();
  const [open, setOpen] = useState<string | null>(null);
  const plates = versions(board, shot.id, "plate");
  const clips = versions(board, shot.id, "clip");
  const all = [...plates, ...clips];
  if (all.length === 0) return null;
  const shown = all.find((a) => a.id === open);
  const ratio = board.project.aspect === "16:9" ? "16 / 9" : "9 / 16";
  const label = (a: Asset) => {
    const n = (a.kind === "plate" ? plates : clips).indexOf(a) + 1;
    return `${a.kind === "plate" ? "Image" : "Take"} ${n}`;
  };
  const use = async (a: Asset) => {
    toast(await mb("use_version", { project: board.project.id, asset: a.id }));
    reload();
  };
  return (
    <div className="border-b border-line px-4 py-3">
      <div className="mb-2 flex text-[11px] uppercase tracking-wider text-fg3">
        <span>Versions</span>
        {clips.length > 1 && (
          <span className="ml-auto normal-case tracking-normal">{clips.length} takes · tap one to play it with the song</span>
        )}
      </div>
      <div className="flex gap-2 overflow-x-auto pb-1">
        {all.map((a) => (
          <button key={a.id} onClick={() => setOpen(open === a.id ? null : a.id)}
            className="relative w-14 shrink-0 overflow-hidden rounded border"
            style={{ aspectRatio: ratio, borderColor: open === a.id ? "var(--fg)" : a.active ? "var(--accent)" : "var(--line)" }}
            title={`${label(a)} · ${a.source}${a.active ? " · in use" : ""}`}>
            {a.kind === "plate"
              ? <img src={media(a.path, a.id)} alt="" className="h-full w-full object-cover" />
              : a.poster ? <img src={media(a.poster, a.id)} alt="" className="h-full w-full object-cover" />
                : <video src={media(a.path, a.id)} muted preload="metadata" className="h-full w-full object-cover" />}
            <span className="absolute bottom-0 left-0 right-0 bg-black/70 px-1 text-[9px]">{label(a)}{a.active ? " ●" : ""}</span>
          </button>
        ))}
      </div>
      {shown && (
        <div className="mt-2 rounded border border-line bg-s2 p-2">
          {shown.kind === "plate"
            ? <img src={media(shown.path, shown.id)} alt="" className="w-full rounded" />
            : <TakePreview board={board} shot={shot} take={shown} />}
          <div className="mt-2 flex items-center gap-2 text-[11px] text-fg3">
            <span>{label(shown)} · {shown.source}{shown.cost_usd ? ` · $${shown.cost_usd.toFixed(2)}` : ""}</span>
            {shown.active
              ? <span className="ml-auto text-accent">In use</span>
              : (
                <button onClick={() => use(shown)}
                  className="ml-auto rounded bg-accent px-2 py-1 text-[12px] font-medium text-black hover:opacity-90">
                  Use this {shown.kind === "plate" ? "image" : "take"}
                </button>
              )}
          </div>
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

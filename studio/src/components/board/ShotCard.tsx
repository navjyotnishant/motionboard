"use client";
// One shot: the frame (clip if there is one, else the plate), a thin bar with number, timecode and state.
// Hovering a clip plays it muted; a guard stop shows its reason and suggestion on the card.
import { useEffect, useRef } from "react";
import { media, STATE_COLOR, STATE_LABEL, tc } from "@/lib/client";
import { directionChanged } from "@/lib/art";
import { activeAsset, lastJob, type Board, type Shot } from "./types";

export function ShotCard({ board, shot, selected, onSelect, onOpen, playing, audioOn = false, offset = 0, solo = false, onPlay }: {
  board: Board; shot: Shot; selected: boolean; onSelect: () => void; onOpen: () => void; playing: boolean;
  audioOn?: boolean; offset?: number; solo?: boolean; onPlay?: () => void;
}) {
  const plate = activeAsset(board, shot.id, "plate");
  const clip = activeAsset(board, shot.id, "clip");
  const job = lastJob(board, shot.id);
  const vid = useRef<HTMLVideoElement>(null);
  const ratio = board.project.aspect === "16:9" ? "16 / 9" : "9 / 16";
  // While the song plays through this shot, run the clip muted and in step with the audio.
  const synced = playing && audioOn && !!clip?.path;
  useEffect(() => {
    const v = vid.current;
    if (!v) return;
    if (synced) {
      if (Math.abs(v.currentTime - offset) > 0.15) v.currentTime = Math.max(0, offset);
      if (v.paused) v.play().catch(() => {});
    } else if (!v.paused && !v.matches(":hover")) {
      v.pause();
    }
  }, [synced, offset]);
  const failed = job && (job.state === "failed" || job.state === "stopped") && shot.state !== "clip_approved";
  const stale = directionChanged(board).has(shot.id);
  return (
    <div
      data-shot={shot.ord}
      onClick={onSelect}
      onDoubleClick={onOpen}
      onMouseEnter={() => vid.current?.play().catch(() => {})}
      onMouseLeave={() => { if (vid.current && !synced) { vid.current.pause(); vid.current.currentTime = 0; } }}
      className="cursor-pointer select-none rounded-md border bg-s1"
      style={{ borderColor: selected ? "var(--accent)" : playing ? "var(--line-strong)" : "var(--line)" }}
    >
      <div className="relative overflow-hidden rounded-t-md bg-s3" style={{ aspectRatio: ratio }}>
        {clip?.path ? (
          <video ref={vid} src={media(clip.proxy || clip.path, clip.id)}
            poster={clip.poster ? media(clip.poster, clip.id) : plate?.path ? media(plate.path, plate.id) : undefined}
            muted loop={!synced} playsInline preload="metadata" className="h-full w-full object-cover" />
        ) : plate?.path ? (
          <img src={media(plate.path, plate.id)} alt="" loading="lazy" className="h-full w-full object-cover" />
        ) : (
          <div className="flex h-full flex-col justify-end p-2 text-[11px] leading-snug text-fg3">
            <span className="line-clamp-6">{shot.visual}</span>
          </div>
        )}
        {shot.state === "clip_rendering" && job && (
          <div className="absolute inset-x-0 bottom-0 h-1 bg-black/40">
            <div className="h-full bg-accent" style={{ width: `${Math.round(job.progress * 100)}%` }} />
          </div>
        )}
        {shot.lip_sync && (
          <span className="absolute left-1.5 top-1.5 rounded bg-black/60 px-1.5 py-0.5 text-[10px] text-fg">LIP-SYNC</span>
        )}
        {onPlay && (
          <button
            onClick={(e) => { e.stopPropagation(); onPlay(); }}
            onDoubleClick={(e) => e.stopPropagation()}
            title={solo ? "Stop" : clip?.path ? "Play this shot with its audio (P)" : "Play this shot's audio (P)"}
            aria-label={solo ? "Stop shot" : "Play shot"}
            className={`absolute bottom-1.5 right-1.5 flex h-7 w-7 items-center justify-center rounded-full text-black shadow ${solo ? "bg-accent" : "bg-white/85 hover:bg-accent"}`}>
            {solo ? (
              <svg width="10" height="10" viewBox="0 0 10 10"><rect x="1.5" y="1.5" width="7" height="7" fill="currentColor" /></svg>
            ) : (
              <svg width="10" height="10" viewBox="0 0 10 10"><path d="M2.5 1 L9 5 L2.5 9 Z" fill="currentColor" /></svg>
            )}
          </button>
        )}
        {shot.dirty && (
          <span className="absolute right-1.5 top-1.5 rounded bg-bad/80 px-1.5 py-0.5 text-[10px] text-white">REDO</span>
        )}
        {!shot.dirty && stale && (
          <span data-direction-changed title="Made under an earlier art direction; redo when you choose"
            className="absolute right-1.5 top-1.5 rounded bg-warn/80 px-1.5 py-0.5 text-[10px] text-black">DIRECTION</span>
        )}
        {failed && (
          <div className="absolute inset-x-0 bottom-0 bg-black/75 p-2 text-[11px] leading-snug">
            <div className="text-bad">{job.stop_reason || "render failed"}</div>
            {job.suggestion && <div className="mt-0.5 text-fg2">{job.suggestion}</div>}
          </div>
        )}
      </div>
      <div className="flex items-center gap-2 px-2 py-1.5 text-[11px]">
        <span className="font-medium text-fg">{String(shot.ord).padStart(2, "0")}</span>
        <span className="tnum font-mono text-fg3">{tc(shot.start)}</span>
        <span className="tnum font-mono text-fg3">{(shot.end - shot.start).toFixed(1)}s</span>
        <span className="ml-auto flex items-center gap-1 text-fg3" title={STATE_LABEL[shot.state]}>
          <span className="h-2 w-2 rounded-full" style={{ background: STATE_COLOR[shot.state] }} />
        </span>
      </div>
      <div className="space-y-1 border-t border-line px-2 py-2 text-[12px] leading-snug">
        {shot.lyric && <div className="line-clamp-3 italic text-fg2">“{shot.lyric}”</div>}
        <div className="line-clamp-4 text-fg">{shot.action}</div>
      </div>
    </div>
  );
}

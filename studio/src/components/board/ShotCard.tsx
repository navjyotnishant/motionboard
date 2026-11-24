"use client";
// One shot: the frame (clip if there is one, else the plate), a thin bar with number, timecode and state.
// Hovering a clip plays it muted; a guard stop shows its reason and suggestion on the card.
import { useRef } from "react";
import { media, STATE_COLOR, STATE_LABEL, tc } from "@/lib/client";
import { activeAsset, lastJob, type Board, type Shot } from "./types";

export function ShotCard({ board, shot, selected, onSelect, onOpen, playing }: {
  board: Board; shot: Shot; selected: boolean; onSelect: () => void; onOpen: () => void; playing: boolean;
}) {
  const plate = activeAsset(board, shot.id, "plate");
  const clip = activeAsset(board, shot.id, "clip");
  const job = lastJob(board, shot.id);
  const vid = useRef<HTMLVideoElement>(null);
  const ratio = board.project.aspect === "16:9" ? "16 / 9" : "9 / 16";
  const failed = job && (job.state === "failed" || job.state === "stopped") && shot.state !== "clip_approved";
  return (
    <div
      data-shot={shot.ord}
      onClick={onSelect}
      onDoubleClick={onOpen}
      onMouseEnter={() => vid.current?.play().catch(() => {})}
      onMouseLeave={() => { if (vid.current) { vid.current.pause(); vid.current.currentTime = 0; } }}
      className="cursor-pointer select-none rounded-md border bg-s1"
      style={{ borderColor: selected ? "var(--accent)" : playing ? "var(--line-strong)" : "var(--line)" }}
    >
      <div className="relative overflow-hidden rounded-t-md bg-s3" style={{ aspectRatio: ratio }}>
        {clip?.path ? (
          <video ref={vid} src={media(clip.proxy || clip.path, clip.id)}
            poster={clip.poster ? media(clip.poster, clip.id) : plate?.path ? media(plate.path, plate.id) : undefined}
            muted loop playsInline preload="none" className="h-full w-full object-cover" />
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
        {shot.dirty && (
          <span className="absolute right-1.5 top-1.5 rounded bg-bad/80 px-1.5 py-0.5 text-[10px] text-white">REDO</span>
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
    </div>
  );
}

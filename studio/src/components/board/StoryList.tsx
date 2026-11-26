"use client";
// The board as a script: one row per shot, read top to bottom without opening a card.
// Time and lyric on the left, what happens on the right, a small frame when a plate exists.
import { media, STATE_COLOR, STATE_LABEL, tc } from "@/lib/client";
import { activeAsset, type Board } from "./types";

export function StoryList({ board, selected, playing, onSelect, onOpen, solo = null, onPlay }: {
  board: Board; selected: string | null; playing: string | null;
  onSelect: (id: string) => void; onOpen: (id: string) => void;
  solo?: string | null; onPlay?: (id: string) => void;
}) {
  const wide = board.project.aspect === "16:9";
  const names = new Map(board.characters.map((c) => [c.id, c.name]));
  return (
    <ol className="mx-auto max-w-4xl divide-y divide-line rounded-md border border-line bg-s1">
      {board.shots.map((s) => {
        const plate = activeAsset(board, s.id, "plate");
        const on = s.id === selected;
        return (
          <li
            key={s.id}
            data-shot={s.ord}
            onClick={() => onSelect(s.id)}
            onDoubleClick={() => onOpen(s.id)}
            className="flex cursor-pointer gap-4 px-4 py-3 hover:bg-s2"
            style={{ boxShadow: on ? "inset 3px 0 0 var(--accent)" : s.id === playing ? "inset 3px 0 0 var(--line-strong)" : undefined }}
          >
            <div className="w-24 shrink-0 text-[12px]">
              <div className="flex items-center gap-2">
                <span className="font-medium text-fg">{String(s.ord).padStart(2, "0")}</span>
                {onPlay && (
                  <button onClick={(e) => { e.stopPropagation(); onPlay(s.id); }} onDoubleClick={(e) => e.stopPropagation()}
                    title={solo === s.id ? "Stop" : "Play this shot with its audio (P)"} aria-label={solo === s.id ? "Stop shot" : "Play shot"}
                    className={`flex h-6 w-6 items-center justify-center rounded-full text-black ${solo === s.id ? "bg-accent" : "bg-fg2 hover:bg-accent"}`}>
                    {solo === s.id ? (
                      <svg width="9" height="9" viewBox="0 0 10 10"><rect x="1.5" y="1.5" width="7" height="7" fill="currentColor" /></svg>
                    ) : (
                      <svg width="9" height="9" viewBox="0 0 10 10"><path d="M2.5 1 L9 5 L2.5 9 Z" fill="currentColor" /></svg>
                    )}
                  </button>
                )}
              </div>
              <div className="tnum font-mono text-fg3">{tc(s.start)}</div>
              <div className="tnum font-mono text-fg3">{(s.end - s.start).toFixed(1)}s</div>
              <div className="mt-1 flex items-center gap-1 text-[11px] text-fg3">
                <span className="h-2 w-2 rounded-full" style={{ background: STATE_COLOR[s.state] }} />
                {STATE_LABEL[s.state]}
              </div>
            </div>
            <div className="min-w-0 flex-1 space-y-1.5 text-[13px] leading-relaxed">
              {s.lyric && <div className="italic text-fg2">“{s.lyric}”</div>}
              <div className="text-fg">{s.action}</div>
              <div className="text-[12px] text-fg3">{s.visual}</div>
              <div className="flex flex-wrap gap-x-3 text-[11px] text-fg3">
                {s.camera && <span>camera: {s.camera}</span>}
                <span>{s.has_figure ? (s.cast.length ? s.cast.map((c) => names.get(c) ?? c).join(", ") : "figure") : "no figure"}</span>
                {s.lip_sync && <span className="text-accent">lip-sync</span>}
                {s.dirty && <span className="text-bad">redo</span>}
              </div>
            </div>
            {plate?.path && (
              <img src={media(plate.path, plate.id)} alt="" loading="lazy"
                className="shrink-0 rounded object-cover"
                style={{ width: wide ? 128 : 54, aspectRatio: wide ? "16 / 9" : "9 / 16" }} />
            )}
          </li>
        );
      })}
    </ol>
  );
}

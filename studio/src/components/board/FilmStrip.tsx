"use client";
// A strip of frames under the waveform, each as wide as its shot is long.
import { media } from "@/lib/client";
import { activeAsset, type Board } from "./types";

export function FilmStrip({ board, selected, onSelect }: {
  board: Board; selected: string | null; onSelect: (id: string) => void;
}) {
  const shots = board.shots;
  const dur = shots.length ? shots[shots.length - 1].end : 1;
  return (
    <div className="flex h-11 w-full overflow-hidden border-t border-line bg-bg">
      {shots.map((s) => {
        const plate = activeAsset(board, s.id, "plate");
        return (
          <button key={s.id} onClick={() => onSelect(s.id)} title={`Shot ${s.ord}`}
            className="relative h-full overflow-hidden border-r border-line"
            style={{ width: `${((s.end - s.start) / dur) * 100}%`, outline: s.id === selected ? "1px solid var(--accent)" : undefined,
              outlineOffset: -1 }}>
            {plate?.path
              ? <img src={media(plate.path, plate.id)} alt="" className="h-full w-full object-cover opacity-80" loading="lazy" />
              : <div className="h-full w-full bg-s2" />}
          </button>
        );
      })}
    </div>
  );
}

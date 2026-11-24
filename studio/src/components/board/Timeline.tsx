"use client";
// Waveform from stored peaks with beats, sung lines and shot regions. Drag a cut to move it; it snaps to a
// beat within 120 ms. Click anywhere to seek. A canvas keeps it fast with long songs and many beats.
import { useCallback, useEffect, useRef, useState } from "react";
import { tc } from "@/lib/client";
import type { Board } from "./types";

const SNAP = 0.12;
const H = 120;

export function Timeline({ board, time, selected, onSeek, onSelect, onMoveCut }: {
  board: Board; time: number; selected: string | null; onSeek: (t: number) => void;
  onSelect: (shotId: string) => void; onMoveCut: (ord: number, end: number) => void;
}) {
  const wrap = useRef<HTMLDivElement>(null);
  const cv = useRef<HTMLCanvasElement>(null);
  const [w, setW] = useState(800);
  const [drag, setDrag] = useState<{ ord: number; t: number } | null>(null);
  const shots = board.shots;
  const dur = shots.length ? shots[shots.length - 1].end : (board.project.segment_end ?? 0) - (board.project.segment_start ?? 0) || 1;
  const beats = board.analysis?.beats ?? [];
  const lines = board.analysis?.lines ?? [];
  const peaks = board.analysis?.peaks ?? [];
  const x = useCallback((t: number) => (t / dur) * w, [dur, w]);
  const tOf = useCallback((px: number) => Math.max(0, Math.min(dur, (px / w) * dur)), [dur, w]);

  useEffect(() => {
    const el = wrap.current;
    if (!el) return;
    const ro = new ResizeObserver(() => setW(el.clientWidth));
    ro.observe(el);
    setW(el.clientWidth);
    return () => ro.disconnect();
  }, []);

  const snap = useCallback((t: number) => {
    let best = t, bd = SNAP;
    for (const b of beats) { const d = Math.abs(b - t); if (d < bd) { bd = d; best = b; } }
    return best;
  }, [beats]);

  useEffect(() => {
    const c = cv.current;
    if (!c) return;
    const dpr = window.devicePixelRatio || 1;
    c.width = w * dpr; c.height = H * dpr;
    const g = c.getContext("2d")!;
    g.setTransform(dpr, 0, 0, dpr, 0, 0);
    const css = getComputedStyle(document.documentElement);
    const col = (n: string) => css.getPropertyValue(n).trim();
    g.fillStyle = col("--surface-1"); g.fillRect(0, 0, w, H);
    // shot regions
    shots.forEach((s, i) => {
      const end = drag && drag.ord === s.ord ? drag.t : s.end;
      const start = drag && drag.ord === s.ord - 1 ? drag.t : s.start;
      g.fillStyle = s.id === selected ? "rgba(232,176,97,0.16)" : i % 2 ? "rgba(255,255,255,0.03)" : "rgba(255,255,255,0.06)";
      g.fillRect(x(start), 18, x(end) - x(start), H - 18);
      g.fillStyle = col("--text-3"); g.font = "10px ui-monospace, monospace";
      g.fillText(String(s.ord).padStart(2, "0"), x(start) + 4, H - 6);
    });
    // waveform
    const mid = 18 + (H - 18) / 2, amp = (H - 30) / 2;
    g.fillStyle = col("--text-3");
    if (peaks.length) {
      for (let px = 0; px < w; px++) {
        const i = Math.floor((px / w) * peaks.length);
        const v = Math.abs(peaks[i] ?? 0);
        g.fillRect(px, mid - v * amp, 1, Math.max(1, v * amp * 2));
      }
    }
    // beats
    g.fillStyle = "rgba(255,255,255,0.18)";
    for (const b of beats) g.fillRect(Math.round(x(b)), 18, 1, 6);
    // sung lines
    g.fillStyle = "rgba(111,168,239,0.55)";
    for (const l of lines) g.fillRect(x(l.start), 4, Math.max(2, x(l.end) - x(l.start) - 2), 6);
    // cuts
    shots.slice(0, -1).forEach((s) => {
      const t = drag && drag.ord === s.ord ? drag.t : s.end;
      g.fillStyle = drag && drag.ord === s.ord ? col("--accent") : col("--line-strong");
      g.fillRect(Math.round(x(t)) - 1, 14, 2, H - 14);
    });
    // playhead
    g.fillStyle = col("--accent");
    g.fillRect(Math.round(x(time)), 0, 1, H);
  }, [w, shots, beats, lines, peaks, time, selected, drag, x]);

  const cutNear = (px: number) => {
    for (const s of shots.slice(0, -1)) if (Math.abs(x(s.end) - px) <= 5) return s.ord;
    return null;
  };

  return (
    <div className="border-t border-line bg-s1">
      <div className="flex items-center gap-3 px-3 py-1 text-[11px] text-fg3">
        <span className="tnum font-mono text-fg">{tc(time)}</span>
        <span className="tnum font-mono">/ {tc(dur)}</span>
        {board.analysis?.tempo_bpm && <span>{Math.round(board.analysis.tempo_bpm)} BPM</span>}
        <span className="ml-auto">drag a cut to move it · snaps to beats</span>
      </div>
      <div ref={wrap} className="relative h-[120px] w-full">
        <canvas
          ref={cv}
          style={{ width: w, height: H, cursor: drag ? "ew-resize" : "default" }}
          onPointerMove={(e) => {
            const px = e.nativeEvent.offsetX;
            if (drag) {
              const s = shots.find((q) => q.ord === drag.ord)!;
              const nxt = shots.find((q) => q.ord === drag.ord + 1)!;
              const t = Math.min(nxt.end - 0.5, Math.max(s.start + 0.5, snap(tOf(px))));
              setDrag({ ord: drag.ord, t });
            } else {
              (e.target as HTMLCanvasElement).style.cursor = cutNear(px) ? "ew-resize" : "pointer";
            }
          }}
          onPointerDown={(e) => {
            const px = e.nativeEvent.offsetX;
            const ord = cutNear(px);
            if (ord) {
              (e.target as HTMLCanvasElement).setPointerCapture(e.pointerId);
              setDrag({ ord, t: shots.find((s) => s.ord === ord)!.end });
            } else {
              const t = tOf(px);
              onSeek(t);
              const s = shots.find((q) => t >= q.start && t < q.end);
              if (s) onSelect(s.id);
            }
          }}
          onPointerUp={() => {
            if (drag) {
              const s = shots.find((q) => q.ord === drag.ord)!;
              if (Math.abs(drag.t - s.end) > 0.01) onMoveCut(drag.ord, Math.round(drag.t * 1000) / 1000);
              setDrag(null);
            }
          }}
        />
      </div>
    </div>
  );
}

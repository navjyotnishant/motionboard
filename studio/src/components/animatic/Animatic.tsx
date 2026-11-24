"use client";
// Full screen animatic: each shot's clip (or plate) over the song segment, with the sung line.
// Space plays and pauses, J and L step back and forward a shot, K pauses, Esc closes.
import { useEffect, useRef, useState } from "react";
import { media, tc } from "@/lib/client";
import { activeAsset, type Board } from "@/components/board/types";

export function Animatic({ board, audio, onClose }: { board: Board; audio: string; onClose: () => void }) {
  const a = useRef<HTMLAudioElement>(null);
  const v = useRef<HTMLVideoElement>(null);
  const [t, setT] = useState(0);
  const [playing, setPlaying] = useState(false);
  const shots = board.shots;
  const cur = shots.find((s) => t >= s.start && t < s.end) || shots[shots.length - 1];
  const clip = cur && activeAsset(board, cur.id, "clip");
  const plate = cur && activeAsset(board, cur.id, "plate");
  const line = board.analysis?.lines.find((l) => t >= l.start && t < l.end);

  useEffect(() => {
    let raf = 0;
    const loop = () => { if (a.current) setT(a.current.currentTime); raf = requestAnimationFrame(loop); };
    raf = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(raf);
  }, []);
  useEffect(() => {
    if (!v.current || !cur) return;
    const want = t - cur.start;
    if (Math.abs(v.current.currentTime - want) > 0.15) v.current.currentTime = Math.max(0, want);
    if (playing) v.current.play().catch(() => {}); else v.current.pause();
  }, [t, cur, playing]);
  useEffect(() => {
    const step = (d: number) => {
      const i = shots.findIndex((s) => s.id === cur?.id);
      const s = shots[Math.max(0, Math.min(shots.length - 1, i + d))];
      if (a.current && s) a.current.currentTime = s.start;
    };
    const toggle = () => { const el = a.current; if (!el) return; if (el.paused) el.play(); else el.pause(); };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      else if (e.key === " ") { e.preventDefault(); toggle(); }
      else if (e.key === "k") a.current?.pause();
      else if (e.key === "j") step(-1);
      else if (e.key === "l") step(1);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [shots, cur, onClose]);

  const ratio = board.project.aspect === "16:9" ? "16 / 9" : "9 / 16";
  return (
    <div className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-black">
      <audio ref={a} src={audio} onPlay={() => setPlaying(true)} onPause={() => setPlaying(false)} autoPlay />
      <div className="relative h-[82vh] overflow-hidden bg-neutral-900" style={{ aspectRatio: ratio }}>
        {clip?.path
          ? <video key={clip.id} ref={v} src={media(clip.path, clip.id)} muted playsInline className="h-full w-full object-cover" />
          : plate?.path ? <img src={media(plate.path, plate.id)} alt="" className="h-full w-full object-cover" />
            : <div className="flex h-full items-center justify-center p-8 text-center text-fg3">{cur?.visual}</div>}
        {line && <div className="absolute inset-x-0 bottom-[12%] px-6 text-center text-[22px] font-medium text-white [text-shadow:0_2px_12px_rgba(0,0,0,.9)]">{line.text}</div>}
      </div>
      <div className="mt-3 flex items-center gap-4 text-[12px] text-fg3">
        <span className="tnum font-mono text-fg">{tc(t)}</span>
        <span>shot {cur?.ord}</span>
        <span>Space play · J/L shot · Esc close</span>
        <button className="text-fg2 hover:text-fg" onClick={onClose}>Close</button>
      </div>
    </div>
  );
}

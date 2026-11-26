"use client";
// The board: gate bar on top, shot cards in order, the selected shot's panel on the right, film strip and
// waveform below, render queue in a drawer. Chat edits arrive through the event stream and redraw in place.
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { getJson, mb, patchShot, useEvents } from "@/lib/client";
import { media } from "@/lib/client";
import { useShortcuts } from "@/lib/shortcuts";
import { TopBar } from "@/components/ui/TopBar";
import { KbdHelp } from "@/components/ui/KbdHelp";
import { useToast } from "@/components/ui/Toast";
import { Animatic } from "@/components/animatic/Animatic";
import { QueuePanel } from "@/components/queue/QueuePanel";
import { SystemLoad } from "@/components/queue/SystemLoad";
import { reviewKind } from "@/components/review/ApproveBar";
import { ShotCard } from "./ShotCard";
import { SidePanel } from "./SidePanel";
import { Timeline } from "./Timeline";
import { FilmStrip } from "./FilmStrip";
import { GateBar } from "./GateBar";
import { ExportMenu } from "./ExportMenu";
import { StoryList } from "./StoryList";
import type { Board } from "./types";

export function BoardView({ id }: { id: string }) {
  const toast = useToast();
  const [board, setBoard] = useState<Board | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [panel, setPanel] = useState(false);
  const [queueOpen, setQueueOpen] = useState(false);
  const [help, setHelp] = useState(false);
  const [animatic, setAnimatic] = useState(false);
  const [view, setView] = useState<"grid" | "story">("grid");
  useEffect(() => { try { const v = localStorage.getItem("mb.view"); if (v === "story" || v === "grid") setView(v); } catch {} }, []);
  const pick = (v: "grid" | "story") => { setView(v); try { localStorage.setItem("mb.view", v); } catch {} };
  const [time, setTime] = useState(0);
  const [playing, setPlaying] = useState(false);
  const stopAt = useRef<number | null>(null);
  const [soloShot, setSoloShot] = useState<string | null>(null);
  const [rejectSignal, setRejectSignal] = useState(0);
  const [tick, setTick] = useState(0);
  const audio = useRef<HTMLAudioElement>(null);

  const load = useCallback(() => {
    getJson<Board>(`/api/projects/${id}`).then((b) => { setBoard(b); setError(null); }).catch((e) => setError(String(e)));
  }, [id]);
  useEffect(load, [load]);
  const [since, setSince] = useState<number | null>(null);
  useEffect(() => { if (board && since === null) setSince(board.seq); }, [board, since]);
  useEvents(since, () => { load(); setTick((t) => t + 1); });

  useEffect(() => {
    let raf = 0;
    const loop = () => {
      const a = audio.current;
      if (a && !a.paused) {
        setTime(a.currentTime);
        if (stopAt.current !== null && a.currentTime >= stopAt.current) { a.pause(); stopAt.current = null; setSoloShot(null); }
      }
      raf = requestAnimationFrame(loop);
    };
    raf = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(raf);
  }, []);

  const shots = useMemo(() => board?.shots ?? [], [board]);
  const sel = shots.find((s) => s.id === selected) || null;
  const playingShot = shots.find((s) => time >= s.start && time < s.end);
  const segment = board ? `${board.project.folder}/audio/segment.wav` : "";

  const seek = (t: number) => { setTime(t); if (audio.current) audio.current.currentTime = t; };
  const move = (d: number) => {
    if (!shots.length) return;
    const i = sel ? shots.indexOf(sel) : -1;
    const n = shots[Math.max(0, Math.min(shots.length - 1, i + d))];
    setSelected(n.id); seek(n.start);
    document.querySelector(`[data-shot="${n.ord}"]`)?.scrollIntoView({ block: "nearest" });
  };
  const toggle = () => {
    const a = audio.current; if (!a) return;
    stopAt.current = null; setSoloShot(null);
    if (a.paused) a.play(); else a.pause();
  };
  // Play one shot's slice of the song (and its clip, in sync) and stop at the cut. A second press stops it.
  const playShot = (id: string) => {
    const a = audio.current; const s = shots.find((q) => q.id === id);
    if (!a || !s) return;
    if (soloShot === id && !a.paused) { a.pause(); stopAt.current = null; setSoloShot(null); return; }
    setSelected(id); setSoloShot(id);
    a.currentTime = s.start; setTime(s.start); stopAt.current = s.end;
    a.play().catch(() => {});
  };

  useShortcuts({
    space: toggle,
    k: () => audio.current?.pause(),
    j: () => seek(Math.max(0, time - 2)),
    l: () => seek(time + 2),
    left: () => move(-1),
    right: () => move(1),
    e: () => { if (sel) setPanel(true); },
    p: () => { if (sel) playShot(sel.id); },
    q: () => setQueueOpen((o) => !o),
    v: () => setAnimatic(true),
    s: () => pick(view === "grid" ? "story" : "grid"),
    help: () => setHelp((h) => !h),
    escape: () => { setHelp(false); setPanel(false); setAnimatic(false); },
    a: async () => {
      if (!sel || !board) return;
      const kind = reviewKind(board, sel);
      if (!kind) return;
      toast(await mb("review", { project: board.project.id, shot: sel.ord, kind, decision: "approve" }));
      load();
    },
    r: () => { if (sel) { setPanel(true); setRejectSignal((n) => n + 1); } },
  });

  if (error) return <div className="p-6 text-bad">{error}</div>;
  if (!board) return <div className="p-6 text-fg3">Loading…</div>;
  const ratio = board.project.aspect === "16:9";

  return (
    <div className="flex h-full flex-col">
      <audio ref={audio} src={media(segment)} preload="auto" onPlay={() => setPlaying(true)} onEnded={() => setPlaying(false)}
        onPause={() => { setPlaying(false); if (audio.current) setTime(audio.current.currentTime); }} />
      <TopBar title={<span>{board.project.title} <span className="text-fg3">· {board.project.mode ?? "no mode"} · {board.project.visual_look ?? ""}</span></span>}>
        <SystemLoad onOpen={() => setQueueOpen(true)} />
        <GateBar board={board} reload={load} />
        <span className="mx-1 h-5 w-px bg-line" />
        <span className="flex overflow-hidden rounded border border-line text-[12px]">
          {(["grid", "story"] as const).map((v) => (
            <button key={v} onClick={() => pick(v)} className={`px-2 py-1 ${view === v ? "bg-s3 text-fg" : "text-fg3 hover:bg-s2"}`}>
              {v === "grid" ? "Grid" : "Story"}
            </button>
          ))}
        </span>
        <button className="rounded px-2 py-1 text-[12px] text-fg2 hover:bg-s3" onClick={() => setAnimatic(true)}>Animatic <kbd className="opacity-50">V</kbd></button>
        <button className="rounded px-2 py-1 text-[12px] text-fg2 hover:bg-s3" onClick={() => setQueueOpen((o) => !o)}>Queue <kbd className="opacity-50">Q</kbd></button>
        <ExportMenu board={board} />
        <button className="rounded px-2 py-1 text-[12px] text-fg3 hover:bg-s3" onClick={() => setHelp(true)}>?</button>
      </TopBar>
      <div className="flex min-h-0 flex-1">
        <main className="scroll-thin min-w-0 flex-1 overflow-y-auto p-4">
          {shots.length === 0 && (
            <div className="rounded-md border border-dashed border-line p-10 text-center text-fg2">
              No shots yet. Draft the board from chat or the start page.
            </div>
          )}
          {view === "story" ? (
            <StoryList board={board} selected={selected} playing={playingShot?.id ?? null}
              solo={playing ? soloShot : null} onPlay={playShot}
              onSelect={(sid) => { setSelected(sid); const q = shots.find((x) => x.id === sid); if (q) seek(q.start); }}
              onOpen={(sid) => { setSelected(sid); setPanel(true); }} />
          ) : (
          <div className={`grid gap-3 ${ratio ? "grid-cols-[repeat(auto-fill,minmax(260px,1fr))]" : "grid-cols-[repeat(auto-fill,minmax(190px,1fr))]"}`}>
            {shots.map((s) => (
              <ShotCard key={s.id} board={board} shot={s} selected={s.id === selected} playing={s.id === playingShot?.id}
                audioOn={playing} offset={s.id === playingShot?.id ? time - s.start : 0}
                solo={soloShot === s.id && playing} onPlay={() => playShot(s.id)}
                onSelect={() => { setSelected(s.id); seek(s.start); }} onOpen={() => { setSelected(s.id); setPanel(true); }} />
            ))}
          </div>
          )}
        </main>
        {panel && sel && (
          <SidePanel board={board} shot={sel} onClose={() => setPanel(false)} reload={load} rejectSignal={rejectSignal} />
        )}
      </div>
      <FilmStrip board={board} selected={selected} onSelect={(sid) => { setSelected(sid); const s = shots.find((q) => q.id === sid); if (s) seek(s.start); }} />
      <Timeline board={board} time={time} playing={playing} onToggle={toggle} selected={selected} onSeek={seek} onSelect={setSelected}
        onMoveCut={async (ord, end) => {
          const s = shots.find((q) => q.ord === ord)!;
          const r = await patchShot(s.id, s.updated_at, { end });
          if (r.status !== 200) toast("ok" in r.body ? r.body : { ok: false, command: "move", data: {}, verified: [], not_verified: [], next: null,
            error: { code: "MOVE", message: r.body.message || r.body.error || "move failed" } });
          load();
        }} />
      {queueOpen && <QueuePanel onClose={() => setQueueOpen(false)} tick={tick} />}
      {help && <KbdHelp onClose={() => setHelp(false)} />}
      {animatic && <Animatic board={board} audio={media(segment)} onClose={() => setAnimatic(false)} />}
    </div>
  );
}

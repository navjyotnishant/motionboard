import React from "react";
import { AbsoluteFill, Img, OffthreadVideo, interpolate, random, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { C, Card, Kinetic, MONO, SANS, Scene, Step, Sub, clamp, pop, ramp } from "./kit";
import { PLATES } from "./scenes1";

/** The ruby thread from the Museum of Almosts reel: it draws itself across the frame. */
export const Thread: React.FC<{ at?: number; d: string; len?: number; dur?: number }> = ({ at = 0, d, len = 2600, dur = 50 }) => {
  const f = useCurrentFrame(); const p = ramp(f, at, at + dur);
  return (
    <svg width={1920} height={1080} style={{ position: "absolute", inset: 0 }}>
      <path d={d} fill="none" stroke={C.ruby} strokeWidth={4} strokeLinecap="round" strokeDasharray={len} strokeDashoffset={len * (1 - p)} style={{ filter: `drop-shadow(0 0 10px ${C.ruby})` }} />
    </svg>
  );
};

/** 6. Review: four takes, one flagged by the tool, one picked by the creator. */
export const Takes: React.FC<{ len: number }> = ({ len }) => {
  const f = useCurrentFrame(); const { fps } = useVideoConfig();
  const flag = pop(f, fps, 70, 10); const pick = pop(f, fps, 105, 11);
  return (
    <Scene len={len} gx={50} gy={65}>
      <div style={{ position: "absolute", left: 130, top: 110 }}><Step n="5" label="Review" /></div>
      <div style={{ position: "absolute", left: 130, top: 190 }}><Kinetic text="Compare takes. Pick one." hot={["Pick"]} at={8} size={100} /></div>
      <AbsoluteFill style={{ perspective: 1800 }}>
        <div style={{ position: "absolute", left: 130, top: 400, display: "flex", gap: 35 }}>
          {[1, 2, 3].map((v, i) => {
            const p = pop(f, fps, 22 + i * 6); const picked = i === 2; const bad = i === 0;
            const lift = picked ? pick : 0; const dim = !picked ? 1 - pick * 0.55 : 1;
            return (
              <div key={v} style={{ opacity: p * dim, transform: `translateY(${(1 - p) * 90 - lift * 26}px) rotateY(${(1 - p) * -40}deg) scale(${1 + lift * 0.08})` }}>
                <Card w={530} h={298} ring={picked && pick > 0.2 ? C.amber : bad && flag > 0.2 ? C.ruby : undefined}>
                  <OffthreadVideo muted src={staticFile(`take-${v}.mp4`)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                </Card>
                <div style={{ display: "flex", justifyContent: "space-between", marginTop: 14, fontFamily: MONO, fontSize: 22, letterSpacing: 2, color: C.dim }}>
                  <span>TAKE {i + 1}</span>
                  {bad && <span style={{ color: C.ruby, opacity: flag }}>FLAGGED</span>}
                  {picked && <span style={{ color: C.amber, opacity: pick }}>IN USE</span>}
                </div>
              </div>
            );
          })}
        </div>
      </AbsoluteFill>
      <div style={{ position: "absolute", left: 130, top: 850 }}><Sub at={72} width={1300}>Every take is kept. The take in use only changes when you say so.</Sub></div>
    </Scene>
  );
};

/** 7. Studio: the real app in a tilted window; the camera pushes into the take picker, then the queue. */
export const Studio: React.FC<{ len: number }> = ({ len }) => {
  const f = useCurrentFrame();
  const flat = ramp(f, 0, 40);
  const shots = ["12-studio-board-clips", "14-studio-shot-takes", "15-studio-queue"]; const cut = [0, 80, 150];
  const z = interpolate(f, [30, 78, 80, 148, 150, len], [1, 1.16, 1.5, 1.72, 1.45, 1.6], clamp);
  const ox = interpolate(f, [30, 78, 80, 148, 150, len], [50, 40, 88, 92, 80, 86], clamp);
  const oy = interpolate(f, [30, 78, 80, 148, 150, len], [40, 30, 34, 44, 96, 98], clamp);
  return (
    <Scene len={len} push={0} gx={50} gy={50}>
      <div style={{ position: "absolute", left: 130, top: 70 }}><Step n="6" label="Studio" /></div>
      <div style={{ position: "absolute", right: 130, top: 60 }}><Kinetic text="The whole video on one board." hot={["board"]} at={8} size={54} align="center" width={900} /></div>
      <AbsoluteFill style={{ perspective: 2200, alignItems: "center", justifyContent: "center" }}>
        <div style={{ marginTop: 110, width: 1500, height: 844, borderRadius: 18, overflow: "hidden", border: `2px solid ${C.line}`, boxShadow: "0 50px 140px #000c",
          transform: `rotateY(${(1 - flat) * -22}deg) rotateX(${(1 - flat) * 10}deg) translateZ(${(1 - flat) * -300}px)` }}>
          <div style={{ height: 34, background: "#161c2c", display: "flex", alignItems: "center", gap: 8, paddingLeft: 14 }}>
            {["#ff5f57", "#febc2e", "#28c840"].map((c) => <div key={c} style={{ width: 12, height: 12, borderRadius: 6, background: c }} />)}
            <div style={{ fontFamily: MONO, fontSize: 14, color: C.dim, marginLeft: 16 }}>localhost:4317</div>
          </div>
          <div style={{ position: "relative", width: 1500, height: 810, overflow: "hidden" }}>
            {shots.map((s, i) => (
              <Img key={s} src={staticFile(`${s}.jpg`)} style={{ position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "cover", objectPosition: "top",
                opacity: f >= cut[i] && (i === 2 || f < cut[i + 1]) ? 1 : 0, transform: `scale(${z})`, transformOrigin: `${ox}% ${oy}%` }} />
            ))}
          </div>
        </div>
      </AbsoluteFill>
      <div style={{ position: "absolute", left: 130, bottom: 46, fontFamily: MONO, fontSize: 24, letterSpacing: 2, color: C.ink, background: "#0a0d16dd", padding: "10px 18px", borderRadius: 10, border: `2px solid ${C.line}` }}>
        {f < 80 ? "play it against the song" : f < 150 ? "tap a take, use this take" : "queue, memory and guard, live"}
      </div>
    </Scene>
  );
};

/** 8. Finish: the wide video lands with its lyrics, then the reel and the Museum of Almosts piece join it. */
export const Finish: React.FC<{ len: number }> = ({ len }) => {
  const f = useCurrentFrame(); const { fps } = useVideoConfig();
  const m = ramp(f, 96, 126);
  const w = interpolate(m, [0, 1], [1240, 900]); const left = interpolate(m, [0, 1], [340, 130]); const top = interpolate(m, [0, 1], [250, 330]);
  return (
    <Scene len={len} glow={C.ruby} gx={60} gy={55}>
      <div style={{ position: "absolute", left: 130, top: 90 }}><Step n="7" label="Finish" /></div>
      <div style={{ position: "absolute", left: 130, top: 160, opacity: 1 - m }}><Kinetic text="Lyrics, grade, credits." hot={["Lyrics"]} at={8} size={72} /></div>
      <div style={{ position: "absolute", left: 130, top: 160, opacity: m }}><Kinetic text="One story. Every format." hot={["Every"]} at={104} size={92} /></div>
      <Thread at={100} dur={70} d="M -20 930 C 300 820, 520 1010, 860 900 S 1300 760, 1500 880 S 1800 980, 1960 860" />
      <div style={{ position: "absolute", left, top }}>
        <Card w={w} h={(w * 9) / 16} ring={m > 0.5 ? undefined : C.line}><OffthreadVideo muted src={staticFile("final-a.mp4")} style={{ width: "100%", height: "100%", objectFit: "cover" }} /></Card>
        <div style={{ fontFamily: MONO, fontSize: 22, letterSpacing: 3, color: C.dim, marginTop: 14, opacity: m }}>MUSIC VIDEO  16:9</div>
      </div>
      <AbsoluteFill style={{ perspective: 1800 }}>
        {[["reel.mp4", "REEL  9:16", 1100, 8], ["museum.mp4", "LYRIC STORY  ORIGAMI", 1470, 16]].map(([src, label, x, d], i) => {
          const p = pop(f, fps, 104 + (d as number), 13);
          return (
            <div key={src as string} style={{ position: "absolute", left: x as number, top: 250, opacity: p, transform: `translateY(${(1 - p) * 220}px) rotateY(${(1 - p) * 35 - 6 + i * 4}deg)` }}>
              <Card w={318} h={566}><OffthreadVideo muted src={staticFile(src as string)} style={{ width: "100%", height: "100%", objectFit: "cover" }} /></Card>
              <div style={{ fontFamily: MONO, fontSize: 20, letterSpacing: 3, color: i ? C.ruby : C.dim, marginTop: 14 }}>{label}</div>
            </div>
          );
        })}
      </AbsoluteFill>
      <div style={{ position: "absolute", left: 130, top: 920 }}><Sub at={150} width={900}>A song is one way in. Reels, promos, lyric videos and more.</Sub></div>
    </Scene>
  );
};

/** 9. End: the frames of the board fly back together into the mark. */
export const End: React.FC<{ len: number }> = ({ len }) => {
  const f = useCurrentFrame(); const { fps } = useVideoConfig();
  const TW = 92, TH = 52, G = 10; const gather = (i: number) => pop(f, fps, 6 + i * 2, 15);
  const up = ramp(f, 58, 80);
  return (
    <Scene len={len} push={0.03} gx={50} gy={42}>
      <Thread at={50} dur={60} d="M -20 960 C 380 880, 640 1040, 960 950 S 1560 880, 1960 970" />
      <AbsoluteFill style={{ perspective: 1400 }}>
        <div style={{ position: "absolute", left: 960 - (4 * TW + 3 * G) / 2, top: 250 - up * 60, width: 4 * TW + 3 * G, display: "flex", flexWrap: "wrap", gap: G, transformStyle: "preserve-3d" }}>
          {PLATES.map((n, i) => {
            const p = gather(i); const a = random(`a${i}`) * Math.PI * 2; const r = 900 + random(`r${i}`) * 600;
            return (
              <div key={n} style={{ width: TW, height: TH, borderRadius: 8, overflow: "hidden", border: `2px solid ${i === 5 || i === 6 ? C.amber : C.line}`, opacity: Math.min(1, p * 1.5),
                transform: `translate3d(${Math.cos(a) * r * (1 - p)}px, ${Math.sin(a) * r * (1 - p)}px, ${(1 - p) * 900}px) rotateY(${(1 - p) * 220}deg) rotateX(${(1 - p) * 140}deg)` }}>
                <Img src={staticFile(`plate-${n}.jpg`)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
              </div>
            );
          })}
        </div>
      </AbsoluteFill>
      <AbsoluteFill style={{ alignItems: "center", top: 470 - up * 40 }}>
        <div style={{ fontFamily: SANS, fontWeight: 800, fontSize: 118, letterSpacing: 14, color: C.ink, opacity: ramp(f, 44, 62) }}>MOTIONBOARD</div>
        <div style={{ height: 14 }} />
        <Kinetic text="Free. Open source. Local." hot={["Free."]} at={66} size={56} align="center" width={1500} />
        <div style={{ height: 34 }} />
        <div style={{ fontFamily: MONO, fontSize: 36, color: C.amber, opacity: ramp(f, 96, 112) }}>github.com/navjyotnishant/motionboard</div>
        <div style={{ height: 26 }} />
        <div style={{ fontFamily: SANS, fontWeight: 500, fontSize: 24, color: C.dim, opacity: ramp(f, 110, 126) }}>No account. No credits for video. The people shown are AI-generated characters.</div>
      </AbsoluteFill>
    </Scene>
  );
};

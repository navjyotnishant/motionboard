import React from "react";
import { AbsoluteFill, Img, OffthreadVideo, interpolate, random, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { BEAT, C, Card, Kinetic, MONO, SANS, Scene, Step, Sub, clamp, pop, ramp } from "./kit";

export const PLATES = [2, 6, 9, 10, 15, 18, 20, 33, 40, 41, 46, 47];
const COLS = 4, CW = 300, CH = 169, GAP = 26;

/** 1. Hook: three beats of type, then finished frames fly in from depth. */
export const Hook: React.FC<{ len: number }> = ({ len }) => {
  const f = useCurrentFrame(); const { fps } = useVideoConfig();
  const out = ramp(f, 62, 74);
  return (
    <Scene len={len} push={0.06}>
      <AbsoluteFill style={{ perspective: 1600 }}>
        {[46, 18, 15, 41, 9].map((n, i) => {
          const p = pop(f, fps, 70 + i * 5, 16); const x = (i - 2) * 330; const drift = Math.sin((f + i * 20) / 30) * 8;
          return (
            <div key={n} style={{ position: "absolute", left: 960 - 190 + x, top: 200 + drift + Math.abs(i - 2) * 26, opacity: p,
              transform: `translateZ(${(1 - p) * -1400}px) rotateY(${(i - 2) * -13}deg) rotateX(6deg)` }}>
              <Card w={380} h={214}><OffthreadVideo muted src={staticFile(`clip-${n}.mp4`)} style={{ width: "100%", height: "100%", objectFit: "cover" }} /></Card>
            </div>
          );
        })}
      </AbsoluteFill>
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", opacity: 1 - out, transform: `scale(${1 + out * 0.3})` }}>
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 6 }}>
          <Kinetic text="A song." at={4} size={150} align="center" width={1700} />
          <Kinetic text="An idea." at={4 + BEAT * 1.5} size={150} align="center" width={1700} />
        </div>
      </AbsoluteFill>
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "flex-end", paddingBottom: 150 }}>
        <Kinetic text="A finished video." hot={["finished"]} at={84} size={132} align="center" width={1700} />
        <div style={{ height: 26 }} />
        <Sub at={106} width={1300}><div style={{ textAlign: "center" }}>Motionboard. Free, open source, made on your own Mac.</div></Sub>
      </AbsoluteFill>
    </Scene>
  );
};

/** 2. Listen: the waveform draws, beats pulse, sung lines land on the grid. */
export const Listen: React.FC<{ len: number }> = ({ len }) => {
  const f = useCurrentFrame(); const { fps } = useVideoConfig();
  const N = 150; const drawn = ramp(f, 16, 80) * N; const beat = 1 - ((f % BEAT) / BEAT);
  const lines = [[8, 30, "verse"], [34, 24, "verse"], [62, 34, "chorus"], [100, 22, "verse"], [124, 22, "chorus"]] as const;
  const count = (to: number, a: number) => Math.round(to * ramp(f, a, a + 30));
  return (
    <Scene len={len} gx={50} gy={70}>
      <div style={{ position: "absolute", left: 130, top: 110 }}><Step n="1" label="Listen" /></div>
      <div style={{ position: "absolute", left: 130, top: 180 }}><Kinetic text="It listens first." hot={["listens"]} at={6} size={110} /></div>
      <div style={{ position: "absolute", left: 130, top: 330 }}><Sub at={30} width={1100}>Tempo, beats and every sung line, found on your machine.</Sub></div>
      <div style={{ position: "absolute", left: 130, top: 560, width: 1660, height: 260, display: "flex", alignItems: "center", gap: 4 }}>
        {Array.from({ length: N }).map((_, i) => {
          const h = (0.25 + 0.75 * random(`w${i}`)) * (0.55 + 0.45 * Math.sin(i / 9) ** 2); const on = i < drawn;
          const isBeat = i % 6 === 0; const kick = isBeat ? 1 + beat * 0.35 : 1;
          return <div key={i} style={{ flex: 1, height: on ? `${h * 100 * kick}%` : "2%", borderRadius: 4, background: isBeat ? C.amber : "#5b6686", opacity: on ? 1 : 0.25 }} />;
        })}
      </div>
      {lines.map(([s, w, kind], i) => {
        const p = pop(f, fps, 70 + i * 9);
        return <div key={i} style={{ position: "absolute", left: 130 + (s / N) * 1660, top: 846 + (1 - p) * -40, width: (w / N) * 1660 - 8, height: 46, borderRadius: 10, opacity: p,
          background: kind === "chorus" ? `${C.ruby}cc` : "#2a3350", border: `2px solid ${kind === "chorus" ? C.ruby : "#3c476b"}`, color: C.ink, fontFamily: MONO, fontSize: 20,
          display: "flex", alignItems: "center", justifyContent: "center", letterSpacing: 2 }}>{kind.toUpperCase()}</div>;
      })}
      <div style={{ position: "absolute", right: 130, top: 190, display: "flex", gap: 46, fontFamily: SANS }}>
        {[[count(117, 40), "BPM"], [count(436, 50), "beats"], [count(71, 60), "sung lines"]].map(([v, l], i) => (
          <div key={i} style={{ textAlign: "right", opacity: ramp(f, 40 + i * 10, 52 + i * 10) }}>
            <div style={{ fontWeight: 800, fontSize: 84, color: C.ink, fontVariantNumeric: "tabular-nums" }}>{v}</div>
            <div style={{ fontFamily: MONO, fontSize: 22, color: C.dim, letterSpacing: 3 }}>{String(l).toUpperCase()}</div>
          </div>
        ))}
      </div>
    </Scene>
  );
};

const Skeleton: React.FC<{ i: number }> = ({ i }) => (
  <div style={{ padding: 18, height: "100%", boxSizing: "border-box", display: "flex", flexDirection: "column", gap: 10 }}>
    <div style={{ fontFamily: MONO, fontSize: 15, color: C.amber, letterSpacing: 2 }}>{String(i + 1).padStart(2, "0")}  0:{String(4 + i * 3).padStart(2, "0")}</div>
    {[0.9, 0.7, 0.8, 0.45].map((w, k) => <div key={k} style={{ height: 11, width: `${w * 100}%`, borderRadius: 6, background: k === 0 ? "#4a5578" : "#2c3654" }} />)}
  </div>
);

/** The board as a plane in space. mode: text cards, flipping to images, or playing clips. */
export const Board: React.FC<{ mode: "text" | "flip" | "play"; tilt?: number; x?: number; y?: number; scale?: number }> = ({ mode, tilt = 34, x = 800, y = 270, scale = 0.9 }) => {
  const f = useCurrentFrame(); const { fps } = useVideoConfig();
  return (
    <AbsoluteFill style={{ perspective: 1800 }}>
      <div style={{ position: "absolute", left: x, top: y, width: COLS * (CW + GAP), transformStyle: "preserve-3d",
        transform: `scale(${scale}) rotateX(${tilt}deg) rotateZ(-7deg) translateY(${-f * 0.35}px)`, transformOrigin: "50% 40%", display: "flex", flexWrap: "wrap", gap: GAP }}>
        {PLATES.map((n, i) => {
          const p = mode === "text" ? pop(f, fps, 10 + i * 4) : 1;
          const flip = mode === "flip" ? ramp(f, 24 + i * 6, 46 + i * 6) : mode === "play" ? 1 : 0;
          const lit = mode === "play" && i % 2 === 0;
          return (
            <div key={n} style={{ width: CW, height: CH, opacity: p, transform: `translateZ(${(1 - p) * 500}px) translateY(${(1 - p) * 80}px) rotateY(${flip * 180}deg)`, transformStyle: "preserve-3d" }}>
              <div style={{ position: "absolute", inset: 0, backfaceVisibility: "hidden" }}><Card w={CW} h={CH}><Skeleton i={i} /></Card></div>
              <div style={{ position: "absolute", inset: 0, backfaceVisibility: "hidden", transform: "rotateY(180deg)" }}>
                <Card w={CW} h={CH} ring={lit ? C.amber : undefined}>
                  {lit ? <OffthreadVideo muted src={staticFile(`clip-${n}.mp4`)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                    : <Img src={staticFile(`plate-${n}.jpg`)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />}
                </Card>
              </div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

/** 3. Storyboard: cards deal onto the plane; an approval stamp lands. */
export const Storyboard: React.FC<{ len: number }> = ({ len }) => {
  const f = useCurrentFrame(); const { fps } = useVideoConfig(); const s = pop(f, fps, 150, 9);
  return (
    <Scene len={len} gx={70} gy={50}>
      <Board mode="text" />
      <div style={{ position: "absolute", left: 130, top: 110 }}><Step n="2" label="Storyboard" /></div>
      <div style={{ position: "absolute", left: 130, top: 190 }}><Kinetic text="A storyboard timed to the music." hot={["storyboard"]} at={8} size={92} width={720} /></div>
      <div style={{ position: "absolute", left: 130, top: 640 }}><Sub at={70} width={640}>A director's treatment first: what the song means, not what it names.</Sub></div>
      <div style={{ position: "absolute", left: 1240, top: 700, opacity: Math.min(1, s * 2), transform: `rotate(-9deg) scale(${2.2 - s * 1.2})`, border: `6px solid ${C.green}`, color: C.green,
        fontFamily: MONO, fontSize: 54, letterSpacing: 8, padding: "10px 30px", borderRadius: 14, background: "#0a0d16cc" }}>APPROVED</div>
      <div style={{ position: "absolute", left: 130, top: 850 }}><Sub at={150} width={700}><span style={{ color: C.ink }}>Nothing renders until you approve it.</span></Sub></div>
    </Scene>
  );
};

/** 4. Images: every card turns over into its picture. */
export const Images: React.FC<{ len: number }> = ({ len }) => {
  const f = useCurrentFrame(); const { fps } = useVideoConfig();
  return (
    <Scene len={len} gx={70} gy={50}>
      <Board mode="flip" tilt={interpolate(f, [0, len], [34, 22], clamp)} />
      <div style={{ position: "absolute", left: 130, top: 110 }}><Step n="3" label="Images" /></div>
      <div style={{ position: "absolute", left: 130, top: 190 }}><Kinetic text="One image per shot." hot={["image"]} at={8} size={92} width={700} /></div>
      <div style={{ position: "absolute", left: 130, top: 470, display: "flex", flexDirection: "column", gap: 14 }}>
        {["your own pictures", "a local model", "an API", "an image tool"].map((t, i) => {
          const p = pop(f, fps, 50 + i * 8);
          return <div key={t} style={{ fontFamily: MONO, fontSize: 28, color: C.ink, border: `2px solid ${C.line}`, background: C.bg2, borderRadius: 12, padding: "12px 22px", width: "fit-content",
            opacity: p, transform: `translateX(${(1 - p) * -40}px)` }}><span style={{ color: C.amber }}>+ </span>{t}</div>;
        })}
      </div>
      <div style={{ position: "absolute", left: 130, top: 850 }}><Sub at={100} width={700}>Characters keep the same face from shot to shot.</Sub></div>
    </Scene>
  );
};

/** 5. Motion: the pictures start to move while a memory guard watches the machine. */
export const Motion: React.FC<{ len: number }> = ({ len }) => {
  const f = useCurrentFrame();
  const mem = 38 + 34 * ramp(f, 40, 150) + Math.sin(f / 7) * 2.5; const done = Math.min(12, Math.floor(ramp(f, 40, 190) * 12));
  return (
    <Scene len={len} gx={70} gy={50}>
      <Board mode="play" tilt={22} scale={0.94} />
      <div style={{ position: "absolute", left: 130, top: 110 }}><Step n="4" label="Motion" /></div>
      <div style={{ position: "absolute", left: 130, top: 190 }}><Kinetic text="Animated on your Mac." hot={["Mac"]} at={8} size={92} width={720} /></div>
      <div style={{ position: "absolute", left: 130, top: 500, width: 620, opacity: ramp(f, 34, 48), fontFamily: MONO, color: C.dim, fontSize: 22, letterSpacing: 2 }}>
        <div style={{ display: "flex", justifyContent: "space-between" }}><span>MEMORY GUARD</span><span style={{ color: C.ink }}>{Math.round(mem)}%</span></div>
        <div style={{ position: "relative", height: 26, borderRadius: 13, background: C.bg2, border: `2px solid ${C.line}`, marginTop: 12, overflow: "hidden" }}>
          <div style={{ width: `${mem}%`, height: "100%", background: `linear-gradient(90deg, ${C.green}, ${C.amber})` }} />
          <div style={{ position: "absolute", left: "92%", top: -4, bottom: -4, width: 3, background: C.ruby }} />
        </div>
        <div style={{ display: "flex", justifyContent: "space-between", marginTop: 26 }}><span>RENDER QUEUE</span><span style={{ color: C.ink }}>{done} / 12 shots</span></div>
        <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
          {Array.from({ length: 12 }).map((_, i) => <div key={i} style={{ flex: 1, height: 14, borderRadius: 7, background: i < done ? C.amber : C.line }} />)}
        </div>
      </div>
      <div style={{ position: "absolute", left: 130, top: 850 }}><Sub at={90} width={700}>Free, open video models. One shot at a time. It never takes the machine down.</Sub></div>
    </Scene>
  );
};

import React from "react";
import { Img, OffthreadVideo, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { C, Card, Kinetic, MONO, SANS, Scene, Step, Sub, clamp, pop, ramp } from "./kit";
import { PLATES } from "./scenes1";

/** Free: takes keep stacking up while the cost stays at zero. Learn by trying, not by paying. */
export const Free: React.FC<{ len: number }> = ({ len }) => {
  const f = useCurrentFrame(); const { fps } = useVideoConfig();
  const takes = Math.floor(interpolate(f, [20, len - 30], [1, 48], clamp));
  const zero = pop(f, fps, 10, 9);
  return (
    <Scene len={len} glow={C.green} gx={30} gy={50}>
      <div style={{ position: "absolute", left: 130, top: 110 }}><Step n="$" label="Free" /></div>
      <div style={{ position: "absolute", left: 130, top: 200, fontFamily: SANS, fontWeight: 800, fontSize: 300, lineHeight: 1, letterSpacing: -8,
        color: C.green, opacity: zero, transform: `scale(${0.7 + zero * 0.3})`, transformOrigin: "left center", textShadow: `0 0 60px ${C.green}55` }}>$0</div>
      <div style={{ position: "absolute", left: 140, top: 520 }}><Kinetic text="to render, redo and learn." hot={["learn"]} at={22} size={70} width={820} /></div>
      <div style={{ position: "absolute", left: 140, top: 720 }}>
        <Sub at={60} width={780}>Free, open video models run on your own Mac. No credits. No subscription. No limit on takes.</Sub>
      </div>
      <div style={{ position: "absolute", left: 140, top: 900 }}>
        <Sub at={95} width={780}><span style={{ color: C.ink }}>Practise directing and editing as much as you like.</span></Sub>
      </div>
      <div style={{ position: "absolute", right: 120, top: 150, width: 760 }}>
        <div style={{ display: "flex", justifyContent: "space-between", fontFamily: MONO, fontSize: 26, letterSpacing: 3, color: C.dim, marginBottom: 18 }}>
          <span>TAKES RENDERED <span style={{ color: C.ink }}>{takes}</span></span>
          <span>COST <span style={{ color: C.green }}>$0.00</span></span>
        </div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 10 }}>
          {Array.from({ length: 48 }).map((_, i) => {
            const on = i < takes; const p = on ? pop(f, fps, 20 + i * ((len - 50) / 48), 16) : 0;
            const n = PLATES[i % PLATES.length];
            return (
              <div key={i} style={{ width: 118, height: 66, opacity: p, transform: `scale(${0.6 + p * 0.4})` }}>
                <Card w={118} h={66} ring={i === takes - 1 ? C.green : undefined}>
                  {i === takes - 1
                    ? <OffthreadVideo muted src={staticFile(`clip-${n}.mp4`)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                    : <Img src={staticFile(`plate-${n}.jpg`)} style={{ width: "100%", height: "100%", objectFit: "cover", filter: `saturate(${0.6 + (i % 3) * 0.2})` }} />}
                </Card>
              </div>
            );
          })}
        </div>
        <div style={{ marginTop: 22, fontFamily: MONO, fontSize: 20, letterSpacing: 2, color: C.dim, opacity: ramp(f, 110, 125) }}>
          LTX-2.3  ·  LTX-2.5  ·  RUNS ON YOUR MAC
        </div>
      </div>
    </Scene>
  );
};

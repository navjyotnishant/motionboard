import React from "react";
import { AbsoluteFill, Img, staticFile } from "remotion";
import { C, Card, MONO, SANS } from "./kit";
import { PLATES } from "./scenes1";

/** Cover: $0 is the hook; the board of finished frames proves what it makes. Reads at thumbnail size. */
export const Cover: React.FC = () => {
  const order = [15, 46, 18, 41, 9, 47, 2, 40, 33, 20, 6, 10];
  return (
    <AbsoluteFill style={{ background: C.bg, overflow: "hidden" }}>
      <AbsoluteFill style={{ background: `radial-gradient(900px 700px at 22% 45%, ${C.green}26, transparent 70%), radial-gradient(1000px 800px at 85% 50%, ${C.ruby}22, transparent 70%)` }} />
      <AbsoluteFill style={{
        backgroundImage: `linear-gradient(${C.line} 1px, transparent 1px), linear-gradient(90deg, ${C.line} 1px, transparent 1px)`,
        backgroundSize: "80px 80px", opacity: 0.35,
        maskImage: "radial-gradient(ellipse at 30% 50%, black 15%, transparent 70%)", WebkitMaskImage: "radial-gradient(ellipse at 30% 50%, black 15%, transparent 70%)" }} />
      <AbsoluteFill style={{ perspective: 1700 }}>
        <div style={{ position: "absolute", left: 930, top: 40, width: 4 * 300 + 3 * 22, display: "flex", flexWrap: "wrap", gap: 22,
          transform: "rotateX(26deg) rotateY(-24deg) rotateZ(-6deg)", transformOrigin: "30% 50%" }}>
          {order.map((n, i) => (
            <Card key={n} w={300} h={169} ring={i === 1 ? C.amber : i === 4 ? C.green : undefined}>
              <Img src={staticFile(`plate-${n}.jpg`)} style={{ width: "100%", height: "100%", objectFit: "cover", filter: i === 1 || i === 4 ? "none" : "brightness(0.82)" }} />
            </Card>
          ))}
        </div>
      </AbsoluteFill>
      <svg width={1920} height={1080} style={{ position: "absolute", inset: 0 }}>
        <path d="M 1000 1100 C 1180 900, 1420 980, 1620 840 S 1860 720, 1960 760" fill="none" stroke={C.ruby} strokeWidth={6} strokeLinecap="round" style={{ filter: `drop-shadow(0 0 14px ${C.ruby})` }} />
      </svg>
      <AbsoluteFill style={{ background: `linear-gradient(90deg, ${C.bg} 0%, ${C.bg}f2 34%, ${C.bg}00 56%)` }} />
      <div style={{ position: "absolute", left: 110, top: 90, fontFamily: MONO, fontSize: 34, letterSpacing: 10, color: C.amber }}>MOTIONBOARD</div>
      <div style={{ position: "absolute", left: 92, top: 150, fontFamily: SANS, fontWeight: 800, fontSize: 470, lineHeight: 1, letterSpacing: -18, color: C.green,
        textShadow: `0 0 80px ${C.green}66` }}>$0</div>
      <div style={{ position: "absolute", left: 110, top: 640, fontFamily: SANS, fontWeight: 800, fontSize: 92, lineHeight: 1.04, letterSpacing: -2, color: C.ink }}>
        AI music videos<br />on your own Mac
      </div>
      <div style={{ position: "absolute", left: 110, top: 880, display: "flex", gap: 14 }}>
        {["FREE VIDEO MODELS", "OPEN SOURCE", "NO CREDITS"].map((t, i) => (
          <div key={t} style={{ fontFamily: MONO, fontSize: 26, letterSpacing: 3, color: i === 0 ? "#08140e" : C.ink, background: i === 0 ? C.green : "#ffffff10",
            border: `2px solid ${i === 0 ? C.green : C.line}`, borderRadius: 10, padding: "10px 18px" }}>{t}</div>
        ))}
      </div>
    </AbsoluteFill>
  );
};

import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig, Easing } from "remotion";
import { loadFont as loadInter } from "@remotion/google-fonts/InterTight";
import { loadFont as loadMono } from "@remotion/google-fonts/JetBrainsMono";

export const SANS = loadInter("normal", { weights: ["500", "700", "800"], subsets: ["latin"] }).fontFamily;
export const MONO = loadMono("normal", { weights: ["500"], subsets: ["latin"] }).fontFamily;
export const C = { bg: "#0a0d16", bg2: "#111727", ink: "#f3f1ea", dim: "#8d93a6", line: "#232b40", amber: "#f5a623", ruby: "#e2305c", green: "#3ddc97" };
export const BEAT = 15; // 120 BPM at 30 fps: every scene length is a whole number of beats

export const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
export const ease = Easing.bezier(0.22, 1, 0.36, 1);
/** 0 to 1 between two frames, eased. */
export const ramp = (f: number, a: number, b: number) => interpolate(f, [a, b], [0, 1], { ...clamp, easing: ease });
export const pop = (f: number, fps: number, delay = 0, damping = 14) =>
  spring({ frame: f - delay, fps, config: { damping, mass: 0.7, stiffness: 140 } });

/** Navy field with a drifting grid and a soft amber glow: calm, never flat. */
export const Bg: React.FC<{ glow?: string; gx?: number; gy?: number }> = ({ glow = C.amber, gx = 50, gy = 40 }) => {
  const f = useCurrentFrame();
  const d = (f * 0.35) % 80;
  return (
    <AbsoluteFill style={{ background: C.bg }}>
      <AbsoluteFill style={{
        backgroundImage: `linear-gradient(${C.line} 1px, transparent 1px), linear-gradient(90deg, ${C.line} 1px, transparent 1px)`,
        backgroundSize: "80px 80px", backgroundPosition: `${d}px ${d * 0.6}px`, opacity: 0.45,
        maskImage: "radial-gradient(ellipse at 50% 45%, black 20%, transparent 78%)",
        WebkitMaskImage: "radial-gradient(ellipse at 50% 45%, black 20%, transparent 78%)" }} />
      <AbsoluteFill style={{ background: `radial-gradient(900px 600px at ${gx}% ${gy}%, ${glow}22, transparent 70%)` }} />
    </AbsoluteFill>
  );
};

/** Words arrive one at a time on the beat; the key word sits in an amber box. */
export const Kinetic: React.FC<{ text: string; hot?: string[]; at?: number; size?: number; step?: number; align?: "left" | "center"; width?: number }> =
  ({ text, hot = [], at = 0, size = 84, step = 4, align = "left", width = 1500 }) => {
    const f = useCurrentFrame(); const { fps } = useVideoConfig();
    return (
      <div style={{ display: "flex", flexWrap: "wrap", gap: `${size * 0.1}px ${size * 0.26}px`, width, justifyContent: align === "center" ? "center" : "flex-start",
        fontFamily: SANS, fontWeight: 800, fontSize: size, lineHeight: 1.08, letterSpacing: -1.5, color: C.ink }}>
        {text.split(" ").map((w, i) => {
          const p = pop(f, fps, at + i * step); const isHot = hot.includes(w.replace(/[.,]/g, ""));
          return (
            <span key={i} style={{ display: "inline-block", opacity: Math.min(1, p * 1.4), transform: `translateY(${(1 - p) * 34}px) scale(${0.9 + p * 0.1})`,
              background: isHot ? C.amber : "transparent", color: isHot ? "#141414" : C.ink, padding: isHot ? `0 ${size * 0.14}px` : 0, borderRadius: size * 0.12 }}>{w}</span>
          );
        })}
      </div>
    );
  };

export const Step: React.FC<{ n: string; label: string; at?: number }> = ({ n, label, at = 0 }) => {
  const f = useCurrentFrame(); const p = ramp(f, at, at + 14);
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 16, fontFamily: MONO, fontSize: 26, letterSpacing: 4, color: C.amber, opacity: p, transform: `translateX(${(1 - p) * -30}px)` }}>
      <span style={{ border: `2px solid ${C.amber}`, borderRadius: 8, padding: "4px 12px" }}>{n}</span>{label.toUpperCase()}
    </div>
  );
};

export const Sub: React.FC<{ children: React.ReactNode; at?: number; width?: number }> = ({ children, at = 0, width = 900 }) => {
  const f = useCurrentFrame(); const p = ramp(f, at, at + 16);
  return <div style={{ fontFamily: SANS, fontWeight: 500, fontSize: 36, lineHeight: 1.3, color: C.dim, width, opacity: p, transform: `translateY(${(1 - p) * 18}px)` }}>{children}</div>;
};

/** Scene wrapper: fades at both ends and holds a slow push in so nothing is ever still. */
export const Scene: React.FC<{ len: number; children: React.ReactNode; push?: number; glow?: string; gx?: number; gy?: number }> = ({ len, children, push = 0.04, glow, gx, gy }) => {
  const f = useCurrentFrame();
  const o = Math.min(ramp(f, 0, 8), 1 - ramp(f, len - 7, len));
  return (
    <AbsoluteFill style={{ opacity: o }}>
      <Bg glow={glow} gx={gx} gy={gy} />
      <AbsoluteFill style={{ transform: `scale(${1 + push * (f / len)})` }}>{children}</AbsoluteFill>
    </AbsoluteFill>
  );
};

export const Progress: React.FC<{ total: number }> = ({ total }) => {
  const f = useCurrentFrame();
  return <div style={{ position: "absolute", left: 0, bottom: 0, height: 6, width: `${(f / total) * 100}%`, background: C.amber }} />;
};

export const Card: React.FC<{ w: number; h: number; children?: React.ReactNode; style?: React.CSSProperties; ring?: string }> = ({ w, h, children, style, ring }) => (
  <div style={{ width: w, height: h, borderRadius: 14, overflow: "hidden", background: C.bg2, border: `2px solid ${ring ?? C.line}`,
    boxShadow: ring ? `0 0 0 4px ${ring}55, 0 30px 80px #000a` : "0 24px 60px #0009", ...style }}>{children}</div>
);

"use client";
// Template tiles: one per story mode with its signature animation, plus a look to pair it with.
import { useState } from "react";

export type Mode = { slug: string; name: string; summary: string; animation: string; lip_sync: string };
export type Look = { slug: string; name: string; summary: string };

export function TemplatePicker({ modes, looks, busy, onPick }: {
  modes: Mode[]; looks: Look[]; busy: boolean; onPick: (mode: string, look: string) => void;
}) {
  const [mode, setMode] = useState<string | null>(null);
  const [look, setLook] = useState(looks[0]?.slug || "");
  return (
    <div>
      <div className="grid grid-cols-[repeat(auto-fill,minmax(200px,1fr))] gap-3">
        {modes.map((m) => (
          <button key={m.slug} onClick={() => setMode(m.slug)}
            className="rounded-md border bg-s1 p-4 text-left"
            style={{ borderColor: mode === m.slug ? "var(--accent)" : "var(--line)" }}>
            <div className="font-medium">{m.name}</div>
            <div className="mt-1 text-[12px] leading-snug text-fg2">{m.summary}</div>
            {m.lip_sync !== "never" && <div className="mt-2 text-[11px] text-fg3">lip-sync: {m.lip_sync}</div>}
          </button>
        ))}
      </div>
      <div className="mt-4 flex items-center gap-3">
        <span className="text-[12px] text-fg3">Look</span>
        <div className="flex flex-wrap gap-2">
          {looks.map((l) => (
            <button key={l.slug} title={l.summary} onClick={() => setLook(l.slug)}
              className="rounded border px-3 py-1 text-[12px]"
              style={{ borderColor: look === l.slug ? "var(--accent)" : "var(--line)", color: look === l.slug ? "var(--text)" : "var(--text-2)" }}>
              {l.name}
            </button>
          ))}
        </div>
        <button disabled={!mode || !look || busy} onClick={() => mode && onPick(mode, look)}
          className="ml-auto rounded bg-accent px-4 py-1.5 font-medium text-accent-ink">
          {busy ? "Drafting…" : "Draft the board"}
        </button>
      </div>
    </div>
  );
}

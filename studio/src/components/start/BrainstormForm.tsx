"use client";
// A few questions, then three concept cards side by side. Pick one to draft the board from its shot ideas.
import { useState } from "react";
import type { Look } from "./TemplatePicker";

export type Concept = {
  id: string | null; title: string; premise: string; hero_image_idea: string; mode: string; look: string;
  sample_shots: string[]; shots_file: string;
};

export function BrainstormForm({ project, looks, busy, onPick }: {
  project: string; looks: Look[]; busy: boolean; onPick: (c: Concept) => void;
}) {
  const [answers, setAnswers] = useState({ mood: "", world: "", characters: "", look: "" });
  const [concepts, setConcepts] = useState<Concept[] | null>(null);
  const [thinking, setThinking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function go() {
    setThinking(true); setError(null);
    const r = await fetch("/api/brainstorm", { method: "POST", headers: { "content-type": "application/json" },
      body: JSON.stringify({ project_id: project, answers }) });
    const j = await r.json();
    setThinking(false);
    if (!r.ok) { setError(j.message || j.error); return; }
    setConcepts(j.concepts);
  }

  const field = (k: keyof typeof answers, label: string, ph: string) => (
    <label className="block"><span className="mb-1 block text-[12px] text-fg3">{label}</span>
      <input value={answers[k]} placeholder={ph} onChange={(e) => setAnswers({ ...answers, [k]: e.target.value })} /></label>
  );

  return (
    <div>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {field("mood", "Mood", "tender, late night")}
        {field("world", "World", "a river city in the rain")}
        {field("characters", "Characters", "HER and HIM")}
        <label className="block"><span className="mb-1 block text-[12px] text-fg3">Look</span>
          <select value={answers.look} onChange={(e) => setAnswers({ ...answers, look: e.target.value })}>
            <option value="">Open</option>
            {looks.map((l) => <option key={l.slug} value={l.slug}>{l.name}</option>)}
          </select></label>
      </div>
      <div className="mt-3 flex items-center gap-3">
        <button disabled={thinking} onClick={go} className="rounded border border-line px-4 py-1.5 text-fg hover:bg-s3">
          {thinking ? "Claude is thinking (up to a minute)…" : concepts ? "Three new concepts" : "Brainstorm three concepts"}
        </button>
        {error && <span className="text-bad">{error}</span>}
      </div>
      {concepts && (
        <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-3">
          {concepts.map((c, i) => (
            <div key={c.id || i} className="flex flex-col rounded-md border border-line bg-s1 p-4">
              <div className="text-[15px] font-medium">{c.title}</div>
              <div className="mt-1 text-[11px] text-fg3">{c.mode} · {c.look}</div>
              <p className="mt-2 text-[13px] text-fg2">{c.premise}</p>
              {c.hero_image_idea && <p className="mt-2 text-[12px] italic text-fg3">{c.hero_image_idea}</p>}
              <ul className="mt-2 list-disc space-y-1 pl-4 text-[12px] text-fg2">
                {c.sample_shots.slice(0, 3).map((s, j) => <li key={j}>{s}</li>)}
              </ul>
              <button disabled={busy} onClick={() => onPick(c)}
                className="mt-auto rounded bg-accent px-3 py-1.5 pt-1.5 font-medium text-accent-ink" style={{ marginTop: 16 }}>
                {busy ? "Drafting…" : "Use this concept"}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

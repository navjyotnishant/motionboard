"use client";
// Start a board: song, lyrics, idea and aspect; then either a template (mode plus look) or a brainstorm of
// three concepts with Claude. Either way ends with `mb draft` and opens the board.
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { getJson, mb } from "@/lib/client";
import { useToast } from "@/components/ui/Toast";
import { TemplatePicker, type Mode, type Look } from "./TemplatePicker";
import { BrainstormForm, type Concept } from "./BrainstormForm";

export function StartFlow() {
  const toast = useToast();
  const router = useRouter();
  const [step, setStep] = useState<"song" | "choose">("song");
  const [busy, setBusy] = useState<string | null>(null);
  const [project, setProject] = useState<string | null>(null);
  const [modes, setModes] = useState<{ modes: Mode[]; looks: Look[] } | null>(null);
  const [path, setPath] = useState(false);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { getJson<{ modes: Mode[]; looks: Look[] }>("/api/modes").then(setModes).catch(() => {}); }, []);

  async function create(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy("create"); setError(null);
    const r = await fetch("/api/start", { method: "POST", body: new FormData(e.currentTarget) });
    const j = await r.json();
    setBusy(null);
    if (!r.ok) { setError(j.error || j.created?.error?.message || "could not create the project"); return; }
    if (j.analyzed) toast(j.analyzed);
    setProject(j.project); setStep("choose");
  }

  async function draft(mode: string, look: string, shotsFile?: string, concept?: string) {
    if (!project) return;
    setBusy("draft");
    if (concept) await mb("concepts_choose", { project, concept });
    const r = await mb("draft", { project, mode, look, shots_file: shotsFile });
    setBusy(null); toast(r);
    if (r.ok) router.push(`/p/${project}`);
  }

  if (step === "song") {
    return (
      <form onSubmit={create} className="mx-auto max-w-[640px] space-y-4">
        <h1 className="text-[20px] font-medium">New project</h1>
        <label className="block"><span className="mb-1 block text-[12px] text-fg3">Title</span>
          <input name="title" required placeholder="Paper Boats" /></label>
        <div>
          <span className="mb-1 block text-[12px] text-fg3">Song</span>
          {path
            ? <input name="song_path" placeholder="/Users/you/Music/song.wav" />
            : <input type="file" name="song_file" accept="audio/*" className="py-2" />}
          <button type="button" className="mt-1 text-[12px] text-fg3 hover:text-fg2" onClick={() => setPath(!path)}>
            {path ? "Choose a file instead" : "Give a path on this Mac instead"}
          </button>
        </div>
        <label className="block"><span className="mb-1 block text-[12px] text-fg3">Lyrics (optional, improves line timing)</span>
          <textarea name="lyrics" rows={6} /></label>
        <label className="block"><span className="mb-1 block text-[12px] text-fg3">Idea (optional)</span>
          <textarea name="idea" rows={2} placeholder="Two strangers fold paper boats on a night river" /></label>
        <div className="flex gap-4">
          <label className="block flex-1"><span className="mb-1 block text-[12px] text-fg3">Aspect</span>
            <select name="aspect" defaultValue="9:16"><option value="9:16">9:16 vertical</option><option value="16:9">16:9 wide</option></select></label>
          <label className="block flex-1"><span className="mb-1 block text-[12px] text-fg3">People</span>
            <select name="look" defaultValue="stylized"><option value="stylized">Stylized</option>
              <option value="realistic">Realistic (flagged as synthetic)</option></select></label>
        </div>
        {error && <div className="text-bad">{error}</div>}
        <button disabled={!!busy} className="rounded bg-accent px-4 py-2 font-medium text-accent-ink">
          {busy ? "Creating and analysing the song…" : "Create and analyse"}
        </button>
      </form>
    );
  }

  return (
    <div className="mx-auto max-w-[1100px] space-y-8">
      <div>
        <h1 className="text-[20px] font-medium">How do you want to start?</h1>
        <p className="text-fg2">Pick a template, or brainstorm three concepts with Claude.</p>
      </div>
      <section>
        <h2 className="mb-3 text-[15px] font-medium">Template</h2>
        {modes ? <TemplatePicker modes={modes.modes} looks={modes.looks} busy={busy === "draft"}
          onPick={(m, l) => draft(m, l)} /> : <div className="text-fg3">Loading modes…</div>}
      </section>
      <section>
        <h2 className="mb-3 text-[15px] font-medium">Brainstorm</h2>
        {project && <BrainstormForm project={project} looks={modes?.looks ?? []} busy={busy === "draft"}
          onPick={(c: Concept) => draft(c.mode, c.look, c.shots_file, c.id || undefined)} />}
      </section>
    </div>
  );
}

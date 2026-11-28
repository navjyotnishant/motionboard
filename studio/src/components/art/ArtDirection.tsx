"use client";
// The Art view: the film's Art Direction Bible as the creator reviews it. Image first: palette swatches and
// character references lead, text supports them. Every change goes through `mb` (submit, approve, send back,
// references); the engine owns the rules and this view only shows what it stored.
import { useEffect, useState } from "react";
import { mb, media } from "@/lib/client";
import { useToast } from "@/components/ui/Toast";
import { affected, motifGrid, palette, statusOf, type Tone } from "@/lib/art";
import type { ArtVersion, Bible, Board, Character } from "@/components/board/types";

const TONE: Record<Tone, string> = { idle: "var(--idle)", warn: "var(--warn)", ok: "var(--ok)", info: "var(--info)" };
const PURPOSES = ["face", "silhouette", "costume", "material", "detail", "turnaround", "other"] as const;

function Label({ children }: { children: React.ReactNode }) {
  return <div className="mb-1.5 text-[11px] uppercase tracking-wider text-fg3">{children}</div>;
}

function Text({ label, value }: { label: string; value?: string | string[] }) {
  if (!value || (Array.isArray(value) && !value.length)) return null;
  return (
    <div className="mb-2">
      <div className="text-[11px] text-fg3">{label}</div>
      {Array.isArray(value)
        ? <ul className="mt-0.5 list-disc pl-4 text-[13px] leading-snug text-fg2">{value.map((v, i) => <li key={i}>{v}</li>)}</ul>
        : <div className="text-[13px] leading-snug text-fg2">{value}</div>}
    </div>
  );
}

function Panel({ title, children, testid }: { title: string; children: React.ReactNode; testid?: string }) {
  return (
    <section data-art-section={testid} className="rounded-md border border-line bg-s1 p-4">
      <Label>{title}</Label>
      {children}
    </section>
  );
}

export function ArtDirection({ board, reload, onOpenShot }: { board: Board; reload: () => void; onOpenShot: (ord: number) => void }) {
  const toast = useToast();
  const ad = board.artDirection;
  const status = statusOf(ad);
  const [which, setWhich] = useState<"pending" | "approved">(ad.pending ? "pending" : "approved");
  // A new pending version is what the creator is here to review: show it; when it is approved or gone, show the approved one.
  const pendingId = ad.pending?.id ?? null;
  useEffect(() => { setWhich(pendingId ? "pending" : "approved"); }, [pendingId]);
  const shown: ArtVersion | null = which === "pending" ? ad.pending : ad.approved;
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState("");
  const [noting, setNoting] = useState(false);
  const pid = board.project.id;

  async function act(action: string, args: Record<string, unknown> = {}) {
    setBusy(true);
    const r = await mb(action, { project: pid, ...args });
    setBusy(false);
    toast(r);
    if (r.ok) { setNoting(false); setNote(""); }
    reload();
  }

  if (!ad.approved && !ad.pending) {
    return (
      <div data-art className="mx-auto max-w-xl rounded-md border border-dashed border-line p-10 text-center text-fg2">
        No art direction yet. Ask the production designer in chat to design the world, or skip it for a simple film:
        nothing waits for it unless it is a full Bible.
      </div>
    );
  }

  const body: Bible = shown?.body ?? {};
  const swatches = palette(body);
  const grid = motifGrid(body, board.shots);
  const pendingImpact = affected(ad.pending);
  const primary = "rounded bg-accent px-3 py-1 text-[12px] font-medium text-accent-ink disabled:opacity-50";
  const quiet = "rounded border border-line px-3 py-1 text-[12px] text-fg2 hover:text-fg disabled:opacity-50";

  return (
    <div data-art className="mx-auto max-w-[1200px] space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <span data-art-status className="flex items-center gap-1.5 rounded-full border border-line px-2.5 py-1 text-[12px]">
          <span className="h-2 w-2 rounded-full" style={{ background: TONE[status.tone] }} />
          {status.label}
        </span>
        {ad.approved && ad.pending && (
          <span className="flex overflow-hidden rounded border border-line text-[12px]">
            {(["pending", "approved"] as const).map((w) => (
              <button key={w} onClick={() => setWhich(w)} className={`px-2 py-1 ${which === w ? "bg-s3 text-fg" : "text-fg3 hover:bg-s2"}`}>
                {w === "pending" ? `Pending v${ad.pending!.version}` : `Approved v${ad.approved!.version}`}
              </button>
            ))}
          </span>
        )}
        <span className="text-[12px] text-fg3">{shown ? `${shown.profile} profile` : ""}{ad.required ? " · plates wait for approval" : ""}</span>
        <span className="ml-auto flex items-center gap-2">
          {ad.pending?.status === "draft" && (
            <button className={quiet} disabled={busy} onClick={() => act("art_submit")}>Submit for review</button>
          )}
          {ad.pending && (
            <>
              <button className={quiet} disabled={busy} onClick={() => setNoting((n) => !n)}>Send back</button>
              <button data-art-approve className={primary} disabled={busy} onClick={() => act("art_approve")}>
                Approve v{ad.pending.version}
              </button>
            </>
          )}
        </span>
      </div>
      {noting && ad.pending && (
        <div className="flex gap-2">
          <textarea rows={2} value={note} onChange={(e) => setNote(e.target.value)} placeholder="What should change, and why" />
          <button className={quiet} disabled={busy || !note.trim()} onClick={() => act("art_reject", { note })}>Send</button>
        </div>
      )}
      {ad.pending?.note && <div className="text-[13px] text-fg2">Note on v{ad.pending.version}: {ad.pending.note}</div>}

      {ad.pending && (ad.pending.impact?.changed?.length ?? 0) > 0 && (
        <div data-art-pending className="rounded-md border border-line bg-s2 p-3 text-[13px]">
          <div className="text-fg">
            Pending changes: <span className="text-fg2">{ad.pending.impact.changed!.join(", ")}</span>
            {ad.pending.impact.characters?.length ? <span className="text-fg2"> · {ad.pending.impact.characters.join(", ")}</span> : null}
          </div>
          <div className="mt-1.5 flex flex-wrap items-center gap-1.5 text-fg3">
            {pendingImpact.size
              ? <>Shots with plates or clips made under the current direction:
                {[...pendingImpact.entries()].map(([ord, reasons]) => (
                  <button key={ord} data-affected={ord} title={reasons.join("; ")} onClick={() => onOpenShot(ord)}
                    className="rounded border border-line px-1.5 py-0.5 text-[12px] text-fg hover:border-accent">{ord}</button>
                ))}</>
              : <>No existing plate or clip is affected.</>}
          </div>
          <div className="mt-1 text-[12px] text-fg3">Approving changes prompts only. Nothing is regenerated until you choose.</div>
        </div>
      )}

      {body.identity && (
        <Panel title="Film identity" testid="identity">
          <div className="text-[17px] text-fg">{body.identity.title || board.project.title}</div>
          {body.identity.concept && <div className="mt-1 text-[14px] text-fg2">{body.identity.concept}</div>}
          <div className="mt-3 grid gap-x-6 md:grid-cols-2">
            <Text label="Central metaphor" value={body.identity.central_metaphor} />
            <Text label="Emotional intention" value={body.identity.emotional_intention} />
            <Text label="Song and image" value={body.identity.song_relationship} />
            <Text label="Audience experience" value={body.identity.audience_experience} />
          </div>
        </Panel>
      )}

      {(swatches.length > 0 || body.lighting) && (
        <Panel title="Colour and light" testid="palette">
          <div className="flex flex-wrap gap-3">
            {swatches.map((s) => (
              <div key={s.hex + s.name} data-swatch={s.hex} className="w-[96px]">
                <div className="h-16 rounded border border-line" style={{ background: s.hex }} />
                <div className="mt-1 text-[12px] text-fg">{s.name}</div>
                <div className="tnum font-mono text-[11px] text-fg3">{s.hex}</div>
                {s.role && <div className="text-[11px] text-fg3">{s.role}</div>}
              </div>
            ))}
          </div>
          <div className="mt-3 grid gap-x-6 md:grid-cols-2">
            <Text label="Relationships" value={body.color?.relationships} />
            <Text label="Light" value={body.lighting?.quality} />
            <Text label="Sources" value={body.lighting?.sources} />
            <Text label="Shadows" value={body.lighting?.shadows} />
          </div>
        </Panel>
      )}

      {(body.characters?.length || board.characters.length) ? (
        <Panel title="Characters" testid="characters">
          <div className="grid gap-4 md:grid-cols-2">
            {board.characters.map((c) => (
              <CharacterCard key={c.id} board={board} c={c} design={(body.characters ?? []).find(
                (x: { name?: string }) => (x.name ?? "").toUpperCase() === c.name)} reload={reload} />
            ))}
          </div>
        </Panel>
      ) : null}

      {(body.world || body.materials?.length || body.objects?.length) && (
        <Panel title="World, materials and objects" testid="world">
          <div className="grid gap-x-6 md:grid-cols-2">
            <div>
              <Text label="World" value={body.world?.description} />
              <Text label="Physical rules" value={body.world?.physical_rules} />
              <Text label="Never in this world" value={body.world?.excluded} />
            </div>
            <div>
              {(body.materials ?? []).map((m: { name: string; properties?: string; light_response?: string; motion_response?: string }) => (
                <Text key={m.name} label={`Material · ${m.name}`} value={[m.properties, m.light_response, m.motion_response].filter(Boolean).join(" ")} />
              ))}
              {(body.objects ?? []).map((o: { name: string; role?: string; meaning?: string }) => (
                <Text key={o.name} label={`${o.role === "symbol" ? "Symbol" : "Prop"} · ${o.name}`} value={o.meaning} />
              ))}
            </div>
          </div>
        </Panel>
      )}

      {grid.length > 0 && (
        <Panel title="Motifs across the film" testid="motifs">
          <div className="scroll-thin overflow-x-auto">
            <table className="text-[12px]">
              <thead>
                <tr><th />{board.shots.map((s) => <th key={s.id} className="tnum px-1 font-mono font-normal text-fg3">{s.ord}</th>)}</tr>
              </thead>
              <tbody>
                {grid.map((m) => (
                  <tr key={m.name} data-motif={m.name}>
                    <td className="pr-3 align-top text-fg" title={m.meaning}>{m.name}</td>
                    {m.cells.map((cell) => (
                      <td key={cell.ord} className="px-0.5">
                        <button title={cell.state ?? "not in this shot"} onClick={() => onOpenShot(cell.ord)}
                          data-motif-cell={cell.ord} data-state={cell.state ?? ""}
                          className="block h-5 w-5 rounded-sm border border-line"
                          style={{ background: cell.state ? "var(--accent)" : "transparent", opacity: cell.state ? 0.85 : 1 }} />
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {grid.map((m) => m.payoff ? <div key={m.name} className="mt-2 text-[12px] text-fg2"><b className="text-fg">{m.name}</b> payoff: {m.payoff}</div> : null)}
        </Panel>
      )}

      {(body.motion || body.camera || body.constraints) && (
        <Panel title="Motion, camera and constraints" testid="motion">
          <div className="grid gap-x-6 md:grid-cols-3">
            <div><Text label="Moves" value={body.motion?.allowed} /><Text label="Never moves" value={body.motion?.forbidden} /></div>
            <div><Text label="Framing" value={body.camera?.framing} /><Text label="Camera movement" value={body.camera?.movement} /><Text label="Lens" value={body.camera?.lens} /></div>
            <div><Text label="Never changes" value={body.constraints?.never_change} /><Text label="May evolve" value={body.constraints?.may_evolve} /></div>
          </div>
        </Panel>
      )}

      <Panel title="Versions" testid="versions">
        <ul className="space-y-1 text-[12px]">
          {[...ad.versions].reverse().map((v) => (
            <li key={v.id} className="flex gap-3 text-fg2">
              <span className="tnum w-8 font-mono text-fg">v{v.version}</span>
              <span className="w-24">{v.status.replace("_", " ")}</span>
              <span className="w-16 text-fg3">{v.profile}</span>
              <span className="flex-1">{v.note}</span>
              <span className="tnum font-mono text-fg3">{v.approved_at ? `approved ${v.approved_at.slice(0, 10)} · ${v.approved_via}` : v.created_at.slice(0, 10)}</span>
            </li>
          ))}
        </ul>
      </Panel>
    </div>
  );
}

function CharacterCard({ board, c, design, reload }: {
  board: Board; c: Character; design?: { silhouette?: string; materials?: string; color?: string; construction?: string };
  reload: () => void;
}) {
  const toast = useToast();
  const [path, setPath] = useState("");
  const [purpose, setPurpose] = useState<(typeof PURPOSES)[number]>("face");
  const [busy, setBusy] = useState(false);
  const pid = board.project.id;
  async function act(action: string, args: Record<string, unknown>) {
    setBusy(true);
    const r = await mb(action, { project: pid, ...args });
    setBusy(false);
    toast(r);
    if (r.ok) setPath("");
    reload();
  }
  return (
    <div data-character={c.name} className="rounded border border-line p-3">
      <div className="flex items-baseline gap-2">
        <span className="text-[14px] font-medium text-fg">{c.name}</span>
        <span className="text-[12px] text-fg3">{c.references.length} reference{c.references.length === 1 ? "" : "s"}</span>
      </div>
      <div className="mt-2 flex flex-wrap gap-2">
        {c.references.map((r) => (
          <figure key={r.id} data-ref={r.id} className="w-[88px]">
            <div className="relative h-[88px] overflow-hidden rounded border bg-s3"
              style={{ borderColor: r.is_primary ? "var(--accent)" : "var(--line)" }}>
              <img src={media(r.path)} alt={`${c.name} ${r.purpose}`} loading="lazy" className="h-full w-full object-cover" />
              {r.is_primary && <span className="absolute left-1 top-1 rounded bg-black/70 px-1 text-[10px] text-accent">primary</span>}
            </div>
            <figcaption className="mt-0.5 flex items-center justify-between text-[11px] text-fg3">
              <span>{r.purpose}</span>
              <span className="flex gap-1">
                {!r.is_primary && <button disabled={busy} title="Make primary" onClick={() => act("ref_primary", { id: r.id })}>★</button>}
                <button disabled={busy} title="Remove (the file stays on disk)" onClick={() => act("ref_remove", { id: r.id })}>×</button>
              </span>
            </figcaption>
          </figure>
        ))}
      </div>
      <div className="mt-2 flex gap-1.5">
        <input value={path} onChange={(e) => setPath(e.target.value)} placeholder="Image path on this Mac" className="min-w-0 flex-1 py-0.5 text-[12px]" />
        <select value={purpose} onChange={(e) => setPurpose(e.target.value as (typeof PURPOSES)[number])} className="w-auto py-0.5 text-[12px]">
          {PURPOSES.map((p) => <option key={p} value={p}>{p}</option>)}
        </select>
        <button disabled={busy || !path.trim()} className="rounded border border-line px-2 text-[12px] text-fg2 hover:text-fg"
          onClick={() => act("ref_add", { name: c.name, file: path.trim(), purpose })}>Add</button>
      </div>
      {design && (
        <div className="mt-3">
          <Text label="Silhouette" value={design.silhouette} />
          <Text label="Construction" value={design.construction} />
          <Text label="Materials" value={design.materials} />
          <Text label="Colour" value={design.color} />
        </div>
      )}
    </div>
  );
}

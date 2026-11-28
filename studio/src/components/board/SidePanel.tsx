"use client";
// Everything about one shot: fields, cast, character style lines, versions, notes, approve and reject.
// Text fields save on blur through PATCH /api/shots/:id (the engine applies the rules).
import { useEffect, useState } from "react";
import { mb, patchShot, STATE_COLOR, STATE_LABEL, tc } from "@/lib/client";
import { useToast } from "@/components/ui/Toast";
import { VersionStrip } from "@/components/review/VersionStrip";
import { ApproveBar } from "@/components/review/ApproveBar";
import type { Board, Shot } from "./types";
import { CREATIVE_FIELDS, creativeCount, findingsFor, motifsToText, ROLE_LABEL } from "@/lib/art";

const FIELDS: { key: keyof Shot; label: string; rows: number }[] = [
  { key: "lyric", label: "Lyric", rows: 2 },
  { key: "visual", label: "Visual", rows: 3 },
  { key: "action", label: "Action", rows: 2 },
  { key: "camera", label: "Camera", rows: 1 },
  { key: "plate_prompt", label: "Plate prompt", rows: 4 },
  { key: "motion_prompt", label: "Motion prompt", rows: 3 },
];

export function SidePanel({ board, shot, onClose, reload, rejectSignal }: {
  board: Board; shot: Shot; onClose: () => void; reload: () => void; rejectSignal: number;
}) {
  const toast = useToast();
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  useEffect(() => setDraft({}), [shot.id]);

  async function save(fields: Record<string, unknown>) {
    setBusy(true);
    const r = await patchShot(shot.id, shot.updated_at, fields);
    setBusy(false);
    if (r.status === 409) {
      toast({ ok: false, command: "edit", data: {}, verified: [], not_verified: [], next: null,
        error: { code: "CONFLICT", message: "This shot changed elsewhere. Reloaded the latest version." } });
    } else if (r.status !== 200) {
      const rep = r.body;
      toast("ok" in rep ? rep : { ok: false, command: "edit", data: {}, verified: [], not_verified: [], next: null,
        error: { code: "EDIT", message: rep.error || "edit failed" } });
    }
    setDraft({});
    reload();
  }

  const project = board.project.id;
  const byId = Object.fromEntries(board.characters.map((c) => [c.id, c]));

  return (
    <aside className="scroll-thin flex w-[380px] shrink-0 flex-col overflow-y-auto border-l border-line bg-s1">
      <div className="flex items-center gap-2 border-b border-line px-4 py-3">
        <span className="text-[15px] font-medium">Shot {shot.ord}</span>
        <span className="tnum font-mono text-[12px] text-fg3">{tc(shot.start)} – {tc(shot.end)}</span>
        <span className="tnum font-mono text-[12px] text-fg3">{shot.frames}f</span>
        <span className="ml-auto flex items-center gap-1.5 text-[12px] text-fg2">
          <span className="h-2 w-2 rounded-full" style={{ background: STATE_COLOR[shot.state] }} />
          {STATE_LABEL[shot.state]}
        </span>
        <button onClick={onClose} className="ml-2 text-fg3 hover:text-fg" aria-label="Close">×</button>
      </div>

      <ApproveBar board={board} shot={shot} reload={reload} rejectSignal={rejectSignal} />
      <VersionStrip board={board} shot={shot} reload={reload} />

      <div className="space-y-3 px-4 py-3">
        {FIELDS.map((f) => {
          const val = draft[f.key as string] ?? (shot[f.key] as string);
          return (
            <label key={f.key} className="block">
              <span className="mb-1 block text-[11px] uppercase tracking-wider text-fg3">{f.label}</span>
              <textarea
                rows={f.rows}
                value={val}
                disabled={busy}
                onChange={(e) => setDraft({ ...draft, [f.key]: e.target.value })}
                onBlur={() => { if (draft[f.key as string] !== undefined && draft[f.key as string] !== shot[f.key]) save({ [f.key]: draft[f.key as string] }); }}
              />
            </label>
          );
        })}
        <div className="flex gap-4 text-[13px]">
          <label className="flex items-center gap-2">
            <input type="checkbox" className="w-auto" checked={shot.has_figure} disabled={busy}
              onChange={(e) => save({ has_figure: e.target.checked })} />
            Figure in shot
          </label>
          <label className="flex items-center gap-2">
            <input type="checkbox" className="w-auto" checked={shot.lip_sync} disabled={busy || !shot.has_figure}
              onChange={(e) => save({ lip_sync: e.target.checked })} />
            Lip-sync
          </label>
        </div>
      </div>

      <CreativeContext board={board} shot={shot} busy={busy} save={save} />

      <div className="border-t border-line px-4 py-3">
        <div className="mb-2 text-[11px] uppercase tracking-wider text-fg3">Characters</div>
        {board.characters.length === 0 && <div className="text-fg3">None in this project.</div>}
        <div className="space-y-3">
          {board.characters.map((c) => {
            const on = shot.cast.includes(c.id);
            return (
              <div key={c.id}>
                <label className="flex items-center gap-2 text-[13px]">
                  <input type="checkbox" className="w-auto" checked={on} disabled={busy || (!on && !shot.has_figure)}
                    onChange={async (e) => {
                      setBusy(true);
                      const r = await mb("character_link", { project, name: c.name, shots: String(shot.ord), on: e.target.checked });
                      setBusy(false);
                      toast(r); reload();
                    }} />
                  <span className="font-medium">{c.name}</span>
                  {c.references.length > 0 && (
                    <span className="text-[11px] text-fg3">{c.references.length} reference{c.references.length === 1 ? "" : "s"}</span>
                  )}
                </label>
                <CharacterLine project={project} name={c.name} value={byId[c.id].style_line} reload={reload} />
              </div>
            );
          })}
        </div>
      </div>
    </aside>
  );
}

function CharacterLine({ project, name, value, reload }: { project: string; name: string; value: string; reload: () => void }) {
  const toast = useToast();
  const [v, setV] = useState(value);
  useEffect(() => setV(value), [value]);
  return (
    <textarea rows={2} className="mt-1" placeholder="How they look (added to plate prompts of their shots)" value={v}
      onChange={(e) => setV(e.target.value)}
      onBlur={async () => {
        if (v === value) return;
        const r = await mb("character_set", { project, name, field: "style_line", value: v });
        toast(r); reload();
      }} />
  );
}

// The shot's creative intent, collapsed by default so the main fields stay on top. Empty fields cost nothing;
// motifs and continuity reach the prompts (the engine decides), the rest guide the crew and the reviews.
function CreativeContext({ board, shot, busy, save }: {
  board: Board; shot: Shot; busy: boolean; save: (f: Record<string, unknown>) => Promise<void>;
}) {
  const c = shot.creative || {};
  const filled = creativeCount(c);
  const findings = findingsFor(board, shot.ord);
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState<Record<string, string>>({});
  useEffect(() => { setDraft({}); }, [shot.id]);
  const value = (k: string) => draft[k] ?? (k === "motifs" ? motifsToText(c.motifs) : String(c[k as keyof typeof c] ?? ""));
  return (
    <div data-creative className="border-t border-line px-4 py-2">
      <button onClick={() => setOpen((o) => !o)} className="flex w-full items-center gap-2 text-[11px] uppercase tracking-wider text-fg3">
        <span>{open ? "▾" : "▸"}</span> Creative context
        <span className="normal-case tracking-normal">{filled ? `${filled} set` : "optional"}</span>
        {findings.length > 0 && <span data-findings className="ml-auto normal-case tracking-normal text-warn">{findings.length} review note{findings.length === 1 ? "" : "s"}</span>}
      </button>
      {open && (
        <div className="mt-2 space-y-2">
          {CREATIVE_FIELDS.map((f) => (
            <label key={f.key} className="block">
              <span className="mb-1 block text-[11px] text-fg3">{f.label}</span>
              <textarea rows={f.rows} data-creative-field={f.key} value={value(f.key)} disabled={busy}
                onChange={(e) => setDraft({ ...draft, [f.key]: e.target.value })}
                onBlur={() => {
                  const now = draft[f.key];
                  const was = f.key === "motifs" ? motifsToText(c.motifs) : String(c[f.key as keyof typeof c] ?? "");
                  if (now !== undefined && now !== was) save({ [f.key]: now });
                }} />
            </label>
          ))}
          {findings.map((x, i) => (
            <div key={i} data-finding className="rounded border border-line bg-s2 p-2 text-[12px] leading-snug">
              <div className="text-fg3">{ROLE_LABEL[x.role] ?? x.role} · {x.verdict}{x.motif ? ` · ${x.motif}` : ""}</div>
              <div className="mt-0.5 text-fg">{x.observation}</div>
              <div className="mt-0.5 text-fg2">Audience: {x.audience_impact}</div>
              <div className="mt-0.5 text-fg2">Why it matters: {x.implication}</div>
              <div className="mt-0.5 text-fg">Change: {x.recommendation}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

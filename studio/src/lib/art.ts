// View helpers for the Art view and the shot panel. Pure functions over the board read model: no rules live here
// (the engine owns validation, approval and impact); these only arrange what the engine stored for display.
import type { ArtVersion, Bible, Board, Creative, Motif } from "@/components/board/types";

export type Tone = "idle" | "warn" | "ok" | "info";

export function statusOf(ad: Board["artDirection"] | undefined): { label: string; tone: Tone; version: number | null } {
  if (!ad || (!ad.approved && !ad.pending)) return { label: "No art direction", tone: "idle", version: null };
  if (ad.pending?.status === "in_review") return { label: "Awaiting review", tone: "warn", version: ad.pending.version };
  if (ad.pending) return { label: "Draft", tone: "info", version: ad.pending.version };
  return { label: `Approved v${ad.approved!.version}`, tone: "ok", version: ad.approved!.version };
}

export type Swatch = { name: string; hex: string; role: string };

export function palette(body: Bible | undefined): Swatch[] {
  const list = (body?.color?.palette ?? []) as { name?: string; hex?: string; role?: string }[];
  return list
    .filter((p) => typeof p.hex === "string" && /^#[0-9a-f]{6}$/i.test(p.hex))
    .map((p) => ({ name: p.name ?? "", hex: p.hex!, role: p.role ?? "" }));
}

/** Motif rows by shot columns: the Bible's motifs first (in its order), then any a shot names that the Bible does not. */
export function motifGrid(body: Bible | undefined, shots: { ord: number; creative: Creative }[]) {
  const names: string[] = ((body?.motifs ?? []) as { name?: string }[]).map((m) => m.name ?? "").filter(Boolean);
  const key = (n: string) => names.find((x) => x.toLowerCase() === n.toLowerCase()) ?? n;
  for (const s of shots) for (const m of s.creative?.motifs ?? []) if (!names.includes(key(m.name))) names.push(m.name);
  return names.map((name) => {
    const entry = ((body?.motifs ?? []) as { name?: string; meaning?: string; payoff?: string }[])
      .find((m) => (m.name ?? "").toLowerCase() === name.toLowerCase());
    return {
      name, meaning: entry?.meaning ?? "", payoff: entry?.payoff ?? "",
      cells: shots.map((s) => ({
        ord: s.ord,
        state: (s.creative?.motifs ?? []).find((m) => key(m.name) === name)?.state ?? null,
      })),
    };
  });
}

/** Shot number to the reasons a version's impact gives for it. */
export function affected(v: ArtVersion | null | undefined): Map<number, string[]> {
  return new Map((v?.impact?.shots ?? []).map((s) => [s.shot, s.reasons]));
}

/** Shots whose plate or clip in use was made under an earlier direction: listed in the approved version's impact and
 *  still using an asset that impact named. Redoing the shot (a new active asset) clears it. */
export function directionChanged(board: Board): Set<string> {
  const out = new Set<string>();
  for (const s of board.artDirection?.approved?.impact?.shots ?? []) {
    const shot = board.shots.find((x) => x.ord === s.shot);
    if (!shot) continue;
    const named = new Set(s.assets.map((a) => a.id));
    if (board.assets.some((a) => a.shot_id === shot.id && a.active && named.has(a.id))) out.add(shot.id);
  }
  return out;
}

export function motifsToText(m: Motif[] | undefined): string {
  return (m ?? []).map((x) => (x.state ? `${x.name}: ${x.state}` : x.name)).join("\n");
}

export const CREATIVE_FIELDS = [
  { key: "intent", label: "Dramatic intention", rows: 2 },
  { key: "audience", label: "Audience experience", rows: 1 },
  { key: "metaphor", label: "Visual metaphor", rows: 1 },
  { key: "motifs", label: "Motifs (one per line, name: state)", rows: 2 },
  { key: "continuity", label: "Continuity", rows: 2 },
  { key: "objects", label: "Objects from the art direction (comma separated)", rows: 1 },
  { key: "materials", label: "Materials from the art direction (comma separated)", rows: 1 },
] as const;

/** A creative field as the text the panel edits: motifs as lines, materials and objects as a comma list. */
export function creativeText(c: Creative | undefined, key: string): string {
  if (key === "motifs") return motifsToText(c?.motifs);
  const v = c?.[key as keyof Creative];
  return Array.isArray(v) ? (v as string[]).join(", ") : String(v ?? "");
}

/** Which prompts of a shot are the creator's own, for the panel's marker. */
export function authoredParts(s: { plate_authored?: boolean; motion_authored?: boolean }): ("plate" | "motion")[] {
  return (["plate", "motion"] as const).filter((p) => !!s[`${p}_authored`]);
}

export function creativeCount(c: Creative | undefined): number {
  if (!c) return 0;
  return ["intent", "audience", "metaphor", "continuity"].filter((k) => !!c[k as keyof Creative]).length +
    (c.motifs?.length ? 1 : 0) + (c.materials?.length ? 1 : 0) + (c.objects?.length ? 1 : 0);
}

/** Open findings about one shot, newest review first, with the role and verdict of the review they come from. */
export function findingsFor(board: Board, ord: number) {
  return (board.critiques ?? [])
    .filter((c) => !c.resolved_at)
    .flatMap((c) => c.findings.filter((f) => f.shots?.includes(ord)).map((f) => ({ ...f, role: c.role, verdict: c.verdict, critique: c.id })));
}

export const ROLE_LABEL: Record<string, string> = {
  director: "Director", production_designer: "Production designer", cinematographer: "Cinematographer",
  editor: "Editor", emotion_editor: "Emotional editor", creator: "Creator",
};

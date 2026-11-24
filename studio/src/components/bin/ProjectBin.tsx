"use client";
// Project bin: one tile per project with its first approved plate as the hero frame.
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { getJson, media, useEvents } from "@/lib/client";

type P = { id: string; title: string; aspect: string; mode: string | null; visual_look: string | null;
  shots: number; hero: string | null; stage: string; updated_at: string };

export function ProjectBin() {
  const [projects, setProjects] = useState<P[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(() => {
    getJson<{ projects: P[] }>("/api/projects").then((d) => setProjects(d.projects)).catch((e) => setError(String(e)));
  }, []);
  useEffect(load, [load]);
  useEvents(projects ? 0 : null, (ev) => { if (ev.some((e) => e.entity === "project" || e.entity === "asset_version")) load(); });

  if (error) return <div className="text-bad">{error}</div>;
  if (!projects) return <div className="text-fg3">Loading…</div>;
  return (
    <div>
      <div className="mb-5 flex items-baseline gap-3">
        <h1 className="text-[20px] font-medium">Projects</h1>
        <span className="text-fg3">{projects.length}</span>
        <Link href="/new" className="ml-auto rounded bg-accent px-3 py-1.5 text-[13px] font-medium text-accent-ink">
          New project
        </Link>
      </div>
      {projects.length === 0 && (
        <div className="rounded-md border border-dashed border-line p-10 text-center text-fg2">
          No projects yet. Start one here or ask Claude to make a music video.
        </div>
      )}
      <div className="grid grid-cols-[repeat(auto-fill,minmax(200px,1fr))] gap-4">
        {projects.map((p) => (
          <Link key={p.id} href={`/p/${p.id}`} className="group">
            <div className="overflow-hidden rounded-md border border-line bg-s2 group-hover:border-line-strong"
              style={{ aspectRatio: p.aspect === "16:9" ? "16 / 9" : "9 / 16", maxHeight: 340 }}>
              {p.hero
                ? <img src={media(p.hero)} alt="" className="h-full w-full object-cover" loading="lazy" />
                : <div className="flex h-full items-center justify-center text-fg3">{p.shots ? `${p.shots} shots` : "No board yet"}</div>}
            </div>
            <div className="mt-2 truncate text-[13px] font-medium">{p.title}</div>
            <div className="flex gap-2 text-[12px] text-fg3">
              <span>{p.aspect}</span>
              {p.mode && <span>· {p.mode}</span>}
              <span className="ml-auto">{p.stage}</span>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}

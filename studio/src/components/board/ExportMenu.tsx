"use client";
// Export the project (JSON with media) or a contact sheet into the project's exports folder.
import { useState } from "react";
import { mb } from "@/lib/client";
import { useToast } from "@/components/ui/Toast";
import type { Board } from "./types";

export function ExportMenu({ board }: { board: Board }) {
  const toast = useToast();
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const stamp = () => new Date().toISOString().slice(0, 19).replace(/[:T]/g, "-");
  const items: { label: string; run: () => Promise<void> }[] = [
    { label: "Project JSON with media", run: async () => toast(await mb("export_json",
      { project: board.project.id, out: `${board.project.folder}/exports/project-${stamp()}` })) },
    { label: "Project JSON, no media", run: async () => toast(await mb("export_json",
      { project: board.project.id, out: `${board.project.folder}/exports/project-${stamp()}-lite`, no_media: true })) },
    { label: "Contact sheet (storyboard)", run: async () => toast(await mb("sheet", { project: board.project.id, kind: "storyboard" })) },
    { label: "Contact sheet (plates)", run: async () => toast(await mb("sheet", { project: board.project.id, kind: "plates" })) },
  ];
  return (
    <div className="relative">
      <button className="rounded px-2 py-1 text-[12px] text-fg2 hover:bg-s3" onClick={() => setOpen((o) => !o)}>
        {busy ? "Exporting…" : "Export"}
      </button>
      {open && (
        <div className="absolute right-0 top-8 z-30 w-56 rounded-md border border-line bg-s2 py-1">
          {items.map((it) => (
            <button key={it.label} disabled={busy} className="block w-full px-3 py-1.5 text-left text-[12px] hover:bg-s3"
              onClick={async () => { setOpen(false); setBusy(true); await it.run(); setBusy(false); }}>
              {it.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

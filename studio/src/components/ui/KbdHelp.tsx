"use client";
import { SHORTCUTS } from "@/lib/shortcuts";

export function KbdHelp({ onClose }: { onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/60" onClick={onClose}>
      <div className="w-[420px] rounded-md border border-line bg-s1 p-5" onClick={(e) => e.stopPropagation()}>
        <div className="mb-3 text-[15px] font-medium">Keyboard</div>
        <div className="space-y-2">
          {SHORTCUTS.map((s) => (
            <div key={s.key} className="flex items-center justify-between text-fg2">
              <span>{s.label}</span>
              <kbd className="rounded border border-line bg-s2 px-2 py-0.5 font-mono text-[12px] text-fg">{s.key}</kbd>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

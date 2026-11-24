"use client";
// Keyboard shortcut registry. Ignored while typing in a field.
import { useEffect, useRef } from "react";

export const SHORTCUTS: { key: string; label: string }[] = [
  { key: "Space", label: "Play or pause the song" },
  { key: "J / K / L", label: "Back, pause, forward" },
  { key: "← / →", label: "Previous or next shot" },
  { key: "A", label: "Approve the selected shot's plate or clip" },
  { key: "R", label: "Reject (asks for a note)" },
  { key: "E", label: "Edit the selected shot" },
  { key: "V", label: "Animatic" },
  { key: "Q", label: "Render queue" },
  { key: "?", label: "This help" },
  { key: "Esc", label: "Close panels" },
];

export type Handlers = Partial<Record<
  "space" | "j" | "k" | "l" | "left" | "right" | "a" | "r" | "e" | "v" | "q" | "help" | "escape", () => void>>;

const MAP: Record<string, keyof Handlers> = {
  " ": "space", j: "j", k: "k", l: "l", ArrowLeft: "left", ArrowRight: "right", a: "a", r: "r", e: "e", v: "v",
  q: "q", "?": "help", Escape: "escape",
};

export function useShortcuts(handlers: Handlers) {
  const h = useRef(handlers);
  useEffect(() => { h.current = handlers; }, [handlers]);
  useEffect(() => {
    const onKey = (ev: KeyboardEvent) => {
      const t = ev.target as HTMLElement | null;
      const typing = t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.tagName === "SELECT" || t.isContentEditable);
      if (typing && ev.key !== "Escape") return;
      if (ev.metaKey || ev.ctrlKey || ev.altKey) return;
      const name = MAP[ev.key] ?? MAP[ev.key.toLowerCase()];
      const fn = name && h.current[name];
      if (fn) { ev.preventDefault(); fn(); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);
}

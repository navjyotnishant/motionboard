"use client";
// Every mb action ends in a toast: the result, plus expandable verified and not verified lists.
import { createContext, useCallback, useContext, useState } from "react";
import type { Report } from "@/lib/client";

type Toast = { id: number; report: Report; open: boolean };
const Ctx = createContext<(r: Report) => void>(() => {});
export const useToast = () => useContext(Ctx);

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const push = useCallback((report: Report) => {
    const id = Date.now() + Math.random();
    setToasts((t) => [...t.slice(-3), { id, report, open: false }]);
    if (report.ok) setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id || x.open)), 6000);
  }, []);
  return (
    <Ctx.Provider value={push}>
      {children}
      <div className="fixed bottom-4 right-4 z-50 flex w-[380px] flex-col gap-2">
        {toasts.map((t) => {
          const r = t.report;
          const more = r.verified.length + r.not_verified.length > 0;
          return (
            <div key={t.id} className="rounded-md border border-line bg-s2 p-3 text-[13px]">
              <div className="flex items-start gap-2">
                <span className="mt-1 h-2 w-2 shrink-0 rounded-full" style={{ background: r.ok ? "var(--ok)" : "var(--bad)" }} />
                <div className="min-w-0 flex-1">
                  <div className="font-medium">{r.ok ? `${r.command} done` : r.error?.message || `${r.command} failed`}</div>
                  {!r.ok && r.error?.hint && <div className="mt-1 text-fg2">{r.error.hint}</div>}
                  {more && (
                    <button className="mt-1 text-fg3 hover:text-fg2" onClick={() =>
                      setToasts((all) => all.map((x) => (x.id === t.id ? { ...x, open: !x.open } : x)))}>
                      {t.open ? "Hide details" : `Details (${r.verified.length} verified, ${r.not_verified.length} not verified)`}
                    </button>
                  )}
                  {t.open && (
                    <div className="mt-2 space-y-1">
                      {r.verified.map((v, i) => <div key={`v${i}`} className="text-ok">✓ <span className="text-fg2">{v}</span></div>)}
                      {r.not_verified.map((v, i) => <div key={`n${i}`} className="text-warn">○ <span className="text-fg2">{v}</span></div>)}
                    </div>
                  )}
                </div>
                <button className="text-fg3 hover:text-fg" aria-label="Close"
                  onClick={() => setToasts((all) => all.filter((x) => x.id !== t.id))}>×</button>
              </div>
            </div>
          );
        })}
      </div>
    </Ctx.Provider>
  );
}

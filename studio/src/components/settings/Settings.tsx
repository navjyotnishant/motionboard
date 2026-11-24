"use client";
// Guard presets (set active, create), plate adapters (list, add), paths, theme and accent.
import { Fragment, useCallback, useEffect, useState } from "react";
import { getJson, mb } from "@/lib/client";
import { useToast } from "@/components/ui/Toast";

type G = { name: string; start_free_pct: number; kill_free_pct: number; swap_ceiling_mb: number; poll_seconds: number; builtin: number };
type A = { name: string; kind: string; config: Record<string, unknown>; cost_per_image_usd: number; enabled: number };
type S = { guards: G[]; active: string; adapters: A[]; paths: Record<string, string> };

const ACCENTS = ["#e8b061", "#6fa8ef", "#5fcf8a", "#ef6a8a", "#b48cf2"];

export function applyAppearance() {
  try {
    const theme = localStorage.getItem("mb-theme");
    const accent = localStorage.getItem("mb-accent");
    if (theme === "light") document.documentElement.dataset.theme = "light"; else delete document.documentElement.dataset.theme;
    if (accent) document.documentElement.style.setProperty("--accent", accent);
  } catch { /* storage can be unavailable */ }
}

export function Settings() {
  const toast = useToast();
  const [s, setS] = useState<S | null>(null);
  const [g, setG] = useState({ name: "", start: 40, kill: 10, swap: 2048 });
  const [a, setA] = useState({ name: "", kind: "handoff", config: '{"hint": "Muse"}', cost: 0 });
  const [theme, setTheme] = useState("dark");
  const load = useCallback(() => { getJson<S>("/api/settings").then(setS).catch(() => {}); }, []);
  useEffect(() => {
    load();
    try { setTheme(localStorage.getItem("mb-theme") || "dark"); } catch { /* ignore */ }
  }, [load]);
  const run = async (action: string, args: Record<string, unknown>) => { toast(await mb(action, args)); load(); };
  if (!s) return <div className="text-fg3">Loading…</div>;
  const card = "rounded-md border border-line bg-s1 p-5";

  return (
    <div className="mx-auto max-w-[900px] space-y-6">
      <section className={card}>
        <h2 className="mb-1 text-[15px] font-medium">Memory guard</h2>
        <p className="mb-3 text-[12px] text-fg3">Jobs wait until free memory reaches the start floor and stop below the kill floor or when swap grows past the ceiling.</p>
        <table className="w-full text-[13px]">
          <thead className="text-left text-[11px] uppercase text-fg3"><tr><th className="py-1">Preset</th><th>Start</th><th>Kill</th><th>Swap ceiling</th><th /></tr></thead>
          <tbody>
            {s.guards.map((x) => (
              <tr key={x.name} className="border-t border-line">
                <td className="py-2">{x.name}{x.builtin ? <span className="ml-2 text-[11px] text-fg3">built in</span> : null}</td>
                <td className="tnum">{x.start_free_pct}%</td><td className="tnum">{x.kill_free_pct}%</td>
                <td className="tnum">{x.swap_ceiling_mb} MB</td>
                <td className="text-right">
                  {s.active === x.name
                    ? <span className="text-ok">active</span>
                    : <button className="rounded border border-line px-2 py-0.5 text-[12px]" onClick={() => run("guard_set", { name: x.name })}>Use</button>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="mt-3 grid grid-cols-5 items-end gap-2">
          <label><span className="text-[11px] text-fg3">Name</span><input value={g.name} onChange={(e) => setG({ ...g, name: e.target.value })} /></label>
          <label><span className="text-[11px] text-fg3">Start %</span><input type="number" value={g.start} onChange={(e) => setG({ ...g, start: Number(e.target.value) })} /></label>
          <label><span className="text-[11px] text-fg3">Kill % (1 to 50)</span><input type="number" value={g.kill} onChange={(e) => setG({ ...g, kill: Number(e.target.value) })} /></label>
          <label><span className="text-[11px] text-fg3">Swap MB</span><input type="number" value={g.swap} onChange={(e) => setG({ ...g, swap: Number(e.target.value) })} /></label>
          <button disabled={!g.name} className="h-[34px] rounded border border-line text-[12px]"
            onClick={() => run("guard_create", { name: g.name, start: g.start, kill: g.kill, swap: g.swap })}>Create preset</button>
        </div>
      </section>

      <section className={card}>
        <h2 className="mb-1 text-[15px] font-medium">Plate adapters</h2>
        <p className="mb-3 text-[12px] text-fg3">Any image source. Keys are never stored: name a key_file or key_env in the config.</p>
        <div className="space-y-2">
          {s.adapters.map((x) => (
            <div key={x.name} className="flex items-center gap-3 rounded border border-line bg-s2 px-3 py-2 text-[13px]">
              <span className="font-medium">{x.name}</span><span className="text-fg3">{x.kind}</span>
              <code className="truncate text-[11px] text-fg3">{JSON.stringify(x.config)}</code>
              <span className="ml-auto text-fg2">{x.cost_per_image_usd ? `$${x.cost_per_image_usd}/image` : "free"}</span>
            </div>
          ))}
        </div>
        <div className="mt-3 grid grid-cols-[1fr_1fr_2fr_100px_auto] items-end gap-2">
          <label><span className="text-[11px] text-fg3">Name</span><input value={a.name} onChange={(e) => setA({ ...a, name: e.target.value })} /></label>
          <label><span className="text-[11px] text-fg3">Kind</span>
            <select value={a.kind} onChange={(e) => setA({ ...a, kind: e.target.value })}>
              {["manual", "command", "http", "handoff"].map((k) => <option key={k}>{k}</option>)}
            </select></label>
          <label><span className="text-[11px] text-fg3">Config (JSON)</span><input value={a.config} onChange={(e) => setA({ ...a, config: e.target.value })} /></label>
          <label><span className="text-[11px] text-fg3">$/image</span><input type="number" step="0.001" value={a.cost} onChange={(e) => setA({ ...a, cost: Number(e.target.value) })} /></label>
          <button disabled={!a.name} className="h-[34px] rounded border border-line px-3 text-[12px]" onClick={() => {
            let cfg: Record<string, unknown>;
            try { cfg = JSON.parse(a.config); } catch { toast({ ok: false, command: "adapter", data: {}, verified: [], not_verified: [], next: null, error: { code: "INVALID_INPUT", message: "config is not valid JSON" } }); return; }
            run("adapter_add", { name: a.name, kind: a.kind, config: cfg, cost: a.cost || undefined });
          }}>Add</button>
        </div>
      </section>

      <section className={card}>
        <h2 className="mb-3 text-[15px] font-medium">Appearance</h2>
        <div className="flex items-center gap-4">
          <div className="flex gap-2">
            {["dark", "light"].map((t) => (
              <button key={t} className="rounded border px-3 py-1 text-[12px] capitalize"
                style={{ borderColor: theme === t ? "var(--accent)" : "var(--line)" }}
                onClick={() => { setTheme(t); try { localStorage.setItem("mb-theme", t); } catch { /* ignore */ } applyAppearance(); }}>{t}</button>
            ))}
          </div>
          <div className="flex gap-2">
            {ACCENTS.map((c) => (
              <button key={c} aria-label={`accent ${c}`} className="h-6 w-6 rounded-full border border-line" style={{ background: c }}
                onClick={() => { try { localStorage.setItem("mb-accent", c); } catch { /* ignore */ } applyAppearance(); }} />
            ))}
          </div>
        </div>
      </section>

      <section className={card}>
        <h2 className="mb-3 text-[15px] font-medium">Paths</h2>
        <dl className="grid grid-cols-[120px_1fr] gap-y-1 text-[12px]">
          {Object.entries(s.paths).map(([k, v]) => (
            <Fragment key={k}><dt className="text-fg3">{k}</dt><dd className="font-mono text-fg2">{v}</dd></Fragment>))}
        </dl>
        <p className="mt-2 text-[11px] text-fg3">Change them with MB_HOME, MB_DB and MB_PROJECTS, then restart with mb studio stop and start.</p>
      </section>
    </div>
  );
}

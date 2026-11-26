// Live memory reading for the meter, the same sources the engine guard uses.
import "server-only";
import { execFile } from "node:child_process";
import fs from "node:fs";
import os from "node:os";

const run = (cmd: string, args: string[]) =>
  new Promise<string>((resolve) => execFile(cmd, args, { timeout: 4000 }, (_e, out) => resolve(out || "")));

// CPU use since the previous sample, from the per-core tick counters (no extra process).
let prevCpu: { idle: number; total: number } | null = null;
function cpuPct(): number | null {
  const t = os.cpus().reduce((a, c) => {
    const tot = c.times.user + c.times.nice + c.times.sys + c.times.idle + c.times.irq;
    return { idle: a.idle + c.times.idle, total: a.total + tot };
  }, { idle: 0, total: 0 });
  const p = prevCpu;
  prevCpu = t;
  if (!p || t.total <= p.total) return null;
  return Math.round(100 * (1 - (t.idle - p.idle) / (t.total - p.total)));
}

// GPU busy share on Apple silicon, read from the accelerator's statistics (no sudo needed).
async function gpuPct(): Promise<number | null> {
  if (process.platform !== "darwin") return null;
  const out = await run("ioreg", ["-r", "-d", "1", "-w", "0", "-c", "IOAccelerator"]);
  const m = /"Device Utilization %"=(\d+)/.exec(out);
  return m ? Number(m[1]) : null;
}

cpuPct(); // seed the counters so the first request already has a reading

export type SystemSample = {
  free_pct: number | null; swap_mb: number | null; total_gb: number; cpu_pct: number | null; gpu_pct: number | null;
};

export async function sampleSystem(): Promise<SystemSample> {
  const [mem, gpu] = await Promise.all([sampleNow(), gpuPct()]);
  return { ...mem, cpu_pct: cpuPct(), gpu_pct: gpu };
}

export async function sampleNow(): Promise<{ free_pct: number | null; swap_mb: number | null; total_gb: number }> {
  const total_gb = Math.round((os.totalmem() / 2 ** 30) * 10) / 10;
  if (process.platform === "darwin") {
    const [mp, sw] = await Promise.all([run("memory_pressure", []), run("sysctl", ["vm.swapusage"])]);
    const f = /free percentage:\s*(\d+)%/.exec(mp);
    const s = /used = ([\d.]+)([MG])/.exec(sw);
    return {
      free_pct: f ? Number(f[1]) : null,
      swap_mb: s ? Math.round(Number(s[1]) * (s[2] === "G" ? 1024 : 1)) : null,
      total_gb,
    };
  }
  try {
    const m = fs.readFileSync("/proc/meminfo", "utf8");
    const kb = (k: string) => Number(new RegExp(`${k}:\\s+(\\d+)`).exec(m)?.[1] || 0);
    return {
      free_pct: Math.round((kb("MemAvailable") / kb("MemTotal")) * 100),
      swap_mb: Math.round((kb("SwapTotal") - kb("SwapFree")) / 1024),
      total_gb,
    };
  } catch {
    return { free_pct: null, swap_mb: null, total_gb };
  }
}

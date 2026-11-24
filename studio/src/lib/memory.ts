// Live memory reading for the meter, the same sources the engine guard uses.
import "server-only";
import { execFile } from "node:child_process";
import fs from "node:fs";
import os from "node:os";

const run = (cmd: string, args: string[]) =>
  new Promise<string>((resolve) => execFile(cmd, args, { timeout: 4000 }, (_e, out) => resolve(out || "")));

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

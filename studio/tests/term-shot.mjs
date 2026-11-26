// Render a terminal-style screenshot from a text file, for docs and the demo video.
// Usage: node tests/term-shot.mjs <in.txt> <out.png> [title]
import { chromium } from "@playwright/test";
import fs from "node:fs";

const [inFile, out, title = "Terminal"] = process.argv.slice(2);
const esc = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
const body = esc(fs.readFileSync(inFile, "utf8"))
  .replace(/^(\$ .*)$/gm, '<span class="cmd">$1</span>')
  .replace(/^(✓ .*)$/gm, '<span class="ok">$1</span>')
  .replace(/^(· .*)$/gm, '<span class="dim">$1</span>');
const html = `<!doctype html><html><body><div class="win"><div class="bar"><i></i><i></i><i></i><span>${esc(title)}</span></div>
<pre>${body}</pre></div><style>
body{margin:0;background:#0b0b0d;padding:40px;font-family:ui-monospace,Menlo,monospace}
.win{width:1120px;border-radius:12px;background:#16161a;border:1px solid #2a2a30;box-shadow:0 20px 60px #0008;overflow:hidden}
.bar{height:36px;display:flex;align-items:center;gap:8px;padding:0 14px;background:#1d1d22;border-bottom:1px solid #2a2a30}
.bar i{width:12px;height:12px;border-radius:50%;background:#ff5f57}.bar i:nth-child(2){background:#febc2e}.bar i:nth-child(3){background:#28c840}
.bar span{margin-left:12px;color:#8a8a93;font-size:13px}
pre{margin:0;padding:22px 26px;color:#d6d6dc;font-size:15px;line-height:1.55;white-space:pre-wrap}
.cmd{color:#f2b35b}.ok{color:#58d68d}.dim{color:#8a8a93}</style></body></html>`;
const b = await chromium.launch({ channel: "chrome", headless: true });
const p = await b.newPage({ viewport: { width: 1200, height: 400 }, deviceScaleFactor: 2 });
await p.setContent(html);
const el = await p.$(".win");
await el.screenshot({ path: out });
await b.close();

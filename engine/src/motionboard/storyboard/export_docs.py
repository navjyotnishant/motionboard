"""Board exports for sharing (002 T043, T044).

PDF: a title page, then six shots per landscape page (frame, number, timecode, lyric, visual, action, camera).
HTML: one self-contained file (images and the song segment embedded) with the shot list and an animatic player.
"""

import base64
import html
import io
import json
import sqlite3
import subprocess
import tempfile
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw

from motionboard.storyboard.contact_sheet import ACCENT, BG, LINE, MUTED, PANEL, TEXT, _active, _clip_frame, _font, tc


def _shots(conn: sqlite3.Connection, pid: str) -> list[dict]:
    return [dict(r) for r in conn.execute("SELECT * FROM shot WHERE project_id = ? ORDER BY ord", (pid,))]


def _frame(conn: sqlite3.Connection, shot: dict) -> Image.Image | None:
    clip = _active(conn, shot["id"], "clip")
    if clip:
        f = _clip_frame(clip, min(0.5, (shot["end"] - shot["start"]) / 2))
        if f:
            return f
    plate = _active(conn, shot["id"], "plate")
    return Image.open(plate).convert("RGB") if plate else None


def _fit(img: Image.Image, w: int, h: int) -> Image.Image:
    from PIL import ImageOps
    return ImageOps.fit(img, (w, h), Image.LANCZOS)


def _wrap(d: ImageDraw.ImageDraw, x: int, y: int, label: str, text: str, width: int, font, small, lines: int) -> int:
    d.text((x, y), label.upper(), font=small, fill=MUTED)
    y += 26
    for ln in textwrap.wrap(text or "-", width=width)[:lines]:
        d.text((x, y), ln, font=font, fill=TEXT)
        y += 30
    return y + 8


def pdf(conn: sqlite3.Connection, project: dict, out: Path) -> Path:
    W, H = 2480, 1754  # A4 landscape at 210 dpi
    shots = _shots(conn, project["id"])
    big, font, small = _font(64), _font(24), _font(19)
    pages = []
    cover = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(cover)
    d.text((140, 520), project["title"], font=_font(110), fill=TEXT)
    meta = f"{len(shots)} shots · {project['aspect']} · {project.get('mode') or ''} · {project.get('visual_look') or ''}"
    d.text((140, 680), meta, font=big, fill=MUTED)
    if shots:
        d.text((140, 780), f"{tc(shots[-1]['end'])} long", font=big, fill=MUTED)
    d.rectangle((140, 900, 260, 910), fill=ACCENT)
    pages.append(cover)
    vertical = project["aspect"] == "9:16"
    fw, fh = (330, 586) if vertical else (700, 394)
    per = 6
    cols, rows = 3, 2
    cw, ch = (W - 160) // cols, (H - 200) // rows
    for start in range(0, len(shots), per):
        page = Image.new("RGB", (W, H), BG)
        d = ImageDraw.Draw(page)
        d.text((80, 50), f"{project['title']}  ·  shots {start + 1} to {min(start + per, len(shots))}", font=font, fill=MUTED)
        for i, s in enumerate(shots[start:start + per]):
            x, y = 80 + (i % cols) * cw, 120 + (i // cols) * ch
            d.rectangle((x, y, x + cw - 30, y + ch - 30), fill=PANEL, outline=LINE)
            img = _frame(conn, s)
            fx, fy = x + 20, y + 20
            if vertical:
                if img:
                    page.paste(_fit(img, fw, fh), (fx, fy))
                else:
                    d.rectangle((fx, fy, fx + fw, fy + fh), fill=BG, outline=LINE)
                tx, ty, tw = fx + fw + 24, fy, 22
            else:
                if img:
                    page.paste(_fit(img, fw, fh), (fx, fy))
                else:
                    d.rectangle((fx, fy, fx + fw, fy + fh), fill=BG, outline=LINE)
                tx, ty, tw = fx, fy + fh + 16, 52
            d.text((tx, ty), f"{s['ord']:02d}", font=big, fill=ACCENT)
            d.text((tx + 100, ty + 30), f"{tc(s['start'])} to {tc(s['end'])}", font=small, fill=MUTED)
            ty += 90
            ty = _wrap(d, tx, ty, "lyric", s["lyric"], tw, font, small, 2)
            ty = _wrap(d, tx, ty, "visual", s["visual"], tw, font, small, 4 if vertical else 2)
            ty = _wrap(d, tx, ty, "action", s["action"], tw, font, small, 3 if vertical else 1)
            _wrap(d, tx, ty, "camera", s["camera"], tw, font, small, 2 if vertical else 1)
        pages.append(page)
    out.parent.mkdir(parents=True, exist_ok=True)
    pages[0].save(out, "PDF", resolution=210, save_all=True, append_images=pages[1:])
    return out


def _b64_image(img: Image.Image, width: int = 360) -> str:
    img = img.copy()
    img.thumbnail((width, width * 2))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=78)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def _b64_audio(project: dict) -> str | None:
    seg = Path(project["folder"]) / "audio" / "segment.wav"
    if not seg.exists():
        return None
    with tempfile.TemporaryDirectory() as d:
        mp3 = Path(d) / "s.mp3"
        r = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(seg), "-b:a", "96k",
                            str(mp3)], capture_output=True)
        if r.returncode != 0:
            return None
        return "data:audio/mpeg;base64," + base64.b64encode(mp3.read_bytes()).decode()


PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><title>__TITLE__ · storyboard</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
body{margin:0;background:#0b0b0d;color:#ecebe8;font:14px/1.45 Inter,system-ui,sans-serif}
header{padding:24px 32px;border-bottom:1px solid #2a2a33;display:flex;gap:16px;align-items:baseline}
h1{font-size:22px;margin:0;font-weight:500} .m{color:#8b8a93}
main{padding:24px 32px;display:grid;grid-template-columns:repeat(auto-fill,minmax(__COL__px,1fr));gap:16px}
.s{background:#121216;border:1px solid #2a2a33;border-radius:8px;overflow:hidden}
.s.on{border-color:#e8b061} .s img{width:100%;display:block;aspect-ratio:__RATIO__;object-fit:cover;background:#202027}
.s .b{padding:10px 12px} .n{color:#e8b061;font-weight:600;margin-right:8px} .t{font:12px ui-monospace,monospace;color:#8b8a93}
.k{font-size:10px;letter-spacing:.08em;text-transform:uppercase;color:#6f6e78;margin-top:8px}
#player{position:sticky;top:0;background:#0b0b0d;z-index:2;padding:12px 32px;border-bottom:1px solid #2a2a33;display:flex;gap:16px;align-items:center}
#stage{height:240px;aspect-ratio:__RATIO__;background:#202027;border-radius:6px;overflow:hidden;position:relative}
#stage img{width:100%;height:100%;object-fit:cover} #line{position:absolute;left:0;right:0;bottom:12px;text-align:center;font-size:13px;text-shadow:0 1px 8px #000}
button{background:#e8b061;color:#1a1206;border:0;border-radius:4px;padding:6px 12px;font-weight:600;cursor:pointer}
</style></head><body>
<header><h1>__TITLE__</h1><span class="m">__META__</span></header>
__PLAYER__
<main>__CARDS__</main>
<script>
const SHOTS=__SHOTS__, LINES=__LINES__;
const a=document.getElementById('audio'), img=document.getElementById('frame'), ln=document.getElementById('line');
if(a){(function tick(){const t=a.currentTime;const s=SHOTS.find(x=>t>=x.start&&t<x.end)||SHOTS[SHOTS.length-1];
 if(s&&img.dataset.ord!=s.ord){img.src=s.img||'';img.dataset.ord=s.ord;document.querySelectorAll('.s').forEach(e=>e.classList.toggle('on',e.dataset.ord==s.ord));}
 const l=LINES.find(x=>t>=x.start&&t<x.end);ln.textContent=l?l.text:'';requestAnimationFrame(tick);})();}
document.querySelectorAll('.s').forEach(e=>e.onclick=()=>{if(a){a.currentTime=+e.dataset.start;a.play();}});
</script></body></html>"""


def html_export(conn: sqlite3.Connection, project: dict, out: Path, with_audio: bool = True) -> Path:
    shots = _shots(conn, project["id"])
    a = conn.execute("SELECT lines FROM song_analysis WHERE project_id = ?", (project["id"],)).fetchone()
    lines = json.loads(a["lines"]) if a else []
    vertical = project["aspect"] == "9:16"
    data, cards = [], []
    for s in shots:
        img = _frame(conn, s)
        src = _b64_image(img, 360 if vertical else 560) if img else ""
        data.append({"ord": s["ord"], "start": s["start"], "end": s["end"], "img": src})
        e = html.escape
        cards.append(
            f'<div class="s" data-ord="{s["ord"]}" data-start="{s["start"]}">'
            + (f'<img src="{src}" alt="">' if src else '<img alt="">')
            + f'<div class="b"><span class="n">{s["ord"]:02d}</span><span class="t">{tc(s["start"])} to {tc(s["end"])}</span>'
            + f'<div class="k">Lyric</div><div>{e(s["lyric"] or "-")}</div>'
            + f'<div class="k">Visual</div><div>{e(s["visual"])}</div>'
            + f'<div class="k">Action</div><div>{e(s["action"])}</div>'
            + f'<div class="k">Camera</div><div>{e(s["camera"])}</div></div></div>')
    audio = _b64_audio(project) if with_audio else None
    player = (f'<div id="player"><div id="stage"><img id="frame" alt=""><div id="line"></div></div>'
              f'<audio id="audio" controls src="{audio}"></audio><span class="m">Play to watch the animatic; click a shot to jump.</span></div>'
              if audio else "")
    meta = f"{len(shots)} shots · {project['aspect']} · {project.get('mode') or ''} · {project.get('visual_look') or ''}"
    page = (PAGE.replace("__TITLE__", html.escape(project["title"])).replace("__META__", html.escape(meta))
            .replace("__RATIO__", "9/16" if vertical else "16/9").replace("__COL__", "220" if vertical else "360")
            .replace("__PLAYER__", player).replace("__CARDS__", "\n".join(cards))
            .replace("__SHOTS__", json.dumps(data)).replace("__LINES__", json.dumps(lines)))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page)
    return out

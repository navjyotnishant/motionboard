"""Contact sheet: one tile per shot with frame, number, timecode, lyric and state (T032)."""

import sqlite3
import subprocess
import tempfile
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

BG = (14, 15, 17)
PANEL = (22, 24, 27)
LINE = (36, 39, 44)
TEXT = (231, 231, 233)
MUTED = (139, 143, 151)
ACCENT = (242, 163, 58)
STATE_COLOURS = {
    "plate_approved": (88, 166, 110), "clip_approved": (88, 166, 110),
    "needs_redo": (214, 92, 92), "clip_failed": (214, 92, 92),
    "clip_rendering": (92, 140, 214), "clip_queued": (92, 140, 214),
}


def _font(size: int):
    for name in ("Inter-Regular.ttf", "/System/Library/Fonts/SFNS.ttf", "/System/Library/Fonts/Helvetica.ttc",
                 "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


def tc(seconds: float) -> str:
    m, s = divmod(seconds, 60)
    return f"{int(m)}:{s:04.1f}"


def _active(conn: sqlite3.Connection, shot_id: str, kind: str) -> str | None:
    row = conn.execute("SELECT path FROM asset_version WHERE shot_id = ? AND kind = ? AND active = 1",
                       (shot_id, kind)).fetchone()
    return row["path"] if row and row["path"] and Path(row["path"]).exists() else None


def _clip_frame(path: str, at: float = 0.5) -> Image.Image | None:
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / "f.png"
        r = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-ss", str(at), "-i", path,
                            "-frames:v", "1", str(out)], capture_output=True)
        if r.returncode == 0 and out.exists():
            return Image.open(out).convert("RGB")
    return None


def render(conn: sqlite3.Connection, project: dict, kind: str, out: Path) -> Path:
    shots = [dict(r) for r in conn.execute("SELECT * FROM shot WHERE project_id = ? ORDER BY ord", (project["id"],))]
    vertical = project["aspect"] == "9:16"
    tw, th = (240, 427) if vertical else (384, 216)
    cols = 6 if vertical else 4
    cap_h = 92
    pad = 16
    cols = max(1, min(cols, len(shots)))
    rows = max(1, -(-len(shots) // cols))
    header = 64
    W = pad + cols * (tw + pad)
    H = header + pad + rows * (th + cap_h + pad)
    sheet = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(sheet)
    f_title, f_cap, f_small = _font(26), _font(15), _font(13)
    d.text((pad, 18), f"{project['title']}  ·  {kind}  ·  {len(shots)} shots", font=f_title, fill=TEXT)
    for i, s in enumerate(shots):
        x = pad + (i % cols) * (tw + pad)
        y = header + pad + (i // cols) * (th + cap_h + pad)
        img = None
        if kind == "clips":
            p = _active(conn, s["id"], "clip")
            img = _clip_frame(p) if p else None
        if img is None and kind in ("plates", "clips"):
            p = _active(conn, s["id"], "plate")
            img = Image.open(p).convert("RGB") if p else None
        if img is not None:
            sheet.paste(ImageOps.fit(img, (tw, th)), (x, y))
        else:
            d.rectangle([x, y, x + tw, y + th], fill=PANEL, outline=LINE)
            wrap = textwrap.wrap(s["visual"], width=28 if vertical else 44)[:10]
            for k, line in enumerate(wrap):
                d.text((x + 12, y + 14 + k * 19), line, font=f_small, fill=MUTED)
            act = textwrap.wrap("action: " + s["action"], width=28 if vertical else 44)[:3]
            for k, line in enumerate(act):
                d.text((x + 12, y + th - 14 - 19 * (len(act) - k)), line, font=f_small, fill=TEXT)
        d.rectangle([x, y + th, x + tw, y + th + cap_h], fill=PANEL)
        colour = STATE_COLOURS.get(s["state"], MUTED)
        d.ellipse([x + tw - 18, y + th + 12, x + tw - 8, y + th + 22], fill=colour)
        d.text((x + 10, y + th + 8), f"{s['ord']:02d}", font=f_cap, fill=ACCENT)
        d.text((x + 42, y + th + 8), f"{tc(s['start'])} – {tc(s['end'])}", font=f_small, fill=MUTED)
        lyric = textwrap.wrap(s["lyric"] or "(instrumental)", width=30 if vertical else 48)[:2]
        for k, line in enumerate(lyric):
            d.text((x + 10, y + th + 34 + k * 18), line, font=f_small, fill=TEXT)
        d.text((x + 10, y + th + cap_h - 20), ("figure" if s["has_figure"] else "no figure")
               + (" · lip-sync" if s["lip_sync"] else ""), font=f_small, fill=MUTED)
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    return out

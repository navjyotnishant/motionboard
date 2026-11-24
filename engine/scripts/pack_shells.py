"""Write the HTML shells for the Phase 9 packs. Each pack keeps its own copy, so packs stay self-contained."""
import shutil
import sys
from pathlib import Path

ROOT = Path.home() / "dev/motionboard/modes"
FONTSRC = [ROOT / "two-lovers/animation/fonts", Path.home() / "Movies/NAVAAN-reels/letter-never-sent/film/fonts"]
NOTICE = "Required Notice: Copyright (c) 2026 Navjyot Nishant. PolyForm Noncommercial 1.0.0."
GSAP = '<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>'

PACKS = {
    "studio-session": {
        "title": "Studio Session", "what": "REC light, tape counter, VU meters, typed lyric sheet, cassette end card",
        "fonts": [("JBM", "500", "normal", "jetbrains-mono-latin-500-normal.woff2"),
                  ("CG", "500", "normal", "cormorant-garamond-latin-500-normal.woff2"),
                  ("CG", "400", "italic", "cormorant-garamond-latin-400-italic.woff2")],
        "ofl": ["OFL-JetBrainsMono.txt", "OFL-CormorantGaramond.txt"],
    },
    "travel": {
        "title": "Travel", "what": "route line drawn between cuts, lyric ink stamps, boarding pass end card",
        "fonts": [("JBM", "500", "normal", "jetbrains-mono-latin-500-normal.woff2"),
                  ("CG", "500", "normal", "cormorant-garamond-latin-500-normal.woff2"),
                  ("CG", "400", "italic", "cormorant-garamond-latin-400-italic.woff2")],
        "ofl": ["OFL-JetBrainsMono.txt", "OFL-CormorantGaramond.txt"],
    },
    "lyric-story": {
        "title": "Lyric Story", "what": "one big word per beat with hard cuts, handwritten line underneath",
        "fonts": [("IT", "800", "normal", "inter-tight-latin-800-normal.woff2"),
                  ("IT", "500", "normal", "inter-tight-latin-500-normal.woff2"),
                  ("LBA", "400", "normal", "la-belle-aurore-latin-400-normal.woff2")],
        "ofl": ["OFL-InterTight.txt", "OFL-LaBelleAurore.txt"],
    },
    "mood-loop": {
        "title": "Mood Loop", "what": "light leaks, drifting particles, breathing lyric fades",
        "fonts": [("CG", "500", "normal", "cormorant-garamond-latin-500-normal.woff2"),
                  ("CG", "400", "italic", "cormorant-garamond-latin-400-italic.woff2")],
        "ofl": ["OFL-CormorantGaramond.txt"],
    },
}


def faces(fonts):
    return "\n".join(
        f'      @font-face {{ font-family: "{f}"; font-weight: {w}; font-style: {s}; src: url(fonts/{file}) format("woff2"); }}'
        for f, w, s, file in fonts)


def loads(fonts):
    return ", ".join(f"document.fonts.load('{'italic ' if s == 'italic' else ''}{w} 60px \"{f}\"')" for f, w, s, _ in fonts)


def shell(p, kind):
    bg = "#fff" if kind == "matte" else "#000"
    dur = "1" if kind == "cover" else "__DURATION__"
    fontcss = "" if kind == "matte" else faces(p["fonts"])
    extra = "      #bg { position: absolute; inset: 0; background: url(cover-bg.jpg) center / cover no-repeat; }\n" \
        if kind == "cover" else ""
    body_bg = '        <div id="bg"></div>\n' if kind == "cover" else ""
    ready = "Promise.resolve()" if kind == "matte" else \
        f"document.fonts.ready.then(function () {{ return Promise.all([{loads(p['fonts'])}]); }})"
    obj = {"overlay": "OVERLAY", "matte": "MATTE", "cover": "COVER"}[kind]
    return f"""<!doctype html>
<!-- Motionboard · {p['title']} pack · {kind}. {p['what']}.
     {NOTICE} -->
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=__W__, height=__H__" />
    <title>{p['title']} · {kind}</title>
    {GSAP}
    <style>
{fontcss}
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{ width: __W__px; height: __H__px; overflow: hidden; background: {bg}; }}
      #root {{ position: relative; width: __W__px; height: __H__px; overflow: hidden; background: {bg}; }}
      .layer {{ position: absolute; inset: 0; pointer-events: none; }}
      #fx {{ position: absolute; inset: 0; width: __W__px; height: __H__px; }}
{extra}    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{dur}" data-width="__W__" data-height="__H__">
      <div id="stage" class="clip layer" data-start="0" data-duration="{dur}" data-track-index="1">
{body_bg}        <canvas id="fx" width="__W__" height="__H__"></canvas>
      </div>
    </div>
    <script src="js/config.js"></script>
    <script src="js/common.js"></script>
    <script src="js/{kind}.js"></script>
    <script>
      (function () {{
        var root = document.getElementById("root"), duration = parseFloat(root.dataset.duration), clock = {{ t: 0 }};
        window.__hf = window.__hf || {{}}; window.__hf.buildReady = window.__hf.buildReady || {{}};
        window.__hf.buildReady["main"] = {ready}.then(function () {{ window.{obj}.init(); window.{obj}.render(0); }});
        var tl = gsap.timeline({{ paused: true }});
        tl.to(clock, {{ t: duration, duration: duration, ease: "none", onUpdate: function () {{ window.{obj}.render(clock.t); }} }});
        window.__timelines = window.__timelines || {{}}; window.__timelines["main"] = tl;
      }})();
    </script>
  </body>
</html>
"""


def main(slugs):
    for slug in slugs:
        p = PACKS[slug]
        d = ROOT / slug / "animation"
        (d / "js").mkdir(parents=True, exist_ok=True)
        (d / "fonts").mkdir(exist_ok=True)
        for kind in ("overlay", "matte", "cover"):
            (d / f"{kind}.html").write_text(shell(p, kind))
        for _, _, _, file in p["fonts"]:
            src = next((s / file for s in FONTSRC if (s / file).exists()), None)
            if src is None:
                sys.exit(f"missing font {file}")
            shutil.copy2(src, d / "fonts" / file)
        for ofl in p["ofl"]:
            src = ROOT / "two-lovers/animation/fonts" / ofl
            if src.exists():
                shutil.copy2(src, d / "fonts" / ofl)
        (d / "NOTICE").write_text(
            f"Motionboard animation pack: {p['title']} ({p['what']})\n\n"
            "Licensed under the PolyForm Noncommercial License 1.0.0, see ../../LICENSE\n"
            "(https://polyformproject.org/licenses/noncommercial/1.0.0).\n\n"
            "Required Notice: Copyright (c) 2026 Navjyot Nishant (https://github.com/navjyotnishant/motionboard)\n\n"
            "Fonts in fonts/ are licensed separately under the SIL Open Font License 1.1 (see the OFL files there).\n")
        print(slug, "ok")


if __name__ == "__main__":
    main(sys.argv[1:] or list(PACKS))

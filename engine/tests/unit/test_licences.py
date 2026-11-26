"""Every animation pack carries the PolyForm Noncommercial notice (T076); the engine is Apache 2.0."""

from motionboard import config

ROOT = config.repo_root()
NOTICE = "Required Notice: Copyright (c) 2026 Navjyot Nishant"


def test_modes_licence_is_polyform_noncommercial():
    text = (ROOT / "modes" / "LICENSE").read_text()
    assert "PolyForm Noncommercial License 1.0.0" in text
    assert NOTICE in text


def test_every_pack_has_notice_and_marked_files():
    packs = [p for p in (ROOT / "modes").glob("*/animation") if (p / "pack.json").exists()]
    assert packs, "no animation packs found"
    for pack in packs:
        assert NOTICE in (pack / "NOTICE").read_text(), pack
        for f in [*pack.glob("*.html"), *pack.glob("js/*.js")]:
            if f.name == "config.js":
                continue
            assert "PolyForm Noncommercial" in f.read_text(), f


def test_bundled_fonts_ship_with_their_licence():
    for pack in (ROOT / "modes").glob("*/animation"):
        fonts = list((pack / "fonts").glob("*.woff2")) if (pack / "fonts").exists() else []
        if fonts:
            assert list((pack / "fonts").glob("OFL*.txt")), pack


def test_engine_is_apache():
    assert "Apache License" in (ROOT / "LICENSE").read_text().splitlines()[1]
    assert "Version 2.0, January 2004" in (ROOT / "LICENSE").read_text()
    assert (ROOT / "NOTICE").read_text().startswith("Motionboard")

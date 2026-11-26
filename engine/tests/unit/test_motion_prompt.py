"""Motion prompts: lip-sync shots carry the singing clause; looks' 'film still' wording never reaches video."""

from motionboard.storyboard.draft import SINGING, motion_prompt
from motionboard.storyboard.templates import Look


def look() -> Look:
    return Look(slug="t", name="T", summary="", world="", style_line="photorealistic cinematic film still, amber light",
                no_figure_line="no people", negative="")


def test_lip_sync_adds_singing_clause():
    p = motion_prompt("he sings the line", "close-up", True, look(), lip_sync=True)
    assert "precise lip movement" in p and "each syllable" in p
    assert p.index("He sings the line") < p.index("precise lip movement") < p.index("Camera: close-up")


def test_no_singing_clause_without_lip_sync_or_figure():
    assert SINGING not in motion_prompt("he walks", "wide", True, look())
    assert "precise lip movement" not in motion_prompt("rain runs", "macro", False, look(), lip_sync=True)


def test_film_still_becomes_film_shot_for_video():
    p = motion_prompt("he walks", "wide", True, look())
    assert "film still" not in p and "film shot" in p


def test_detailed_paragraph_has_all_parts_and_stays_under_200_words():
    p = motion_prompt("he turns the phone face down", "slow push in, medium close-up", True, look(),
                      visual="HIM sits on the edge of an unmade bed in a dark bedroom",
                      cast=["Adrian, dark curly hair, light stubble, black knit sweater"])
    for part in ("He turns the phone face down.", "breathing", "Adrian, dark curly hair",
                 "The scene: HIM sits", "Camera: slow push in", "amber light"):
        assert part in p, part
    assert "\n" not in p and len(p.split()) <= 200

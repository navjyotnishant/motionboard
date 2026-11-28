"""Art Direction Bible shape, profiles, warnings and the Markdown view (feature 003, FR-001 to FR-002, FR-007)."""

import copy
import json
from pathlib import Path

from motionboard.direction import bible

REPO = Path(__file__).resolve().parents[3]
FIX = Path(__file__).resolve().parents[1] / "fixtures" / "almost-yours"


def museum() -> dict:
    return json.loads((FIX / "bible.json").read_text())


def test_engine_schema_is_the_spec_contract():
    spec = json.loads((REPO / "specs/003-creative-direction-system/contracts/art-direction.schema.json").read_text())
    assert bible.schema() == spec
    assert set(spec["properties"]) == set(bible.SECTIONS)


def test_museum_of_almosts_is_a_complete_full_bible():
    b = museum()
    assert bible.structure_errors(b) == []
    assert bible.profile_errors(b, "full") == []
    assert "Paper suits that" in b["identity"]["song_relationship"]  # why origami fits the song (acceptance 2)


def test_full_profile_names_each_missing_part():
    b = museum()
    del b["motifs"][0]["payoff"]
    b["motifs"][0]["evolution"] = b["motifs"][0]["evolution"][:1]
    b["color"]["palette"] = b["color"]["palette"][:1]
    del b["constraints"]["never_change"]
    errs = bible.profile_errors(b, "full")
    assert any("payoff" in e for e in errs)
    assert any("at least two stages" in e for e in errs)
    assert any("color.palette" in e for e in errs)
    assert any("never_change" in e for e in errs)


def test_compact_profile_needs_only_concept_world_palette():
    b = {"identity": {"concept": "a road trip"}, "world": {"description": "desert highways at dusk"},
         "color": {"prompt_line": "dusty orange and teal"}}
    assert bible.structure_errors(b) == [] and bible.profile_errors(b, "compact") == []
    assert bible.profile_errors({"world": {"description": "x"}}, "compact")


def test_structure_errors_refuse_unknown_fields_and_bad_hex():
    b = museum()
    b["mood"] = "sad"
    b["color"]["palette"][0]["hex"] = "navy"
    b["characters"][0]["eyes"] = "big"
    errs = bible.structure_errors(b)
    assert any(e.startswith("mood: unknown field") for e in errs)
    assert any("hex" in e and "navy" in e for e in errs)
    assert any("characters[0].eyes: unknown field" in e for e in errs)


def test_vague_words_without_meaning_are_flagged():
    b = copy.deepcopy(museum())
    b["lighting"]["quality"] = "Make it cinematic and beautiful"
    warns = bible.vague_warnings(b)
    assert any(w.startswith("lighting.quality") for w in warns)
    assert not bible.vague_warnings(museum())


def test_cast_warnings_point_at_missing_designs():
    warns = bible.cast_warnings(museum(), {"HER": [2, 3], "HIM": [3], "SINGER": [1], "GHOST": []})
    assert warns == ["characters: SINGER appears in shots 1 but has no design here"]
    assert bible.cast_warnings(museum(), {"HER": [2]}) == [
        "characters: HIM is designed here but is not a character in the project"]


def test_markdown_view_has_every_section_and_says_it_is_generated():
    md = bible.render_markdown(museum(), {"title": "Almost Yours", "version": 2, "status": "approved",
                                          "profile": "full", "approved_at": "2026-11-27T10:00:00Z",
                                          "approved_via": "studio"})
    for heading in ("A. Film identity", "B. World", "C. Characters", "### HER", "D. Materials and objects",
                    "E. Colour and light", "F. Cinematic language", "G. Motifs and progression",
                    "H. Motion grammar", "I. Visual constraints"):
        assert f"## {heading}" in md or heading in md, heading
    assert "Generated from the Motionboard database" in md
    assert "| ruby | `#9B111E` | accent |" in md
    assert "Version 2 · approved · full profile · approved 2026-11-27 via studio" in md

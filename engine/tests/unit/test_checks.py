"""Checks that find a bad take or a bad board without a person: scene jumps in a clip, half sung lines."""

import shutil
import subprocess

import pytest

from motionboard import checks
from motionboard.storyboard.draft import motion_prompt
from motionboard.storyboard.templates import Look

needs_ffmpeg = pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg not installed")


def test_a_move_is_not_a_cut():
    steady = [1.0, 1.2, 0.9, 1.1, 1.3, 1.0, 1.1]
    assert checks.find_cuts(steady) == []
    # A fast move raises every frame's change together; nothing stands out from the clip's own level.
    assert checks.find_cuts([5.0, 6.0, 7.0, 6.5, 5.5, 6.0]) == []


def test_a_jump_is_a_cut_and_reports_the_frame_after_it():
    assert checks.find_cuts([1.0, 1.2, 0.9, 40.0, 1.1, 1.0, 1.2]) == [4]
    # Under the floor: a still clip with one small flicker is not a cut.
    assert checks.find_cuts([0.1, 0.1, 0.1, 3.0, 0.1, 0.1]) == []


def _clip(path, graph, frames=48):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", graph, "-frames:v", str(frames),
                    "-pix_fmt", "yuv420p", str(path)], check=True)
    return path


@needs_ffmpeg
def test_scene_cut_found_in_a_real_file(tmp_path):
    one = _clip(tmp_path / "one.mp4", "testsrc2=s=320x180:r=24")
    assert checks.clip_problem(one) is None
    a = _clip(tmp_path / "a.mp4", "testsrc2=s=320x180:r=24", 24)
    b = _clip(tmp_path / "b.mp4", "mandelbrot=s=320x180:r=24", 24)
    two = tmp_path / "two.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(a), "-i", str(b), "-filter_complex",
                    "[0:v][1:v]concat=n=2:v=1[v]", "-map", "[v]", "-pix_fmt", "yuv420p", str(two)], check=True)
    assert checks.scene_cuts(two) == [24]
    assert "scene jumps at frame 24" in checks.clip_problem(two)


def _shot(ord_, start, end, sing):
    return {"ord": ord_, "start": start, "end": end, "lip_sync": sing}


LINE = [{"start": 56.9, "end": 61.7, "text": "You only miss me in the dark,"}]


def test_line_cut_off_by_the_next_shot_is_flagged_with_the_fix():
    w = checks.split_lines([_shot(18, 56.9, 59.141, 1), _shot(19, 59.141, 61.7, 0)], LINE)
    assert len(w) == 1
    assert "shot 18 sings only part" in w[0] and "59.1 to 61.7 s" in w[0] and "make shot 19 a singing shot" in w[0]


def test_singer_arriving_mid_line_is_flagged():
    w = checks.split_lines([_shot(45, 54.0, 59.0, 0), _shot(46, 59.0, 61.7, 1)], LINE)
    assert len(w) == 1 and "56.9 to 59.0 s" in w[0] and "shot 45" in w[0]


def test_whole_line_on_one_or_more_singing_shots_is_fine():
    assert checks.split_lines([_shot(18, 56.9, 61.7, 1)], LINE) == []
    assert checks.split_lines([_shot(18, 56.9, 59.141, 1), _shot(19, 59.141, 61.7, 1)], LINE) == []
    # A cut that snapped to a beat a little inside the line does not split it.
    assert checks.split_lines([_shot(18, 57.05, 61.6, 1)], LINE) == []


def test_lines_with_no_singing_shot_are_left_alone():
    assert checks.split_lines([_shot(1, 50.0, 70.0, 0)], LINE) == []
    # A singing shot that only brushes the line (the tail of the one before) does not claim it.
    assert checks.split_lines([_shot(17, 50.0, 57.2, 1), _shot(18, 57.2, 70.0, 0)], LINE) == []


def test_clip_prompt_never_lists_things_that_are_not_in_the_frame():
    look = Look(slug="t", name="T", summary="", world="", style_line="cinematic film still",
                no_figure_line="only rooms, windows, streets and objects, no people", negative="")
    obj = motion_prompt("the flame leans and goes out", "macro, static", False, look)
    assert "streets" not in obj and "no people" not in obj
    assert "Nobody and nothing new enters the frame" in obj
    people = motion_prompt("she turns to the window", "medium", True, look)
    assert "keeps the same face, hair and clothes" in people


def test_shot_that_repeats_its_lyric_is_listed_and_singing_shots_are_not():
    literal = {"ord": 30, "lyric": "You leave your jacket by my door,", "lip_sync": 0,
               "visual": "a leather jacket hangs on the door of a dim hallway", "action": "the jacket sways"}
    meant = {"ord": 31, "lyric": "You leave your jacket by my door,", "lip_sync": 0,
             "visual": "HIM sets two cups on the counter, then puts one back", "action": "he closes the cupboard"}
    singer = {**literal, "ord": 32, "lip_sync": 1}
    w = checks.literal_shots([literal, meant, singer])
    assert len(w) == 1 and w[0].startswith("shot 30") and "door, jacket" in w[0]

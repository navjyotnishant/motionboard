"""ffmpeg command builder and animation pack config (T062)."""

import json
from pathlib import Path

from motionboard.finish import assemble, overlay

SHOTS = [{"start": 0.0, "end": 2.531}, {"start": 2.531, "end": 5.039}, {"start": 5.039, "end": 10.0}]
CLIPS = [Path(f"/c/shot-0{i}.mp4") for i in (1, 2, 3)]


def test_cut_frames_follow_shot_times():
    assert assemble.cut_frames(SHOTS, 24) == [0, 61, 121, 240]


def test_plan_trims_each_clip_to_its_frames_and_sets_duration():
    plan = assemble.build(SHOTS, CLIPS, Path("/a/seg.wav"), Path("/o/final.mp4"), "9:16",
                          overlay=Path("/o/ov.mp4"), matte=Path("/o/mt.mp4"), tail=1.5)
    graph = plan.cmd[plan.cmd.index("-filter_complex") + 1]
    assert "trim=end_frame=61" in graph and "trim=end_frame=60" in graph and "trim=end_frame=119" in graph
    assert "scale=1080:1920" in graph
    assert "blend=all_mode=multiply" in graph and "blend=all_mode=screen" in graph
    assert graph.index("multiply") < graph.index("screen")  # matte dims before the overlay lights
    assert "noise=alls=3" in graph and "apad=pad_dur=1.5" in graph
    assert plan.duration == 11.5 and plan.total_frames == 276
    assert plan.cmd[-1] == "/o/final.mp4" and "+faststart" in plan.cmd


def test_plan_without_pack_and_landscape():
    plan = assemble.build(SHOTS, CLIPS, Path("/a/seg.wav"), Path("/o/f.mp4"), "16:9")
    graph = plan.cmd[plan.cmd.index("-filter_complex") + 1]
    assert "scale=1920:1080" in graph and "blend" not in graph


def test_pack_config_and_templating(tmp_path):
    project = {"aspect": "9:16", "theme": json.dumps({"artist": "NAVAAN", "song": "Paper Boats",
                                                      "highlight_words": ["almost"]})}
    analysis = {"beats": [0.5 * i for i in range(1, 20)],
                "lines": [{"start": 0.0, "end": 2.5, "text": "paper boats", "source": "beat"}]}
    cfg = overlay.make_config(project, analysis, SHOTS, 1.5)
    assert cfg["duration"] == 11.5 and cfg["music_end"] == 10.0
    assert cfg["cuts"] == [2.531, 5.039]
    assert cfg["downbeats"][:2] == [0.5, 2.5]
    work = overlay.prepare("two-lovers", cfg, tmp_path / "pack")
    html = (work / "overlay.html").read_text()
    assert "__DURATION__" not in html and 'data-duration="11.500"' in html and 'width="1080"' in html
    assert (work / "js" / "config.js").read_text().startswith("window.MB = ")
    assert (work / "NOTICE").exists()


def test_every_mode_pack_declares_layers():
    for mode in ("two-lovers",):
        p = overlay.load_pack(mode)
        assert {"matte", "overlay"} <= set(p["layers"])
        assert "9:16" in p["aspects"]

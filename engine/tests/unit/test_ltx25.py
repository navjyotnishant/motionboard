"""LTX-2.5 backend: command building and the registry."""

from pathlib import Path

from motionboard.backends import registry
from motionboard.backends.base import ClipJob
from motionboard.backends.ltx25 import LTX25Backend


def job(mode, tmp_path):
    return ClipJob(mode, tmp_path / "p.png", "he sings", 576, 1024, 97, tmp_path / "o.mp4", 24, 7,
                   tmp_path / "v.wav" if mode == "a2v" else None)


def test_registered():
    assert "ltx25" in registry.names()


def test_lipsync_uses_dfr_with_the_detail_addon(tmp_path, monkeypatch):
    lora = tmp_path / "detail.safetensors"
    lora.write_bytes(b"x")
    monkeypatch.setenv("MB_LTX25_DETAIL_LORA", str(lora))
    cmd = LTX25Backend(bin_path="ltx", snapshot=str(tmp_path)).build_command(job("a2v", tmp_path))
    assert "--dfr" in cmd and cmd[cmd.index("--detailing-lora") + 1] == str(lora)
    assert "--distilled" not in cmd and cmd[cmd.index("--seed") + 1] == "7"


def test_lipsync_falls_back_to_fast_path_without_the_addon(tmp_path, monkeypatch):
    monkeypatch.setenv("MB_LTX25_DETAIL_LORA", str(tmp_path / "missing"))
    cmd = LTX25Backend(bin_path="ltx", snapshot=str(tmp_path)).build_command(job("a2v", tmp_path))
    assert "--distilled" in cmd and "--dfr" not in cmd


def test_image_to_video_uses_fast_path(tmp_path):
    cmd = LTX25Backend(bin_path="ltx", snapshot=str(tmp_path)).build_command(job("i2v", tmp_path))
    assert cmd[1] == "generate" and "--distilled" in cmd and "--no-audio" in cmd


def test_progress_reads_ancestral_lines():
    b = LTX25Backend()
    assert b.parse_progress("Denoising (ancestral):  50%|█████     | 4/8 [00:46<00:47, 11.83s/it]") == 0.15
    assert b.parse_progress("Saved to: x.mp4") == 1.0
    assert isinstance(Path("x"), Path)

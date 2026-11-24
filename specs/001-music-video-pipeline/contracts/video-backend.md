# Contract: Video backend

```python
class VideoBackend(Protocol):
    name: str                      # "ltx23"
    license_url: str
    frame_rule: Callable[[int], int]   # LTX: round to 8k+1
    min_frames: int
    sizes: dict[str, tuple[int, int]]  # {"9:16": (576, 1024), "16:9": (1024, 576)}
    def check_installed(self) -> InstallStatus: ...
    def build_command(self, job: ClipJob) -> list[str]: ...
    def parse_progress(self, line: str) -> float | None: ...
```

`ClipJob`: `mode (i2v | a2v), plate, prompt, width, height, frames, fps, seed, audio | None, out`.

## ltx23
- i2v: `<ltx_bin> generate --model <snapshot> --distilled --low-ram --no-audio -W w -H h -f frames --frame-rate 24 --seed 42 --image <plate> -p <prompt> -o <out>`
- a2v: `<ltx_bin> a2v --model <snapshot> --distilled --low-ram -W w -H h -f frames --frame-rate 24 --seed 42 --audio <vocal.wav> --image <plate> -p <prompt> -o <out>`
- Always pass the local snapshot path as `--model`.
- Prompt = shot motion_prompt + character style lines (figure shots) or the no figure style line (object shots).

## stub
Writes a solid colour MP4 of the right length with ffmpeg; used by tests and CI.

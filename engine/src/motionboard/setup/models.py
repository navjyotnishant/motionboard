"""Model catalog (research R12). Motionboard never downloads weights by itself: it shows
the licence, the size and the exact commands, and the creator runs them."""

from dataclasses import dataclass, field
from pathlib import Path

from motionboard.backends.ltx23 import find_snapshot


@dataclass(frozen=True)
class ModelEntry:
    key: str
    repo: str
    role: str
    licence: str
    licence_url: str
    approx_gb: float
    include: tuple[str, ...] = ()
    exclude: tuple[str, ...] = ()
    required_for: str = ""
    optional: bool = False
    backlog: bool = False
    notes: list[str] = field(default_factory=list)

    def download_command(self) -> str:
        parts = ["HF_HUB_DISABLE_XET=1 hf download", self.repo]
        parts += [f"--include '{p}'" for p in self.include]
        parts += [f"--exclude '{p}'" for p in self.exclude]
        return " ".join(parts)

    def present(self) -> Path | None:
        snap = find_snapshot(self.repo)
        if not snap:
            return None
        want = [p for p in self.include if "*" not in p]
        if not want:  # no file list: any weights file in the snapshot counts
            return snap if (snap / "config.json").exists() or any(snap.glob("*.safetensors")) else None
        return snap if all((snap / w).exists() for w in want) else None


CATALOG: list[ModelEntry] = [
    ModelEntry(
        key="ltx23", repo="dgrauet/ltx-2.3-mlx-q8", role="video model (image to video, audio to video)",
        licence="LTX-2 Community License (free commercial use under USD 10M annual revenue)",
        licence_url="https://huggingface.co/Lightricks/LTX-2.3/blob/main/LICENSE", approx_gb=29.0,
        include=("transformer-distilled-1.1.safetensors", "vae_decoder.safetensors", "vae_encoder.safetensors",
                 "audio_vae.safetensors", "vocoder.safetensors", "connector.safetensors",
                 "spatial_upscaler_x2_v1_1.safetensors", "spatial_upscaler_x2_v1_1_config.json",
                 "config.json", "embedded_config.json", "quantize_config.json", "split_model.json", "LICENSE",
                 "README.md"),
        required_for="clips",
        notes=["The full repo is about 87.5 GB; the include list keeps it near 29 GB.",
               "Accept the licence on Hugging Face and run `hf auth login` first."],
    ),
    ModelEntry(
        key="gemma", repo="mlx-community/gemma-3-12b-it-4bit", role="LTX text encoder",
        licence="Gemma Terms of Use", licence_url="https://ai.google.dev/gemma/terms", approx_gb=7.5,
        required_for="clips",
    ),
    ModelEntry(
        key="whisper", repo="mlx-community/whisper-large-v3-turbo", role="lyric line alignment (optional)",
        licence="MIT", licence_url="https://huggingface.co/openai/whisper-large-v3-turbo", approx_gb=1.6,
        required_for="voice matched lyric timing", optional=True,
        notes=["Install the engine extra: uv sync --extra align"],
    ),
    ModelEntry(
        key="demucs", repo="(downloaded by demucs on first use)", role="vocal isolation for lip-sync (optional)",
        licence="MIT", licence_url="https://github.com/facebookresearch/demucs/blob/main/LICENSE", approx_gb=0.3,
        required_for="clean lip-sync", optional=True, notes=["Install the engine extra: uv sync --extra vocals"],
    ),
    ModelEntry(
        key="wan22", repo="Wan-AI/Wan2.2-TI2V-5B", role="alternative video model (backlog)",
        licence="Apache 2.0", licence_url="https://huggingface.co/Wan-AI/Wan2.2-TI2V-5B", approx_gb=32.0,
        backlog=True, notes=["Video decode exceeded 36 GB in tests; not supported in v1."],
    ),
    ModelEntry(
        key="ltx25", repo="dgrauet/ltx-2.5-mlx-q8", role="newer video model, more accurate lip-sync (optional)",
        licence="LTX-2 Community License", licence_url="https://github.com/Lightricks/LTX-2/blob/main/LICENSE-2_x",
        approx_gb=43.0, exclude=("transformer-dev.safetensors", "*lora*"), optional=True,
        notes=["Brings its own text encoder. Use it with: mb clips --backend ltx25.",
               "Only lip-sync shots are measured on a 36 GB Mac so far."],
    ),
    ModelEntry(
        key="ltx25-detail", repo="Lightricks/LTX-2.5-22b-IC-LoRA-Pixel-Spatial-Upscaler",
        role="detail add-on for LTX-2.5, keeps faces sharp on lip-sync shots (optional)",
        licence="LTX-2 Community License", licence_url="https://github.com/Lightricks/LTX-2/blob/main/LICENSE-2_x",
        approx_gb=0.3, optional=True,
        notes=["Gated: accept the licence on its Hugging Face page and run `hf auth login` first."],
    ),
]

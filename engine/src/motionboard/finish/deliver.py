"""Copy the delivery to a folder and verify what arrived (T059)."""

import shutil
from pathlib import Path

from motionboard import assets
from motionboard.report import MbError


def deliver(video: Path, cover: Path | None, metadata: Path | None, folder: Path) -> dict:
    folder = Path(folder).expanduser()
    folder.mkdir(parents=True, exist_ok=True)
    copied = {}
    for kind, src in (("video", video), ("cover", cover), ("metadata", metadata)):
        if src is None:
            continue
        if not Path(src).exists():
            raise MbError("NOT_FOUND", f"{kind} file missing: {src}", hint="run mb finish first")
        dst = folder / Path(src).name
        shutil.copy2(src, dst)
        if dst.stat().st_size != Path(src).stat().st_size:
            raise MbError("INTERNAL", f"copy of {kind} is incomplete")
        copied[kind] = str(dst)
    info = assets.probe(Path(copied["video"]))
    return {"copied": copied, "probe": info}

"""Command plates: any local image model run as a CLI, under the memory guard.

config: {"cmd": ["python", "gen.py", "--prompt", "{prompt}", "--out", "{out}", "--size", "{w}x{h}"],
         "cwd": "~/tools/sd"}  placeholders: {prompt} {negative} {out} {w} {h} {ref} {seed}
"""

from pathlib import Path

from motionboard.db.connection import open_db
from motionboard.guard import presets
from motionboard.guard.run import run_guarded
from motionboard.plates.adapter import PlateRequest, PlateResult
from motionboard.report import MbError


class CommandAdapter:
    kind = "command"

    def __init__(self, name: str, cfg: dict, cost: float):
        self.name, self.cfg, self.cost_per_image_usd = name, cfg, cost

    def request(self, req: PlateRequest) -> PlateResult:
        values = {"prompt": req.prompt, "negative": req.negative, "out": str(req.out), "w": str(req.width),
                  "h": str(req.height), "ref": str(req.reference_image or ""), "seed": str(req.seed)}
        cmd = [part.format(**values) for part in self.cfg["cmd"]]
        cwd = Path(self.cfg["cwd"]).expanduser() if self.cfg.get("cwd") else None
        conn = open_db()
        try:
            profile = presets.active(conn)
        finally:
            conn.close()
        out = run_guarded(cmd, profile, cwd=cwd, log_path=req.out.with_suffix(".log"))
        if out.stopped:
            raise MbError("GUARD_STOPPED", out.stop_reason or "stopped")
        if out.exit_code != 0 or not req.out.exists():
            raise MbError("INTERNAL", f"plate command failed (exit {out.exit_code}); see {req.out.with_suffix('.log')}")
        return PlateResult(req.out, self.cost_per_image_usd)

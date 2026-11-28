"""Command plates: any local image model run as a CLI, under the memory guard.

config: {"cmd": ["python", "gen.py", "--prompt", "{prompt}", "--out", "{out}", "--size", "{w}x{h}"],
         "cwd": "~/tools/sd"}  placeholders: {prompt} {negative} {out} {w} {h} {ref} {seed}

References: an element that is exactly "{refs}" expands to one argument per reference path (no limit); "{ref}"
inside an element takes one reference. With neither, the command takes no references.
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

    def reference_capacity(self) -> int | None:
        parts = self.cfg.get("cmd", [])
        if any(p == "{refs}" for p in parts):
            return None
        return 1 if any("{ref}" in p for p in parts) else 0

    def request(self, req: PlateRequest) -> PlateResult:
        first = str(req.references[0].path) if req.references else ""
        values = {"prompt": req.prompt, "negative": req.negative, "out": str(req.out), "w": str(req.width),
                  "h": str(req.height), "ref": first, "seed": str(req.seed)}
        cmd = []
        for part in self.cfg["cmd"]:
            if part == "{refs}":
                cmd += [str(r.path) for r in req.references]
            else:
                cmd.append(part.format(**values))
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

"""Command reports (contracts/cli.md): one JSON object, with what was and was not verified."""

import json
import re
from dataclasses import dataclass, field
from typing import Any

from motionboard.db.repo import SECRET_PATTERNS

ERROR_CODES = {
    "GATE_NOT_APPROVED",
    "FIT_REFUSED",
    "GUARD_STOPPED",
    "COST_NOT_CONFIRMED",
    "MISSING_TOOL",
    "MISSING_MODEL",
    "INVALID_INPUT",
    "NOT_FOUND",
    "INTERNAL",
}


def redact(text: str) -> str:
    for p in SECRET_PATTERNS:
        text = p.sub("[REDACTED]", text)
    return re.sub(r"(?i)(authorization:\s*bearer\s+)\S+", r"\1[REDACTED]", text)


class MbError(Exception):
    def __init__(self, code: str, message: str, hint: str = "", data: dict | None = None):
        if code not in ERROR_CODES:
            raise ValueError(f"unknown error code {code}")
        super().__init__(message)
        self.code, self.message, self.hint, self.data = code, message, hint, data or {}


@dataclass
class Report:
    command: str
    ok: bool = True
    project: str | None = None
    data: dict[str, Any] = field(default_factory=dict)
    verified: list[str] = field(default_factory=list)
    not_verified: list[str] = field(default_factory=list)
    next: str | None = None
    error: dict[str, str] | None = None

    @classmethod
    def failure(cls, command: str, err: MbError, project: str | None = None) -> "Report":
        return cls(
            command=command,
            ok=False,
            project=project,
            data=err.data,
            error={"code": err.code, "message": err.message, "hint": err.hint},
        )

    def to_dict(self) -> dict[str, Any]:
        d = {
            "ok": self.ok,
            "command": self.command,
            "project": self.project,
            "data": self.data,
            "verified": self.verified,
            "not_verified": self.not_verified,
            "next": self.next,
        }
        if self.error:
            d["error"] = self.error
        return d

    def to_json(self) -> str:
        return redact(json.dumps(self.to_dict(), default=str))

    def to_text(self) -> str:
        lines = []
        if self.ok:
            lines.append(f"ok: {self.command}")
        else:
            lines.append(f"error {self.error['code']}: {self.error['message']}")
            if self.error.get("hint"):
                lines.append(f"hint: {self.error['hint']}")
        for k, v in self.data.items():
            lines.append(f"  {k}: {v}")
        lines += [f"  verified: {v}" for v in self.verified]
        lines += [f"  not verified: {v}" for v in self.not_verified]
        if self.next:
            lines.append(f"next: {self.next}")
        return redact("\n".join(lines))

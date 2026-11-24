"""Backend registry. MB_BACKEND overrides the project's backend (tests use MB_BACKEND=stub)."""

import os

from motionboard.backends.base import VideoBackend
from motionboard.backends.ltx23 import LTX23Backend
from motionboard.backends.stub import StubBackend
from motionboard.report import MbError

_REGISTRY: dict[str, VideoBackend] = {}


def register(backend: VideoBackend) -> None:
    _REGISTRY[backend.name] = backend


def get(name: str | None = None) -> VideoBackend:
    name = os.environ.get("MB_BACKEND") or name or "ltx23"
    if name not in _REGISTRY:
        raise MbError("NOT_FOUND", f"no video backend named '{name}'", hint=f"available: {', '.join(names())}")
    return _REGISTRY[name]


def names() -> list[str]:
    return sorted(_REGISTRY)


register(StubBackend())
register(LTX23Backend())

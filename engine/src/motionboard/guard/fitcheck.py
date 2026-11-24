"""Dry run fit check (research R4).

Model: peak_gb = base_gb + k * megapixel_frames, where megapixel_frames = w * h * frames / 1e6.
Points come from the backend's shipped profile plus fit_sample rows measured on this machine
(local points win when they exist for the same backend and mode).
Headroom: memory the job may use before free memory falls to the kill floor.
"""

import sqlite3
from dataclasses import dataclass, field

from motionboard.backends.base import VideoBackend
from motionboard.guard import monitor
from motionboard.guard.presets import GuardProfile

MARGIN = 0.15


@dataclass
class FitResult:
    fits: bool
    est_peak_gb: float
    available_gb: float
    margin_pct: int
    est_seconds: float | None
    free_pct_now: int
    basis: str
    suggestions: list[str] = field(default_factory=list)

    def summary(self) -> str:
        verdict = "fits" if self.fits else "does not fit"
        return (
            f"{verdict}: estimated peak {self.est_peak_gb:.1f} GB (+{self.margin_pct}% margin) vs "
            f"{self.available_gb:.1f} GB headroom at {self.free_pct_now}% free"
        )


OTHER_MODE_EXTRA = 0.25  # a2v conditions on audio too; until measured, assume a larger peak


def _mpf(w: int, h: int, frames: int) -> float:
    return w * h * frames / 1e6


def _points(backend: VideoBackend, mode: str, conn: sqlite3.Connection | None) -> tuple[list, str]:
    if conn is not None:
        rows = conn.execute(
            "SELECT width, height, frames, peak_used_gb, sec_per_frame FROM fit_sample "
            "WHERE backend = ? AND mode = ?",
            (backend.name, mode),
        ).fetchall()
        if rows:
            return [
                {"width": r[0], "height": r[1], "frames": r[2], "peak_gb": r[3], "sec_per_frame": r[4]}
                for r in rows
            ], f"{len(rows)} local measurement(s)"
    prof = backend.profile()
    pts = [p for p in prof.get("points", []) if p.get("mode", "i2v") == mode]
    if pts or mode == "i2v":
        return pts, f"{len(pts)} shipped profile point(s)"
    # No measurement for this mode yet: borrow the i2v points with extra headroom, and say so.
    base, basis = _points(backend, "i2v", conn)
    if not base:
        return [], basis
    bumped = [dict(p, peak_gb=p["peak_gb"] * (1 + OTHER_MODE_EXTRA)) for p in base]
    return bumped, f"{basis} for i2v plus {int(OTHER_MODE_EXTRA * 100)}% (no {mode} measurement yet)"


def _model(points: list[dict], base_gb: float) -> tuple[float, float]:
    """Return (base, k). One point: line through base. Two or more distinct sizes: least squares."""
    if not points:
        return base_gb, 0.0
    xs = [_mpf(p["width"], p["height"], p["frames"]) for p in points]
    ys = [p["peak_gb"] for p in points]
    if len(set(xs)) >= 2:
        n = len(xs)
        mx, my = sum(xs) / n, sum(ys) / n
        k = sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True)) / sum((x - mx) ** 2 for x in xs)
        k = max(k, 0.0)
        return max(my - k * mx, 0.0), k
    x, y = xs[0], ys[0]
    return base_gb, max((y - base_gb) / x, 0.0) if x else 0.0


def _speed(points: list[dict]) -> float | None:
    s = [p["sec_per_frame"] for p in points if p.get("sec_per_frame")]
    return sum(s) / len(s) if s else None


def fit(
    backend: VideoBackend,
    mode: str,
    width: int,
    height: int,
    frames: int,
    profile: GuardProfile,
    conn: sqlite3.Connection | None = None,
    sample: monitor.Sample | None = None,
) -> FitResult:
    s = sample or monitor.sample()
    points, basis = _points(backend, mode, conn)
    base, k = _model(points, backend.profile().get("base_gb", 0.0))
    est = base + k * _mpf(width, height, frames)
    available = max(0.0, s.total_gb * (s.free_pct - profile.kill_free_pct) / 100)
    need = est * (1 + MARGIN)
    spf = _speed(points)
    res = FitResult(
        fits=bool(points) and need <= available,
        est_peak_gb=round(est, 2),
        available_gb=round(available, 2),
        margin_pct=int(MARGIN * 100),
        est_seconds=round(spf * frames, 1) if spf else None,
        free_pct_now=s.free_pct,
        basis=basis,
    )
    if not points:
        res.suggestions.append(f"no memory profile for {backend.name} {mode}; run one short test shot first")
        return res
    if res.fits:
        return res
    if s.free_pct < profile.start_free_pct:
        res.suggestions.append(
            f"free memory is {s.free_pct}%, below the start floor {profile.start_free_pct}%; close other apps"
        )
    if k > 0:
        budget = available / (1 + MARGIN) - base
        max_frames = int(budget / (k * width * height / 1e6)) if budget > 0 else 0
        max_frames = backend.frame_rule(max_frames) if max_frames >= backend.min_frames else 0
        while max_frames and base + k * _mpf(width, height, max_frames) > available / (1 + MARGIN):
            max_frames = backend.frame_rule(max_frames - 8) if max_frames > 9 else 0
        if max_frames >= backend.min_frames:
            res.suggestions.append(f"same size with {max_frames} frames, then join shots")
        for scale in (0.875, 0.75, 0.625):
            w, h = int(width * scale) // 32 * 32, int(height * scale) // 32 * 32
            if base + k * _mpf(w, h, frames) <= available / (1 + MARGIN):
                res.suggestions.append(f"{w}x{h} at {frames} frames, upscaled in finishing")
                break
    res.suggestions.append("a lighter guard preset only if you accept more risk: mb guard --set max")
    return res

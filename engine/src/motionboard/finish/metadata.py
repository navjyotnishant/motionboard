"""Metadata file next to the final video (T058). The creator's own conventions (titles,
tags, hashtags) come from the project theme; nothing is invented about the song."""

import json
from pathlib import Path


def write(project: dict, out: Path, video: Path, cover: Path | None, post_time: str | None = None,
          platforms: list[str] | None = None) -> Path:
    theme = json.loads(project.get("theme") or "{}")
    song, artist = theme.get("song") or project["title"], theme.get("artist") or ""
    title = theme.get("video_title") or (f"{song} by {artist}" if artist else song)
    synthetic = bool(project.get("synthetic_people"))
    lines = [
        f"# {title}",
        "",
        f"- Video: {video.name}",
        f"- Cover: {cover.name if cover else 'none'}",
        f"- Aspect: {project['aspect']}",
        f"- Post at: {post_time or theme.get('post_time') or 'not set'}",
        f"- Platforms: {', '.join(platforms or theme.get('platforms') or ['not set'])}",
        f"- Altered or synthetic content (realistic people made with AI): {'Yes' if synthetic else 'No'}",
        f"- Mode: {project.get('mode') or '-'} · Look: {project.get('visual_look') or '-'}",
        "",
        "## Title",
        title,
        "",
        "## Description",
        theme.get("description") or project.get("idea") or "",
        "",
        "## Tags",
        ", ".join(theme.get("tags", [])) or "(add tags)",
        "",
        "## Hashtags",
        " ".join(theme.get("hashtags", [])) or "(add hashtags)",
        "",
        "## Lyrics",
        project.get("lyrics", "").strip(),
        "",
    ]
    out.write_text("\n".join(lines))
    return out

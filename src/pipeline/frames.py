from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from src.utils.subprocess import run_cmd

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class FrameExtractParams:
    fps: float
    max_frames: int
    start_seconds: float
    duration_seconds: float


def extract_frames(video_path: Path, out_dir: Path, params: FrameExtractParams) -> Path:
    """
    Extract frames using ffmpeg.
    Output format: frame_000001.jpg, ...
    """
    out_dir.mkdir(parents=True, exist_ok=True)

    # Build ffmpeg command
    # -ss and -t are optional
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"]

    if params.start_seconds and params.start_seconds > 0:
        cmd += ["-ss", str(params.start_seconds)]

    cmd += ["-i", str(video_path)]

    if params.duration_seconds and params.duration_seconds > 0:
        cmd += ["-t", str(params.duration_seconds)]

    # fps filter
    vf = f"fps={params.fps}"

    # Use quality 2 for jpg, good compromise
    out_pattern = out_dir / "frame_%06d.jpg"

    cmd += [
        "-vf", vf,
        "-q:v", "2",
        str(out_pattern),
    ]

    run_cmd(cmd)

    # Optionally cap number of frames
    if params.max_frames and params.max_frames > 0:
        _cap_frames(out_dir, params.max_frames)

    return out_dir


def _cap_frames(out_dir: Path, max_frames: int) -> None:
    frames = sorted(out_dir.glob("frame_*.jpg"))
    if len(frames) <= max_frames:
        return
    to_delete = frames[max_frames:]
    for p in to_delete:
        p.unlink(missing_ok=True)
    log.info("Capped frames to %d (deleted %d)", max_frames, len(to_delete))

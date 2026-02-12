from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from src.utils.subprocess import run_cmd

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class FrameExtractParams:
    """
    Parameters controlling video-to-frames extraction.

    Attributes:
        fps (float):
            Frames per second to extract from the video.
            Example: fps=2 extracts 2 frames per second.

        max_frames (int):
            Maximum number of frames to keep.
            If 0, no limit is applied.

        start_seconds (float):
            Offset (in seconds) from the start of the video to begin extraction.
            If 0, extraction starts from the beginning.

        duration_seconds (float):
            Duration (in seconds) of the video segment to extract frames from.
            If 0, extraction continues until the end of the video.
    """
    fps: float
    max_frames: int
    start_seconds: float
    duration_seconds: float


def extract_frames(video_path: Path, out_dir: Path, params: FrameExtractParams) -> Path:
    """
    Extract frames from a video file using ffmpeg.

    Frames are written as sequential JPEG images in the output directory
    using the naming pattern:

        frame_000001.jpg
        frame_000002.jpg
        ...

    The extraction is controlled by the FrameExtractParams object, which supports:
      - start offset (-ss)
      - duration (-t)
      - fps filter (-vf fps=...)

    After extraction, the function optionally limits the number of frames
    using `_cap_frames()`.

    Args:
        video_path (Path):
            Path to the input video file.

        out_dir (Path):
            Directory where extracted frames will be saved.

        params (FrameExtractParams):
            Extraction parameters (fps, max_frames, start_seconds, duration_seconds).

    Returns:
        Path:
            The output directory containing extracted frames.
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

    # Execute ffmpeg extraction command
    run_cmd(cmd)

    # Optionally cap number of frames
    if params.max_frames and params.max_frames > 0:
        _cap_frames(out_dir, params.max_frames)

    return out_dir


def _cap_frames(out_dir: Path, max_frames: int) -> None:
    """
    Remove frames beyond a maximum count.

    This function scans the output directory for extracted frames,
    sorts them in filename order, and deletes any frames after the
    first `max_frames`.

    This is useful when extracting at a high FPS but wanting to
    limit the total number of frames passed into photogrammetry.

    Args:
        out_dir (Path):
            Directory containing extracted frames.

        max_frames (int):
            Maximum number of frames to keep.
            Any frames beyond this count are deleted.

    Returns:
        None
    """
    frames = sorted(out_dir.glob("frame_*.jpg"))
    if len(frames) <= max_frames:
        return
    to_delete = frames[max_frames:]
    for p in to_delete:
        p.unlink(missing_ok=True)
    log.info("Capped frames to %d (deleted %d)", max_frames, len(to_delete))

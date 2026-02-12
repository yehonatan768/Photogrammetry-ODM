from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


@dataclass(frozen=True)
class RuntimeConfig:
    runs_dir: Path
    data_dir: Path
    log_level: str


@dataclass(frozen=True)
class ODMConfig:
    host_env: str
    host_default: str
    parallel_uploads: int
    poll_seconds: int


@dataclass(frozen=True)
class VideoConfig:
    fps: float
    max_frames: int
    start_seconds: float
    duration_seconds: float


@dataclass(frozen=True)
class ProjectConfig:
    name: str


@dataclass(frozen=True)
class AppConfig:
    project: ProjectConfig
    runtime: RuntimeConfig
    odm: ODMConfig
    video: VideoConfig
    odm_options: Dict[str, Any]


def _get(d: Dict[str, Any], path: str, default=None):
    cur = d
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return default
        cur = cur[part]
    return cur


def load_config(path: Path) -> AppConfig:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))

    project = ProjectConfig(name=str(_get(raw, "project.name", "Photogrammetry-ODM")))

    runs_dir = Path(str(_get(raw, "runtime.runs_dir", "runs")))
    data_dir = Path(str(_get(raw, "runtime.data_dir", "data")))
    log_level = str(_get(raw, "runtime.log_level", "INFO"))
    runtime = RuntimeConfig(runs_dir=runs_dir, data_dir=data_dir, log_level=log_level)

    odm = ODMConfig(
        host_env=str(_get(raw, "odm.host_env", "ODM_HOST")),
        host_default=str(_get(raw, "odm.host_default", "http://localhost:3000")),
        parallel_uploads=int(_get(raw, "odm.parallel_uploads", 4)),
        poll_seconds=int(_get(raw, "odm.poll_seconds", 10)),
    )

    video = VideoConfig(
        fps=float(_get(raw, "video.fps", 2)),
        max_frames=int(_get(raw, "video.max_frames", 0)),
        start_seconds=float(_get(raw, "video.start_seconds", 0)),
        duration_seconds=float(_get(raw, "video.duration_seconds", 0)),
    )

    odm_options = dict(_get(raw, "odm_options", {}) or {})

    return AppConfig(project=project, runtime=runtime, odm=odm, video=video, odm_options=odm_options)

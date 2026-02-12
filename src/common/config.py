from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


@dataclass(frozen=True)
class RuntimeConfig:
    """
    Holds runtime-related configuration parameters.

    Attributes:
        runs_dir (Path):
            Directory where pipeline run outputs will be stored.
            Example: "runs/exp001", "runs/latest", etc.

        data_dir (Path):
            Directory containing input datasets, videos, extracted frames, etc.

        log_level (str):
            Logging level to be used throughout the pipeline.
            Typical values: "DEBUG", "INFO", "WARNING", "ERROR".
    """
    runs_dir: Path
    data_dir: Path
    log_level: str


@dataclass(frozen=True)
class ODMConfig:
    """
    Holds OpenDroneMap / NodeODM related configuration.

    Attributes:
        host_env (str):
            The environment variable name that stores the NodeODM host URL.
            Example: "ODM_HOST"

        host_default (str):
            Default NodeODM host URL if the environment variable is not set.
            Example: "http://localhost:3000"

        parallel_uploads (int):
            Number of parallel image uploads to NodeODM.
            This improves speed for large datasets.

        poll_seconds (int):
            How often (in seconds) to poll NodeODM task status.
            Example: check every 10 seconds.
    """
    host_env: str
    host_default: str
    parallel_uploads: int
    poll_seconds: int


@dataclass(frozen=True)
class VideoConfig:
    """
    Holds video preprocessing configuration.

    Attributes:
        fps (float):
            Frames per second to extract from the input drone video.

        max_frames (int):
            Maximum number of frames to extract.
            If set to 0, it usually means "no limit" (extract all frames).

        start_seconds (float):
            Starting time offset (in seconds) for video frame extraction.

        duration_seconds (float):
            Duration (in seconds) of the video segment to process.
            If 0, it usually means "until the end of the video".
    """
    fps: float
    max_frames: int
    start_seconds: float
    duration_seconds: float


@dataclass(frozen=True)
class ProjectConfig:
    """
    Holds basic project metadata.

    Attributes:
        name (str):
            Project name identifier used for folder naming, logs, etc.
            Example: "Photogrammetry-ODM"
    """
    name: str


@dataclass(frozen=True)
class AppConfig:
    """
    Root application configuration object.

    This is the main config container returned by `load_config()`.
    It contains structured configuration sections for the project.

    Attributes:
        project (ProjectConfig):
            Metadata about the project.

        runtime (RuntimeConfig):
            Runtime paths and logging settings.

        odm (ODMConfig):
            NodeODM connection and processing settings.

        video (VideoConfig):
            Video preprocessing and extraction parameters.

        odm_options (Dict[str, Any]):
            Additional raw ODM processing options.
            This is passed directly to NodeODM (or used by the pipeline)
            and may include options like:
                - dsm
                - dtm
                - pc-ept
                - gltf
                - orthophoto-resolution
                - feature-quality
                - etc.
    """
    project: ProjectConfig
    runtime: RuntimeConfig
    odm: ODMConfig
    video: VideoConfig
    odm_options: Dict[str, Any]


def _get(d: Dict[str, Any], path: str, default=None):
    """
    Helper function for safely retrieving nested dictionary values.

    This function allows accessing YAML-loaded dictionaries using
    dot-separated keys.

    Example:
        raw = {"runtime": {"runs_dir": "runs"}}
        _get(raw, "runtime.runs_dir")  -> "runs"

    Args:
        d (Dict[str, Any]):
            Dictionary to read from (usually YAML parsed output).

        path (str):
            Dot-separated path representing nested keys.
            Example: "runtime.runs_dir"

        default:
            Value to return if the key path does not exist.

    Returns:
        Any:
            The value at the requested path if it exists,
            otherwise the provided default.
    """
    cur = d
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return default
        cur = cur[part]
    return cur


def load_config(path: Path) -> AppConfig:
    """
    Load application configuration from a YAML file and convert it
    into strongly typed dataclass objects.

    This function reads a YAML config file and builds:
        - ProjectConfig
        - RuntimeConfig
        - ODMConfig
        - VideoConfig
        - AppConfig

    Any missing values in the YAML will fallback to defaults.

    Expected YAML structure example:

        project:
          name: "Photogrammetry-ODM"

        runtime:
          runs_dir: "runs"
          data_dir: "data"
          log_level: "INFO"

        odm:
          host_env: "ODM_HOST"
          host_default: "http://localhost:3000"
          parallel_uploads: 4
          poll_seconds: 10

        video:
          fps: 2
          max_frames: 0
          start_seconds: 0
          duration_seconds: 0

        odm_options:
          dsm: true
          dtm: false
          pc-ept: true
          gltf: true

    Args:
        path (Path):
            Path to the YAML configuration file.

    Returns:
        AppConfig:
            Fully constructed structured configuration object.
    """
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))

    # Project metadata
    project = ProjectConfig(name=str(_get(raw, "project.name", "Photogrammetry-ODM")))

    # Runtime paths + logging
    runs_dir = Path(str(_get(raw, "runtime.runs_dir", "runs")))
    data_dir = Path(str(_get(raw, "runtime.data_dir", "data")))
    log_level = str(_get(raw, "runtime.log_level", "INFO"))
    runtime = RuntimeConfig(runs_dir=runs_dir, data_dir=data_dir, log_level=log_level)

    # NodeODM settings
    odm = ODMConfig(
        host_env=str(_get(raw, "odm.host_env", "ODM_HOST")),
        host_default=str(_get(raw, "odm.host_default", "http://localhost:3000")),
        parallel_uploads=int(_get(raw, "odm.parallel_uploads", 4)),
        poll_seconds=int(_get(raw, "odm.poll_seconds", 10)),
    )

    # Video extraction settings
    video = VideoConfig(
        fps=float(_get(raw, "video.fps", 2)),
        max_frames=int(_get(raw, "video.max_frames", 0)),
        start_seconds=float(_get(raw, "video.start_seconds", 0)),
        duration_seconds=float(_get(raw, "video.duration_seconds", 0)),
    )

    # Raw ODM processing options (kept flexible)
    odm_options = dict(_get(raw, "odm_options", {}) or {})

    return AppConfig(project=project, runtime=runtime, odm=odm, video=video, odm_options=odm_options)

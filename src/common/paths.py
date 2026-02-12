from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RunPaths:
    run_dir: Path
    logs_dir: Path
    frames_dir: Path
    odm_out_dir: Path
    processed_dir: Path


def build_run_paths(runs_dir: Path, data_dir: Path, run_id: str) -> RunPaths:
    run_dir = runs_dir / run_id
    logs_dir = run_dir / "logs"
    frames_dir = data_dir / "interim" / "frames" / run_id
    odm_out_dir = run_dir / "odm"
    processed_dir = data_dir / "processed" / "odm_results" / run_id
    return RunPaths(
        run_dir=run_dir,
        logs_dir=logs_dir,
        frames_dir=frames_dir,
        odm_out_dir=odm_out_dir,
        processed_dir=processed_dir,
    )

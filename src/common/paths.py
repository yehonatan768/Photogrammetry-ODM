from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RunPaths:
    """
    Container object holding all important filesystem paths
    associated with a single pipeline run.

    This dataclass groups together the directories used during a run,
    making it easier to pass around a single object instead of multiple
    separate Path variables.

    Attributes:
        run_dir (Path):
            Root directory of the current run.
            Usually located inside the main `runs_dir`.

        logs_dir (Path):
            Directory where log files for the run are stored.

        frames_dir (Path):
            Directory where extracted video frames for the run are stored.
            This is typically placed under the `data_dir/interim/frames/`.

        odm_out_dir (Path):
            Directory where NodeODM / ODM output artifacts are saved
            for this run.

        processed_dir (Path):
            Directory where final processed results are stored.
            This usually contains exported models, point clouds,
            orthophotos, and other final outputs.
    """
    run_dir: Path
    logs_dir: Path
    frames_dir: Path
    odm_out_dir: Path
    processed_dir: Path


def build_run_paths(runs_dir: Path, data_dir: Path, run_id: str) -> RunPaths:
    """
    Construct all filesystem paths required for a pipeline run.

    This function creates a structured directory layout based on:
        - runs_dir (where run outputs are stored)
        - data_dir (where datasets/intermediate files live)
        - run_id (unique identifier for the current run)

    The function does not create directories on disk; it only builds
    and returns the expected Path objects.

    Directory layout produced:

        runs_dir/
            <run_id>/
                logs/
                odm/

        data_dir/
            interim/
                frames/
                    <run_id>/

            processed/
                odm_results/
                    <run_id>/

    Args:
        runs_dir (Path):
            Root directory where all run folders are created.

        data_dir (Path):
            Root data directory used for storing intermediate and processed outputs.

        run_id (str):
            Unique run identifier (timestamp, UUID, experiment name, etc.).

    Returns:
        RunPaths:
            A structured RunPaths object containing all important
            directories for the given run.
    """
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

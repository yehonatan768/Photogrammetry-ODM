from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, Dict, Optional

from src.common.config import AppConfig
from src.common.paths import build_run_paths
from src.pipeline.frames import FrameExtractParams, extract_frames
from src.pipeline.odm_client import connect, get_odm_hosts, pick_best_odm_host
from src.pipeline.odm_task import ODMTaskParams, submit_task, wait_for_completion, download_assets
from src.utils.hashing import sha1_file

log = logging.getLogger(__name__)


def _make_run_id(video_path: Path) -> str:
    # stable-ish id: timestamp + hash prefix
    ts = time.strftime("%Y%m%d_%H%M%S")
    h = sha1_file(video_path)[:10]
    return f"run_{ts}_{h}"


def _merge_odm_options(base: Dict[str, Any], extra: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(base)
    merged.update(extra or {})
    return merged


def _copy_summary_outputs(odm_out_dir: Path, processed_dir: Path) -> None:
    """
    Copy a few commonly-used artifacts into data/processed for convenience.
    We avoid being too opinionated: just copy entire directory if you want,
    but here we copy key targets when they exist.
    """
    processed_dir.mkdir(parents=True, exist_ok=True)

    candidates = [
        # Common ODM outputs (may vary by options)
        odm_out_dir / "odm_orthophoto" / "odm_orthophoto.tif",
        odm_out_dir / "odm_orthophoto" / "odm_orthophoto.png",
        odm_out_dir / "odm_dem" / "dsm.tif",
        odm_out_dir / "odm_georeferencing" / "odm_georeferenced_model.laz",
        odm_out_dir / "odm_texturing" / "odm_textured_model.obj",
        odm_out_dir / "odm_texturing" / "odm_textured_model_geo.obj",
        odm_out_dir / "odm_mesh" / "odm_mesh.ply",
        odm_out_dir / "odm_report" / "report.pdf",
    ]

    for p in candidates:
        if p.exists():
            dst = processed_dir / p.name
            dst.write_bytes(p.read_bytes())
            log.info("Copied %s -> %s", p, dst)


def run_pipeline(
    cfg: AppConfig,
    video_path: Path,
    run_id: Optional[str] = None,
    fps: Optional[float] = None,
    max_frames: Optional[int] = None,
    start_seconds: Optional[float] = None,
    duration_seconds: Optional[float] = None,
    odm_extra_options: Optional[Dict[str, Any]] = None,
    copy_processed: bool = True,
) -> None:
    if not video_path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")

    run_id = run_id or _make_run_id(video_path)
    paths = build_run_paths(cfg.runtime.runs_dir, cfg.runtime.data_dir, run_id)

    # Create directories
    paths.run_dir.mkdir(parents=True, exist_ok=True)
    paths.logs_dir.mkdir(parents=True, exist_ok=True)
    paths.frames_dir.mkdir(parents=True, exist_ok=True)
    paths.odm_out_dir.mkdir(parents=True, exist_ok=True)

    log.info("Run id: %s", run_id)
    log.info("Run dir: %s", paths.run_dir)

    # 1) Extract frames
    vcfg = cfg.video
    fparams = FrameExtractParams(
        fps=float(fps if fps is not None else vcfg.fps),
        max_frames=int(max_frames if max_frames is not None else vcfg.max_frames),
        start_seconds=float(start_seconds if start_seconds is not None else vcfg.start_seconds),
        duration_seconds=float(duration_seconds if duration_seconds is not None else vcfg.duration_seconds),
    )
    extract_frames(video_path=video_path, out_dir=paths.frames_dir, params=fparams)

    # 2) Connect to NodeODM
    hosts = get_odm_hosts(cfg.odm.host_env, cfg.odm.host_default)
    host = pick_best_odm_host(hosts)
    node = connect(host)

    # 3) Submit task
    odm_opts = _merge_odm_options(cfg.odm_options, odm_extra_options or {})
    tparams = ODMTaskParams(options=odm_opts, parallel_uploads=cfg.odm.parallel_uploads, poll_seconds=cfg.odm.poll_seconds)

    task = submit_task(node=node, images_dir=paths.frames_dir, params=tparams)

    # 4) Wait for completion
    wait_for_completion(task=task, poll_seconds=cfg.odm.poll_seconds)

    # 5) Download results
    download_assets(task=task, out_dir=paths.odm_out_dir)

    # 6) Optionally copy summary outputs
    if copy_processed:
        _copy_summary_outputs(paths.odm_out_dir, paths.processed_dir)

    log.info("Pipeline completed successfully.")
    log.info("Results: %s", paths.odm_out_dir)

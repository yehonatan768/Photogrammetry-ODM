from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from pyodm import Node, exceptions
from tqdm import tqdm

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class ODMTaskParams:
    """
    Parameters controlling NodeODM task submission and monitoring.

    Attributes:
        options (Dict[str, Any]):
            Dictionary of ODM processing options (passed directly to NodeODM).
            Example:
                {"dsm": True, "pc-ept": True, "mesh_size": 200000}

        parallel_uploads (int):
            Number of parallel uploads used when sending images to NodeODM.

        poll_seconds (int):
            Polling interval (seconds) for checking task status.
    """
    options: Dict[str, Any]
    parallel_uploads: int
    poll_seconds: int


def submit_task(node: Node, images_dir: Path, params: ODMTaskParams):
    """
    Submit a photogrammetry task to NodeODM using a folder of extracted images.

    The function scans the given directory for .jpg images, sorts them,
    and uploads them to NodeODM via pyodm.

    It also logs upload progress every 5%.

    Args:
        node (Node):
            Connected pyodm Node instance.

        images_dir (Path):
            Directory containing extracted frame images (*.jpg).

        params (ODMTaskParams):
            Task submission parameters including ODM options and upload settings.

    Returns:
        Task:
            A pyodm Task object (type depends on pyodm version).

    Raises:
        ValueError:
            If no .jpg images are found in the directory.
    """
    images = sorted(str(p) for p in images_dir.glob("*.jpg"))
    if not images:
        raise ValueError(f"No images found in {images_dir}")

    log.info("Submitting ODM task with %d images", len(images))

    last = {"p": -1}

    def on_upload(pct: float):
        """
        Upload progress callback used by pyodm.

        Logs progress in increments of 5% to avoid spamming logs.

        Args:
            pct (float):
                Upload progress percentage (0-100).
        """
        p = int(pct)
        if p >= last["p"] + 5:
            last["p"] = p
            log.info("Upload progress: %d%%", p)

    task = node.create_task(
        files=images,  # IMPORTANT: pyodm expects a list[str], not Path objects
        options=params.options,
        parallel_uploads=params.parallel_uploads,
        progress_callback=on_upload,
    )

    uuid = getattr(task, "uuid", None) or getattr(task, "task_id", None) or str(task)
    log.info("Task created: %s", uuid)
    return task


def _safe(obj: Any, name: str, default=None):
    """
    Safe attribute/dictionary getter.

    This helper supports both dict-based responses and object-based
    responses (depending on pyodm version).

    Args:
        obj (Any):
            Object or dictionary.

        name (str):
            Attribute or key name.

        default:
            Value returned if attribute/key is missing.

    Returns:
        Any:
            Extracted value or default.
    """
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _status_to_str(status: Any) -> str:
    """
    Convert NodeODM task status into a stable string representation.

    Some pyodm versions return TaskStatus enums, while others return
    plain strings or dict structures.

    This function normalizes the status value so the pipeline can
    consistently compare it.

    Args:
        status (Any):
            Raw status field returned by task.info().

    Returns:
        str:
            Normalized status string such as:
                "COMPLETED", "FAILED", "CANCELED", "UNKNOWN"
    """
    """
    pyodm returns TaskStatus enums (ex: <TaskStatus.FAILED: 30>) in some versions.
    Normalize to a stable string.
    """
    if status is None:
        return "UNKNOWN"
    # Enum-like: has .name
    n = getattr(status, "name", None)
    if isinstance(n, str) and n:
        return n
    # Sometimes it's already a string
    if isinstance(status, str):
        return status
    return str(status)


def wait_for_completion(task, poll_seconds: int, max_connection_errors: int = 30) -> None:
    """
    Poll NodeODM until the task finishes (COMPLETED/FAILED/CANCELED).

    This function repeatedly calls `task.info()` until completion.
    It shows a tqdm progress bar based on NodeODM-reported progress.

    It is resilient to transient connection failures:
      - NodeConnectionError will be retried up to max_connection_errors times
      - NodeResponseError (task not found) fails immediately

    Args:
        task:
            pyodm Task object returned from node.create_task().

        poll_seconds (int):
            How many seconds to wait between each poll.

        max_connection_errors (int):
            Maximum consecutive connection errors allowed before failing.

    Returns:
        None

    Raises:
        RuntimeError:
            If the task fails, is canceled, disappears, or NodeODM becomes unreachable.
    """
    """
    Poll until COMPLETED/FAILED/CANCELED.
    Retries transient NodeODM connection errors.
    """
    pbar = tqdm(total=100, desc="ODM", unit="%")
    last_progress = -1
    consecutive_conn_errors = 0

    uuid = getattr(task, "uuid", None) or getattr(task, "task_id", None)

    while True:
        try:
            info = task.info()
            consecutive_conn_errors = 0
        except exceptions.NodeConnectionError as e:
            consecutive_conn_errors += 1
            log.warning(
                "NodeODM connection error while polling task %s (%s). Retry %d/%d in %ds...",
                uuid, e, consecutive_conn_errors, max_connection_errors, poll_seconds
            )
            if consecutive_conn_errors >= max_connection_errors:
                pbar.close()
                raise RuntimeError(
                    f"Lost connection to NodeODM while polling task {uuid}. "
                    f"NodeODM may have crashed or storage may be misconfigured."
                ) from e
            time.sleep(poll_seconds)
            continue
        except exceptions.NodeResponseError as e:
            # This is the “<uuid> not found” case.
            pbar.close()
            raise RuntimeError(
                f"NodeODM says task {uuid} was not found. "
                f"This almost always means the task was not persisted (storage/volume problem) "
                f"or NodeODM was restarted without persistent /var/www/data.\n"
                f"Original error: {e}"
            ) from e

        status_raw = _safe(info, "status")
        status = _status_to_str(status_raw)
        progress = int(_safe(info, "progress", 0) or 0)
        last_error = _safe(info, "last_error", None)

        if progress != last_progress:
            pbar.n = max(0, min(100, progress))
            pbar.refresh()
            last_progress = progress

        if status in ("COMPLETED", "FAILED", "CANCELED"):
            if status == "COMPLETED":
                pbar.n = 100
                pbar.refresh()
                pbar.close()
                log.info("ODM task completed.")
                return

            pbar.close()
            raise RuntimeError(
                f"ODM task ended with status={status}. last_error={last_error}. info={info}"
            )

        time.sleep(poll_seconds)


def download_assets(task, out_dir: Path) -> None:
    """
    Download NodeODM output assets to a local directory.

    This uses pyodm's built-in download_assets method, which downloads
    all available outputs generated by the ODM pipeline.

    Args:
        task:
            pyodm Task object.

        out_dir (Path):
            Output directory where downloaded results will be stored.

    Returns:
        None
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    log.info("Downloading ODM assets into %s", out_dir)
    task.download_assets(str(out_dir))
    log.info("Download done.")

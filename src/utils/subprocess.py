from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import List, Optional

log = logging.getLogger(__name__)


def run_cmd(cmd: List[str], cwd: Optional[Path] = None) -> None:
    """
    Run an external system command and raise an error if it fails.

    This is a small wrapper around `subprocess.run()` that:
      - logs the command being executed
      - captures stdout/stderr
      - raises RuntimeError if the command fails
      - logs stdout/stderr output when available

    It is mainly used for running external tools such as:
      - ffmpeg (frame extraction)
      - future pipeline dependencies (COLMAP, OpenMVS, etc.)

    Args:
        cmd (List[str]):
            Command to execute as a list of tokens.
            Example:
                ["ffmpeg", "-i", "input.mp4", "out_%06d.jpg"]

        cwd (Optional[Path]):
            Working directory where the command will run.
            If None, uses the current process working directory.

    Returns:
        None

    Raises:
        RuntimeError:
            If the command returns a non-zero exit code.
            The error includes the return code and command string.
    """
    log.info("Running: %s", " ".join(cmd))
    p = subprocess.run(cmd, cwd=str(cwd) if cwd else None, capture_output=True, text=True)
    if p.returncode != 0:
        log.error("STDOUT:\n%s", p.stdout)
        log.error("STDERR:\n%s", p.stderr)
        raise RuntimeError(f"Command failed with code {p.returncode}: {' '.join(cmd)}")
    if p.stdout.strip():
        log.info("STDOUT:\n%s", p.stdout.strip())
    if p.stderr.strip():
        log.warning("STDERR:\n%s", p.stderr.strip())

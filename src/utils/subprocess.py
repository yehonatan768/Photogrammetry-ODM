from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import List, Optional

log = logging.getLogger(__name__)


def run_cmd(cmd: List[str], cwd: Optional[Path] = None) -> None:
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

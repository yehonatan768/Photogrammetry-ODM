from __future__ import annotations

import hashlib
from pathlib import Path


def sha1_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    """
    Compute the SHA1 hash of a file.

    This function reads the file in chunks (default: 1MB) to avoid
    loading large files entirely into memory. It is useful for:
      - generating stable run identifiers
      - verifying file integrity
      - caching and deduplication logic

    Args:
        path (Path):
            Path to the file whose SHA1 hash should be computed.

        chunk_size (int):
            Number of bytes to read per iteration.
            Default is 1MB (1024 * 1024).

    Returns:
        str:
            SHA1 digest as a hexadecimal string.
            Example:
                "2fd4e1c67a2d28fced849ee1bb76e7391b93eb12"
    """
    h = hashlib.sha1()
    with path.open("rb") as f:
        while True:
            b = f.read(chunk_size)
            if not b:
                break
            h.update(b)
    return h.hexdigest()

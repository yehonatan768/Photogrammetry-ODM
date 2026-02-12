from __future__ import annotations

import logging
import os
from urllib.parse import urlparse

import requests

from pyodm import Node, exceptions

log = logging.getLogger(__name__)


def get_odm_hosts(host_env: str, default: str) -> list[str]:
    """Return one or more NodeODM hosts.

    Supports comma-separated lists in either the environment variable or the config default.
    Example: "http://nodeodm1:3000,http://nodeodm2:3000"
    """

    raw = os.getenv(host_env, default)
    # Allow commas or whitespace as separators.
    parts = [p.strip() for p in raw.replace("\n", ",").replace(" ", ",").split(",") if p.strip()]
    return parts or [default]


def get_odm_host(host_env: str, default: str) -> str:
    """Back-compat: returns the first host."""
    return get_odm_hosts(host_env, default)[0]


def _parse_host_port(odm_host: str) -> tuple[str, int]:
    """
    Supports:
      - http://nodeodm:3000
      - https://127.0.0.1:3000
      - nodeodm:3000
      - nodeodm (defaults to 3000)
    """
    s = odm_host.strip()

    if "://" in s:
        u = urlparse(s)
        host = u.hostname or "localhost"
        port = u.port or 3000
        return host, int(port)

    # no scheme
    if ":" in s:
        host, port_s = s.rsplit(":", 1)
        return host, int(port_s)

    return s, 3000


def connect(odm_host: str) -> Node:
    host, port = _parse_host_port(odm_host)
    log.info("Connecting to NodeODM: host=%s port=%s", host, port)

    node = Node(host, port)
    try:
        info = node.info()

        def _safe(obj, name: str):
            if isinstance(obj, dict):
                return obj.get(name)
            return getattr(obj, name, None)

        log.info(
            "Connected to NodeODM: engine=%s | cpu=%s | mem=%s",
            _safe(info, "engine"),
            _safe(info, "cpu"),
            _safe(info, "memory"),
        )

    except exceptions.NodeConnectionError as e:
        raise RuntimeError(f"Failed to connect to NodeODM at {host}:{port}: {e}") from e

    return node


def _normalize_base_url(odm_host: str) -> str:
    """Ensure we have a base URL like http://host:port"""
    s = odm_host.strip()
    if "://" not in s:
        s = "http://" + s
    # keep as provided (NodeODM is usually plain http)
    u = urlparse(s)
    host = u.hostname or "localhost"
    port = u.port or 3000
    scheme = u.scheme or "http"
    return f"{scheme}://{host}:{port}"


def _node_load(base_url: str, timeout_s: float = 2.0) -> tuple[int, int, int]:
    """Return (running, queued, total) task counts for a NodeODM instance."""
    # /task/list returns a list of {uuid: ...}
    r = requests.get(f"{base_url}/task/list", timeout=timeout_s)
    r.raise_for_status()
    items = r.json() or []
    uuids = [it.get("uuid") for it in items if isinstance(it, dict) and it.get("uuid")]

    running = queued = 0
    for uid in uuids:
        try:
            info = requests.get(f"{base_url}/task/{uid}/info", timeout=timeout_s).json()
            code = (info.get("status") or {}).get("code")
            if code == 20:
                running += 1
            elif code == 10:
                queued += 1
        except Exception:
            # If a single task info fails, don't break scheduling.
            continue

    return running, queued, len(uuids)


def pick_best_odm_host(hosts: list[str], timeout_s: float = 2.0) -> str:
    """Pick the least-loaded NodeODM host.

    Heuristic:
      1) Prefer fewer running tasks
      2) Then fewer queued tasks
      3) Then fewer total tasks

    If load probing fails for all hosts, fallback to the first host.
    """

    if not hosts:
        raise ValueError("hosts must be non-empty")

    best: tuple[int, int, int, str] | None = None
    for h in hosts:
        base = _normalize_base_url(h)
        try:
            running, queued, total = _node_load(base, timeout_s=timeout_s)
            cand = (running, queued, total, h)
            if best is None or cand[:3] < best[:3]:
                best = cand
        except Exception:
            continue

    return (best[3] if best is not None else hosts[0])

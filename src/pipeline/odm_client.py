from __future__ import annotations

import logging
import os
from urllib.parse import urlparse

import requests

from pyodm import Node, exceptions

log = logging.getLogger(__name__)


def get_odm_hosts(host_env: str, default: str) -> list[str]:
    """
    Return one or more NodeODM host URLs.

    This function supports providing multiple NodeODM hosts in a
    comma-separated format. Hosts can be provided either through:

      1. Environment variable (host_env)
      2. The default value passed in the configuration

    Example:
        ODM_HOST="http://nodeodm1:3000,http://nodeodm2:3000"

    It also supports whitespace or newline-separated formats.

    Args:
        host_env (str):
            Environment variable name that may contain the host list.

        default (str):
            Default host (or comma-separated host list) if the env var is missing.

    Returns:
        list[str]:
            A list of NodeODM host strings.
            If parsing results in an empty list, the default is returned.
    """
    raw = os.getenv(host_env, default)
    # Allow commas or whitespace as separators.
    parts = [p.strip() for p in raw.replace("\n", ",").replace(" ", ",").split(",") if p.strip()]
    return parts or [default]


def get_odm_host(host_env: str, default: str) -> str:
    """
    Backward-compatible helper that returns only the first NodeODM host.

    This exists for compatibility with older versions of the pipeline that
    assumed only a single host.

    Args:
        host_env (str):
            Environment variable name containing ODM host(s).

        default (str):
            Default ODM host if the env var is missing.

    Returns:
        str:
            First ODM host string.
    """
    return get_odm_hosts(host_env, default)[0]


def _parse_host_port(odm_host: str) -> tuple[str, int]:
    """
    Parse a NodeODM host string into (hostname, port).

    Supported formats:
      - http://nodeodm:3000
      - https://127.0.0.1:3000
      - nodeodm:3000
      - nodeodm   (defaults to port 3000)

    Args:
        odm_host (str):
            NodeODM host string.

    Returns:
        tuple[str, int]:
            Parsed hostname and port number.
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
    """
    Connect to a NodeODM server and validate connectivity.

    This function creates a `pyodm.Node` object and performs a basic
    `node.info()` request to ensure the server is reachable.

    If the connection fails, a RuntimeError is raised.

    Args:
        odm_host (str):
            NodeODM host string (may include scheme and port).

    Returns:
        Node:
            Connected pyodm Node instance.

    Raises:
        RuntimeError:
            If NodeODM is unreachable or returns connection errors.
    """
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
    """
    Normalize a NodeODM host string into a valid base URL.

    Ensures the output always contains a scheme and explicit port.

    Examples:
        "nodeodm:3000"     -> "http://nodeodm:3000"
        "http://nodeodm"   -> "http://nodeodm:3000"

    Args:
        odm_host (str):
            NodeODM host string.

    Returns:
        str:
            Normalized base URL in the form: scheme://host:port
    """
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
    """
    Query a NodeODM instance for its current workload.

    This function calls:
      - GET /task/list
      - GET /task/<uuid>/info for each task

    Then counts tasks based on their status code:
      - code 20 = running
      - code 10 = queued

    Args:
        base_url (str):
            Normalized base URL for NodeODM.

        timeout_s (float):
            Request timeout in seconds for each HTTP call.

    Returns:
        tuple[int, int, int]:
            (running_tasks, queued_tasks, total_tasks)
    """
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
    """
    Pick the least-loaded NodeODM host from a list.

    This function probes each host by calling `_node_load()` and selects
    the best candidate based on a simple heuristic:

      1) Prefer fewer running tasks
      2) Then fewer queued tasks
      3) Then fewer total tasks

    If all hosts fail probing (network error, timeout, etc.),
    the function falls back to the first host.

    Args:
        hosts (list[str]):
            List of NodeODM host strings.

        timeout_s (float):
            Timeout for HTTP probing requests.

    Returns:
        str:
            The selected NodeODM host.

    Raises:
        ValueError:
            If the input list is empty.
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

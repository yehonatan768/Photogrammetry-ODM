import argparse
from pathlib import Path

from src.common.config import load_config
from src.common.logging import setup_logging
from src.pipeline.run import run_pipeline


def build_parser() -> argparse.ArgumentParser:
    """
    Build and return the CLI argument parser for the application.

    This defines the command-line interface structure, including:
      - global arguments (config path)
      - subcommands (run)
      - run-specific arguments (video, fps overrides, ODM options)

    Returns:
        argparse.ArgumentParser:
            Fully configured argument parser.
    """
    p = argparse.ArgumentParser(prog="Photogrammetry-ODM", description="Drone video -> frames -> ODM 3D model pipeline")
    p.add_argument("--config", type=str, default="configs/default.yaml", help="Path to YAML config")

    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="Run the full pipeline")
    r.add_argument("--video", type=str, required=True, help="Path to input video (inside container)")
    r.add_argument("--run-id", type=str, default="", help="Optional run id; default auto")
    r.add_argument("--fps", type=float, default=None, help="Override extraction fps")
    r.add_argument("--max-frames", type=int, default=None, help="Override max frames (0=unlimited)")
    r.add_argument("--start-seconds", type=float, default=None, help="Override video start offset")
    r.add_argument("--duration-seconds", type=float, default=None, help="Override extraction duration (0=full)")
    r.add_argument("--odm-opt", action="append", default=[], help="Extra ODM options as key=value (repeatable)")
    r.add_argument("--no-copy-processed", action="store_true", help="Do not copy summary outputs to data/processed")
    return p


def parse_kv_list(kv_list):
    """
    Parse a list of key=value strings into a Python dictionary.

    This is mainly used for the repeatable CLI argument:
        --odm-opt key=value

    Supported coercions:
      - "true"/"false" -> bool
      - integers -> int
      - floats -> float
      - otherwise remains string

    Example:
        ["dsm=true", "mesh_size=200000", "pc_quality=high"]

    Returns:
        dict:
            Parsed dictionary of values with basic type inference.

    Raises:
        ValueError:
            If any item does not contain '='.
    """
    out = {}
    for item in kv_list or []:
        if "=" not in item:
            raise ValueError(f"Invalid --odm-opt '{item}'. Must be key=value")
        k, v = item.split("=", 1)
        # basic type coercion
        vl = v.strip().lower()
        if vl in ("true", "false"):
            out[k.strip()] = (vl == "true")
        else:
            # try int/float
            try:
                out[k.strip()] = int(v)
            except ValueError:
                try:
                    out[k.strip()] = float(v)
                except ValueError:
                    out[k.strip()] = v
    return out


def main():
    """
    Main entrypoint for the CLI application.

    Workflow:
      1. Parse CLI arguments
      2. Validate config file exists
      3. Load configuration from YAML into AppConfig
      4. Setup global logging
      5. Execute requested command (currently only "run")

    Supported command:
      - run: executes the full pipeline from video -> frames -> ODM outputs
    """
    parser = build_parser()
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.exists():
        raise FileNotFoundError(
            f"Config not found: {config_path}. "
            f"Create it (recommended) or run with --config <path>."
        )
    cfg = load_config(config_path)

    setup_logging(cfg.runtime.log_level)

    if args.cmd == "run":
        extra_odm = parse_kv_list(args.odm_opt)
        run_pipeline(
            cfg=cfg,
            video_path=Path(args.video),
            run_id=args.run_id or None,
            fps=args.fps,
            max_frames=args.max_frames,
            start_seconds=args.start_seconds,
            duration_seconds=args.duration_seconds,
            odm_extra_options=extra_odm,
            copy_processed=not args.no_copy_processed,
        )


if __name__ == "__main__":
    main()

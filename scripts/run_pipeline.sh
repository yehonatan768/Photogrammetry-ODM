#!/usr/bin/env bash
set -euo pipefail

VIDEO_PATH="${1:-}"
if [[ -z "$VIDEO_PATH" ]]; then
  echo "Usage: ./scripts/run_pipeline.sh data/raw/videos/my.mp4"
  exit 1
fi

docker compose up -d --build
docker compose run --rm pipeline python -m src.cli run --video "$VIDEO_PATH"

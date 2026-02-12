#!/usr/bin/env bash
set -euo pipefail
docker compose up -d --build
docker compose run --rm pipeline python -m src.cli run --video data/raw/videos/DJI0004.mp4

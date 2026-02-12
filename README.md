# ODM Drone Video → 3D Model Pipeline (Docker + Python 3.11 + NodeODM GPU)

This project converts a drone **video** into a **3D reconstruction** using OpenDroneMap via **NodeODM**.
It is designed for **Windows 11 + Docker Desktop** and a **Python 3.11** pipeline container.
NodeODM runs as a separate service (GPU image) and the pipeline container submits tasks via PyODM.

## What it does
1. Takes an input video (e.g., `data/raw/videos/flight.mp4`)
2. Extracts frames into `data/interim/frames/<run_id>/`
3. Submits frames to NodeODM (ODM) via PyODM
4. Polls until completion
5. Downloads outputs into `runs/<run_id>/odm/` and optionally copies key artifacts into `data/processed/odm_results/<run_id>/`

## Requirements
- Windows 11
- Docker Desktop
- NVIDIA GPU + CUDA 12.1 drivers installed on host
- Docker Desktop configured for NVIDIA runtime (GPU support)
- Sufficient disk space (ODM outputs can be large)

## Quickstart
1) Put your video here:
- `data/raw/videos/my_flight.mp4`

2) Start services:
```powershell
docker compose up -d --build

# Photogrammetry-ODM  
**Drone video → extracted frames → OpenDroneMap (NodeODM) → downloadable 3D/geo outputs**  
Runs with **Docker Compose** (NodeODM as a service + a small Python runner container).

---

## 1) What this project does (high level)

Given a drone **video** (MP4/MOV):

1. **Extract frames** with `ffmpeg` at a configurable FPS (and optional time window).
2. **Submit the extracted images** to a running **NodeODM** instance via **PyODM**.
3. **Poll task progress** until completion.
4. **Download ODM outputs** (orthophoto, DSM/DTM, point cloud, mesh, report, etc.).
5. (Optional) **Copy “summary” artifacts** into `data/processed/...` for convenience.

This repo is built to be **repeatable** (run-id folders, deterministic paths, config-driven defaults) and easy to run on:
- **Windows 11 + Docker Desktop (WSL2 backend)**  
- **Linux (Docker Engine + Compose plugin)**

---

## 2) Needed hardware (recommended)

Minimum workable (small projects):
- **CPU:** 6+ cores (12 threads recommended)
- **RAM:** 32 GB (64 GB recommended for larger runs)
- **Disk:** NVMe recommended (photogrammetry is I/O heavy)
- **GPU (optional):** NVIDIA GPU with CUDA support (speeds parts of ODM when available)

Good “smooth” setup (medium to large projects):
- **CPU:** 8–16 cores
- **RAM:** 64–128 GB
- **Disk:** NVMe SSD with 100+ GB free per large run
- **GPU:** NVIDIA RTX-class GPU

> Note: NodeODM can run CPU-only. GPU mainly helps some stages and can reduce wall-time, but ODM is still often CPU+RAM bound.

---

## 3) Software prerequisites (and versions used here)

### Docker-based runtime (the recommended path)
This repo is designed around containers, so your host machine mainly needs Docker:

**Windows 11**
- Windows 11 + **WSL2** enabled  
- **Docker Desktop** (WSL2 backend)
- **NVIDIA driver** that supports WSL2 (only if you want GPU)
- (Optional) PowerShell 5+ (already present on Windows)

**Linux**
- **Docker Engine** + **docker compose** plugin
- (Optional) `nvidia-container-toolkit` (only if you want GPU)

### Inside the pipeline container
- **Python:** `3.11` (Dockerfile uses `python:3.11-slim`)
- **Python packages (pinned):**
  - `pyyaml==6.0.2`
  - `pydantic==2.10.6`
  - `requests==2.32.3`
  - `tqdm==4.67.1`
  - `python-dotenv==1.0.1`
  - `pyodm==1.5.9`
- **ffmpeg:** installed via apt in the container

### NodeODM container
- `opendronemap/nodeodm:gpu` (runs NodeODM and ODM engine inside)

---

## 4) Repository layout (project structure)

```
Photogrammetry-ODM/
├─ docker-compose.yml
├─ docker/
│  ├─ pipeline/
│  │  ├─ Dockerfile
│  │  ├─ requirements.txt
│  │  └─ .dockerignore
│  └─ configs/
│     └─ defaults.yaml
├─ scripts/
│  ├─ setup_and_run_windows11.ps1
│  ├─ setup_and_run_linux.sh
│  ├─ run_pipeline.ps1
│  ├─ run_pipeline.sh
│  ├─ run_dji0004.ps1
│  └─ run_dji0004.sh
├─ src/
│  ├─ cli.py
│  ├─ configs/
│  │  └─ default.yaml
│  ├─ common/
│  │  ├─ config.py
│  │  ├─ logging.py
│  │  └─ paths.py
│  ├─ pipeline/
│  │  ├─ frames.py
│  │  ├─ odm_client.py
│  │  ├─ odm_task.py
│  │  └─ run.py
│  └─ utils/
│     ├─ hashing.py
│     └─ subprocess.py
└─ commands.txt
```

---

## 5) Key paths and outputs

### Inputs
- Put your video(s) under:
  - `data/raw/videos/<your_video>.mp4`

> The folder is created by you (Git does not store large videos). Any path you pass must exist **inside the pipeline container**, which mounts the repo at `/app`.

### Per-run outputs
Each run generates a unique `run_id` (timestamp + video hash prefix), stored in:

- **Run directory (main outputs):**
  - `runs/<run_id>/`
  - `runs/<run_id>/odm/`  ← full downloaded ODM outputs

- **Frames (intermediate):**
  - `data/interim/frames/<run_id>/frame_000001.jpg ...`

- **Processed “summary” outputs (optional copy):**
  - `data/processed/odm_results/<run_id>/`
  - Copies a few common artifacts when they exist (e.g., orthophoto, DSM, LAZ, OBJ/PLY, report.pdf)

---

## 6) Install & setup

### Option A: Windows 11 (WSL2 + Docker Desktop)
1. Install Docker Desktop and enable **Use the WSL 2 based engine**.
2. If using GPU:
   - Install an NVIDIA driver that supports WSL2
   - Confirm on host:
     ```powershell
     nvidia-smi
     ```
3. Optional but helpful: run the included setup script (it checks WSL, Docker, and GPU):
   ```powershell
   # From repo root
   powershell -ExecutionPolicy Bypass -File .\scripts\setup_and_run_windows11.ps1
   ```

### Option B: Linux
Use the helper script (Debian/Ubuntu oriented; adjust for other distros):
```bash
chmod +x scripts/setup_and_run_linux.sh
./scripts/setup_and_run_linux.sh
```

---

## 7) Configuration

### Main config file
Default config used by the CLI:
- `src/configs/default.yaml`

Key knobs you’ll likely change:
- `video.fps`, `video.max_frames`, `video.start_seconds`, `video.duration_seconds`
- `odm.parallel_uploads`, `odm.poll_seconds`
- `odm_options.*` (ODM parameters sent to NodeODM)

### NodeODM host selection (single or multi-node)
The pipeline reads **ODM_HOST** (comma-separated list supported):

- In `docker-compose.yml` the pipeline container is configured with:
  - `ODM_HOST=http://nodeodm:3000,http://nodeodm2:3000`

The runner will probe each host and pick the least-loaded one.

---

## 8) Step-by-step workflow (recommended)

### Terminal #1 — Start services (NodeODM + pipeline build)
From repo root:
```powershell
docker compose up -d --build
```

This starts:
- NodeODM at:
  - `http://localhost:3000` (container `nodeodm`)
  - `http://localhost:3001` (container `nodeodm2`)
- Builds the pipeline image (Python 3.11 + deps + ffmpeg)

### Terminal #2 — Run a pipeline job
Put your video here:
- `data/raw/videos/Barn.mp4` (example)

Run:
```powershell
docker compose run --rm pipeline python -m src.cli run --video data/raw/videos/Barn.mp4 --fps 1 --max-frames 300
```

Where:
- `--fps` overrides the YAML FPS
- `--max-frames 300` caps extracted frames (0 means unlimited)

### What happens during the run
1. ffmpeg extracts frames into `data/interim/frames/<run_id>/`
2. frames are uploaded to NodeODM (upload progress logs in ~5% steps)
3. task is processed; CLI shows a progress bar via `tqdm`
4. outputs are downloaded to `runs/<run_id>/odm/`
5. “summary outputs” are copied to `data/processed/odm_results/<run_id>/` (unless disabled)

---

## 9) Monitoring NodeODM (run in a separate terminal)

### Quick health check
```powershell
curl.exe -s http://localhost:3000/info
```

### List tasks
```powershell
curl.exe -s http://localhost:3000/task/list
```

### Detailed progress table (PowerShell)
```powershell
$tasks = curl.exe -s http://localhost:3000/task/list | ConvertFrom-Json

$tasks | ForEach-Object {
    $u = $_.uuid
    $info = curl.exe -s "http://localhost:3000/task/$u/info" | ConvertFrom-Json
    [pscustomobject]@{
        uuid     = $u
        code     = $info.status.code
        progress = $info.progress
        minutes  = "{0:N1}" -f ($info.processingTime / 60000)
        images   = $info.imagesCount
    }
} | Format-Table -Auto
```

NodeODM status codes you’ll commonly see:
- `10` = queued
- `20` = running  
(Other codes may appear depending on NodeODM/ODM version; the safest indicator is `progress` and `last_error`.)

---

## 10) CLI usage

### Help
```bash
docker compose run --rm pipeline python -m src.cli --help
```

### Run (minimal)
```bash
docker compose run --rm pipeline python -m src.cli run --video data/raw/videos/DJI0004.mp4
```

### Override extraction window
```bash
docker compose run --rm pipeline python -m src.cli run \
  --video data/raw/videos/Barn.mp4 \
  --fps 2 \
  --start-seconds 10 \
  --duration-seconds 30
```

### Pass extra ODM options (repeatable)
```bash
docker compose run --rm pipeline python -m src.cli run \
  --video data/raw/videos/Barn.mp4 \
  --odm-opt feature-quality=ultra \
  --odm-opt pc-quality=high \
  --odm-opt mesh-size=300000
```

### Disable copying “processed summary outputs”
```bash
docker compose run --rm pipeline python -m src.cli run --video data/raw/videos/Barn.mp4 --no-copy-processed
```

---

## 11) Script reference (what to use, and when)

### Windows PowerShell
- `scripts/run_pipeline.ps1`
  - Run any video:
    ```powershell
    .\scripts\run_pipeline.ps1 -VideoPath "data/raw/videos/Barn.mp4"
    ```
- `scripts/run_dji0004.ps1`
  - Convenience runner for `data/raw/videos/DJI0004.mp4`
- `scripts/setup_and_run_windows11.ps1`
  - Tries to enable/check WSL2, Docker, and GPU; good first-run helper

### Linux Bash
- `scripts/run_pipeline.sh`
  - Run any video:
    ```bash
    ./scripts/run_pipeline.sh data/raw/videos/Barn.mp4
    ```
- `scripts/run_dji0004.sh`
  - Convenience runner for `DJI0004.mp4`
- `scripts/setup_and_run_linux.sh`
  - Installs Docker + (optional) NVIDIA runtime toolkit; then runs `DJI0004.mp4`

---

## 12) Troubleshooting (common)

### “Task not found” after submit / NodeODM restart
This is usually a **persistence/volume** issue. NodeODM tasks must persist in `/var/www/data`.
This repo uses Docker volumes:
- `nodeodm_data:/var/www/data`
- `nodeodm2_data:/var/www/data`

Check:
```bash
docker volume ls
docker logs nodeodm --tail 200
```

### GPU not being used
If you want GPU acceleration, confirm:
- Host `nvidia-smi` works
- Docker GPU passthrough works:
  ```bash
  docker run --rm --gpus all nvidia/cuda:12.1.0-base-ubuntu22.04 nvidia-smi
  ```
If that fails, NodeODM will still work CPU-only, just slower.

### Very slow progress / “stuck” for long periods
ODM can spend long time in some stages with minimal progress updates. Monitor:
- CPU/RAM usage (host task manager / `htop`)
- NodeODM logs:
  ```bash
  docker logs -f nodeodm
  ```

---

## 13) Notes on customization

If you want to make the pipeline more “production-grade”, common upgrades are:
- Add a **run manifest** (store config + chosen host + ODM task uuid in `runs/<run_id>/`)
- Save full logs into `runs/<run_id>/logs/`
- Add a “resume” mode (skip extraction if frames already exist)
- Add a “download-only” mode (re-download outputs if a run was interrupted)

---

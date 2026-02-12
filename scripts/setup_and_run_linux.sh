#!/usr/bin/env bash
# scripts/setup_and_run_linux.sh
# Ubuntu/Debian-oriented installer + runner (works on many distros with minor changes)
# Does:
# 1) Installs Docker Engine + Compose plugin if missing
# 2) Installs NVIDIA container toolkit if NVIDIA GPU exists
# 3) Tests GPU in Docker (optional)
# 4) Builds + starts services
# 5) Runs pipeline on data/raw/videos/DJI0004.mp4

set -euo pipefail

info(){ echo -e "\033[36m[INFO]\033[0m $*"; }
warn(){ echo -e "\033[33m[WARN]\033[0m $*"; }
fail(){ echo -e "\033[31m[FAIL]\033[0m $*"; exit 1; }

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

VIDEO_PATH="data/raw/videos/DJI0004.mp4"
[[ -f "$VIDEO_PATH" ]] || fail "Missing video: $VIDEO_PATH. Put DJI0004.mp4 there and re-run."

info "Step 1/5: Install Docker Engine + Compose plugin if missing"
if ! command -v docker >/dev/null 2>&1; then
  info "Docker not found. Installing (Debian/Ubuntu)..."

  sudo apt-get update
  sudo apt-get install -y ca-certificates curl gnupg

  sudo install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  sudo chmod a+r /etc/apt/keyrings/docker.gpg

  UBUNTU_CODENAME="$(. /etc/os-release && echo "${VERSION_CODENAME}")"
  echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
    ${UBUNTU_CODENAME} stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

  sudo apt-get update
  sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

  sudo usermod -aG docker "$USER" || true
  warn "You may need to log out/in for docker group changes to take effect."
fi

info "Docker version:"
docker --version

info "Step 2/5: Install NVIDIA container toolkit (only if NVIDIA GPU exists)"
if command -v nvidia-smi >/dev/null 2>&1; then
  info "NVIDIA GPU detected (nvidia-smi ok). Installing nvidia-container-toolkit if missing..."

  if ! dpkg -s nvidia-container-toolkit >/dev/null 2>&1; then
    # This is the common approach; distro-specific variations exist.
    # If this fails on your distro, install via your distro docs.
    distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
    curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
    curl -fsSL https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list \
      | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' \
      | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list >/dev/null

    sudo apt-get update
    sudo apt-get install -y nvidia-container-toolkit
    sudo nvidia-ctk runtime configure --runtime=docker || true
    sudo systemctl restart docker
  else
    info "nvidia-container-toolkit already installed."
  fi
else
  warn "nvidia-smi not found. GPU acceleration won't be available (CPU-only is fine)."
fi

info "Step 3/5: Docker GPU test (optional)"
if command -v nvidia-smi >/dev/null 2>&1; then
  set +e
  docker run --rm --gpus all nvidia/cuda:12.1.0-base-ubuntu22.04 nvidia-smi >/dev/null 2>&1
  rc=$?
  set -e
  if [[ $rc -eq 0 ]]; then
    info "Docker GPU test PASSED."
  else
    warn "Docker GPU test FAILED. NodeODM will run CPU-only."
  fi
fi

info "Step 4/5: Build and start services"
docker compose up -d --build

info "Wait a few seconds for NodeODM to be ready..."
sleep 5

info "Step 5/5: Run pipeline on $VIDEO_PATH"
docker compose run --rm pipeline python -m src.cli run --video "$VIDEO_PATH"

info "Done. Check outputs under runs/ and data/processed/odm_results/"

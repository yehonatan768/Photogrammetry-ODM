# scripts/setup_and_run_windows11.ps1
# Requires: PowerShell running as Administrator for best results
# Does:
# 1) Ensures WSL2 is enabled/updated
# 2) Installs Docker Desktop via winget (if missing)
# 3) Checks GPU availability (optional, but recommended)
# 4) Builds + starts services
# 5) Runs pipeline on data/raw/videos/DJI0004.mp4

$ErrorActionPreference = "Stop"

function Info($msg) { Write-Host "[INFO] $msg" -ForegroundColor Cyan }
function Warn($msg) { Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Fail($msg) { Write-Host "[FAIL] $msg" -ForegroundColor Red; exit 1 }

# Move to repo root (script is in scripts/)
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $RepoRoot

$VideoPath = "data/raw/videos/DJI0004.mp4"
if (!(Test-Path $VideoPath)) {
  Fail "Missing video: $VideoPath. Put DJI0004.mp4 there and re-run."
}

Info "Step 1/3: Ensure WSL2 is available (Windows 11 recommended)"
try {
  wsl --status | Out-Null
} catch {
  Warn "WSL not available. Attempting to enable WSL + VirtualMachinePlatform..."
  # These require admin + reboot sometimes
  dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart | Out-Null
  dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart | Out-Null
  Warn "WSL features enabled. You may need to REBOOT, then re-run this script."
}

try {
  Info "Updating WSL kernel (wsl --update)"
  wsl --update | Out-Null
} catch {
  Warn "WSL update failed or not supported on this system. Continue, but GPU support may fail."
}

Info "Step 2/3: Ensure Docker Desktop is installed"
$dockerOk = $true
try { docker version | Out-Null } catch { $dockerOk = $false }

if (-not $dockerOk) {
  Info "Docker not found. Trying to install Docker Desktop via winget..."
  try {
    winget --version | Out-Null
  } catch {
    Fail "winget not available. Install Docker Desktop manually, then re-run. (Microsoft Store/App Installer usually provides winget.)"
  }

  # Docker Desktop package id can vary; this is the common one
  try {
    winget install -e --id Docker.DockerDesktop --accept-source-agreements --accept-package-agreements
  } catch {
    Fail "Docker Desktop install via winget failed. Install Docker Desktop manually, then re-run."
  }

  Warn "Docker Desktop installed. Launch Docker Desktop once, ensure it's using WSL2 backend, then re-run this script."
  exit 0
}

Info "Step 3/3: GPU sanity check (optional but recommended)"
try {
  nvidia-smi | Out-Null
  Info "Host NVIDIA driver detected (nvidia-smi ok)."
} catch {
  Warn "nvidia-smi not found. If you want GPU acceleration, install NVIDIA drivers that support WSL2 + Docker GPU."
}

Info "Testing Docker GPU passthrough with CUDA 12.1 base image..."
try {
  docker run --rm --gpus all nvidia/cuda:12.1.0-base-ubuntu22.04 nvidia-smi | Out-Null
  Info "Docker GPU test PASSED."
} catch {
  Warn "Docker GPU test FAILED. NodeODM will still run on CPU, but it will be slower."
}



Info "Done Setting up."

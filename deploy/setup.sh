#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════
# Loomin-Docs — Air-Gapped RHEL 9 Bootstrap Script
# This script installs Docker, loads container images, loads
# Ollama model weights, and starts all services.
# Run as root on a clean RHEL 9 VM with no internet access.
# ═══════════════════════════════════════════════════════════════════
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RPMS_DIR="${SCRIPT_DIR}/rpms"
IMAGES_DIR="${SCRIPT_DIR}/images"
MODELS_DIR="${SCRIPT_DIR}/models"

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

log()   { echo -e "${CYAN}[LOOMIN]${NC} $1"; }
ok()    { echo -e "${GREEN}[  OK  ]${NC} $1"; }
fail()  { echo -e "${RED}[FAIL ]${NC} $1"; exit 1; }

# ─── 1. Install Docker from local RPMs ─────────────────────────────
log "Step 1/5: Installing Docker Engine from local RPMs..."
if command -v docker &>/dev/null; then
    ok "Docker already installed: $(docker --version)"
else
    if [ ! -d "$RPMS_DIR" ]; then
        fail "RPM directory not found: $RPMS_DIR"
        echo ""
        echo "To prepare RPMs on an internet-connected RHEL 9 machine:"
        echo "  sudo dnf install --downloadonly --downloaddir=./rpms \\"
        echo "    docker-ce docker-ce-cli containerd.io docker-compose-plugin"
    fi
    rpm -Uvh --nodeps "${RPMS_DIR}"/*.rpm || fail "RPM installation failed"
    ok "Docker RPMs installed"
fi

# ─── 2. Start Docker ───────────────────────────────────────────────
log "Step 2/5: Starting Docker daemon..."
systemctl enable docker --now
systemctl is-active docker &>/dev/null && ok "Docker daemon running" || fail "Docker failed to start"

# ─── 3. Load Docker images ─────────────────────────────────────────
log "Step 3/5: Loading Docker images from tar archives..."
if [ -d "$IMAGES_DIR" ]; then
    for tar_file in "${IMAGES_DIR}"/*.tar; do
        [ -f "$tar_file" ] || continue
        log "  Loading $(basename "$tar_file")..."
        docker load -i "$tar_file"
        ok "  Loaded $(basename "$tar_file")"
    done
else
    log "  No images directory found. Will build from source instead."
    log "  (This requires Dockerfiles in ../frontend and ../backend)"
fi

# ─── 4. Side-load Ollama model weights ─────────────────────────────
log "Step 4/5: Side-loading Ollama model weights..."
#
# Model weights are too large to include in the repository.
# To prepare model weights on an internet-connected machine:
#
#   1. Install Ollama: curl -fsSL https://ollama.ai/install.sh | sh
#   2. Pull the model: ollama pull llama3
#   3. Copy the model blobs:
#      cp -r ~/.ollama/models ./deploy/models/
#
# The directory structure should look like:
#   deploy/models/
#   ├── manifests/
#   │   └── registry.ollama.ai/
#   │       └── library/
#   │           └── llama3/
#   │               └── latest
#   └── blobs/
#       └── sha256-*
#
if [ -d "$MODELS_DIR" ]; then
    # Create the Ollama volume and copy models into it
    docker volume create loomin-docs_ollama-models 2>/dev/null || true
    VOLUME_PATH=$(docker volume inspect loomin-docs_ollama-models --format '{{ .Mountpoint }}')
    cp -r "${MODELS_DIR}"/* "${VOLUME_PATH}/" 2>/dev/null || true
    ok "Model weights loaded into Docker volume"
else
    log "  No models directory found at: $MODELS_DIR"
    log "  You'll need to pull models after starting Ollama (requires network)."
    log "  See deploy/README-DEPLOY.md for offline instructions."
fi

# ─── 5. Start services ────────────────────────────────────────────
log "Step 5/5: Starting Loomin-Docs services..."
cd "$SCRIPT_DIR"
docker compose up -d --build

echo ""
ok "═══════════════════════════════════════════════════"
ok "  Loomin-Docs is running!"
ok "  Frontend:  http://localhost:3000"
ok "  Backend:   http://localhost:8000/docs"
ok "  Ollama:    http://localhost:11434"
ok "═══════════════════════════════════════════════════"

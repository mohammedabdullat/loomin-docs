# Loomin-Docs — Air-Gapped Deployment Guide

This guide explains how to prepare the bootstrap package on an internet-connected machine and deploy Loomin-Docs on a clean RHEL 9 VM with no network access.

## Prerequisites (Internet-Connected Machine)

You need a RHEL 9 (or compatible) machine with internet access to download:

### 1. Docker RPMs

```bash
# Enable Docker CE repo
sudo dnf config-manager --add-repo https://download.docker.com/linux/rhel/docker-ce.repo

# Download RPMs (without installing)
mkdir -p deploy/rpms
sudo dnf install --downloadonly --downloaddir=deploy/rpms \
    docker-ce docker-ce-cli containerd.io docker-compose-plugin

# You should get ~10 RPM files totaling ~100 MB
```

### 2. Docker Images

```bash
# Build the images
cd deploy && docker compose build

# Save images as tar archives
mkdir -p images
docker save loomin-frontend -o images/loomin-frontend.tar
docker save loomin-backend -o images/loomin-backend.tar
docker save ollama/ollama:latest -o images/ollama.tar

# Each tar will be 500 MB — 2 GB depending on the image
```

### 3. Ollama Model Weights

```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Pull desired models
ollama pull llama3
ollama pull mistral    # optional second model

# Copy the model storage
mkdir -p deploy/models
cp -r ~/.ollama/models/* deploy/models/

# llama3 is ~4.7 GB, mistral is ~4.1 GB
```

### 4. Embedding Model (Already Baked Into Backend Image)

The `all-MiniLM-L6-v2` sentence-transformers model is pre-downloaded during the backend Docker build. No additional steps needed.

---

## Creating the Bootstrap Archive

```bash
# From the project root:
tar czf loomin-bootstrap.tar.gz \
    deploy/setup.sh \
    deploy/docker-compose.yml \
    deploy/Modelfile \
    deploy/rpms/ \
    deploy/images/ \
    deploy/models/ \
    frontend/ \
    backend/

# The archive will be 5-15 GB depending on models included.
# Transfer via USB drive, SCP to the air-gapped network, etc.
```

---

## Deploying on the Air-Gapped RHEL 9 VM

```bash
# 1. Transfer and extract the archive
tar xzf loomin-bootstrap.tar.gz
cd deploy

# 2. Run the bootstrap script as root
chmod +x setup.sh
sudo ./setup.sh

# 3. Verify all services are running
docker ps
# Should show: loomin-frontend, loomin-backend, loomin-ollama

# 4. Open in browser
# http://<vm-ip>:3000
```

### Optional: Create Custom Model Profile

```bash
# After services are running:
docker cp Modelfile loomin-ollama:/tmp/Modelfile
docker exec loomin-ollama ollama create loomin-assistant -f /tmp/Modelfile
```

---

## Troubleshooting

| Issue | Solution |
|-------|---------|
| `docker: command not found` | RPMs not installed. Check `deploy/rpms/` has the correct RHEL 9 RPMs. |
| Backend can't reach Ollama | Verify `docker network ls` shows `loomin-net`. |
| No models available | Ensure `deploy/models/` was copied correctly. Check `docker exec loomin-ollama ollama list`. |
| Slow inference | Check if GPU pass-through is enabled in `docker-compose.yml`. |
| Port 3000 blocked | Check firewall: `firewall-cmd --add-port=3000/tcp --permanent && firewall-cmd --reload` |

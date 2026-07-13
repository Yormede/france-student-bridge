#!/bin/bash
# deploy_docker.sh — Déploiement Docker du France Student Bridge
# A execute sur le host ct104 (LXC avec Docker), PAS depuis le conteneur opencode.
set -e

cd "$(dirname "$0")"

echo ">>> Build de l'image fs-bridge:latest..."
docker build -t fs-bridge:latest .

echo ">>> Arret du conteneur existant..."
docker rm -f fs-bridge 2>/dev/null || true

echo ">>> Demarrage du conteneur..."
docker run -d \
    --name fs-bridge \
    --restart unless-stopped \
    -p 8765:8765 \
    -v "$(pwd)/storage:/app/storage" \
    -v "$(pwd)/store.json:/app/store.json" \
    -e FS_EMAIL="${FS_EMAIL}" \
    -e FS_PASSWORD="${FS_PASSWORD}" \
    -e CHROME_PATH=/usr/bin/chromium \
    fs-bridge:latest

echo ">>> Bridge demarre sur http://localhost:8765"
echo ">>> Health: curl http://localhost:8765/health"
echo ">>> Logs: docker logs -f fs-bridge"
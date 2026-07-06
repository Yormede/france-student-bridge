#!/bin/bash
export FS_EMAIL="${FS_EMAIL:-}"
export FS_PASSWORD="${FS_PASSWORD:-}"
export BIND_HOST="${BIND_HOST:-0.0.0.0}"
export BIND_PORT="${BIND_PORT:-8765}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================"
echo "  Bridge Service - France Student API"
echo "========================================"
echo ""
echo "Endpoints:"
echo "  Health:  http://${BIND_HOST}:${BIND_PORT}/health"
echo "  Models:  http://${BIND_HOST}:${BIND_PORT}/models"
echo "  Chat:    http://${BIND_HOST}:${BIND_PORT}/chat/completions"
echo "  Images:  http://${BIND_HOST}:${BIND_PORT}/images/<filename>"
echo ""

if [ -z "$FS_EMAIL" ] || [ -z "$FS_PASSWORD" ]; then
    echo "⚠️  FS_EMAIL / FS_PASSWORD non definis."
    echo "   Set-les via variables d'environnement:"
    echo "   export FS_EMAIL=ton@email.com"
    echo "   export FS_PASSWORD=ton_mdp"
    echo ""
    echo "   Ou appelle POST /auth/login avec email + password"
    echo ""
fi

exec python3 bridge_server.py "$@"

#!/usr/bin/env bash
# Affiche l'état de la stack Langfuse + santé Web + tail logs récents.
set -euo pipefail
cd "$(dirname "$0")"

echo "=== Containers ==="
docker compose ps
echo ""
echo "=== Health Web ==="
if curl -sf http://localhost:3000/api/public/health 2>/dev/null; then
  echo "✅ http://localhost:3000 répond"
else
  echo "❌ http://localhost:3000 ne répond pas"
fi
echo ""
echo "=== Health Worker ==="
if curl -sf http://localhost:3030/health 2>/dev/null; then
  echo "✅ worker port 3030 OK"
else
  echo "❌ worker port 3030 ne répond pas"
fi
echo ""
echo "=== Logs (web, 20 dernières lignes) ==="
docker compose logs langfuse-web --tail 20

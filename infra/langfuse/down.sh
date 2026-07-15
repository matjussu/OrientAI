#!/usr/bin/env bash
# Arrête la stack Langfuse (préserve les volumes — les données restent).
# Pour effacer aussi les données: docker compose down -v
set -euo pipefail
cd "$(dirname "$0")"
docker compose down
echo "✅ Langfuse stoppé (volumes préservés)."

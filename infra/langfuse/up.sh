#!/usr/bin/env bash
# Démarre la stack Langfuse self-hosted (Postgres + ClickHouse + Redis + MinIO + web + worker)
set -euo pipefail
cd "$(dirname "$0")"

if [[ ! -f .env ]]; then
  echo "❌ .env manquant. Copier .env.example et générer les secrets." >&2
  exit 1
fi

docker compose up -d
echo ""
echo "⏳ Attente que les services soient sains (max ~60s)…"
for i in {1..30}; do
  if curl -sf http://localhost:3000/api/public/health >/dev/null 2>&1; then
    echo "✅ Langfuse up sur http://localhost:3000"
    echo "   Login : voir LANGFUSE_INIT_USER_EMAIL + LANGFUSE_INIT_USER_PASSWORD dans .env"
    exit 0
  fi
  sleep 2
done

echo "⚠️  Timeout health-check. Inspecte avec :"
echo "    docker compose -f $(pwd)/docker-compose.yml ps"
echo "    docker compose -f $(pwd)/docker-compose.yml logs langfuse-web --tail 50"
exit 1

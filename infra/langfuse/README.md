# Langfuse self-hosted — OrientIA observability stack

Stack Docker Compose pour Langfuse v3 (web + worker + Postgres + ClickHouse + Redis + MinIO).
Pré-configurée pour OrientIA : org / projet / user / API keys initialisés au boot.

## Architecture des ports

| Service | Port host | Bind | Usage |
|---|---|---|---|
| Langfuse Web UI | `3000` | `0.0.0.0` | Dashboard, prompts, traces |
| Langfuse Worker | `3030` | `127.0.0.1` | Background ingestion |
| Postgres | `5432` | `127.0.0.1` | Metadata Langfuse |
| ClickHouse | `8123` / `9000` | `127.0.0.1` | Traces analytics |
| Redis | `6379` | `127.0.0.1` | Queue ingestion |
| MinIO S3 API | `9090` | `0.0.0.0` | Object storage events/media |
| MinIO console | `9091` | `127.0.0.1` | Admin S3 |

## Prérequis

- WSL2 Ubuntu 24.04 avec systemd activé (`/etc/wsl.conf` → `[boot] systemd=true`)
- Docker Engine + Compose v2 — voir `install_docker.sh` ci-dessous
- ~4 GB RAM dispo (ClickHouse + Postgres + Redis + MinIO + 2 containers Node)

## Installation initiale

### 1. Installer Docker (une seule fois, requiert sudo)

```bash
sudo bash infra/langfuse/install_docker.sh
# Puis dans le shell courant :
newgrp docker
# ou ouvre un nouveau terminal WSL pour récupérer l'appartenance au groupe.
```

### 2. Démarrer la stack

```bash
bash infra/langfuse/up.sh
```

Le premier `up` télécharge ~3 GB d'images Docker (postgres, clickhouse, redis, minio, langfuse-web, langfuse-worker) — compter 5-10 min selon connexion. Au bout d'environ 60s après les pulls, le service est prêt.

### 3. Login UI

Ouvre http://localhost:3000 et connecte-toi avec les credentials du `.env` :
- `LANGFUSE_INIT_USER_EMAIL` → email
- `LANGFUSE_INIT_USER_PASSWORD` → password

L'organisation `OrientIA` + le projet `OrientIA RAG` + les API keys sont déjà créés au boot.

## Utilisation au quotidien

```bash
bash infra/langfuse/up.sh        # démarre
bash infra/langfuse/down.sh      # arrête (volumes préservés)
bash infra/langfuse/status.sh    # état + santé + logs
```

## Intégration côté Python (OrientIA)

Les API keys sont dans `.env` (côté infra) et doivent être également disponibles
côté process Python OrientIA. Ajouter à `~/projets/OrientIA/.env` :

```bash
LANGFUSE_PUBLIC_KEY=pk-lf-8506f194-1698d64c15c2647acd3d3f86
LANGFUSE_SECRET_KEY=sk-lf-5fdae191a85d3fd5660d7de000a146044762d8996b01c9d2
LANGFUSE_HOST=http://localhost:3000
```

Puis dans le code :

```python
import src.observability  # noqa: F401 — shim mistralai pour ragas/instructor
from langfuse import Langfuse, observe

# Pipeline tracing exemple
@observe(name="orientia_answer")
def answer(question: str) -> str:
    ...
```

## Effacer complètement (reset)

```bash
docker compose -f infra/langfuse/docker-compose.yml down -v
```

`-v` supprime aussi les 5 volumes nommés (postgres, clickhouse_data, clickhouse_logs, minio_data, redis_data). À utiliser pour repartir vierge.

## Sécurité

- Tous les ports internes sont bindés sur `127.0.0.1` sauf le web UI (`3000`) et MinIO S3 (`9090`).
- Le `.env` est gitignored — ne jamais le commiter.
- Les secrets ont été générés avec `openssl rand` au moment du setup (2026-05-13).

## Sources

- Langfuse self-host docs : https://langfuse.com/self-hosting
- Docker compose officiel : https://github.com/langfuse/langfuse/blob/main/docker-compose.yml

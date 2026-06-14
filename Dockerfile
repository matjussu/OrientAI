# Image Python 3.12-slim — léger (~150 MB base) suffit pour CPU-only FAISS.
# Build pour Railway Pro $20/mois (8 GB RAM target, single worker).
FROM python:3.12-slim

WORKDIR /app

# Deps OS minimales pour faiss-cpu / numpy / pandas (compilation)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Deps Python — copie séparée pour profiter du cache Docker
COPY requirements.lock .
RUN pip install --no-cache-dir -r requirements.lock

# Code application
COPY src/ ./src/

# MIGRATION VOLUME (ordre 2026-06-14-1501) — les gros artefacts (corpus formations.json
# + index FAISS + 4 quad sub-indexes + manifest + golden_qa) ne sont PLUS embarqués dans
# l'image : ils vivent sur le VOLUME Railway monté à /app/data. Raison : `railway up`
# bakant ~510MB d'index tape la limite d'upload Cloudflare (413). Avec le volume, le
# deploy est CODE-ONLY (image légère) et les artefacts sont uploadés UNE fois
# (`railway volume files upload`), plus jamais de 413/502.
#
# Anti-shadow-mount (cf incident Option C 06-12 où le volume masquait l'index baké ->
# prod servait le 47220 en silence) : l'image ne contient AUCUN index baké, il n'y a
# donc RIEN à masquer. L'app lit l'index UNIQUEMENT depuis le volume -> désalignement
# silencieux impossible par construction.
#
# SÉQUENCE OBLIGATOIRE : volume créé + peuplé AVANT le deploy code (sinon fail-fast au
# boot via _require_artifacts dans server.py). Le volume DOIT monter à /app/data : le
# manifest quad se résout via parents[2]=/app + chemins relatifs, il faut donc que
# /app/data == le volume.

# Railway injecte $PORT automatiquement
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1

COPY scripts/build_quad_subindexes.py ./scripts/build_quad_subindexes.py

EXPOSE 8000

# --workers 1 OBLIGATOIRE : `_pipeline.last_validation` est mutable + global.
# Multi-worker = OOM (chaque worker recharge ~280 MB) + race conditions.
CMD ["sh", "-c", "uvicorn src.api.server:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]

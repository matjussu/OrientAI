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

# MIGRATION VOLUME — Approche A (ordre 2026-06-14-1501, 2026-06-14) : les INDEX FAISS
# (formations.index + 4 quad sub-indexes + manifest + golden_qa, ~412MB) vivent sur le
# VOLUME Railway DÉJÀ monté à /app/data/embeddings -> ils ne sont PLUS COPY dans l'image
# (sinon `railway up` baker ~410MB tape la limite Cloudflare 413). Mis à jour 1×
# (`railway volume files upload --overwrite`), plus jamais de 413 à l'upload.
#
# Le CORPUS (formations.json + golden_qa_meta.json, ~107MB) RESTE dans l'image : le
# volume ne couvre que /app/data/embeddings, pas /app/data/processed. railway up upload
# ~corpus seul ~35MB compressé -> sous la limite, plus de 413.
#
# Anti-shadow-mount : l'image ne COPY AUCUN data/embeddings -> rien à masquer sous le
# volume (le volume EST la seule source d'index). Le manifest quad se résout via
# parents[2]=/app + chemins relatifs (data/embeddings/...) = /app/data/embeddings = volume.
# Fail-fast au boot si index/corpus absent (_require_artifacts dans server.py).
COPY data/processed/formations.json ./data/processed/formations.json
COPY data/processed/golden_qa_meta.json ./data/processed/golden_qa_meta.json

# Railway injecte $PORT automatiquement
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1

COPY scripts/build_quad_subindexes.py ./scripts/build_quad_subindexes.py

EXPOSE 8000

# --workers 1 OBLIGATOIRE : `_pipeline.last_validation` est mutable + global.
# Multi-worker = OOM (chaque worker recharge ~280 MB) + race conditions.
CMD ["sh", "-c", "uvicorn src.api.server:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]

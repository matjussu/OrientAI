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

# Corpus principal (~135 MB) embarqué dans l'image — aligné sur main : 52040 fiches
# (salaire+quartiles InserSup + debouches ROME #146).
# Option C (index dans l'image) ABANDONNÉE le 2026-06-12 : tarball railway up 1.8GB ->
# 413 Cloudflare. Retour à l'approche volume : l'index FAISS #2 + quad sub-indexes +
# manifest (~410 MB, dense-sigle-OFF, 52040) vivent sur le volume Railway ÉLARGI (>500MB)
# monté sur /app/data/embeddings (ORIENTIA_INDEX_PATH). Ne PAS COPY l'index dans l'image
# (tarball trop lourd pour la limite d'upload Cloudflare).
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

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
COPY data/processed/formations.json ./data/processed/formations.json
COPY data/processed/golden_qa_meta.json ./data/processed/golden_qa_meta.json

# Option C (ordre 1535, 2026-06-12) — index FAISS + quad sub-indexes + manifest
# EMBARQUÉS dans l'image (état #2 dense-sigle-OFF, 52040, aligné corpus). Décision :
# le volume Railway (quota 500MB, mutations destructives gatées) est abandonné comme
# source des index. Le volume sera DÉTACHÉ au deploy (sinon il masque /app/data/embeddings
# de l'image). Avantage : état atomique code+corpus+index, rollback = redeploy image
# précédente, plus aucune op volume. ~+412 MB image (index 213 + quads 196 + golden 3).
COPY data/embeddings/formations.index ./data/embeddings/formations.index
COPY data/embeddings/formations_v7_formations.index ./data/embeddings/formations_v7_formations.index
COPY data/embeddings/formations_v7_metiers.index ./data/embeddings/formations_v7_metiers.index
COPY data/embeddings/formations_v7_statistiques.index ./data/embeddings/formations_v7_statistiques.index
COPY data/embeddings/formations_v7_aides_territoires.index ./data/embeddings/formations_v7_aides_territoires.index
COPY data/embeddings/formations_partition_manifest.json ./data/embeddings/formations_partition_manifest.json
COPY data/embeddings/golden_qa.index ./data/embeddings/golden_qa.index

# Railway injecte $PORT automatiquement
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1

COPY scripts/build_quad_subindexes.py ./scripts/build_quad_subindexes.py

EXPOSE 8000

# --workers 1 OBLIGATOIRE : `_pipeline.last_validation` est mutable + global.
# Multi-worker = OOM (chaque worker recharge ~280 MB) + race conditions.
CMD ["sh", "-c", "uvicorn src.api.server:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]

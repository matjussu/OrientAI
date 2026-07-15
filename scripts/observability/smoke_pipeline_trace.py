"""Smoke pipeline trace — lance OrientIAPipeline.answer() sur 1 question réelle
et confirme que la trace nested (10 spans) remonte dans Langfuse.

Charge :
  - corpus : data/processed/formations_v5.json (47 193 fiches au 2026-05-13)
  - index  : data/embeddings/formations_v5.index

Préalable : Langfuse self-hosted doit tourner (bash infra/langfuse/up.sh)
et LANGFUSE_PUBLIC_KEY / SECRET_KEY / HOST doivent être set dans .env.

Usage :
    cd ~/projets/OrientIA && source .venv/bin/activate
    python scripts/observability/smoke_pipeline_trace.py
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

# Doit être set pour activer l'instrumentation (sinon no-op)
if not os.environ.get("LANGFUSE_PUBLIC_KEY"):
    print("❌ LANGFUSE_PUBLIC_KEY absent. Active dans .env avant de lancer.")
    sys.exit(1)

import src.observability as obs  # noqa: E402

from mistralai.client import Mistral  # noqa: E402
from src.config import load_config  # noqa: E402
from src.rag.factory import make_production_pipeline  # noqa: E402


CORPUS_PATH = REPO_ROOT / "data" / "processed" / "formations_v5.json"
INDEX_PATH = REPO_ROOT / "data" / "embeddings" / "formations_v5.index"

# Question Q6 du spot-check : passe le retrieve (5/5 domain match), bonne réponse.
# Cas idéal pour valider que tous les spans nested se peuplent.
QUESTION = "Quelles aides financières pour les étudiants boursiers ?"


def main() -> int:
    print(f"→ Corpus  : {CORPUS_PATH.name}")
    print(f"→ Index   : {INDEX_PATH.name}")
    print(f"→ Question : {QUESTION!r}")
    print()

    if not CORPUS_PATH.exists() or not INDEX_PATH.exists():
        print(f"❌ Corpus ou index manquant : {CORPUS_PATH.exists()=}, {INDEX_PATH.exists()=}")
        return 1

    t0 = time.time()
    cfg = load_config()
    client = Mistral(api_key=cfg.mistral_api_key, timeout_ms=120000)
    fiches = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    print(f"→ Loaded {len(fiches):,} fiches in {time.time()-t0:.1f}s")

    pipeline = make_production_pipeline(client, fiches)
    pipeline.load_index_from(str(INDEX_PATH))
    print(f"→ Pipeline + index ready ({time.time()-t0:.1f}s total)")
    print()

    t1 = time.time()
    answer_text, top = pipeline.answer(QUESTION, top_k_sources=5)
    elapsed = time.time() - t1

    print(f"→ Pipeline answered in {elapsed:.2f}s ({len(top)} sources)")
    print()
    print("─── Réponse (extrait) ───")
    print(answer_text[:400].replace("\n", " ") + ("…" if len(answer_text) > 400 else ""))
    print()

    obs.flush()
    print("✅ Trace flushée vers Langfuse.")
    print(f"   Ouvre {os.environ.get('LANGFUSE_HOST', 'http://localhost:3000')}")
    print("   → projet OrientIA RAG → Traces → cherche 'orientia.answer'")
    return 0


if __name__ == "__main__":
    sys.exit(main())

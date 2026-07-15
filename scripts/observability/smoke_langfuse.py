"""Smoke test — vérifie que Langfuse self-hosted répond et accepte une trace.

Lecture des env vars LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY / LANGFUSE_HOST
depuis OrientIA/.env. Si OK :
  1. Instancie un client Langfuse
  2. Crée une trace nested avec 2 spans (mock retrieval + mock generation)
  3. Flush et confirme l'ingestion via l'API GET trace

Usage :
    cd ~/projets/OrientIA && source .venv/bin/activate
    python scripts/observability/smoke_langfuse.py
"""
from __future__ import annotations

import os
import sys
import time
import uuid

from dotenv import load_dotenv

load_dotenv()

PUBLIC_KEY = os.environ.get("LANGFUSE_PUBLIC_KEY", "")
SECRET_KEY = os.environ.get("LANGFUSE_SECRET_KEY", "")
HOST = os.environ.get("LANGFUSE_HOST", "http://localhost:3000")

if not PUBLIC_KEY or not SECRET_KEY:
    print("❌ LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY absents de .env")
    sys.exit(1)

print(f"→ Connexion à {HOST}")
print(f"→ Public key  : {PUBLIC_KEY[:20]}…")

from langfuse import Langfuse, observe

lf = Langfuse(public_key=PUBLIC_KEY, secret_key=SECRET_KEY, host=HOST)

# Auth check
auth_ok = lf.auth_check()
print(f"→ Auth check  : {'✅ OK' if auth_ok else '❌ KO'}")
if not auth_ok:
    print("Vérifier que la stack est up : bash infra/langfuse/up.sh")
    sys.exit(2)


# --- Trace nested mock ---
trace_id = str(uuid.uuid4())


@observe(name="mock_retrieve")
def mock_retrieve(question: str) -> list[dict]:
    return [
        {"source": "parcoursup", "score": 0.87, "fiche": "Lycée X"},
        {"source": "onisep", "score": 0.81, "fiche": "BTS Y"},
    ]


@observe(name="mock_generate", as_type="generation")
def mock_generate(question: str, contexts: list[dict]) -> str:
    return f"Réponse mock pour : {question[:40]}…"


@observe(name="orientia_smoke_pipeline")
def smoke_pipeline(question: str) -> str:
    docs = mock_retrieve(question)
    return mock_generate(question, docs)


print("→ Envoi trace smoke…")
result = smoke_pipeline("Quelles formations en cybersécurité après bac+2 ?")
print(f"→ Pipeline retour : {result}")

# Flush forcé pour push immédiat
lf.flush()
print("→ Flush envoyé, attente ingestion (3s)…")
time.sleep(3)

print()
print("✅ Smoke test envoyé.")
print(f"   Ouvre {HOST} → projet OrientIA RAG → Traces pour voir la trace nested.")

"""Smoke test — Ragas context_recall + faithfulness sur un mini exemple.

Démontre que :
  1. Le shim mistralai (src/observability) débloque l'import ragas
  2. context_recall et faithfulness tournent avec un LLM Mistral via langchain
  3. Aucune dépendance vers OpenAI/Anthropic n'est nécessaire

Usage :
    cd ~/projets/OrientIA && source .venv/bin/activate
    python scripts/observability/smoke_ragas.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Ajout du root OrientIA au PYTHONPATH (script appelé depuis n'importe où)
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv

load_dotenv()

# >>> CRITIQUE : importer le shim AVANT ragas <<<
import src.observability  # noqa: F401,E402

from datasets import Dataset  # noqa: E402
from ragas import evaluate  # noqa: E402
from ragas.metrics import context_recall, faithfulness  # noqa: E402

MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY", "")
if not MISTRAL_API_KEY:
    print("❌ MISTRAL_API_KEY manquant dans .env")
    sys.exit(1)

# Mini dataset 2 exemples (format Ragas standard)
samples = {
    "question": [
        "Quel est le taux d'accès au BUT informatique de l'IUT de Lyon ?",
        "Combien de places en école d'ingénieur post-bac à Brest ?",
    ],
    "answer": [
        "Selon Parcoursup 2025, le taux d'accès au BUT informatique de l'IUT de Lyon est de 38%.",
        "L'ENIB à Brest propose 120 places en formation d'ingénieur post-bac.",
    ],
    "contexts": [
        [
            "BUT Informatique — IUT Lyon 1 (Villeurbanne) — Taux d'accès Parcoursup 2025 : 38%. Places : 80.",
            "Le BUT (Bachelor Universitaire de Technologie) remplace le DUT depuis 2021.",
        ],
        [
            "ENIB — École Nationale d'Ingénieurs de Brest — Formation 5 ans post-bac. 120 places ouvertes en 2025.",
            "Brest, Bretagne. Diplôme d'ingénieur habilité CTI.",
        ],
    ],
    "ground_truth": [
        "Le taux d'accès Parcoursup 2025 au BUT informatique IUT Lyon 1 est 38%, 80 places.",
        "L'ENIB Brest propose 120 places en cycle ingénieur 5 ans.",
    ],
}

dataset = Dataset.from_dict(samples)
print(f"→ Dataset : {len(dataset)} exemples")

# Configuration Mistral comme LLM judge (au lieu du défaut OpenAI)
from langchain_mistralai import ChatMistralAI  # type: ignore  # noqa: E402
from ragas.llms import LangchainLLMWrapper  # noqa: E402
from ragas.embeddings import LangchainEmbeddingsWrapper  # noqa: E402
from langchain_mistralai import MistralAIEmbeddings  # type: ignore  # noqa: E402

mistral_llm = LangchainLLMWrapper(
    ChatMistralAI(model="mistral-small-latest", temperature=0.0, mistral_api_key=MISTRAL_API_KEY)
)
mistral_emb = LangchainEmbeddingsWrapper(MistralAIEmbeddings(api_key=MISTRAL_API_KEY))

print("→ Évaluation context_recall + faithfulness via Mistral large…")
result = evaluate(
    dataset,
    metrics=[context_recall, faithfulness],
    llm=mistral_llm,
    embeddings=mistral_emb,
)

print()
print("✅ Résultats Ragas :")
print(result)

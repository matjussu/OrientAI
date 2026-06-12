"""Gate CI golden 50q (Phase 4, order 0825) — non-régression retrieval.

Test d'INTÉGRATION : nécessite l'index FAISS (gitignored) + MISTRAL_API_KEY.
Skippé automatiquement si l'environnement est absent, pour que `pytest tests/`
reste vert/rapide en dev sans l'index. Lancer le gate complet :
    PYTHONPATH=. .venv/bin/python -m src.eval.golden_ci
ou via le script qui ajoute la passe juge non bloquante :
    bash audit_empirique_2026-06-09/golden_ci.sh
"""
from __future__ import annotations

import pytest

from src.eval.golden_ci import RECALL_SOURCE_FLOOR, index_available, run_recall_gate

pytestmark = pytest.mark.golden


@pytest.mark.skipif(not index_available(),
                    reason="index FAISS ou MISTRAL_API_KEY absent (gate golden = local/CI dédiée)")
def test_golden_retrieval_source_recall_non_regressed():
    """Le top-k retrieval doit surfacer une fiche de la source attendue
    (parcoursup/monmaster) pour les questions golden qui en spécifient une.
    Signal propre (≠ recall domain, ambigu et non gaté)."""
    m = run_recall_gate()
    assert m["recall_source"] is not None, "aucune question avec expected_source"
    assert m["recall_source"] >= RECALL_SOURCE_FLOOR, (
        f"recall source régressé : {m['recall_source_n']} "
        f"({m['recall_source']:.1%}) < plancher {RECALL_SOURCE_FLOOR:.0%}. "
        f"Misses : {[x for x in m['misses'] if x['type'] == 'source']}"
    )

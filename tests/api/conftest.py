"""Fixtures pour les tests du wrapper FastAPI.

On mocke `_pipeline` au niveau du module `src.api.server` pour ne PAS charger
le vrai FAISS index pendant les tests (185 MB + Mistral SDK init = ~10s overhead
inutile pour des tests d'API contract).

Les golden fixtures partagées avec la plateforme se trouvent dans :
    OrientAI_Platform/tests/fixtures/orientia-answer.golden.json

Elles servent de source de vérité pour la shape des réponses — toute
modification de fixture = modification du contrat HTTP.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def mock_pipeline():
    """Pipeline mock alimenté par des sources réalistes au format brut natif."""
    from src.rag.pipeline import RequestTrace

    p = MagicMock()
    validation = MagicMock()
    validation.honesty_score = 0.92
    validation.flagged = False
    trace = RequestTrace(validation=validation)

    # H1 lot 1.6 : le serveur appelle answer(..., return_trace=True) et lit
    # la validation depuis la TRACE retournée (3-uplet), plus depuis last_*.
    p.answer.return_value = (
        "Réponse mock pour test.",
        [
            {
                "source": "parcoursup",
                "phase": "initial",
                "nom": "Licence Test",
                "etablissement": "Université Test",
                "ville": "Lyon",
                "region": "Auvergne-Rhône-Alpes",
                "uai": "0691775E",
                "annee": "2024",
                "niveau": "Bac+3",
                "type_diplome": "Licence",
                "statut": "Public",
                "labels": [],
            },
            {
                "source": "onisep",
                "nom": "BUT Test",
                "uai": "0123456X",
                "type_diplome": "BUT",
                "labels": ["SecNumEdu"],
            },
        ],
        trace,
    )

    # Rétrocompat lecture pour les tests qui inspectent encore last_validation
    p.last_validation = validation

    return p


@pytest.fixture
def client(mock_pipeline, monkeypatch):
    """TestClient avec `_pipeline` global mocké au niveau module."""
    from src.api import server

    monkeypatch.setattr(server, "_pipeline", mock_pipeline)
    monkeypatch.setattr(server, "_index_size", 47193)
    # Auth désactivée par défaut pour la majorité des tests
    monkeypatch.delenv("ORIENTIA_API_KEY", raising=False)
    # Reset rate limit buckets entre tests (in-memory only)
    server._rate_buckets.clear()
    return TestClient(server.app)

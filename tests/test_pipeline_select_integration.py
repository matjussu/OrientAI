"""Tests integration SELECT bypass dans pipeline.answer() — Chantier 2."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.rag.pipeline import OrientIAPipeline


def _pipeline_with_intent(fiches: list[dict]) -> OrientIAPipeline:
    """Pipeline avec use_intent=True pour activer le routing SELECT."""
    fake_client = MagicMock()
    fake_index = MagicMock()
    p = OrientIAPipeline(client=fake_client, fiches=fiches, use_intent=True)
    p.index = fake_index
    return p


class TestSelectBypassIntegration:
    """Test que pipeline.answer() bypasse le RAG quand SELECT réussit."""

    def test_factual_pointed_with_match_bypasses_generate(self):
        """Question factuelle pointue + entité reconnue → SELECT, pas de generate()."""
        fiches = [
            {
                "id": "F1",
                "nom": "Bachelor Cybersécurité",
                "etablissement": "EFREI Bordeaux",
                "ville": "Bordeaux",
                "niveau": "bac+3",
                "taux_acces_parcoursup_2025": 77.0,
                "lien_form_psup": "https://parcoursup.fr/efrei",
            },
        ]
        p = _pipeline_with_intent(fiches)
        with patch("src.rag.pipeline.generate") as mock_gen:
            answer, top = p.answer("Quel est le taux d'accès du Bachelor EFREI Bordeaux ?")

        # generate() NE DOIT PAS être appelé — c'est tout l'intérêt du SELECT
        mock_gen.assert_not_called()
        # Réponse contient le chiffre exact extrait de la fiche
        assert "77 %" in answer
        # via_select True dans last_select_result
        assert p.last_select_result is not None
        assert p.last_select_result.via_select is True

    def test_factual_pointed_no_match_falls_through_to_rag(self):
        """Option B (J2 U1, 2026-06-11) : factuelle + no_match SELECT -> fall-through
        vers le RAG gardé (tracé), au lieu d'un refus aveugle. generate() EST appelé."""
        fiches = [
            {"nom": "Master Droit", "etablissement": "Sorbonne", "ville": "Paris"},
        ]
        p = _pipeline_with_intent(fiches)
        with patch("src.rag.pipeline.generate", return_value="rag answer") as mock_gen:
            with patch.object(p, "_retrieve_and_filter", return_value=[{"fiche": {"nom": "Master Droit"}}]):
                with patch.object(p, "_maybe_build_golden_qa_prefix", return_value=None):
                    answer, top = p.answer("Quel est le taux d'accès du Bachelor Inexistant XYZ ?")

        # Option B : on ne bypasse plus vers un refus -> le RAG gardé est sollicité.
        mock_gen.assert_called_once()
        assert answer == "rag answer"
        # SELECT a tenté (no_match) et on a fall-through -> tracé pour observabilité.
        assert p.last_select_result.via_select is False
        assert p.last_select_result.reason == "select_no_match"
        assert p.last_select_fallthrough is True

    def test_non_factual_question_uses_rag(self):
        """Question non-factuelle (orientation) → RAG normal, pas de SELECT."""
        fiches = [{"nom": "X"}]
        p = _pipeline_with_intent(fiches)
        with patch("src.rag.pipeline.generate", return_value="rag answer") as mock_gen:
            with patch.object(p, "_retrieve_and_filter", return_value=[{"fiche": {"nom": "X"}}]):
                with patch.object(p, "_maybe_build_golden_qa_prefix", return_value=None):
                    answer, top = p.answer("Je suis en terminale, quelle orientation cyber ?")

        # generate() appelé une fois (pipeline RAG normal)
        mock_gen.assert_called_once()
        assert answer == "rag answer"
        assert p.last_select_result is None  # pas de SELECT tenté

    def test_select_bypass_skips_retry_loop(self):
        """SELECT success → retry_metadata indique select_bypass."""
        fiches = [
            {
                "nom": "Bachelor Cyber",
                "etablissement": "EFREI Bordeaux",
                "ville": "Bordeaux",
                "taux_acces_parcoursup_2025": 77.0,
            },
        ]
        p = _pipeline_with_intent(fiches)
        with patch("src.rag.pipeline.generate") as mock_gen:
            p.answer("Quel est le taux d'accès du Bachelor EFREI Bordeaux ?")

        assert p.last_retry_metadata["retry_skipped_reason"] == "select_bypass"
        assert p.last_retry_metadata["retries_attempted"] == 0
        mock_gen.assert_not_called()

    def test_factual_with_annex_domain_uses_rag(self):
        """Vague 0 fix Q9 — question chiffres avec domain annexe pertinent
        (PCS → insee_salaire) doit utiliser le RAG normal pour ramener
        le corpus annexe, pas court-circuiter avec un fallback unifié."""
        fiches = [{"nom": "Master Droit", "etablissement": "Sorbonne", "ville": "Paris"}]
        p = _pipeline_with_intent(fiches)
        with patch("src.rag.pipeline.generate", return_value="rag answer with PCS data") as mock_gen:
            with patch.object(p, "_retrieve_and_filter", return_value=[{"fiche": {"nom": "X"}}]):
                with patch.object(p, "_maybe_build_golden_qa_prefix", return_value=None):
                    answer, top = p.answer("Salaire moyen d'un cadre supérieur (PCS 37) ?")

        # generate() doit être appelé : le domain_hint=insee_salaire empêche
        # le bypass SELECT (le RAG peut ramener la fiche annexe insee_salaire).
        mock_gen.assert_called_once()
        assert answer == "rag answer with PCS data"
        # last_select_result conservé pour traçabilité (SELECT a tenté lookup)
        assert p.last_select_result is not None
        assert p.last_select_result.via_select is False

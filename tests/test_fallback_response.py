"""Tests fallback unifié — Chantier 1.C."""
from __future__ import annotations

from src.rag.fallback_response import (
    DEFAULT_SUGGESTION,
    format_out_of_scope_response,
    format_unknown_response,
)


class TestFormatUnknownResponse:
    def test_starts_with_canonical_opening(self):
        out = format_unknown_response("le taux d'accès EFREI Bordeaux")
        assert out.startswith("Je n'ai pas l'information sur le taux d'accès EFREI Bordeaux")

    def test_includes_dans_mes_sources_verifiees(self):
        out = format_unknown_response("X")
        assert "dans mes sources vérifiées" in out

    def test_no_field_uses_generic_phrasing(self):
        out = format_unknown_response()
        assert out.startswith("Je n'ai pas cette information dans mes sources vérifiées.")

    def test_default_includes_external_suggestion(self):
        out = format_unknown_response("X")
        assert "Parcoursup" in out
        assert "ONISEP" in out
        assert "CIO" in out or "SCUIO" in out

    def test_near_match_inserted_between_opening_and_suggestion(self):
        out = format_unknown_response(
            missing_field="Master Droit Assas",
            near_match="J'ai trouvé un Master Droit Affaires à Bourgogne mais pas Assas.",
        )
        idx_opening = out.find("Je n'ai pas")
        idx_near = out.find("Bourgogne")
        idx_sugg = out.find("Parcoursup")
        assert idx_opening < idx_near < idx_sugg

    def test_suggestion_can_be_omitted(self):
        out = format_unknown_response("X", suggestion=None)
        assert "Parcoursup" not in out
        assert "ONISEP" not in out

    def test_double_newline_separator(self):
        """Les sections sont séparées par un double newline pour clarté UX."""
        out = format_unknown_response("X", near_match="proche Y")
        assert "\n\n" in out

    def test_no_invention_words_in_default_suggestion(self):
        """La suggestion ne doit jamais inviter à imaginer ou estimer."""
        forbidden = ["estime", "imagine", "approximativement", "environ"]
        for word in forbidden:
            assert word not in DEFAULT_SUGGESTION.lower()


class TestFormatOutOfScopeResponse:
    def test_default_post_bac_scope(self):
        out = format_out_of_scope_response()
        assert "post-bac" in out
        # commit d539c6d : rebranding OrientIA -> OrientAI dans les textes visibles.
        assert "OrientAI" in out

    def test_redirects_to_human_referral(self):
        out = format_out_of_scope_response()
        assert "Psy-EN" in out
        assert "ONISEP" in out
        assert "CIO" in out

    def test_custom_scope_string(self):
        out = format_out_of_scope_response("formations Bac+5 et insertion pro")
        assert "formations Bac+5 et insertion pro" in out



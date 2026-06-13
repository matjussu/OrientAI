"""Tests câblage MODE RÉCIT dans OrientIAPipeline (R1 1c-c, ordre #137).

Branche _prepare_narrative isolée, flag-gated. Invariants vérifiés :
- flag OFF -> branche jamais prise (banc 100q byte-identique).
- flag ON + question courte (non récit) -> branche jamais prise.
- flag ON + récit -> clarify_narrative + route_from_profile + requête forgée
  pilotent le retrieve ; criteria None (géo = boost) ; route_decision exposé.
- scope_classifier urgent -> court-circuit AVANT la branche récit (détresse
  R06/R07 escalade préservée, NON négociable).

_retrieve_and_filter est stubbé (pas d'index FAISS requis ici — le gate index
empirique est séparé, 1c-d).
"""
from __future__ import annotations

from unittest.mock import MagicMock

from src.agent.tools.profile_clarifier import Profile, ProfileClarifier
from src.rag.factory import make_production_pipeline
from src.rag.narrative_query import build_narrative_retrieval_query
from src.rag.narrative_route import route_from_profile
from src.rag.pipeline import OrientIAPipeline, _PreparedGenContext, _ShortCircuitResult


# Flags lourds désactivés : on teste juste le câblage du flag récit, pas les
# composants prod (validator/scope/router/golden font des side-effects).
_LIGHT = dict(
    enable_validator=False,
    enable_scope_classifier=False,
    enable_router_llm=False,
    enable_golden_qa=False,
    enable_post_process=False,
)


_LONG_RECIT = (
    "Bonjour, je suis en train de finir un master MIAGE a l'universite de Lille "
    "et je commence a postuler. Avant de signer, j'aimerais une idee realiste du "
    "salaire a l'embauche et savoir si le taux d'emploi des diplomes est bon. Je "
    "suis pret a etre mobile en France pour un bon poste. Quel salaire net puis-je "
    "viser en sortie de MIAGE Lille et quelles perspectives d'insertion ?"
)
_SHORT_Q = "C'est quoi un BUT informatique ?"


def _profile(**over) -> Profile:
    base = dict(
        age_group="etudiant_master",
        education_level="bac+5",
        intent_type="info_metier_specifique",
        sector_interest=["informatique"],
        region="Hauts-de-France",
        urgent_concern=False,
        confidence=0.8,
        notes=None,
        a_eviter=[],
        contraintes=[],
        mobilite="mobile en France",
        spans={"situation": "master MIAGE a l'universite de Lille", "cible": "insertion salaire"},
    )
    base.update(over)
    return Profile(**base)


def _pipeline(enable_narrative, clarifier, scope_classifier=None):
    p = OrientIAPipeline(
        client=MagicMock(),
        fiches=[],
        enable_narrative_mode=enable_narrative,
        narrative_clarifier=clarifier,
        scope_classifier=scope_classifier,
        enable_geo_coherence=False,
    )
    # Stub retrieve : on capture les args, pas d'index requis.
    captured: dict = {}

    def _stub_retrieve(**kw):
        captured.update(kw)
        return [{"id": "FAKE.1", "text": "fiche", "score": 1.0}]

    p._retrieve_and_filter = _stub_retrieve  # type: ignore[assignment]
    return p, captured


def _clarifier_returning(profile):
    c = MagicMock()
    c.clarify_narrative.return_value = profile
    return c


class TestNarrativeBranchTaken:
    def test_recit_triggers_clarify_and_route(self):
        prof = _profile()
        clar = _clarifier_returning(prof)
        p, captured = _pipeline(True, clar)

        prepared = p._prepare_for_generation(_LONG_RECIT, k=30, top_k_sources=10, criteria=None, history=None)

        assert isinstance(prepared, _PreparedGenContext)
        clar.clarify_narrative.assert_called_once_with(_LONG_RECIT)
        # route_from_profile pilote le retrieve
        expected_route = route_from_profile(prof)
        assert captured["route_decision"].sub_indexes == expected_route.sub_indexes
        # géo = boost : aucun filtre dur
        assert captured["criteria"] is None
        # requête forgée déterministe utilisée pour le retrieve (pas le récit brut)
        assert captured["question"] == build_narrative_retrieval_query(prof, _LONG_RECIT)
        assert captured["question"] != _LONG_RECIT

    def test_exposes_profile_and_route_markers(self):
        prof = _profile()
        p, _ = _pipeline(True, _clarifier_returning(prof))
        p._prepare_for_generation(_LONG_RECIT, k=30, top_k_sources=10, criteria=None, history=None)
        assert p.last_narrative_profile is prof
        assert p.last_router_result is not None
        assert p.last_router_result.sub_indexes == route_from_profile(prof).sub_indexes

    def test_top_served_from_retrieve(self):
        prof = _profile()
        p, _ = _pipeline(True, _clarifier_returning(prof))
        prepared = p._prepare_for_generation(_LONG_RECIT, k=30, top_k_sources=10, criteria=None, history=None)
        assert prepared.top and prepared.top[0]["id"] == "FAKE.1"
        assert prepared.criteria is None


class TestNarrativeBranchSkipped:
    def test_flag_off_skips_narrative(self):
        clar = _clarifier_returning(_profile())
        p, _ = _pipeline(False, clar)
        # router_llm None + intent non factuel -> path classique passe par le stub retrieve
        p._prepare_for_generation(_LONG_RECIT, k=30, top_k_sources=10, criteria=None, history=None)
        clar.clarify_narrative.assert_not_called()

    def test_short_question_skips_narrative_even_flag_on(self):
        clar = _clarifier_returning(_profile())
        p, _ = _pipeline(True, clar)
        p._prepare_for_generation(_SHORT_Q, k=30, top_k_sources=10, criteria=None, history=None)
        clar.clarify_narrative.assert_not_called()


class TestScopePrecedenceOverNarrative:
    def test_urgent_scope_shortcircuits_before_narrative(self):
        # R06/R07 : la détresse DOIT escalader avant tout traitement récit.
        scope = MagicMock()
        scope_res = MagicMock()
        scope_res.label = "urgent"
        scope_res.pre_written_response = "Réponse d'écoute + 3114"
        scope.classify.return_value = scope_res

        clar = _clarifier_returning(_profile())
        p, _ = _pipeline(True, clar, scope_classifier=scope)

        prepared = p._prepare_for_generation(_LONG_RECIT, k=30, top_k_sources=10, criteria=None, history=None)

        assert isinstance(prepared, _ShortCircuitResult)
        assert prepared.reason == "scope_urgent"
        clar.clarify_narrative.assert_not_called()


class TestFactoryNarrativeFlag:
    def test_off_by_default(self, monkeypatch):
        monkeypatch.delenv("ORIENTIA_NARRATIVE_MODE", raising=False)
        p = make_production_pipeline(MagicMock(), [], **_LIGHT)
        assert p.enable_narrative_mode is False
        assert p.narrative_clarifier is None

    def test_explicit_on_creates_clarifier(self, monkeypatch):
        monkeypatch.delenv("ORIENTIA_NARRATIVE_MODE", raising=False)
        p = make_production_pipeline(MagicMock(), [], enable_narrative_mode=True, **_LIGHT)
        assert p.enable_narrative_mode is True
        assert isinstance(p.narrative_clarifier, ProfileClarifier)

    def test_env_var_enables(self, monkeypatch):
        monkeypatch.setenv("ORIENTIA_NARRATIVE_MODE", "1")
        p = make_production_pipeline(MagicMock(), [], **_LIGHT)
        assert p.enable_narrative_mode is True
        assert isinstance(p.narrative_clarifier, ProfileClarifier)

    def test_explicit_false_overrides_env(self, monkeypatch):
        monkeypatch.setenv("ORIENTIA_NARRATIVE_MODE", "1")
        p = make_production_pipeline(MagicMock(), [], enable_narrative_mode=False, **_LIGHT)
        assert p.enable_narrative_mode is False

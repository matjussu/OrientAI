"""Tests src/rag/narrative_route.py — route_from_profile (R1 1c, ordre #137).

En MODE RÉCIT, le profil (extrait par ProfileClarifier.clarify_narrative)
REMPLACE le RouterLLM : `route_from_profile` produit un RouteDecision de
façon DÉTERMINISTE (zéro LLM, donc zéro 3e appel séquentiel = gain latence).

Invariants clés (décision Jarvis ordre #137) :
- recall-first : récits multi-facettes -> on n'exclut rien par filtre dur.
- géo = BOOST jamais filtre dur : `criteria` reste None même quand le profil
  a une région (R11 "mobile France" + R04 géo-absente l'exigent). Le signal
  géo passe par la requête corpus-aware (1c-b), pas par apply_metadata_filter.
"""
from __future__ import annotations

from src.agent.tools.profile_clarifier import Profile
from src.rag.narrative_route import route_from_profile
from src.rag.router_llm import RouteDecision, SUB_INDEX_NAMES


def _profile(**over) -> Profile:
    """Profil de base réaliste (récit), surchargeable par champ."""
    base = dict(
        age_group="etudiant_l1_l3",
        education_level="bac+2",
        intent_type="reorientation_etude",
        sector_interest=[],
        region=None,
        urgent_concern=False,
        confidence=0.8,
        notes=None,
        a_eviter=[],
        contraintes=[],
        mobilite=None,
        spans={},
    )
    base.update(over)
    return Profile(**base)


class TestRouteFromProfileBasics:
    def test_returns_route_decision(self):
        assert isinstance(route_from_profile(_profile()), RouteDecision)

    def test_sub_indexes_subset_of_canonical(self):
        rd = route_from_profile(_profile(sector_interest=["info"], contraintes=["alternance"]))
        assert set(rd.sub_indexes) <= set(SUB_INDEX_NAMES)
        # déduplication / ordre canonique préservés
        assert rd.sub_indexes == [s for s in SUB_INDEX_NAMES if s in set(rd.sub_indexes)]

    def test_floor_sub_indexes_always_present(self):
        # Tout récit d'orientation -> formations (la fiche) + statistiques
        # (insertion/prospects), socle minimal recall.
        rd = route_from_profile(_profile())
        assert "formations" in rd.sub_indexes
        assert "statistiques" in rd.sub_indexes


class TestRouteFromProfileSignals:
    def test_sector_interest_adds_metiers(self):
        rd = route_from_profile(_profile(sector_interest=["informatique", "data"]))
        assert "metiers" in rd.sub_indexes

    def test_no_sector_no_metier_intent_omits_metiers(self):
        rd = route_from_profile(_profile(sector_interest=[], intent_type="reorientation_etude"))
        assert "metiers" not in rd.sub_indexes

    def test_metier_intent_adds_metiers(self):
        rd = route_from_profile(_profile(sector_interest=[], intent_type="info_metier_specifique"))
        assert "metiers" in rd.sub_indexes

    def test_alternance_constraint_adds_aides(self):
        rd = route_from_profile(_profile(contraintes=["alternance"]))
        assert "aides_territoires" in rd.sub_indexes

    def test_financement_constraint_adds_aides(self):
        rd = route_from_profile(_profile(contraintes=["rémunéré pendant la formation"]))
        assert "aides_territoires" in rd.sub_indexes

    def test_no_financing_constraint_omits_aides(self):
        rd = route_from_profile(_profile(contraintes=["études courtes"]))
        assert "aides_territoires" not in rd.sub_indexes


class TestRouteFromProfileGeoIsBoostNotFilter:
    def test_region_never_produces_hard_filter(self):
        # INVARIANT DUR : un profil avec région ne doit JAMAIS créer de
        # criteria.region (filtre dur). Géo = boost via requête (1c-b).
        rd = route_from_profile(_profile(region="Hauts-de-France"))
        assert rd.criteria is None or rd.criteria.region is None

    def test_mobile_candidate_no_region_filter(self):
        rd = route_from_profile(_profile(region="Hauts-de-France", mobilite="mobile en France"))
        assert rd.criteria is None or rd.criteria.region is None
        assert rd.hardlock_region_strict is False


class TestRouteFromProfileNoLocks:
    def test_no_domain_lock(self):
        rd = route_from_profile(_profile(sector_interest=["info"]))
        assert not rd.domain_lock

    def test_no_hardlocks(self):
        rd = route_from_profile(_profile(region="Bretagne", sector_interest=["info"]))
        assert rd.hardlock_region_strict is False
        assert rd.hardlock_domain_strict is False

    def test_no_refusal_at_routing(self):
        # Le refus (urgent/out-of-scope) est géré par le scope_classifier en
        # amont, pas par le routing récit.
        rd = route_from_profile(_profile())
        assert rd.refusal_reason is None

    def test_top_k_bumped_for_recits(self):
        # Récits multi-facettes -> plus de sources servies au générateur.
        rd = route_from_profile(_profile())
        assert rd.top_k_override is not None and rd.top_k_override >= 10


class TestRouteFromProfileConfidence:
    def test_real_profile_high_confidence(self):
        rd = route_from_profile(_profile(confidence=0.85))
        assert rd.confidence >= 0.7
        assert rd.is_fallback is False

    def test_fallback_profile_all_subindexes(self):
        # Profil de repli (clarify_narrative a échoué : confidence 0.0).
        # On maximise le recall -> les 4 sub-index, confidence basse.
        fb = _profile(
            age_group="other_or_unknown",
            education_level="unknown",
            intent_type="other",
            confidence=0.0,
            notes="narrative_fallback:no_tool_call",
        )
        rd = route_from_profile(fb)
        assert set(rd.sub_indexes) == set(SUB_INDEX_NAMES)
        assert rd.confidence < 0.6


class TestRouteFromProfileR11Gate:
    def test_r11_surfaces_formations_and_stats(self):
        # R11 : master MIAGE Lille, mobile France, question insertion/salaire.
        # Prérequis du gate retrieval : formations (la fiche MIAGE) ET
        # statistiques (salaire/insertion) interrogées, ET aucun filtre région
        # (candidat mobile -> ne pas exclure les fiches hors-Lille).
        r11 = _profile(
            age_group="etudiant_master",
            education_level="bac+5",
            intent_type="info_metier_specifique",
            sector_interest=[],
            region="Hauts-de-France",
            mobilite="mobile en France",
            confidence=0.8,
        )
        rd = route_from_profile(r11)
        assert "formations" in rd.sub_indexes
        assert "statistiques" in rd.sub_indexes
        assert rd.criteria is None or rd.criteria.region is None

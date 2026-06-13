"""Tests src/rag/narrative_query.py — build_narrative_retrieval_query (R1 1c-b).

Forge DÉTERMINISTE d'une requête de retrieval focalisée depuis le profil récit
(query_reformuler figé en code, zéro LLM). Règle le problème de DILUTION : on
n'embarque pas les 300+ chars du récit brut, mais les facettes discriminantes.

Invariant dur : `a_eviter` n'entre JAMAIS dans la requête (sinon on ferait
remonter les fiches rejetées). C'est un signal de génération, pas de retrieval.
"""
from __future__ import annotations

from src.agent.tools.profile_clarifier import Profile
from src.rag.narrative_query import _region_from_mobilite, build_narrative_retrieval_query


def _profile(**over) -> Profile:
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


class TestExclusions:
    def test_a_eviter_terms_never_in_query(self):
        q = build_narrative_retrieval_query(
            _profile(sector_interest=["developpement", "data"], a_eviter=["commercial", "vente"]),
            "récit original",
        )
        low = q.lower()
        assert "commercial" not in low
        assert "vente" not in low

    def test_a_eviter_span_never_in_query(self):
        q = build_narrative_retrieval_query(
            _profile(
                sector_interest=["data"],
                spans={"a_eviter": "je ne veux surtout pas finir dans la vente"},
            ),
            "récit original",
        )
        assert "vente" not in q.lower()

    def test_mobilite_not_a_retrieval_term(self):
        # "mobile en France" n'est pas un terme de recherche -> pas dans la requête.
        q = build_narrative_retrieval_query(
            _profile(sector_interest=["informatique"], mobilite="mobile en France"),
            "récit",
        )
        assert "mobile" not in q.lower()


class TestInclusions:
    def test_sector_interest_included(self):
        q = build_narrative_retrieval_query(_profile(sector_interest=["informatique", "data"]), "r")
        low = q.lower()
        assert "informatique" in low and "data" in low

    def test_region_included_as_boost(self):
        q = build_narrative_retrieval_query(
            _profile(sector_interest=["info"], region="Hauts-de-France"), "r"
        )
        assert "hauts-de-france" in q.lower()

    def test_cible_and_situation_spans_included(self):
        q = build_narrative_retrieval_query(
            _profile(
                spans={"cible": "data analyst", "situation": "BUT GEA"},
            ),
            "r",
        )
        low = q.lower()
        assert "data analyst" in low
        assert "but gea" in low

    def test_alternance_constraint_adds_keyword(self):
        q = build_narrative_retrieval_query(
            _profile(sector_interest=["numerique"], contraintes=["alternance"]), "r"
        )
        assert "alternance" in q.lower()


class TestFocus:
    def test_query_shorter_than_long_recit(self):
        # La requête forgée doit être FOCALISÉE, pas le récit brut de 300+ chars.
        recit = (
            "Bonjour, je suis en deuxieme annee de licence de droit a Lille mais "
            "je me rends compte que ca ne me passionne pas, je code le soir, "
            "j'adore les donnees, je voudrais me reorienter, mais je ne veux pas "
            "finir dans le commercial." * 2
        )
        q = build_narrative_retrieval_query(
            _profile(
                sector_interest=["developpement", "donnees"],
                region="Hauts-de-France",
                spans={"cible": "reorientation developpement data"},
                a_eviter=["commercial"],
            ),
            recit,
        )
        assert len(q) < len(recit)

    def test_deterministic(self):
        p = _profile(sector_interest=["info", "data"], region="Bretagne", contraintes=["alternance"])
        assert build_narrative_retrieval_query(p, "r") == build_narrative_retrieval_query(p, "r")


class TestFallback:
    def test_empty_profile_falls_back_to_question(self):
        # Profil de repli sans signal -> on retombe sur la question brute
        # (mieux que retrieve sur une requête vide).
        fb = _profile(
            age_group="other_or_unknown",
            education_level="unknown",
            intent_type="other",
            sector_interest=[],
            confidence=0.0,
        )
        q = build_narrative_retrieval_query(fb, "ceci est le récit original brut")
        assert q.strip() == "ceci est le récit original brut"

    def test_no_signal_no_question_returns_empty_safe(self):
        fb = _profile(sector_interest=[], confidence=0.0)
        q = build_narrative_retrieval_query(fb, "")
        assert isinstance(q, str)


class TestR11GatePrerequisite:
    def test_r11_query_contains_miage_and_lille(self):
        # Prérequis du gate : la requête forgée pour R11 doit porter les termes
        # discriminants MIAGE + Lille (via les spans) pour faire remonter la fiche.
        r11 = _profile(
            age_group="etudiant_master",
            education_level="bac+5",
            intent_type="info_metier_specifique",
            sector_interest=[],
            region="Hauts-de-France",
            mobilite="mobile en France",
            spans={
                "situation": "master MIAGE a l'universite de Lille",
                "cible": "insertion salaire emploi",
            },
        )
        q = build_narrative_retrieval_query(r11, "récit R11").lower()
        assert "miage" in q
        assert "lille" in q


class TestGeoFromMobilite:
    """Fallback géo déterministe (1d post-lock) : dériver la région depuis la
    ville citée en mobilité quand `region` n'est pas peuplée -> alimente le
    boost. Ne sur-contraint JAMAIS un candidat mobile non-localisé."""

    def test_city_in_mobilite_derives_region(self):
        assert _region_from_mobilite("rester à Bordeaux") == "nouvelle-aquitaine"
        assert _region_from_mobilite("rester à Lyon") == "auvergne-rhône-alpes"
        assert _region_from_mobilite("rester à Lille") == "hauts-de-france"
        assert _region_from_mobilite("rester à Nantes ou proximité") == "pays de la loire"

    def test_mobile_en_france_yields_no_region(self):
        # R11 : « mobile en France » n'est PAS une ville -> pas de boost géo
        # fabriqué (le candidat mobile garde tout le corpus).
        assert _region_from_mobilite("mobile en France") == ""
        assert _region_from_mobilite("prêt à bouger partout") == ""

    def test_word_boundary_no_false_positive(self):
        # « pau » ne doit pas matcher dans « paul » ; bordure de mot.
        assert _region_from_mobilite("je m'appelle Paul") == ""

    def test_build_query_derives_region_when_region_none(self):
        p = _profile(sector_interest=["sciences"], region=None, mobilite="rester à Bordeaux")
        q = build_narrative_retrieval_query(p).lower()
        assert "nouvelle-aquitaine" in q

    def test_explicit_region_takes_precedence(self):
        # Si `region` est déjà extraite, on ne la ré-dérive pas depuis mobilite.
        p = _profile(sector_interest=["info"], region="Bretagne", mobilite="rester à Lyon")
        q = build_narrative_retrieval_query(p)
        assert "Bretagne" in q
        assert "auvergne" not in q.lower()

    def test_mobile_candidate_query_has_no_region(self):
        p = _profile(sector_interest=["MIAGE"], region=None, mobilite="mobile en France")
        q = build_narrative_retrieval_query(p).lower()
        for reg in ("nouvelle-aquitaine", "auvergne", "hauts-de-france", "île-de-france"):
            assert reg not in q

    def test_mobilite_none_is_safe(self):
        p = _profile(sector_interest=["info"], region=None, mobilite=None)
        q = build_narrative_retrieval_query(p)
        assert q == "info"

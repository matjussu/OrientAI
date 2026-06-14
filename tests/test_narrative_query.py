"""Tests src/rag/narrative_query.py — build_narrative_retrieval_query (R1 1c-b).

Forge DÉTERMINISTE d'une requête de retrieval focalisée depuis le profil récit
(query_reformuler figé en code, zéro LLM). Règle le problème de DILUTION : on
n'embarque pas les 300+ chars du récit brut, mais les facettes discriminantes.

Invariant dur : `a_eviter` n'entre JAMAIS dans la requête (sinon on ferait
remonter les fiches rejetées). C'est un signal de génération, pas de retrieval.
"""
from __future__ import annotations

from src.agent.tools.profile_clarifier import Profile
from src.rag.narrative_query import (
    _region_from_mobilite,
    build_narrative_clarifier_input,
    build_narrative_retrieval_query,
)


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


class TestBuildClarifierInput:
    """R2 FORK B : accumulation profil par concaténation des tours USER."""

    def test_turn1_no_history_is_question_only(self):
        # Comportement 1c inchangé au tour 1.
        assert build_narrative_clarifier_input("mon récit initial") == "mon récit initial"
        assert build_narrative_clarifier_input("mon récit", None) == "mon récit"
        assert build_narrative_clarifier_input("mon récit", []) == "mon récit"

    def test_concatenates_user_turns_in_order(self):
        history = [
            {"role": "user", "content": "je suis en terminale, j'aime les sciences"},
            {"role": "assistant", "content": "voici des pistes scientifiques ..."},
        ]
        out = build_narrative_clarifier_input("et si je reste à Lyon ?", history)
        assert out == (
            "je suis en terminale, j'aime les sciences\n\net si je reste à Lyon ?"
        )

    def test_assistant_turns_excluded(self):
        history = [
            {"role": "user", "content": "tour user 1"},
            {"role": "assistant", "content": "REPONSE_ASSISTANT_NE_DOIT_PAS_APPARAITRE"},
            {"role": "user", "content": "tour user 2"},
        ]
        out = build_narrative_clarifier_input("question courante", history)
        assert "REPONSE_ASSISTANT" not in out
        assert out == "tour user 1\n\ntour user 2\n\nquestion courante"

    def test_malformed_history_no_crash(self):
        history = ["pas un dict", {"role": "user", "content": None}, {"role": "user"}, {"content": "x"}]
        out = build_narrative_clarifier_input("q", history)
        assert out == "q"

    def test_never_empty_if_question_present(self):
        assert build_narrative_clarifier_input("q", [{"role": "assistant", "content": "x"}]) == "q"


# --- Fix A (ordre 1926) : extraction des options comparées + merge round-robin ---

from src.rag.narrative_query import extract_comparison_options
from src.rag.pipeline import _round_robin_dedup, _fiche_key


def test_extract_options_entre_et():
    assert extract_comparison_options(
        "j'hesite entre une prepa et un BUT informatique, je sais pas") == ["prepa", "but informatique"]


def test_extract_options_a_la_fois_en():
    assert extract_comparison_options(
        "admise a la fois en BUT GEA et en BTS Comptabilite-Gestion. Lequel ?"
    ) == ["but gea", "bts comptabilite-gestion"]


def test_extract_options_mieux_entre():
    opts = extract_comparison_options(
        "qu'est-ce qui serait le mieux entre ecole de commerce et BUT pour viser le marketing ?")
    assert opts == ["ecole de commerce", "but"]


def test_extract_options_ignores_situation_en():
    # Ne doit PAS attraper le « en » de la situation (« en terminale … »).
    opts = extract_comparison_options(
        "Je suis en terminale STMG a Lyon, admise a la fois en BUT GEA et en BTS CG")
    assert "terminale" not in " ".join(opts)
    assert opts == ["but gea", "bts cg"]


def test_extract_options_none_when_not_comparison():
    assert extract_comparison_options("je suis perdu, aucune idee de ce que je veux faire") == []


def test_round_robin_guarantees_each_pool_represented():
    a = [{"fiche": {"nom": "A1"}}, {"fiche": {"nom": "A2"}}]
    b = [{"fiche": {"nom": "B1"}}, {"fiche": {"nom": "B2"}}]
    base = [{"fiche": {"nom": "C1"}}]
    top = _round_robin_dedup([a, b, base], target=4)
    noms = [_fiche_key(x)[0] for x in top]
    assert "a1" in noms and "b1" in noms  # chaque option représentée tôt
    assert len(top) == 4


def test_round_robin_dedups_across_pools():
    shared = {"fiche": {"nom": "X", "etablissement": "U", "ville": "V"}}
    a = [shared, {"fiche": {"nom": "A1"}}]
    b = [dict(shared), {"fiche": {"nom": "B1"}}]  # même fiche que a[0]
    top = _round_robin_dedup([a, b], target=10)
    keys = [_fiche_key(x) for x in top]
    assert len(keys) == len(set(keys))  # pas de doublon

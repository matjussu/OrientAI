"""Tests TDD — enrichissement ROME 4.0 (passerelles + RIASEC + transitions) fact_card.

Ordre 1402. fact_card UNIQUEMENT (jamais fiche_to_text, ADR-033 Run 5). Déterministe.
"""
import re
from pathlib import Path

import pytest

from src.collect.rome_mobilite import (
    parse_rome_enrichment,
    attach_rome_enrichment,
    _transitions,
    _riasec_label,
)

ZIP = Path("data/raw/rome_4_0.zip")


# ---------- helpers purs ----------

def test_transitions_skip_emploi_blanc():
    # "Emploi Blanc" = neutre -> non surfacé (pas de bruit).
    assert _transitions({"transition_eco": "Emploi Blanc"}) == []


def test_transitions_vert_et_flags_O():
    out = _transitions({"transition_eco": "Emploi Vert", "transition_num": "O",
                        "emploi_reglemente": "O", "emploi_cadre": "N", "transition_demo": ""})
    assert "Emploi Vert" in out
    assert "concerné par la transition numérique" in out
    assert "métier réglementé" in out
    assert "emploi cadre" not in out  # 'N' -> pas surfacé


def test_riasec_label():
    assert _riasec_label("R", "I") == "Réaliste / Investigateur"
    assert _riasec_label("R", "") == "Réaliste"
    assert _riasec_label("R", "R") == "Réaliste"   # pas de doublon majeur/mineur
    assert _riasec_label("", "") is None


# ---------- attach ----------

def test_attach_pose_les_champs_sur_metier_seulement():
    fiches = [{"source": "rome_api_v4", "code_rome": "A1101"},
              {"source": "parcoursup", "code_rome": "A1101"}]
    enr = {"A1101": {"passerelles": ["Métier X"], "riasec": "Réaliste",
                     "transitions": ["emploi cadre"]}}
    n = attach_rome_enrichment(fiches, enr)
    assert n == 1
    assert fiches[0]["rome_passerelles"] == ["Métier X"]
    assert fiches[0]["rome_riasec"] == "Réaliste"
    assert fiches[0]["rome_transitions"] == ["emploi cadre"]
    assert "rome_passerelles" not in fiches[1]  # non-métier intact (pas de pollution)


def test_attach_sans_match_reste_intact():
    fiches = [{"source": "rome_api_v4", "code_rome": "ZZZZ"}]
    attach_rome_enrichment(fiches, {})
    assert "rome_passerelles" not in fiches[0]


# ---------- parse (intégration sur le vrai ZIP) ----------

@pytest.mark.skipif(not ZIP.exists(), reason="rome_4_0.zip absent")
def test_parse_integration_a1101():
    enr = parse_rome_enrichment(ZIP)
    assert "A1101" in enr
    rec = enr["A1101"]
    assert rec.get("passerelles") and len(rec["passerelles"]) >= 4
    # passerelles = LIBELLÉS humains, pas des codes ROME nus
    assert not re.fullmatch(r"[A-Z]\d{4}", rec["passerelles"][0])
    assert rec.get("riasec")  # A1101 a un profil RIASEC


# ---------- surfaçage fact_card ----------

def test_factcard_surface_les_champs_rome():
    from src.rag.fact_card import fiche_to_fact_card
    f = {"source": "rome_api_v4", "libelle_metier": "Boulanger", "code_rome": "D1102",
         "rome_passerelles": ["Chef de rayon", "Pizzaïolo"], "rome_riasec": "Réaliste",
         "rome_transitions": ["métier réglementé"]}
    card = fiche_to_fact_card(f, "S1")
    assert card.passerelles == ["Chef de rayon", "Pizzaïolo"]
    assert card.riasec == "Réaliste"
    assert card.transitions == ["métier réglementé"]
    d = card.to_dict()
    assert "passerelles" in d and "riasec" in d and "transitions" in d


def test_factcard_sans_rome_n_expose_rien():
    from src.rag.fact_card import fiche_to_fact_card
    card = fiche_to_fact_card({"source": "parcoursup", "nom": "BTS X"}, "S1")
    d = card.to_dict()
    assert "passerelles" not in d and "riasec" not in d and "transitions" not in d

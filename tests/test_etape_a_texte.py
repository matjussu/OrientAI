"""Étape A : texte lu par le modèle pour une fiche Parcoursup, et contrôles qui le gardent.

Falsification (règle 9) : les contrôles sont joués sur les textes RÉELLEMENT produits par le
`fiche_to_text` de main (89e0f27) sur les mêmes fiches, capturés dans la fixture. Ils doivent
y trouver chacun des défauts mesurés le 23/09/2026 ; un contrôle qui reste muet sur ces textes
ne prouverait rien sur les nouveaux.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest

from src.eval.donnee.controles import controler
from src.rag.embeddings import _format_insertion_pro, _format_profil_admis, fiche_to_text
from src.rag.texte_parcoursup import DEFINITIONS

FIXTURES = json.loads((Path(__file__).parent / "fixtures/etape_a/fiches.json").read_text(encoding="utf-8"))
APRES = FIXTURES["apres"]


def test_fixture_non_vide():
    assert len(APRES) >= 10 and len(FIXTURES["textes_avant"]) >= 9


@pytest.mark.parametrize("cod", sorted(APRES))
def test_nouveau_texte_sans_defaut(cod):
    fiche = APRES[cod]
    assert controler(fiche, fiche_to_text(fiche)) == []


def test_controles_mordent_sur_le_texte_de_main():
    """Chaque défaut connu est retrouvé sur au moins une fiche réelle de l'ancien texte."""
    trouves = Counter()
    for cod, texte in FIXTURES["textes_avant"].items():
        trouves.update(controler(FIXTURES["avant"][cod], texte))
    for defaut in (
        "repartition_nommee_taux_acces",
        "meme_academie_nommee_ile_de_france",
        "insersup_attribue_a_inserjeunes",
        "option_pass_non_dite",
        "ville_non_normalisee",
        "taux_acces_sans_definition",
        "session_non_dite",
    ):
        assert trouves[defaut] > 0, defaut


def test_texte_but_informatique_complet():
    t = fiche_to_text(APRES["7596"])
    assert "Type de formation : BUT (bachelor universitaire de technologie), spécialité Informatique" in t
    assert "Admission (Parcoursup, session 2025) : taux d'accès 34 % ; 96 places" in t
    assert DEFINITIONS["taux_acces"] in t
    assert "Évolution Parcoursup : session 2023" in t
    assert "(académie de Clermont-Ferrand)" in t
    assert "Fiche Parcoursup : https://dossierappel.parcoursup.fr/" in t
    assert t.rstrip().endswith("(SIES)")


def test_pass_nomme_son_option():
    t = fiche_to_text(APRES["36433"])
    assert "PASS (parcours d'accès spécifique santé), option sciences infirmières" in t


def test_pass_cree_a4_nomme_son_option_et_herite():
    fiche = APRES["29180"]
    assert fiche["provenance"]["herite_de"]["cod_aff_form"]
    assert "option Droit (enseignement à distance)" in fiche_to_text(fiche)


def test_ile_de_france_trois_academies_reunies():
    t = fiche_to_text(APRES["9517"])
    assert "Paris" in t and "arrondissement" in t
    assert "les académies de Paris, Créteil et Versailles sont comptées comme une seule" in t


def test_elision_academie():
    assert "(académie d'Aix-Marseille)" in fiche_to_text(APRES["2623"])


def test_insersup_source_granularite_definition():
    t = fiche_to_text(APRES["2139"])
    assert "Inserjeunes" not in t
    assert "InserSup, ministère de l'Enseignement supérieur ; diplômés 2024 ; médiane régionale" in t
    assert "part des diplômés en emploi salarié en France" in t


def test_taux_absent_non_ecrit_mais_defini_si_historique():
    fiche = APRES["22946"]
    assert fiche.get("taux_acces_parcoursup_2025") is None
    t = fiche_to_text(fiche)
    assert "Admission (Parcoursup, session 2025) : taux d'accès" not in t
    assert DEFINITIONS["taux_acces"] in t  # le taux 2023-2024 de l'évolution est défini


def test_repartition_mentions_somme_100_avec_felicitations():
    t = fiche_to_text(APRES["36433"])
    assert "33 % mention très bien avec félicitations" in t


def test_profil_groupe_tout_zero_omis():
    assert _format_profil_admis({"bac_type_pct": {"general": 0.0, "techno": 0.0, "pro": 0.0}}) is None


def test_inserjeunes_cfa_garde_son_libelle():
    """Non-régression des autres sources : un vrai bloc CFA reste étiqueté CFA."""
    out = _format_insertion_pro({"source": "inserjeunes_cfa", "annee": "2023", "taux_emploi_6m": 0.8})
    assert out.startswith("Insertion apprentissage (Inserjeunes CFA, 2023)")


def test_fiche_non_parcoursup_inchangee():
    fiche = {"source": "monmaster", "nom": "M", "etablissement": "E", "ville": "V",
             "taux_admission": 0.2, "n_candidats_pp": 100}
    t = fiche_to_text(fiche)
    assert t.startswith("Formation : M | Établissement : E | Ville : V")
    assert "Définitions" not in t and "Source : Parcoursup" not in t

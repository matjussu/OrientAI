"""Tests src/collect/insersup_salary.py (C2b — salaire InserSup, order 2026-06-11).

Join par-formation : (établissement|UAI, bucket de type, libellé canonique).
"""
from __future__ import annotations

from src.collect.insersup_salary import (
    _canon_formation,
    _type_bucket,
    attach_insersup_salaries,
    build_salary_index,
    match_fiche_salary,
)


_CSV_COLS = [
    "Établissement", "Code UAI de l'établissement", "type_diplome",
    "Domaine disciplinaire", "Libellé du diplôme", "Genre", "Nationalité",
    "Régime d'inscription", "Obtention du diplôme", "Promotion",
    "12-Salaire mensuel net médian en équivalent temps plein - 12 mois après le diplôme",
    "30-Salaire mensuel net médian en équivalent temps plein - 30 mois après le diplôme",
]


def _write_csv(path, rows):
    import csv
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=_CSV_COLS, delimiter=";")
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in _CSV_COLS})


def _row(genre="ensemble", nat="ensemble", regime="ensemble", obt="ensemble", sal="2000"):
    return {
        "Établissement": "Université X", "Code UAI de l'établissement": "0751717J",
        "type_diplome": "Master LMD", "Domaine disciplinaire": "Sciences",
        "Libellé du diplôme": "Acoustique", "Genre": genre, "Nationalité": nat,
        "Régime d'inscription": regime, "Obtention du diplôme": obt, "Promotion": "2022",
        "12-Salaire mensuel net médian en équivalent temps plein - 12 mois après le diplôme": sal,
    }


def test_build_salary_index_keeps_only_ensemble_slice(tmp_path):
    """Verrou audit Jarvis : InserSup ventile par Genre/Nationalité/Régime/Obtention.
    Le parser ne doit retenir QUE la tranche agrégat (tout == 'ensemble'), sinon une
    valeur d'une sous-population (ex hommes) pourrait s'attacher au mauvais grain."""
    csv_path = tmp_path / "insersup.csv"
    _write_csv(csv_path, [
        _row(sal="2000"),                       # ensemble -> retenu
        _row(genre="homme", sal="2200"),        # sous-population -> ignoré
        _row(nat="français", sal="2300"),       # sous-population -> ignoré
        _row(regime="apprentissage", sal="2400"),
        _row(obt="diplômé", sal="2500"),
    ])
    index = build_salary_index(csv_path)
    rec = index["by_name_disc"].get(("universite x", "master", "acoustique"))
    assert rec is not None
    assert rec["salaire"] == 2000  # la valeur ENSEMBLE, pas une sous-population
    assert index["metrics"]["ambiguities_same_key_same_promo"] == 0  # les autres tranches sont filtrées, pas comptées comme ambiguës


def _rec(salaire, etab="Université X", libelle="Acoustique", cohorte="2022"):
    return {"salaire": salaire, "salaire_30m": None, "horizon": "12m", "cohorte": cohorte,
            "_promo": 2022, "etab": etab, "type": "Master LMD", "discipline": "Sciences",
            "libelle": libelle, "uai": "0751717J"}


def _index(name=None, uai=None):
    return {"by_name_disc": name or {}, "by_uai_type": uai or {}, "metrics": {}}


# --- canonicalisation libellé (symétrique fiche/InserSup) ---


def test_canon_formation_strips_suffix_and_type_prefix():
    assert _canon_formation("Master Acoustique — Parcours B") == "acoustique"
    assert _canon_formation("Acoustique") == "acoustique"
    assert _canon_formation("BUT Génie civil - construction durable") == "genie civil"
    # mentions distinctes ne se confondent pas
    assert _canon_formation("Acoustique et musicologie") != _canon_formation("Acoustique")


# --- bucket precision : pas de match sémantiquement faux ---


def test_type_bucket_master_distinct_from_diplome_vise():
    assert _type_bucket("Master LMD") == "master"
    assert _type_bucket("Master MEEF") == "master"
    assert _type_bucket("Licence professionnelle") == "licence_pro"
    assert _type_bucket("Bachelor universitaire de technologie") == "but"
    assert _type_bucket("Diplôme gradé ou visé management niveau bac+5") is None


# --- match MonMaster par nom établissement + libellé canonique ---


def test_match_monmaster_by_name_and_libelle():
    idx = _index(name={("universite x", "master", "acoustique"): _rec(1850)})
    fiche = {"source": "monmaster", "etablissement": "Université X",
             "nom": "Acoustique — Parcours recherche", "niveau": "bac+5"}
    rec, method = match_fiche_salary(fiche, idx)
    assert method == "name_libelle"
    assert rec["salaire"] == 1850


def test_match_monmaster_wrong_formation_no_match():
    idx = _index(name={("universite x", "master", "acoustique"): _rec(1850)})
    fiche = {"source": "monmaster", "etablissement": "Université X", "nom": "Mathématiques"}
    rec, method = match_fiche_salary(fiche, idx)
    assert rec is None and method == "none"


# --- match parcoursup supérieur par UAI + libellé canonique ---


def test_match_parcoursup_by_uai_and_libelle():
    idx = _index(uai={("0751717J", "but", "genie civil"): _rec(1700, libelle="Génie civil")})
    fiche = {"source": "parcoursup", "cod_uai": "0751717J",
             "nom": "BUT Génie civil", "type_diplome": ""}
    rec, method = match_fiche_salary(fiche, idx)
    assert method == "uai_libelle"
    assert rec["salaire"] == 1700


# --- attach : enrichit + n'écrase pas + idempotent + trace cohorte ---


def test_attach_enriches_labels_net_source_and_traces_cohorte():
    idx = _index(name={("universite x", "master", "acoustique"): _rec(1850, cohorte="2022")})
    fiches = [{"source": "monmaster", "etablissement": "Université X", "nom": "Acoustique"}]
    metrics = attach_insersup_salaries(fiches, idx)
    ip = fiches[0]["insertion_pro"]
    assert ip["salaire_median_embauche"] == 1850
    assert ip["salaire_net"] is True
    assert ip["salaire_source"] == "insersup"
    assert ip["salaire_cohorte"] == "2022"   # année tracée par fiche (citation)
    assert metrics["n_enriched"] == 1


def test_attach_does_not_clobber_existing_salary():
    idx = _index(name={("universite x", "master", "acoustique"): _rec(1850)})
    fiches = [{"source": "monmaster", "etablissement": "Université X", "nom": "Acoustique",
               "insertion_pro": {"salaire_median_embauche": 9999}}]
    attach_insersup_salaries(fiches, idx)
    assert fiches[0]["insertion_pro"]["salaire_median_embauche"] == 9999


def test_attach_idempotent():
    idx = _index(name={("universite x", "master", "acoustique"): _rec(1850)})
    fiches = [{"source": "monmaster", "etablissement": "Université X", "nom": "Acoustique"}]
    attach_insersup_salaries(fiches, idx)
    m2 = attach_insersup_salaries(fiches, idx)
    assert m2["n_enriched"] == 0
    assert fiches[0]["insertion_pro"]["salaire_median_embauche"] == 1850

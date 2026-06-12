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


_COL_SAL12 = "12-Salaire mensuel net médian en équivalent temps plein - 12 mois après le diplôme"
_COL_SAL30 = "30-Salaire mensuel net médian en équivalent temps plein - 30 mois après le diplôme"
_COL_Q1_12 = "12-1er quartile du salaire mensuel net en équivalent temps plein - 12 mois après le diplôme"
_COL_Q3_12 = "12-3ème quartile du salaire mensuel net en équivalent temps plein - 12 mois après le diplôme"
_COL_Q1_30 = "30-1er quartile du salaire mensuel net en équivalent temps plein - 30 mois après le diplôme"
_COL_Q3_30 = "30-3ème quartile du salaire mensuel net en équivalent temps plein - 30 mois après le diplôme"

_CSV_COLS = [
    "Établissement", "Code UAI de l'établissement", "type_diplome",
    "Domaine disciplinaire", "Libellé du diplôme", "Genre", "Nationalité",
    "Régime d'inscription", "Obtention du diplôme", "Promotion",
    _COL_SAL12, _COL_SAL30, _COL_Q1_12, _COL_Q3_12, _COL_Q1_30, _COL_Q3_30,
]


def _write_csv(path, rows):
    import csv
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=_CSV_COLS, delimiter=";")
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in _CSV_COLS})


def _row(genre="ensemble", nat="ensemble", regime="ensemble", obt="ensemble", sal="2000",
         q1="1700", q3="2400"):
    return {
        "Établissement": "Université X", "Code UAI de l'établissement": "0751717J",
        "type_diplome": "Master LMD", "Domaine disciplinaire": "Sciences",
        "Libellé du diplôme": "Acoustique", "Genre": genre, "Nationalité": nat,
        "Régime d'inscription": regime, "Obtention du diplôme": obt, "Promotion": "2022",
        _COL_SAL12: sal, _COL_Q1_12: q1, _COL_Q3_12: q3,
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


def _rec(salaire, etab="Université X", libelle="Acoustique", cohorte="2022",
         q1=None, q3=None):
    return {"salaire": salaire, "salaire_30m": None, "horizon": "12m", "cohorte": cohorte,
            "_promo": 2022, "etab": etab, "type": "Master LMD", "discipline": "Sciences",
            "libelle": libelle, "uai": "0751717J", "salaire_q1": q1, "salaire_q3": q3}


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


# --- Phase 1 (order 0825) : quartiles Q1/Q3 (fourchette), même horizon que la médiane ---


def test_build_salary_index_parses_quartiles_same_horizon_as_median(tmp_path):
    """La médiane retenue est 12m -> Q1/Q3 doivent venir des colonnes 12m (pas 30m).
    Rigueur anti-mélange : jamais une médiane 12m avec un quartile 30m."""
    csv_path = tmp_path / "insersup.csv"
    _write_csv(csv_path, [_row(sal="2000", q1="1700", q3="2400")])
    rec = build_salary_index(csv_path)["by_name_disc"][("universite x", "master", "acoustique")]
    assert rec["salaire"] == 2000 and rec["horizon"] == "12m"
    assert rec["salaire_q1"] == 1700
    assert rec["salaire_q3"] == 2400


def test_build_salary_index_quartiles_from_30m_when_12m_absent(tmp_path):
    """Si la médiane vient du 30m (12m null), les quartiles aussi (même horizon)."""
    csv_path = tmp_path / "insersup.csv"
    row = _row(sal="", q1="", q3="")  # 12m vide
    row[_COL_SAL30] = "2600"
    row[_COL_Q1_30] = "2100"
    row[_COL_Q3_30] = "3000"
    _write_csv(csv_path, [row])
    rec = build_salary_index(csv_path)["by_name_disc"][("universite x", "master", "acoustique")]
    assert rec["salaire"] == 2600 and rec["horizon"] == "30m"
    assert rec["salaire_q1"] == 2100
    assert rec["salaire_q3"] == 3000


def test_build_salary_index_quartiles_none_when_absent(tmp_path):
    """Médiane présente mais quartiles vides -> q1/q3 None (pas de fourchette inventée)."""
    csv_path = tmp_path / "insersup.csv"
    _write_csv(csv_path, [_row(sal="2000", q1="", q3="ns")])
    rec = build_salary_index(csv_path)["by_name_disc"][("universite x", "master", "acoustique")]
    assert rec["salaire"] == 2000
    assert rec["salaire_q1"] is None
    assert rec["salaire_q3"] is None


def test_attach_writes_quartiles_when_present():
    idx = _index(name={("universite x", "master", "acoustique"): _rec(1850, q1=1600, q3=2200)})
    fiches = [{"source": "monmaster", "etablissement": "Université X", "nom": "Acoustique"}]
    attach_insersup_salaries(fiches, idx)
    ip = fiches[0]["insertion_pro"]
    assert ip["salaire_median_embauche"] == 1850
    assert ip["salaire_q1"] == 1600
    assert ip["salaire_q3"] == 2200


def test_attach_omits_quartiles_when_absent():
    """Pas de quartile dans la source -> on n'écrit pas de clé q1/q3 (pas de None bruyant)."""
    idx = _index(name={("universite x", "master", "acoustique"): _rec(1850)})  # q1/q3 None
    fiches = [{"source": "monmaster", "etablissement": "Université X", "nom": "Acoustique"}]
    attach_insersup_salaries(fiches, idx)
    ip = fiches[0]["insertion_pro"]
    assert ip["salaire_median_embauche"] == 1850
    assert "salaire_q1" not in ip
    assert "salaire_q3" not in ip


def test_attach_backfills_quartiles_on_existing_insersup_median():
    """Corpus déjà C2b (médiane InserSup posée, pas de quartiles) -> re-run attach
    BACKFILL les quartiles sans re-toucher la médiane. Cas réel du corpus servi."""
    idx = _index(name={("universite x", "master", "acoustique"): _rec(1850, q1=1600, q3=2200)})
    fiches = [{"source": "monmaster", "etablissement": "Université X", "nom": "Acoustique",
               "insertion_pro": {"salaire_median_embauche": 1850, "salaire_source": "insersup"}}]
    metrics = attach_insersup_salaries(fiches, idx)
    ip = fiches[0]["insertion_pro"]
    assert ip["salaire_median_embauche"] == 1850  # médiane inchangée
    assert ip["salaire_q1"] == 1600 and ip["salaire_q3"] == 2200  # fourchette complétée
    assert metrics["n_quartiles_backfilled"] == 1
    assert metrics["n_enriched"] == 0  # pas un nouvel enrichissement


def test_attach_no_quartile_backfill_cross_source():
    """Garde anti-confabulation : médiane d'une AUTRE source (ex Céreq) -> on ne colle
    PAS des quartiles InserSup dessus (cohérence médiane/fourchette même source)."""
    idx = _index(name={("universite x", "master", "acoustique"): _rec(1850, q1=1600, q3=2200)})
    fiches = [{"source": "monmaster", "etablissement": "Université X", "nom": "Acoustique",
               "insertion_pro": {"salaire_median_embauche": 2000, "salaire_source": "cereq"}}]
    metrics = attach_insersup_salaries(fiches, idx)
    ip = fiches[0]["insertion_pro"]
    assert ip["salaire_median_embauche"] == 2000  # médiane Céreq intacte
    assert "salaire_q1" not in ip  # pas de quartile InserSup collé sur médiane Céreq
    assert metrics["n_quartiles_backfilled"] == 0


def test_attach_quartile_backfill_idempotent():
    """Re-run après backfill -> rien à faire (quartiles déjà là)."""
    idx = _index(name={("universite x", "master", "acoustique"): _rec(1850, q1=1600, q3=2200)})
    fiches = [{"source": "monmaster", "etablissement": "Université X", "nom": "Acoustique",
               "insertion_pro": {"salaire_median_embauche": 1850, "salaire_source": "insersup"}}]
    attach_insersup_salaries(fiches, idx)
    m2 = attach_insersup_salaries(fiches, idx)
    assert m2["n_quartiles_backfilled"] == 0
    assert fiches[0]["insertion_pro"]["salaire_q1"] == 1600

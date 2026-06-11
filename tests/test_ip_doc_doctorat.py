"""Tests pour `src/collect/ip_doc_doctorat.py` (MESR Opendatasoft)."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.collect.ip_doc_doctorat import (
    DISCA_TO_DOMAINE,
    IpDocFetchError,
    _safe_int,
    _safe_ratio,
    build_doctorat_insertion_pro,
    disca_to_domaine,
    fetch_ip_doc_records,
    normalize_all,
    normalize_record,
)


# --- C2b (order 2026-06-11) : salaire doctorat -> insertion_pro ---


def test_build_doctorat_insertion_pro_exposes_net_salary():
    fiche = {
        "salaire_net_median_mensuel": 2208,
        "salaire_brut_median_annuel": 34000,
        "situation": "36m",
        "taux_insertion": 0.93,
        "annee": "2022",
    }
    ip = build_doctorat_insertion_pro(fiche)
    assert ip is not None
    assert ip["salaire_median_embauche"] == 2208       # net mensuel, valeur source
    assert ip["salaire_net"] is True                   # étiqueté net (RÈGLE 6)
    assert ip["source"] == "ip_doc_doctorat"
    assert ip["salaire_horizon"] == "36m"
    assert ip["cohorte"] == "2022"                     # année tracée (citation)


def test_build_doctorat_insertion_pro_reads_annee_cohorte():
    """Le corpus servi porte `annee_cohorte` (pas `annee`) — l'année de cohorte
    DOIT être tracée pour la citation (cf détresse-006)."""
    fiche = {"salaire_net_median_mensuel": 2125, "annee_cohorte": 2016, "situation": "12 mois après le diplôme"}
    ip = build_doctorat_insertion_pro(fiche)
    assert ip["cohorte"] == 2016


def test_build_doctorat_insertion_pro_none_without_salary():
    assert build_doctorat_insertion_pro({"situation": "12m", "taux_insertion": 0.9}) is None


def test_normalize_record_attaches_insertion_pro_with_salary():
    rec = {"disca": "Mathématiques", "annee": "2022", "situation": "36m",
           "sal_net_med_mensuel": "2208", "taux_insertion": "0.93"}
    fiche = normalize_record(rec)
    assert isinstance(fiche.get("insertion_pro"), dict)
    assert fiche["insertion_pro"]["salaire_median_embauche"] == 2208


# --- Mapping disca → domaine ---


@pytest.mark.parametrize(
    "disca,expected",
    [
        ("Sciences juridiques et politiques", "eco_gestion"),
        ("Mathématiques et leurs interactions", "sciences_fondamentales"),
        ("Sciences et technologies de l'information et de la communication", "data_ia"),
        ("Biologie, médecine, santé", "sante"),
        ("Sciences pour l'ingénieur", "ingenierie_industrielle"),
        ("Sciences agronomiques et écologiques", "agriculture"),
        ("Langues et littératures", "langues"),
        ("", None),
        (None, None),
    ],
)
def test_disca_to_domaine_exact(disca, expected):
    assert disca_to_domaine(disca) == expected


def test_disca_fuzzy_fallback_sante():
    assert disca_to_domaine("Médecine spécialité") == "sante"
    assert disca_to_domaine("Biologie moléculaire") == "sante"


def test_disca_fuzzy_fallback_data_ia():
    assert disca_to_domaine("Informatique théorique") == "data_ia"
    assert disca_to_domaine("Numérique appliqué") == "data_ia"


def test_disca_fuzzy_fallback_ingenierie():
    assert disca_to_domaine("Ingénierie mécanique") == "ingenierie_industrielle"


def test_disca_fuzzy_fallback_eco_gestion():
    assert disca_to_domaine("Droit international") == "eco_gestion"


def test_disca_unknown_returns_none():
    assert disca_to_domaine("Discipline exotique sans match") is None


# --- Safe parsers ---


def test_safe_int_and_ratio():
    assert _safe_int("1851") == 1851
    assert _safe_int("1 851,5") == 1851
    assert _safe_int("") is None
    assert _safe_ratio("89") == pytest.approx(0.89)
    assert _safe_ratio("1.0") == 1.0
    assert _safe_ratio(None) is None


# --- Normalize ---


def test_normalize_record_basic():
    raw = {
        "annee": "2014",
        "diplome": "DOCTORAT",
        "situation": "36 mois après le diplôme",
        "disca": "Sciences de la société",
        "discipline_principale": "Sciences juridiques et politiques",
        "genre": "femmes et hommes",
        "nbre_de_repondants": "383",
        "part_femmes": "47",
        "taux_insertion": "89",
        "part_stable": "81",
        "part_cadre": "92",
        "part_temps_plein": "88",
        "part_secteur_academique": "43",
        "part_public_hors_secteur_academique": "25",
        "part_r_d_privee": "3",
        "part_prive_hors_secteur_academique_et_r_d": "29",
        "part_en_emploi_a_l_etranger": "32",
        "sal_net_q1_mensuel": "1851",
        "sal_net_med_mensuel": "2267",
        "sal_net_q3_mensuel": "2983",
        "sal_brut_med_annuel": "33000",
    }
    n = normalize_record(raw)
    assert n["source"] == "ip_doc_doctorat"
    assert n["niveau_orientia"] == "bac+8"
    assert n["situation"] == "36 mois après le diplôme"
    assert n["discipline_agregee"] == "Sciences de la société"
    assert n["domaine_orientia"] == "sciences_humaines"
    assert n["taux_insertion"] == pytest.approx(0.89)
    assert n["part_stable"] == pytest.approx(0.81)
    assert n["part_secteur_academique"] == pytest.approx(0.43)
    assert n["part_rd_privee"] == pytest.approx(0.03)
    assert n["part_emploi_etranger"] == pytest.approx(0.32)
    assert n["salaire_net_q1_mensuel"] == 1851
    assert n["salaire_net_median_mensuel"] == 2267
    assert n["salaire_brut_median_annuel"] == 33000


def test_normalize_always_bac_plus_8():
    """Tous les records sont DOCTORAT → bac+8 systématique."""
    raw = {"disca": "X", "situation": "12 mois"}
    n = normalize_record(raw)
    assert n["niveau_orientia"] == "bac+8"


def test_normalize_all():
    raws = [{"disca": "Sciences humaines et humanités"}, {"disca": "Chimie"}]
    out = normalize_all(raws)
    assert len(out) == 2
    assert out[0]["domaine_orientia"] == "sciences_humaines"
    assert out[1]["domaine_orientia"] == "sciences_fondamentales"


# --- Fetch (mocked) ---


def test_fetch_ip_doc_success():
    session = MagicMock()
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = [{"disca": "Chimie"}]
    session.get.return_value = resp
    out = fetch_ip_doc_records(max_records=5, session=session)
    assert out == [{"disca": "Chimie"}]
    assert session.get.call_args[1]["params"]["limit"] == 5


def test_fetch_ip_doc_http_error():
    session = MagicMock()
    resp = MagicMock()
    resp.status_code = 503
    resp.text = "Unavailable"
    session.get.return_value = resp
    with pytest.raises(IpDocFetchError):
        fetch_ip_doc_records(session=session)


def test_fetch_ip_doc_unexpected_shape():
    session = MagicMock()
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"not": "a list"}
    session.get.return_value = resp
    with pytest.raises(IpDocFetchError):
        fetch_ip_doc_records(session=session)


def test_mapping_table_non_empty():
    assert len(DISCA_TO_DOMAINE) > 15

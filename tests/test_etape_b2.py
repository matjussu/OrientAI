"""Étape B-2 : accès aux études de santé des fiches PASS et LAS, et les contrôles qui le gardent.

Entrées réelles (fixture `tests/fixtures/etape_b2/`, extraite par `extraire.py` le 23/09/2026) :
fiches PASS/LAS du corpus B-1, texte `pdftotext -layout` du PDF SIES (Note Flash n°31) et du PDF
de capacités de l'Université de Lille. Les valeurs attendues sont relues dans ces textes par le
test lui-même, pas recopiées du code.

Falsification (règle 9) : chaque contrôle de `controler_sante` est joué sur une fiche ou un texte
cassés par un levier explicite et doit rendre son défaut ; sur la fiche saine, il reste muet.
L'audit des sources rougit sur une valeur, une somme ou un extrait altérés.
"""
from __future__ import annotations

import copy
import dataclasses
import json
import re
from pathlib import Path

import pytest

from src.collect import sante, sante_universites
from src.collect.corpus_etape_b2 import construire, universites_avec_pass
from src.collect.valeur_sourcee import Referentiel
from src.eval.donnee.audit_sante import auditer_capacites, auditer_sies, normaliser
from src.eval.donnee.controles import controler, controler_etape_b, controler_sante
from src.rag.embeddings import fiche_to_text

ICI = Path(__file__).parent / "fixtures/etape_b2"
FICHES = json.loads((ICI / "fiches.json").read_text(encoding="utf-8"))
SIES = normaliser((ICI / "sies_nf31.txt").read_text(encoding="utf-8"))
LILLE = normaliser((ICI / "lille_2026.txt").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def corpus():
    entree = list(FICHES.values())
    # Les universités qui portent un PASS : mesurées sur le corpus complet en production, ici sur
    # la fixture (Paris Nanterre n'y a qu'une LAS, comme dans le corpus complet).
    calcul = sante.CalculSante(Referentiel(), sante_universites.RECHERCHES, universites_avec_pass(entree))
    return {f.get("cod_aff_form") or f.get("id"): f for f in construire(entree, calcul)}


def _fiche(corpus, cas):
    return corpus[FICHES[cas]["cod_aff_form"]]


# ── SIES : les valeurs sont celles des colonnes PASS 2022 et L.AS 2022 du tableau ────────────
def _colonnes_2022(libelle: str) -> tuple[float, float]:
    m = re.search(re.escape(libelle) + r"((?: \d+,\d){5})", SIES)
    assert m, libelle
    *_, p, l = m.group(1).split()
    return float(p.replace(",", ".")), float(l.replace(",", "."))


@pytest.mark.parametrize("cle,libelle", [
    ("medecine", "Médecine"), ("maieutique", "Maïeutique"), ("odontologie", "Odontologie"),
    ("pharmacie", "Pharmacie"), ("kinesitherapie", "Kinésithérapie"), ("ensemble", "en 2ème année de"),
    ("un_an", "dont admis en 1 an"), ("deux_ans", "admis en 2 ans"),
])
def test_sies_valeurs_lues_dans_le_pdf(cle, libelle):
    assert sante.SIES_LIGNES[cle][1] == _colonnes_2022(libelle)


def test_passage_national_par_voie():
    pass_, las = _colonnes_2022("en 2ème année de")
    assert sante.passage_national("PASS")["admis_mmopk_1_ou_2_ans_pct"] == pass_ == 47.5
    assert sante.passage_national("LAS")["admis_mmopk_1_ou_2_ans_pct"] == las == 25.7
    assert "34 200 néo-bacheliers" in SIES and "40,1 %" in SIES


def test_audit_sies_vert_puis_rouge_sur_valeur_alteree():
    assert auditer_sies(sante.SIES_LIGNES, sante.SIES_EXTRAITS_TEXTE, SIES) == []
    lignes = dict(sante.SIES_LIGNES)
    ligne, (p, l) = lignes["pharmacie"]
    lignes["pharmacie"] = (ligne, (p, round(l + 0.1, 1)))
    assert any("pharmacie" in e for e in auditer_sies(lignes, (), SIES))
    lignes["pharmacie"] = (ligne.replace("7,9", "8,9"), (8.9, l))
    assert any("ligne absente" in e for e in auditer_sies(lignes, (), SIES))


# ── audit des capacités : extraits, nombres, sommes ────────────────────────────────────────
def _lille():
    return sante_universites.RECHERCHES["Université de Lille"].capacites


def test_audit_capacites_lille_vert():
    ecarts, non_mesure = auditer_capacites(_lille(), {}, set(), lire=lambda _: LILLE)
    assert ecarts == [] and non_mesure == []


@pytest.mark.parametrize("levier", ["valeur", "somme", "extrait"])
def test_audit_capacites_rougit(levier):
    c = _lille()
    pf = copy.deepcopy(c.par_filiere)
    extraits = c.extraits
    if levier == "valeur":
        pf["pharmacie"]["PASS"] = 109
    elif levier == "somme":
        pf["kinesitherapie"]["LAS"] = 167
    else:
        extraits = tuple(e.replace("PASS 276", "PASS 267") for e in extraits)
    ecarts, _ = auditer_capacites(dataclasses.replace(c, par_filiere=pf, extraits=extraits), {}, set(), lire=lambda _: LILLE)
    assert ecarts


def test_lecture_visuelle_rend_non_mesure_jamais_vert():
    c = sante_universites.RECHERCHES["Nantes Université"].capacites
    ecarts, non_mesure = auditer_capacites(c, {}, sante_universites.LECTURE_VISUELLE,
                                           lire=lambda _: pytest.fail("un scan ne se lit pas"))
    assert ecarts == [] and non_mesure == ["univ_nantes_mmopk_2026_2027"]
    pf = copy.deepcopy(c.par_filiere)
    pf["medecine"]["LAS"] += 1  # la somme reste vérifiée sur un scan
    ecarts, _ = auditer_capacites(dataclasses.replace(c, par_filiere=pf), {}, sante_universites.LECTURE_VISUELLE)
    assert ecarts


def test_panel_complet():
    assert set(sante.PANEL) == set(sante_universites.RECHERCHES)
    for r in sante_universites.RECHERCHES.values():
        assert r.urls, r.universite


# ── normalisation et rattachement ─────────────────────────────────────────────────────────
@pytest.mark.parametrize("cas,universite", [
    ("pass_lille", "Université de Lille"), ("pass_orsay", "Université Paris-Saclay"),
    ("pass_nimes", "Université de Montpellier"), ("las_guyancourt", "Université de Versailles Saint-Quentin-en-Yvelines"),
    ("pass_aubenas", "Université Claude Bernard Lyon 1"), ("las_agen", "Université de Bordeaux"),
    ("pass_toulouse", "Université Toulouse III"), ("las_nantes", "Nantes Université"),
])
def test_universite_de(cas, universite):
    assert sante.universite_de(FICHES[cas]["etablissement"]) == universite


def test_capacites_du_panel(corpus):
    cap = _fiche(corpus, "pass_lille")["sante"]["capacites_universite"]
    assert cap["statut"] == "disponible" and cap["portee"] == "universite"
    assert cap["valeur"]["par_filiere"]["medecine"]["PASS"] == 276
    assert re.search(r"PASS 276 25 44 108 62", LILLE)
    assert cap["source"]["url"].endswith("2026-27-numerus-apertus.pdf") and len(cap["source"]["sha256"]) == 64


def test_raisons_non_disponible(corpus):
    assert _fiche(corpus, "las_nanterre")["sante"]["capacites_universite"]["raison"] == sante.RAISON_SANS_FACULTE
    assert _fiche(corpus, "pass_grenoble")["sante"]["capacites_universite"]["raison"] == sante.RAISON_HORS_PANEL
    orsay = _fiche(corpus, "pass_orsay")["sante"]["capacites_universite"]
    assert orsay["statut"] == "non_disponible" and orsay["source"]["urls_consultees"]
    for cas in FICHES:
        s = _fiche(corpus, cas)["sante"]
        assert s["passage_national"]["portee"] == "nationale"
        assert s["passage_universite"]["statut"] == "non_disponible"  # aucune université ne publie de taux


def test_kine_bordeaux_garde_son_document_et_sa_rentree(corpus):
    v = _fiche(corpus, "las_agen")["sante"]["capacites_universite"]["valeur"]
    assert v["par_filiere"]["kinesitherapie"]["rentree"] == "2025/2026"
    assert [s["id"] for s in v["sources_complementaires"]] == ["univ_bordeaux_kine_2025_2026"]
    assert "(rentrée 2025/2026)" in fiche_to_text(_fiche(corpus, "las_agen"))


def test_fiche_concept_reforme(corpus):
    concept = corpus[sante.REFORME_ID]
    assert concept["statut_reglementaire"] == "annonce"
    texte = fiche_to_text(concept)
    assert "17/04/2026" in texte and "Journal officiel" in texte and "CNESER" not in texte
    assert any("CNESER" in r["resultat"] and "non vérifiée" in r["resultat"] for r in concept["recherches"])


# ── texte : national d'abord, portée dans la phrase ────────────────────────────────────────
def test_texte_national_avant_universite(corpus):
    texte = fiche_to_text(_fiche(corpus, "las_lille"))
    i_nat, i_univ = texte.index("au niveau national"), texte.index("Places en MMOPK")
    assert i_nat < i_univ
    assert "25,7 %" in texte and "toutes mentions confondues" in texte


@pytest.mark.parametrize("cas", list(FICHES))
def test_controles_muets_sur_fiche_saine(corpus, cas):
    f = _fiche(corpus, cas)
    texte = fiche_to_text(f)
    assert controler_sante(f, texte, exiger=True) == []
    assert controler(f, texte) == [] and controler_etape_b(f, texte) == []


def _casse(corpus, cas, levier):
    f = copy.deepcopy(_fiche(corpus, cas))
    texte = fiche_to_text(f)
    if levier == "sante_absent":
        del f["sante"]
    elif levier == "sante_capacites_universite_absent":
        del f["sante"]["capacites_universite"]
    elif levier == "sante_passage_national_sans_portee":
        del f["sante"]["passage_national"]["portee"]
    elif levier == "sante_capacites_universite_sans_url_ou_empreinte":
        del f["sante"]["capacites_universite"]["source"]["sha256"]
    elif levier == "sante_taux_sans_portee":
        texte = texte.replace("au niveau national (SIES", "(SIES", 1)
    elif levier == "sante_31_pourcent_attribue_a_l_universite":
        texte = texte.replace("Taux de passage en MMOPK propre à l'université : non disponible",
                              "Taux de passage en MMOPK publié par l'université : 31,0 %", 1)
    elif levier == "sante_national_non_ecrit":
        texte = " | ".join(s for s in texte.split(" | ") if "au niveau national" not in s)
    elif levier == "sante_passage_universite_non_disponible_sans_raison":
        f["sante"]["passage_universite"]["raison"] = ""
    return f, texte


@pytest.mark.parametrize("levier", [
    "sante_absent", "sante_capacites_universite_absent", "sante_passage_national_sans_portee",
    "sante_capacites_universite_sans_url_ou_empreinte", "sante_taux_sans_portee",
    "sante_31_pourcent_attribue_a_l_universite", "sante_national_non_ecrit",
    "sante_passage_universite_non_disponible_sans_raison",
])
def test_controle_sante_rougit(corpus, levier):
    f, texte = _casse(corpus, "pass_lille", levier)
    assert levier in controler_sante(f, texte, exiger=True)


def test_controle_sante_muet_sur_corpus_anterieur():
    assert controler_sante(FICHES["pass_lille"], fiche_to_text(FICHES["pass_lille"]), exiger=False) == []

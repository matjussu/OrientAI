"""Étape A : villes (COG INSEE), table de domaines, type de formation en clair.

Fixtures tirées des données réelles (`scripts/donnee/generer_fixtures_etape_a.py`) :
extrait du COG INSEE 2025 et TOUTES les lignes BUT du jeu Parcoursup 2025.
"""
from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

import pytest

from src.collect.communes import ReferentielCommunes, cle_nom
from src.collect.domaines import charger_table, classer
from src.collect.types_formation import decrire, niveau_vise

FIXTURES = Path(__file__).parent / "fixtures/etape_a"


@pytest.fixture(scope="module")
def communes() -> ReferentielCommunes:
    return ReferentielCommunes(FIXTURES / "cog_extrait.csv")


@pytest.fixture(scope="module")
def regles():
    return charger_table()


# ── A3 : villes ─────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("brut,dep,ville,code,arr,code_arr", [
    ("Paris  6e  Arrondissement", "75", "Paris", "75056", "6e arrondissement", "75106"),
    ("Lyon 8e  Arrondissement", "69", "Lyon", "69123", "8e arrondissement", "69388"),
    ("Marseille 13e  Arrondissement", "13", "Marseille", "13055", "13e arrondissement", "13213"),
])
def test_arrondissement_ramene_a_la_commune(communes, brut, dep, ville, code, arr, code_arr):
    c = communes.resoudre(brut, dep)
    assert (c.ville, c.code_insee, c.arrondissement, c.code_insee_arrondissement) == (ville, code, arr, code_arr)


@pytest.mark.parametrize("brut,dep,ville,code", [
    ("Saint-Etienne", "42", "Saint-Étienne", "42218"),       # accent manquant
    ("Schoelcher", "972", "Schœlcher", "97229"),               # ligature œ
    ("Vandoeuvre-lès-Nancy", "54", "Vandœuvre-lès-Nancy", "54547"),
    ("Borgo", "20", "Borgo", "2B042"),                         # Corse : « 20 » dans Parcoursup, 2B au COG
    ("Lille CEDEX 5", "59", "Lille", "59350"),
    ("  Aubière  ", "63", "Aubière", "63014"),
    ("Chemillé", "49", "Chemillé-en-Anjou", "49092"),          # commune déléguée -> commune nouvelle
])
def test_ville_rattachee_au_cog(communes, brut, dep, ville, code):
    c = communes.resoudre(brut, dep)
    assert (c.ville, c.code_insee) == (ville, code)


def test_ville_introuvable_reste_sans_code(communes):
    c = communes.resoudre("Marne-la-Vallée", "77")
    assert c.code_insee is None and c.ville == "Marne-la-Vallée"


def test_etranger_sans_code(communes):
    assert communes.resoudre("Madrid", "99").code_insee is None


def test_meme_nom_autre_departement_non_rattache(communes):
    # Un nom seul n'identifie pas une commune : Lille dans le 62 n'existe pas.
    assert communes.resoudre("Lille", "62").code_insee is None


def test_cle_nom_unifie_saint_et_accents():
    assert cle_nom("St-Étienne") == cle_nom("SAINT ETIENNE") == cle_nom("Saint-Etienne")


# ── A2 : domaines ───────────────────────────────────────────────────────────────────


def _lignes_but():
    with (FIXTURES / "intitules_but.csv").open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh, delimiter=";"))


def _domaine(regles, ligne):
    intitule = " ".join(x for x in (ligne["intitule"], ligne["intitule_complet"], ligne["detail"]) if x)
    classe = classer(regles, ligne["fili"], ligne["filiere"], intitule)
    return classe[0] if classe else None


def test_population_but_non_vide():
    # Une preuve sur zéro ligne ne prouve rien.
    assert len(_lignes_but()) == 820


@pytest.mark.parametrize("specialite,domaine,attendu", [
    ("Informatique", "informatique", 49),
    ("Réseaux et télécommunications", "informatique", 30),
    ("Science des données", "data_ia", 15),
    ("Génie électrique et informatique industrielle", "ingenierie_industrielle", 53),
])
def test_but_par_specialite_tous_classes(regles, specialite, domaine, attendu):
    """Toutes les lignes BUT de la spécialité (jeu 2025 entier) sont dans le domaine voulu."""
    lignes = [l for l in _lignes_but() if l["filiere_detaillee"].strip() == specialite]
    assert len(lignes) == attendu
    assert Counter(_domaine(regles, l) for l in lignes) == {domaine: attendu}


def test_but_information_communication_hors_informatique(regles):
    lignes = [l for l in _lignes_but() if l["filiere_detaillee"].startswith("Information communication")]
    assert lignes
    assert all(_domaine(regles, l) not in {"informatique", "cyber", "data_ia"} for l in lignes)


@pytest.mark.parametrize("fili,filiere,intitule,domaine", [
    ("PASS", "Licence - Sciences - technologies - santé", "Licence - Parcours d'Accès Spécifique Santé (PASS)", "sante"),
    ("Licence_Las", "Licence - Sciences - technologies - santé", "Licence - Portail Informatique", "sante"),
    ("IFSI", "D.E secteur sanitaire", "D.E Infirmier", "sante"),
    ("Autre formation", "D.E  secteur sanitaire", "D.E Ergothérapeute", "sante"),
    ("BTS", "BTS - Production", "BTS - Production - Cybersécurité, Informatique et réseaux, ELectronique - Option A", "informatique"),
    ("BTS", "BTS - Services", "BTS - Services - Services informatiques aux organisations", "informatique"),
    ("CPGE", "Classe préparatoire scientifique", "CPGE - MP2I", "informatique"),
    ("CPGE", "Classe préparatoire scientifique", "CPGE - MPSI", "sciences_fondamentales"),
    ("Licence", "Licence - Sciences - technologies - santé", "Licence - Mathématiques", "sciences_fondamentales"),
    ("Autre formation", "DSP", "DSP - Développement et exploitation de parcs informatiques", "informatique"),
    ("Ecole d'Ingénieur", "Formations des écoles d'ingénieurs",
     "Formation d'ingénieur Bac + 5 - Cycle Préparatoire Intégré - Spécialité Généraliste, BTP, Informatique", "ingenierie_industrielle"),
])
def test_regles_par_cas(regles, fili, filiere, intitule, domaine):
    assert classer(regles, fili, filiere, intitule)[0] == domaine


def test_formation_hors_table_rend_none(regles):
    assert classer(regles, "BTS", "BTS - Services", "BTS - Services - Banque") is None


def test_table_refuse_identifiants_doubles(tmp_path):
    table = tmp_path / "t.csv"
    table.write_text("regle;fili;filiere;intitule;domaine;motif\nX1;*;*;a;d;m\nX1;*;*;b;d;m\n", encoding="utf-8")
    with pytest.raises(ValueError):
        charger_table(table)


# ── A1 : type de formation en clair ─────────────────────────────────────────────────


@pytest.mark.parametrize("fili,nom,complet,detail,libelle,precision", [
    ("PASS", "Licence - Parcours d'Accès Spécifique Santé (PASS)",
     "Licence - Parcours d'Accès Spécifique Santé (PASS) - option Mathématiques", None,
     "PASS (parcours d'accès spécifique santé)", "option Mathématiques"),
    ("PASS", "Licence - Parcours d'Accès Spécifique Santé (PASS)",
     "Licence - Parcours d'Accès Spécifique Santé (PASS) - option Droit - enseignement à distance - Enseignement à distance",
     None, "PASS (parcours d'accès spécifique santé)", "option Droit (enseignement à distance)"),
    ("PASS", "Licence - Parcours d'Accès Spécifique Santé (PASS)", None, None,
     "PASS (parcours d'accès spécifique santé)", "option non précisée dans les données ouvertes"),
    ("Licence_Las", "Licence - Mathématiques", "Licence - Mathématiques -  Accès Santé (LAS)", "Mathématiques",
     "LAS (licence avec option accès santé)", "majeure Mathématiques"),
    ("BUT", "BUT - Informatique", None, "Informatique",
     "BUT (bachelor universitaire de technologie)", "spécialité Informatique"),
    ("Ecole d'Ingénieur", "Formation Bac + 3 - Bachelor Cybersécurité", None, "x",
     "Bachelor d'une école d'ingénieurs, recrutement post-bac (bac + 3)", None),
])
def test_type_en_clair(fili, nom, complet, detail, libelle, precision):
    t = decrire(fili, nom, complet, detail)
    assert (t.libelle, t.precision) == (libelle, precision)


def test_cpge_voie_developpee():
    assert decrire("CPGE", "CPGE - MP2I", None, "MP2I").precision.startswith("voie MP2I (")


@pytest.mark.parametrize("fili,nom,attendu", [
    ("Licence", "Licence - Sciences pour l'ingénieur", ("bac+3", "filiere")),      # heuristique : bac+5
    ("BTS", "BTS - Production - Assistance technique d'ingénieur", ("bac+2", "filiere")),
    ("Licence_Las", "Formation d'ingénieur Bac + 5 -  Cycle préparatoire intégré - Accès Santé", ("bac+5", "intitule")),
    ("Ecole d'Ingénieur", "Formation d'ingénieur Bac + 5 - Voie d'accès réservée aux BAC +1 uniquement", ("bac+5", "intitule")),
    ("CPGE", "CPGE - MPSI", (None, "cpge")),
    ("Autre formation", "C.M.I - Cursus Master en Ingénierie - Informatique", ("bac+5", "heuristique")),
])
def test_niveau_vise(fili, nom, attendu):
    assert niveau_vise(fili, nom) == attendu

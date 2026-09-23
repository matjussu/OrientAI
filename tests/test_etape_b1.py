"""Étape B-1 : coût, alternance, insertion, et les contrôles qui les gardent.

Les entrées sont des lignes RÉELLES des sources (fixture `tests/fixtures/etape_b/`, extraite par
`extraire.py` des bruts verrouillés le 23/09/2026) : fiches de l'étape A, lignes Onisep, Parcoursup
apprentissage, InserSup, InserJeunes. Les valeurs attendues sont lues dans ces lignes brutes par le
test lui-même, pas recopiées de la sortie du code.

Falsification (règle 9) : chaque contrôle de `controler_etape_b` est joué sur un texte ou une fiche
cassés par un levier explicite (champ retiré, montant altéré, ancienne insertion réécrite) et doit
rendre son défaut ; le même contrôle sur la fiche saine doit rester muet.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from src.collect.alternance import Alternance, cle_diplome
from src.collect.communes import ReferentielCommunes
from src.collect.corpus_etape_b import ConstructeurEtapeB1, remplissage
from src.collect.couts import CalculCout, lire_cout_onisep, score_intitule
from src.collect.domaines import charger_table
from src.collect.insertion import CalculInsertion
from src.collect.valeur_sourcee import Referentiel
from src.eval.donnee.controles import controler, controler_etape_b
from src.rag.embeddings import fiche_to_text

ICI = Path(__file__).parent / "fixtures/etape_b"
SOURCES = json.loads((ICI / "sources.json").read_text(encoding="utf-8"))
FICHES = SOURCES["fiches"]
VERROU = {
    nom: {"telecharge_le": "2026-09-23"}
    for nom in ("onisep_ideo_actions_es", "parcoursup_apprentissage_2025", "insersup", "inserjeunes_bts")
}


@pytest.fixture(scope="module")
def ref():
    return Referentiel(VERROU)


@pytest.fixture(scope="module")
def constructeur(ref):
    communes = ReferentielCommunes(ICI / "cog_extrait.csv")
    return ConstructeurEtapeB1(
        cout=CalculCout(SOURCES["onisep"], ref),
        alternance=Alternance(SOURCES["apprentissage"], communes, ref),
        insertion=CalculInsertion(SOURCES["insersup"], SOURCES["inserjeunes"], SOURCES["paysage"], ref),
        regles=charger_table(),
    )


@pytest.fixture(scope="module")
def corpus(constructeur):
    return constructeur.construire(list(FICHES.values()))


@pytest.fixture(scope="module")
def par_code(corpus):
    return {str(f["cod_aff_form"]): f for f in corpus}


def _onisep(action: str) -> dict:
    return next(l for l in SOURCES["onisep"] if l["Action de Formation (AF) identifiant Onisep"] == action)


def test_fixture_non_vide():
    assert len(FICHES) == 15 and SOURCES["onisep"] and SOURCES["apprentissage"] and SOURCES["insersup"]


# ── lecture du texte Onisep ──────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("texte, total, fourchette, annuel, annee, appr, bours", [
    ("2200 euros en 2025 (1100 euros par an)", 2200, None, 1100, "2025", False, False),
    ("2996 euros en 2025 (1498 euros par an, gratuit en apprentissage)", 2996, None, 1498, "2025", True, False),
    ("3024 euros en 2026 (1512 euros par ans, gratuit en apprentissage)", 3024, None, 1512, "2026", True, False),
    ("de 460 euros jusqu'à 1722 euros en 2026", None, (460, 1722), None, "2026", False, False),
    ("0 euros en 2026", 0, None, None, "2026", False, False),
    ("27 600 euros en 2025 (9200 euros par an)", 27600, None, 9200, "2025", False, False),
    ("1100 euros en 2026 (550 euros par an, gratuit pour les boursiers)", 1100, None, 550, "2026", False, True),
])
def test_lire_cout_onisep(texte, total, fourchette, annuel, annee, appr, bours):
    lu = lire_cout_onisep(texte)
    assert (lu.total_eur, lu.fourchette_eur, lu.annuel_eur, lu.annee) == (total, fourchette, annuel, annee)
    assert (lu.gratuit_apprentissage, lu.gratuit_boursiers) == (appr, bours)


@pytest.mark.parametrize("texte", ["", "   ", "frais de pension et de scolarité variables", "environ 8000 euros"])
def test_texte_hors_grammaire_jamais_devine(texte):
    assert lire_cout_onisep(texte) is None


# ── coût ─────────────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("cod", ["14476", "43422", "31712", "4974"])
def test_public_cycle_licence_ou_cpge_constante(par_code, cod):
    cout = par_code[cod]["cout"]
    assert cout["statut"] == "disponible" and cout["rattachement"] == "constante_type_statut"
    assert cout["valeur"]["droits_inscription_eur"] == 178 and cout["valeur"]["cvec_eur"] == 105
    assert cout["source"]["id"] == "tableau_droits_2026_2027" and cout["millesime"] == "2026-2027"


@pytest.mark.parametrize("cod", ["10768", "5399", "8882", "23289", "32446", "8296"])
def test_cout_onisep_par_intitule_egal_a_la_ligne_brute(par_code, cod):
    cout = par_code[cod]["cout"]
    assert cout["rattachement"] == "onisep_uai_intitule" and cout["statut"] == "disponible"
    ligne = _onisep(cout["valeur"]["onisep_action"])
    assert ligne["ENS code UAI"] == FICHES[cod]["cod_uai"]
    assert cout["valeur"]["texte_source"] == " ".join(ligne["AF coût scolarité"].split())
    assert cout["source"]["licence"] == "ODbL" and cout["collecte"] == "2026-09-23"


def test_cout_onisep_famille_unanime(par_code):
    cout = par_code["31664"]["cout"]
    assert cout["rattachement"] == "onisep_uai_famille" and cout["statut"] == "disponible"
    uai = FICHES["31664"]["cod_uai"]
    prepas = [l for l in SOURCES["onisep"] if l["ENS code UAI"] == uai and l["FOR type"].startswith("prépa")]
    assert len(prepas) >= 2 and {l["AF coût scolarité"] for l in prepas} == {cout["valeur"]["texte_source"]}


def test_famille_refusee_hors_cpge_bts(ref):
    """Un IFSI dont la seule ligne Onisep « de même famille » est un autre diplôme ne prend pas son coût."""
    fiche = copy.deepcopy(FICHES["23289"])
    fiche["nom"] = fiche["intitule_officiel"] = fiche["filiere_detaillee"] = "Formation X"
    autre = {"ENS code UAI": fiche["cod_uai"], "FOR type": "diplôme d'État du paramédical",
             "Formation (FOR) libellé": "diplôme d'État de puéricultrice", "AF coût scolarité": "5000 euros en 2026",
             "Action de Formation (AF) identifiant Onisep": "AF.TEST"}
    assert CalculCout([autre, dict(autre)], ref).calculer(fiche)["statut"] == "non_disponible"


def test_texte_famille_le_dit(par_code):
    assert "pour toutes les formations de ce type dans cet établissement" in fiche_to_text(par_code["31664"])


def test_cout_ambigu_non_disponible(par_code):
    cout = par_code["4960"]["cout"]
    assert cout["statut"] == "non_disponible" and "coûts différents" in cout["raison"]


def test_cout_sans_ligne_onisep(par_code):
    cout = par_code["47188"]["cout"]
    assert cout["statut"] == "non_disponible" and cout["rattachement"] == "onisep_uai"
    assert not any(l["ENS code UAI"] == FICHES["47188"]["cod_uai"] for l in SOURCES["onisep"])


def test_options_differentes_jamais_rattachees():
    ps = "BTS - Production - Cybersécurité, Informatique et réseaux, ELectronique - Option B : Electronique et réseaux"
    assert score_intitule(ps, "BTS cybersécurité, informatique et réseaux, électronique option A informatique et réseaux") == 0
    assert score_intitule(ps, "BTS cybersécurité, informatique et réseaux, électronique option B électronique et réseaux") == 1


def test_cpge_rattachee_a_sa_voie():
    assert score_intitule("CPGE - PCSI", "classe préparatoire physique-chimie et sciences de l'ingénieur (PCSI) 1re année") == 1
    assert score_intitule("CPGE - PCSI", "classe préparatoire physique et sciences de l'ingénieur (PSI), 2e année") == 0


def test_public_ne_passe_pas_par_onisep(ref):
    """La constante prime : une ligne Onisep au même UAI ne change rien pour une licence publique."""
    fiche = copy.deepcopy(FICHES["43422"])
    fausse = {"ENS code UAI": fiche["cod_uai"], "FOR type": "licence", "Formation (FOR) libellé": fiche["nom"],
              "AF coût scolarité": "9999 euros en 2026", "Action de Formation (AF) identifiant Onisep": "AF.TEST"}
    assert CalculCout([fausse], ref).calculer(fiche)["valeur"]["droits_inscription_eur"] == 178


# ── alternance ───────────────────────────────────────────────────────────────────────────────
def test_alternance_meme_uai(par_code):
    formations = par_code["5399"]["alternance"]["valeur"]["formations"]
    ligne = next(l for l in SOURCES["apprentissage"] if l["cod_aff_form"] == formations[0]["cod_aff_form"])
    assert ligne["cod_uai"] == FICHES["5399"]["cod_uai"] and formations[0]["rattachee_par"] == "uai"
    assert formations[0]["capacite"] == int(ligne["capa_fin"])
    assert cle_diplome(ligne["form_lib_voe_acc"], ligne["fil_lib_voe_acc"]) == cle_diplome(
        FICHES["5399"]["form_lib_voe_acc"], FICHES["5399"]["filiere_detaillee"])


def test_alternance_meme_commune(par_code):
    formations = par_code["8587"]["alternance"]["valeur"]["formations"]
    assert formations and all(f["rattachee_par"] == "commune" for f in formations)
    assert all(f["ville"] == par_code["8587"]["ville"] for f in formations)


def test_alternance_absente_est_une_mesure(par_code):
    alt = par_code["31712"]["alternance"]
    assert alt["statut"] == "disponible" and alt["valeur"] == {"existe_en_apprentissage": False, "formations": []}


def test_jamais_hors_commune(ref):
    """Une formation d'apprentissage du même diplôme dans une autre commune n'est pas rattachée."""
    fiche = FICHES["5399"]
    ailleurs = next(l for l in SOURCES["apprentissage"] if l["cod_uai"] != fiche["cod_uai"]
                    and cle_diplome(l["form_lib_voe_acc"], l["fil_lib_voe_acc"]) == cle_diplome(
                        fiche["form_lib_voe_acc"], fiche["filiere_detaillee"]))
    communes = ReferentielCommunes(ICI / "cog_extrait.csv")
    alt = Alternance([ailleurs], communes, ref)
    if alt.lignes[0]["_code_insee"] == fiche["code_insee"]:
        pytest.skip("la ligne choisie est dans la même commune")
    assert alt.rattacher(fiche)["valeur"]["existe_en_apprentissage"] is False


def test_fiche_apprentissage_creee(par_code):
    fiche = par_code["28094"]
    ligne = next(l for l in SOURCES["apprentissage"] if l["cod_aff_form"] == "28094")
    assert fiche["source"] == "parcoursup_apprentissage" and fiche["fili_code"] == "BTS"
    assert fiche["apprentissage"]["candidats"] == int(ligne["voe_tot"])
    assert fiche["apprentissage"]["voeux_recherche_contrat"] == int(ligne["nb_rech_con"])
    assert fiche["taux_acces_parcoursup_2025"] is None and "alternance" not in fiche
    assert fiche["cout"]["statut"] == "disponible" and fiche["cout"]["source"]["id"] == "code_travail_l6211_1"
    assert fiche["cout"]["valeur"]["gratuit_pour_l_apprenti"] is True
    assert fiche["insertion"]["statut"] == "non_disponible"


def test_texte_apprentissage_cite_le_code_du_travail(par_code):
    t = fiche_to_text(par_code["28094"])
    assert "« La formation est gratuite pour l'apprenti et pour son représentant légal. »" in t
    assert "Code du travail, article L6211-1" in t and "ne dit rien des autres frais" in t


def test_regle_apprentissage_jamais_sur_une_fiche_scolaire(par_code):
    assert all(f["cout"]["source"]["id"] != "code_travail_l6211_1"
               for f in par_code.values() if f["source"] == "parcoursup")


# ── insertion ────────────────────────────────────────────────────────────────────────────────
def test_insersup_but_par_universite(par_code):
    ins = par_code["4974"]["insertion"]
    ligne = ins["valeur"]["lignes"][0]
    brute = next(l for l in SOURCES["insersup"] if l["diplome"] == ligne["perimetre"]["code_diplome_sise"]
                 and l["promo"] == ins["valeur"]["promotion"] and l["id_paysage"] == SOURCES["paysage"]["4974"])
    assert ligne["indicateurs"]["taux_emploi_salarie_fr_12m"] == float(brute["tx_sortants_en_emploi_sal_fr_12"])
    assert ligne["perimetre"]["etablissement"] == brute["uo_lib"] and ligne["perimetre"]["granularite"] == "diplome_etablissement"


def test_insersup_tout_nd_non_disponible(par_code):
    ins = par_code["43422"]["insertion"]
    assert ins["statut"] == "non_disponible" and "ne diffuse aucun taux" in ins["raison"]


def test_inserjeunes_deux_options(par_code):
    lignes = par_code["8882"]["insertion"]["valeur"]["lignes"]
    diplomes = [l["perimetre"]["diplome"] for l in lignes]
    assert len(lignes) == 2 and any("option a" in d for d in diplomes) and any("option b" in d for d in diplomes)


@pytest.mark.parametrize("cod, mot", [("31712", "santé"), ("8296", "classe préparatoire"), ("23289", "paramédicales")])
def test_insertion_sans_source_dite(par_code, cod, mot):
    ins = par_code[cod]["insertion"]
    assert ins["statut"] == "non_disponible" and mot in ins["raison"]


def test_ingenieur_plusieurs_diplomes_non_disponible(par_code):
    assert "diplômes d'ingénieur" in par_code["47188"]["insertion"]["raison"]


# ── corpus ───────────────────────────────────────────────────────────────────────────────────
def test_trois_champs_sur_chaque_fiche_parcoursup(corpus):
    r = remplissage(corpus)
    for champ in ("cout", "alternance", "insertion"):
        assert "absent" not in r["parcoursup"][champ]
    assert sum(r["parcoursup"]["cout"].values()) == len(FICHES)


def test_entree_intacte(constructeur):
    entree = [copy.deepcopy(f) for f in FICHES.values()]
    avant = json.dumps(entree, sort_keys=True)
    constructeur.construire(entree)
    assert json.dumps(entree, sort_keys=True) == avant


def test_autres_sources_recopiees(constructeur):
    autre = {"source": "monmaster", "nom": "Master X", "insertion_pro": {"source": "insersup_mesr"}}
    assert constructeur.construire([autre])[0] == autre


# ── texte ────────────────────────────────────────────────────────────────────────────────────
def test_texte_cout_insertion_alternance(par_code):
    t = fiche_to_text(par_code["4974"])
    assert "droits d'inscription 178 euros par an" in t and "CVEC) 105 euros" in t
    assert "InserSup, promotion 2024" in t and "tous sites de l'établissement" in t
    assert "44,83 %" in t and "emploi stable" not in t
    assert "médiane régionale" not in t  # l'ancienne insertion discipline x région n'est plus écrite


def test_texte_onisep_garde_le_texte_source(par_code):
    t = fiche_to_text(par_code["23289"])
    assert "« 0 euros en 2026 (gratuit en apprentissage) »" in t
    assert "ne dit pas si des droits d'inscription ou la CVEC s'y ajoutent" in t


def test_texte_non_disponible_dit_pourquoi(par_code):
    t = fiche_to_text(par_code["47188"])
    assert "Coût : non disponible (aucune formation de ce lieu d'enseignement dans le jeu Onisep)" in t


def test_texte_apprentissage_sans_taux_acces(par_code):
    t = fiche_to_text(par_code["28094"])
    assert "Taux d'accès : non publié pour les formations en apprentissage" in t
    assert "vœux en recherche de contrat" in t and "fr-esr-parcoursup-apprentissage" in t


def test_corpus_a_texte_inchange():
    """Une fiche sans champ B garde exactement le texte de l'étape A (ancienne insertion comprise)."""
    fiche = next(f for f in FICHES.values() if f.get("insertion_pro"))
    t = fiche_to_text(fiche)
    assert "Coût" not in t and "Alternance" not in t and "médiane régionale" in t


# ── contrôles : muets sur le sain, rouges sur le cassé ───────────────────────────────────────
@pytest.mark.parametrize("cod", sorted(FICHES) + ["28094"])
def test_controles_muets_sur_le_corpus(par_code, cod):
    fiche = par_code[cod]
    texte = fiche_to_text(fiche)
    assert controler(fiche, texte) == [] and controler_etape_b(fiche, texte) == []


def _sans(fiche, champ):
    f = copy.deepcopy(fiche)
    del f[champ]
    return f


@pytest.mark.parametrize("levier, defaut", [
    (lambda f: (_sans(f, "insertion"), None), "insertion_absent"),
    (lambda f: (_sans(f, "alternance"), None), "alternance_absent"),
    (lambda f: (f, fiche_to_text(f).replace("178 euros", "180 euros")), "cout_montant_non_ecrit"),
    (lambda f: (f, fiche_to_text(f).replace("tableau ministériel", "tableau")), "cout_sans_source"),
    (lambda f: (f, fiche_to_text(f) + " | Insertion professionnelle (InserSup ; médiane régionale pour ce type)"),
     "insertion_approchee_ecrite"),
    (lambda f: (f, fiche_to_text(f) + " | taux d'emploi stable à 12 mois 84,6 %"), "emploi_stable_sans_definition"),
    (lambda f: (f, fiche_to_text(f).split(" | Coût")[0]), "cout_non_ecrit"),
])
def test_controles_rougissent(par_code, levier, defaut):
    fiche, texte = levier(copy.deepcopy(par_code["4974"]))
    texte = texte if texte is not None else fiche_to_text(fiche)
    assert defaut in controler_etape_b(fiche, texte)


def test_controle_raison_manquante(par_code):
    fiche = copy.deepcopy(par_code["47188"])
    fiche["cout"]["raison"] = ""
    assert "cout_non_disponible_sans_raison" in controler_etape_b(fiche, fiche_to_text(fiche))


def test_non_disponible_exige_une_raison(ref):
    with pytest.raises(ValueError):
        ref.non_disponible("")


# ── alternance : texte regroupé (retour de Jarvis du 23/09/2026 sur la PR #179) ──────────────
def _avec_formations(fiche: dict, formations: list[dict]) -> dict:
    """Levier explicite : remplace la liste des formations rattachées d'une fiche réelle."""
    f = copy.deepcopy(fiche)
    f["alternance"]["valeur"] = {"existe_en_apprentissage": True, "formations": formations}
    return f


def _formation(cod, etab, cap, cfa=None, precision=None, par="commune"):
    return {"cod_aff_form": cod, "etablissement": etab, "ville": "Paris", "capacite": cap,
            "cfa_partenaire": cfa, "precision": precision, "rattachee_par": par}


def test_partenaire_lu_dans_le_libelle_complet():
    from src.collect.alternance import partenaire
    base = {"g_ea_lib_vx": "Lycée Raspail", "lib_for_voe_ins": "BTS - Production - Electrotechnique - en apprentissage"}
    assert partenaire(base | {"lib_comp_voe_ins": "Lycée Raspail - CFA académique de Paris - BTS - Production - Electrotechnique - en apprentissage"}) == "CFA académique de Paris"
    assert partenaire(base | {"lib_comp_voe_ins": "CFA X - Lycée Raspail - BTS - Production - Electrotechnique - en apprentissage"}) == "CFA X"
    assert partenaire(base | {"lib_comp_voe_ins": "Lycée Raspail - BTS - Production - Electrotechnique - en apprentissage"}) is None


def test_meme_etablissement_deux_cfa_regroupes(par_code):
    f = _avec_formations(par_code["8882"], [_formation("1", "Lycée R", 10, "CFA A"), _formation("2", "Lycée R", 10, "CFA B")])
    t = fiche_to_text(f)
    assert "Lycée R à Paris (2 formations, 20 places : avec CFA A : 10 places / avec CFA B : 10 places)" in t
    assert controler_etape_b(f, t) == []


def test_formations_indistinctes_nommees_par_numero(par_code):
    f = _avec_formations(par_code["8882"], [_formation("44011", "CFA E", 30), _formation("44105", "CFA E", 30)])
    t = fiche_to_text(f)
    assert "le jeu ouvert ne dit pas ce qui les distingue" in t and "n° 44011" in t and "n° 44105" in t
    assert "alternance_doublon" not in controler_etape_b(f, t)


def test_plus_de_cinq_etablissements_resume(par_code):
    fs = [_formation(str(i), f"Lycée {i}", 10) for i in range(6)] + [_formation("9", "Lycée Saint Michel", 12, par="uai")]
    f = _avec_formations(par_code["8882"], fs)
    t = fiche_to_text(f)
    assert "7 formations en apprentissage du même diplôme dans 7 établissements de la même commune (Paris), 72 places au total" in t
    assert "dans le même établissement : Lycée Saint Michel à Paris (12 places)" in t
    assert "Lycée 3" not in t and controler_etape_b(f, t) == []


@pytest.mark.parametrize("ajout, defaut", [
    (" ; ".join(f"Lycée {i} à Paris (10 places)" for i in range(6)), "alternance_liste_trop_longue"),
    ("INSTA à Paris (120 places) ; INSTA à Paris (120 places)", "alternance_doublon"),
])
def test_controle_alternance_rougit(par_code, ajout, defaut):
    """Texte de l'ancienne forme (liste plate), réécrit par levier : le contrôle doit le voir."""
    f = par_code["8882"]
    t = fiche_to_text(f)
    ancien = next(p for p in t.split(" | ") if p.startswith("Alternance"))
    t = t.replace(ancien, "Alternance (Parcoursup apprentissage, session 2025) : ce diplôme existe aussi en apprentissage, même établissement ou même commune : " + ajout)
    assert defaut in controler_etape_b(f, t)

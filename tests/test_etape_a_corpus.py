"""Étape A : construction du corpus, verrou des sources, mesure du banc.

Le constructeur reçoit ses entrées injectées : ces tests tournent sans les fichiers bruts.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from src.collect import sources_officielles as so
from src.collect.communes import ReferentielCommunes
from src.collect.corpus_etape_a import ConstructeurEtapeA
from src.collect.corpus_etape_a import main as construire_main
from src.collect.domaines import charger_table
from src.eval.donnee.banc_textes import mesurer, present

FIXTURES = Path(__file__).parent / "fixtures/etape_a"


def _ligne(cod: str, **extra) -> dict:
    base = {
        "cod_aff_form": cod, "fili": "PASS", "lib_for_voe_ins": "Licence - Parcours d'Accès Spécifique Santé (PASS)",
        "g_ea_lib_vx": "Université de Lille", "ville_etab": "Lille", "dep": "59", "acad_mies": "Lille",
        "form_lib_voe_acc": "Licence - Sciences - technologies - santé",
        "fil_lib_voe_acc": "Parcours d'Accès Spécifique Santé (PASS)", "taux_acces_ens": "17", "capa_fin": "360",
        "voe_tot": "5000", "acc_tot": "350", "pct_tbf": "10", "pct_mention_nonrenseignee": "0",
        "lien_form_psup": f"https://dossierappel.parcoursup.fr/x?g_ta_cod={cod}",
    }
    base.update(extra)
    return base


@pytest.fixture
def constructeur() -> ConstructeurEtapeA:
    officiel = pd.DataFrame([_ligne("27163"), _ligne("29183"), _ligne("1", fili="BTS", lib_for_voe_ins="BTS - Services - Banque",
                                                                       g_ea_lib_vx="Lycée X", form_lib_voe_acc="BTS - Services",
                                                                       fil_lib_voe_acc="Banque")])
    return ConstructeurEtapeA(
        officiel=officiel,
        intitules={"27163": "Licence - Parcours d'Accès Spécifique Santé (PASS) - option Mathématiques",
                   "29183": "Licence - Parcours d'Accès Spécifique Santé (PASS) - option Droit"},
        communes=ReferentielCommunes(FIXTURES / "cog_extrait.csv"),
        regles=charger_table(),
        historique={2025: {}},
        date_collecte="2026-09-23",
    )


@pytest.fixture
def reference() -> list[dict]:
    return [
        {"source": "monmaster", "nom": "Master X", "ville": "TALENCE CEDEX"},
        {"source": "parcoursup", "cod_aff_form": "27163", "nom": "Licence - Parcours d'Accès Spécifique Santé (PASS)",
         "etablissement": "Université de Lille", "ville": "Lille", "domaine": "sante",
         "debouches": [{"libelle": "Médecin"}], "insertion_pro": {"source": "insersup_mesr", "taux_emploi_12m": 0.8}},
    ]


def test_options_pass_reingerees_avec_heritage(constructeur, reference):
    corpus = constructeur.construire(reference)
    ps = [f for f in corpus if f.get("source") == "parcoursup"]
    assert [f["cod_aff_form"] for f in ps] == ["27163", "29183", "1"]
    nouvelle = ps[1]
    assert nouvelle["precision_formation"] == "option Droit"
    assert nouvelle["debouches"] == [{"libelle": "Médecin"}]
    assert nouvelle["provenance"]["herite_de"] == {
        "cod_aff_form": "27163", "champs": ["domaine", "debouches", "insertion_pro"]}
    assert nouvelle["collected_at"] == {"parcoursup": "2026-09-23"}
    # La fiche sans sœur ne reçoit aucun enrichissement inventé.
    assert "debouches" not in ps[2] and "herite_de" not in ps[2]["provenance"]
    assert constructeur.stats["creees"] == 2 and constructeur.stats["corrigees"] == 1


def test_fiche_existante_corrigee(constructeur, reference):
    fiche = constructeur.construire(reference)[1]
    assert (fiche["ville"], fiche["code_insee"], fiche["academie"]) == ("Lille", "59350", "Lille")
    assert (fiche["domaine"], fiche["domaine_regle"]) == ("sante", "S01")
    assert fiche["admission"]["volumes"]["admis_total"] == 350
    assert fiche["profil_admis"]["mentions_pct"]["tbf"] == 10.0


def test_reference_intacte_et_autres_sources_identiques(constructeur, reference):
    avant = copy.deepcopy(reference)
    corpus = constructeur.construire(reference)
    assert reference == avant
    assert corpus[0] == avant[0]


def test_sortie_distincte_de_la_reference(tmp_path):
    ref = tmp_path / "formations.json"
    ref.write_text("[]", encoding="utf-8")
    with pytest.raises(SystemExit):
        construire_main(["--reference", str(ref), "--sortie", str(ref)])


# ── verrou des sources : une empreinte divergente arrête le pipeline ──────────────────


def test_empreinte_divergente_refusee(tmp_path, monkeypatch):
    brut = tmp_path / "data/raw/parcoursup_2025.csv"
    brut.parent.mkdir(parents=True)
    brut.write_bytes(b"a;b\n1;2\n")
    verrou = tmp_path / "verrou.json"
    verrou.write_text(json.dumps({"parcoursup_2025": {"sha256": hashlib.sha256(b"a;b\n1;2\n").hexdigest()}}))
    monkeypatch.setattr(so, "RACINE", tmp_path)
    monkeypatch.setattr(so, "VERROU", verrou)
    assert so.chemin_verifie("parcoursup_2025") == brut
    brut.write_bytes(b"a;b\n1;3\n")  # la source change sans mise à jour du verrou
    with pytest.raises(so.EmpreinteDivergente):
        so.chemin_verifie("parcoursup_2025")


# ── mesure du banc ────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("valeur,unite,texte,attendu", [
    (34.0, "%", "taux d'accès 34 %", True),
    (77.8, "%", "12 mois 78%", True),
    (34.0, "%", "340 places", False),
    (96, "places", "96 places", True),
    (96, "places", "taux 96 %", False),     # typé : un pourcentage n'est pas un effectif
    (1017, "candidats", "1017 candidats", True),
    (1780, "euros nets par mois", "salaire médian net : 1780€/mois", True),
])
def test_presence_typee(valeur, unite, texte, attendu):
    assert present(valeur, unite, texte) is attendu


def test_mesure_banc_et_temoin():
    banc = {"items": [
        {"domaine": "sante", "attendus": {"chiffres": [
            {"valeur": 17, "unite": "%", "champ": "t", "fiche": {"cod_aff_form": "1"}}]}},
        {"domaine": "maths", "attendus": {"chiffres": [
            {"valeur": 55, "unite": "%", "champ": "t", "fiche": {"cod_aff_form": "2"}}]}},
    ]}
    corpus = [{"source": "parcoursup", "cod_aff_form": "1", "t": "17 %"},
              {"source": "parcoursup", "cod_aff_form": "2", "t": "rien"}]
    r = mesurer(banc, corpus, lambda f: f["t"])
    assert (r["presents"], r["chiffres_mesures"], r["temoin_hasard"]) == (1, 2, 0.0)
    assert r["absents"] == [{"fiche": "psup:2", "champ": "t", "valeur": 55, "unite": "%"}]

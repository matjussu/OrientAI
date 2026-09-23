"""Étape C : base structurée, fonctions à filtres fermés, gate (contrat results/donnee_etape_c/CONTRACT.md).

Les tests unitaires tournent sur une mini-base construite avec le vrai schéma : aucun fichier de données
n'est requis. Les tests sur la vraie base sont sautés quand elle n'a pas été construite.
"""
from __future__ import annotations

import json
import math
import sqlite3
from pathlib import Path

import pytest

from src.base_c import SCHEMA, haversine_km, normaliser_departement
from src.base_c import outils
from src.collect import base_etape_c as bc
from src.collect import pipeline_donnee
from src.collect import sources_officielles as so
from src.eval import gate_c

RACINE = Path(__file__).resolve().parents[1]
VRAIE_BASE = RACINE / "data/processed/base_etape_c.sqlite"


# ── Mini-base ──────────────────────────────────────────────────────────────────────────────
CENTRE = (48.0, 2.0)  # commune de référence « 99001 »


def _mini_base(tmp_path: Path) -> Path:
    p = tmp_path / "mini.sqlite"
    con = sqlite3.connect(p)
    con.executescript(SCHEMA)
    con.execute("INSERT INTO source VALUES ('s', 'source test', 'https://exemple.test', 'LO', '2026-09-23', NULL, NULL)")
    for champ, sessions in (("taux_acces", "psup=2025"), ("places", "psup=2025"), ("part_bac_pro", "psup=2025")):
        con.execute("INSERT INTO champ VALUES (?, 'psup', '', ?, '', '%', 'nombre', 'formation', '', '', ?, '', '')",
                    (champ, sessions, champ))
    con.execute("INSERT INTO commune VALUES ('99001', 'Référence', 'REFERENCE', '99', 'Région', ?, ?)", CENTRE)
    # (id, type, filière, taux, places, part_bac_pro, décalage en latitude en degrés)
    fiches = [
        ("psup:1", "licence", "Mathématiques", 50, 30, 10, 0.1),
        ("psup:2", "las", "Mathématiques", 49.99, 30, 20, 0.2),
        ("psup:3", "but", "Informatique", 8, 40, 20, 0.3),
        ("psup:4", "but", "Informatique", 7.9, 40, 5, 0.4),
        ("psup:5", "but", "Informatique", None, 40, 5, 0.5),
    ]
    for fid, type_, filiere, taux, places, pbp, dlat in fiches:
        con.execute("INSERT INTO formation (id, espace, identifiant_source, intitule, type, filiere, apprentissage, domaine, "
                    "derniere_session) VALUES (?, 'psup', ?, ?, ?, ?, 0, 'test', '2025')",
                    (fid, fid.split(":")[1], f"Formation {fid}", type_, filiere))
        con.execute("INSERT INTO lieu (id, rang, commune, code_insee, code_departement, region, lat, lon, precision_geo, source_id) "
                    "VALUES (?, 1, 'X', '99001', '99', 'Région', ?, ?, 'formation', 's')", (fid, CENTRE[0] + dlat, CENTRE[1]))
        for champ, v in (("taux_acces", taux), ("places", places), ("part_bac_pro", pbp)):
            if v is None:
                con.execute("INSERT INTO valeur (id, champ, session, statut, raison, source_id, portee) VALUES "
                            "(?, ?, '2025', 'non_disponible', 'champ vide', 's', 'formation')", (fid, champ))
            else:
                con.execute("INSERT INTO valeur (id, champ, session, valeur_num, statut, source_id, portee) VALUES "
                            "(?, ?, '2025', ?, 'disponible', 's', 'formation')", (fid, champ, v))
    con.commit()
    con.close()
    return p


@pytest.fixture()
def base(tmp_path):
    b = outils.Base.ouvrir(_mini_base(tmp_path))
    yield b
    b.fermer()


def _ids(res):
    return [r["id"] for r in res["resultats"]]


# ── Bornes (contrat v0.1 §8) : une valeur exactement sur chaque seuil ───────────────────────
def test_min_inclusif_valeur_sur_le_seuil(base):
    res = outils.chercher_formations(base, types=["licence"], taux_acces_min=50)
    assert _ids(res) == ["psup:1"]  # 50 passe « >= 50 », 49,99 non


def test_max_strict_valeur_sur_le_seuil(base):
    res = outils.chercher_formations(base, types=["but"], taux_acces_max=8)
    assert _ids(res) == ["psup:4"]  # 7,9 passe « < 8 », 8 non
    assert res["ecartees_non_disponible"] == 1  # psup:5 n'a pas de taux : écartée et comptée


def test_pres_de_inclusif_distance_exactement_egale_au_rayon(base):
    d = haversine_km(CENTRE[0] + 0.3, CENTRE[1], *CENTRE)
    res = outils.chercher_formations(base, pres_de={"code_insee": "99001", "rayon_km": d})
    assert "psup:3" in _ids(res)
    assert "psup:4" not in _ids(res)
    assert _ids(res) == ["psup:1", "psup:2", "psup:3"]  # sans tri : du plus proche au plus loin


def test_part_bac_pro_min_inclusif(base):
    assert _ids(outils.chercher_formations(base, part_bac_pro_min=20)) == ["psup:2", "psup:3"]


def test_licence_inclut_las_mais_las_n_inclut_pas_licence(base):
    assert _ids(outils.chercher_formations(base, types=["licence"])) == ["psup:1", "psup:2"]
    assert _ids(outils.chercher_formations(base, types=["las"])) == ["psup:2"]


def test_tri_desc_non_disponible_en_dernier(base):
    res = outils.chercher_formations(base, types=["but"], tri={"champ": "taux_acces", "sens": "desc"})
    assert _ids(res) == ["psup:3", "psup:4", "psup:5"]


def test_filtre_ferme_refuse_une_filiere_inconnue_avec_candidats(base):
    with pytest.raises(outils.FiltreInvalide, match="Informatique"):
        outils.chercher_formations(base, filieres=["Informatiqeu"])


@pytest.mark.parametrize("args", [{"limite": 51}, {"limite": 0}, {"pres_de": {"code_insee": "99001", "rayon_km": 301}},
                                  {"types": ["doctorat"]}, {"tri": {"champ": "nom", "sens": "desc"}},
                                  {"pres_de": {"code_insee": "00000", "rayon_km": 10}}])
def test_filtres_bornes_refusent_le_hors_liste(base, args):
    with pytest.raises(outils.FiltreInvalide):
        outils.chercher_formations(base, **args)


def test_filtres_appliques_renvoyes_normalises(base):
    res = outils.chercher_formations(base, types=["licence"], pres_de={"code_insee": "99001", "rayon_km": 50})
    f = res["filtres_appliques"]
    assert f["types"] == ["las", "licence"]
    assert f["pres_de"]["commune"] == "Référence" and "vol d'oiseau" in f["pres_de"]["mesure"]


def test_chaque_chiffre_rendu_porte_sa_source(base):
    res = outils.chercher_formations(base, types=["licence"])
    v = res["resultats"][0]["valeurs"]["taux_acces@2025"]
    assert v["source_id"] == "s" and res["sources"]["s"]["url"] == "https://exemple.test"


# ── Contraintes du schéma : garanties structurelles, vues refuser ───────────────────────────
@pytest.mark.parametrize("ligne", [
    ("psup:1", "places", "2024", None, "non_disponible", None, "s", None, "formation"),          # non disponible sans raison
    ("psup:1", "places", "2024", None, "disponible", None, "s", None, "formation"),              # disponible sans valeur
    ("psup:1", "places", "2024", 3, "disponible", None, None, None, "formation"),                # disponible sans source
    ("psup:1", "places", "2024", None, "non_disponible", "vide", None, "x=1", "formation"),       # identifiant sans source
    ("psup:1", "places", "2024", 3, "disponible", None, "s", None, "departementale"),            # portée hors liste
    ("psup:1", "places", "2024", 3, "disponible", None, "inconnue", None, "formation"),          # source inexistante
])
def test_contraintes_refusent_les_lignes_fautives(tmp_path, ligne):
    con = sqlite3.connect(_mini_base(tmp_path))
    con.execute("PRAGMA foreign_keys = ON")
    with pytest.raises(sqlite3.IntegrityError):
        con.execute("INSERT INTO valeur (id, champ, session, valeur_num, statut, raison, source_id, identifiant_source, portee) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", ligne)


def test_contrainte_lieu_sans_coordonnees_doit_le_dire(tmp_path):
    con = sqlite3.connect(_mini_base(tmp_path))
    with pytest.raises(sqlite3.IntegrityError):
        con.execute("INSERT INTO lieu (id, rang, lat, lon, precision_geo) VALUES ('psup:1', 2, NULL, NULL, 'commune')")


# ── Distance, départements, types ──────────────────────────────────────────────────────────
def test_haversine_identites():
    assert math.isclose(haversine_km(0, 0, 0, 1), 2 * math.pi * 6371 / 360, rel_tol=1e-12)
    assert math.isclose(haversine_km(0, 0, 90, 0), math.pi * 6371 / 2, rel_tol=1e-12)
    assert haversine_km(48.1, -1.7, 48.1, -1.7) == 0


@pytest.mark.parametrize("brut,attendu", [("044", "44"), ("059", "59"), ("1", "01"), ("974", "974"), ("02A", "2A"),
                                           ("2B", "2B"), ("75", "75"), (None, None)])
def test_normaliser_departement(brut, attendu):
    assert normaliser_departement(brut) == attendu


@pytest.mark.parametrize("fili,type_formation,attendu", [
    ("PASS", "PASS (parcours d'accès spécifique santé)", "pass"),
    ("Licence_Las", "LAS (licence avec option accès santé)", "las"),
    ("Autre formation", "D.E Ergothérapeute", "diplome_sante"),
    ("Autre formation", "DTS Imagerie médicale et radiologie thérapeutique", "diplome_sante"),
    ("Autre formation", "Certificat de capacité d'Orthophoniste", "diplome_sante"),
    ("Autre formation", "Cycle Universitaire Préparatoire aux Grandes Ecoles", "cupge"),
    ("Autre formation", "Titre professionnel - Développeur web et web mobile (Bac +2)", "titre_pro"),
    ("Autre formation", "FCIL", "autre"),
    ("Ecole de Commerce", "École de commerce, recrutement post-bac", "autre"),
])
def test_types_courts(fili, type_formation, attendu):
    assert bc.type_court(bc.charger_types(), fili, type_formation) == attendu


def test_chemin_lit_un_element_de_liste():
    assert bc.chemin({"cout": {"valeur": {"fourchette_eur": [10, 20]}}}, "cout.valeur.fourchette_eur.1") == 20
    assert bc.chemin({"a": [1]}, "a.3") is None


def test_identifiant_deduit_de_l_export():
    assert bc.identifiant_deduit("psup:7596", "psup", "psup=capa_fin|psup_app=capa_fin") == "cod_aff_form=7596;champ=capa_fin"
    assert bc.identifiant_deduit("mm:ABC", "mm", "mm=col") == "ifc=ABC;champ=col"


def test_catalogue_des_champs_coherent():
    champs = bc.charger_champs()
    for nom, c in champs.items():
        assert not c["parent"] or c["parent"] in champs, nom
        assert c["portee"] in ("formation", "etablissement", "universite", "nationale", "regionale"), nom
        assert c["libelle"] and c["definition"], nom


# ── Verrou : un export JSON compte ses éléments ─────────────────────────────────────────────
def test_empreinte_json_compte_les_elements(tmp_path):
    p = tmp_path / "x.json"
    p.write_text(json.dumps([{"a": 1}, {"a": 2}, {"a": 3}]))
    assert so.empreinte(p)["lignes"] == 3


# ── Pipeline : l'étape C suit B-2, et un échec arrête tout ─────────────────────────────────
def test_pipeline_enchaine_c_apres_b2(monkeypatch):
    appels = []
    for nom, mod in (("verrou", pipeline_donnee.sources_officielles), ("A", pipeline_donnee.corpus_etape_a),
                     ("B1", pipeline_donnee.corpus_etape_b), ("B2", pipeline_donnee.corpus_etape_b2),
                     ("C", pipeline_donnee.base_etape_c)):
        monkeypatch.setattr(mod, "main", lambda argv=None, n=nom: appels.append(n) or 0)
    assert pipeline_donnee.main([]) == 0
    assert appels == ["verrou", "A", "B1", "B2", "C"]


def test_pipeline_n_enchaine_pas_c_si_b2_echoue(monkeypatch):
    appels = []
    for nom, mod, code in (("verrou", pipeline_donnee.sources_officielles, 0), ("A", pipeline_donnee.corpus_etape_a, 0),
                           ("B1", pipeline_donnee.corpus_etape_b, 0), ("B2", pipeline_donnee.corpus_etape_b2, 1),
                           ("C", pipeline_donnee.base_etape_c, 0)):
        monkeypatch.setattr(mod, "main", lambda argv=None, n=nom, c=code: appels.append(n) or c)
    assert pipeline_donnee.main([]) == 1
    assert "C" not in appels


# ── Verdict du gate ────────────────────────────────────────────────────────────────────────
def _rendu(i, taux=None):
    return {"id": i, "valeurs": {} if taux is None else {"taux_acces@2025": {"valeur": taux, "statut": "disponible", "portee": "formation"}}}


def test_verdict_exact_frontiere_ni_juste_ni_fausse(base):
    req = {"attendus": ["psup:1", "psup:2"], "mode": "exact", "frontiere": ["psup:3"]}
    assert gate_c.verdict(base, req, [_rendu("psup:1"), _rendu("psup:2"), _rendu("psup:3")], None)["juste"]
    assert gate_c.verdict(base, req, [_rendu("psup:1"), _rendu("psup:2")], None)["juste"]
    v = gate_c.verdict(base, req, [_rendu("psup:1"), _rendu("psup:4")], None)
    assert not v["juste"] and v["manquantes"] == ["psup:2"] and v["en_trop"] == ["psup:4"]


def test_verdict_vide(base):
    req = {"attendus": [], "mode": "vide"}
    assert gate_c.verdict(base, req, [], None)["juste"]
    assert not gate_c.verdict(base, req, [_rendu("psup:1")], None)["juste"]


def test_verdict_ordre_ex_aequo_permutables(base):
    req = {"attendus": ["psup:1", "psup:2", "psup:3"], "mode": "exact", "ordre": True}
    tri = {"champ": "taux_acces", "sens": "desc"}
    ok = [_rendu("psup:1", 50), _rendu("psup:3", 25), _rendu("psup:2", 25)]
    assert gate_c.verdict(base, req, ok, tri)["juste"]
    faux = [_rendu("psup:2", 25), _rendu("psup:1", 50), _rendu("psup:3", 25)]
    assert not gate_c.verdict(base, req, faux, tri)["juste"]


def test_verdict_valeur_egalite_stricte(base):
    req = {"attendus": ["psup:1"], "mode": "exact", "valeurs": [{"fiche": "psup:1", "champ": "taux_acces", "valeur": 50}]}
    assert gate_c.verdict(base, req, [_rendu("psup:1", 50)], None)["juste"]
    assert not gate_c.verdict(base, req, [_rendu("psup:1", 50.1)], None)["juste"]
    assert not gate_c.verdict(base, req, [_rendu("psup:1")], None)["juste"]  # valeur non rendue = fausse


# ── Vraie base (sautés si elle n'a pas été construite) ──────────────────────────────────────
@pytest.mark.skipif(not VRAIE_BASE.exists(), reason="base de l'étape C non construite")
def test_temoin_psup_7596_de_bout_en_bout():
    b = outils.Base.ouvrir(VRAIE_BASE)
    try:
        f = outils.lire_fiche(b, "psup:7596")
        assert f["valeurs"]["taux_acces@2025"]["valeur"] == 34
        assert f["valeurs"]["places@2025"]["valeur"] == 96
        assert f["sources"]["parcoursup_2025"]["url"].startswith("https://")
    finally:
        b.fermer()


@pytest.mark.skipif(not VRAIE_BASE.exists(), reason="base de l'étape C non construite")
def test_cas_test_rennes_rend_vide_puis_laval():
    b = outils.Base.ouvrir(VRAIE_BASE)
    try:
        vide = outils.chercher_formations(b, types=["but"], filieres=["Informatique"], taux_acces_min=50,
                                          pres_de={"code_insee": "35238", "rayon_km": 50})
        assert vide["nb_resultats"] == 0
        large = outils.chercher_formations(b, types=["but"], filieres=["Informatique"],
                                           pres_de={"code_insee": "35238", "rayon_km": 100})
        assert large["resultats"][0]["id"] == "psup:6231" and large["resultats"][0]["distance_km"] == 69.2
    finally:
        b.fermer()

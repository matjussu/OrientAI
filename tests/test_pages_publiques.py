"""Lecture des pages publiques (src/collect/pages_publiques.py).

Contrôle positif : sur les caches des inventaires de Jarvis (25/09, 88 pages Parcoursup et 40 masters), le parseur
redonne chaque valeur relevée par l'inventaire, écrit par un autre auteur avec d'autres motifs.
"""
import json
from pathlib import Path

import pytest

from src.collect.pages_publiques import Releve, lire_mm, lire_psup

INV = Path.home() / "projets/_orientai-ref/verticale-2026-09/concordance"
CLES = {"places_offertes_2025": "places_offertes", "candidats_2025": "candidats_ont_postule", "classes": "candidats_classes",
        "ont_pu_recevoir_une_proposition": "candidats_ont_pu_recevoir_une_proposition",
        "ont_choisi_d_integrer": "candidats_ont_choisi_d_integrer", "admis_repartition_bac": "admis_repartition",
        "pct_bac_general_admis": "repartition_admis_bac_general", "pct_bac_techno_admis": "repartition_admis_bac_techno",
        "pct_bac_pro_admis": "repartition_admis_bac_pro", "places_session_courante": "places_annee_en_cours"}
sans_inventaire = pytest.mark.skipif(not (INV / "inventaire.json").exists(), reason="inventaires hors dépôt")


@sans_inventaire
def test_parcoursup_redonne_l_inventaire_sur_88_pages():
    lignes = [l for l in json.loads((INV / "inventaire.json").read_text())["lignes"] if l["page"] in CLES]
    ecarts, n = [], 0
    for l in lignes:
        p = lire_psup((INV / "pages" / f"{l['code']}.html").read_text(encoding="utf-8", errors="replace"))
        n += 1
        if (p.get(CLES[l["page"]]) or {}).get("valeur") != l["valeur_page"]:
            ecarts.append((l["code"], l["page"], l["valeur_page"], p.get(CLES[l["page"]])))
    assert n > 900 and ecarts == []


@sans_inventaire
def test_masters_redonne_l_inventaire_sur_40_masters():
    fiches = json.loads((INV / "masters/inventaire_masters.json").read_text())["fiches"]
    for f in fiches:
        contenu = json.loads((INV / "masters/cache/api" / f"{f['uai']}_{f['ifc'][:8]}.json").read_text())["content"]
        lu = lire_mm(contenu, f["ifc"])
        assert (lu is not None) == f["trouvee"], f["ifc"]
        if lu is None:
            continue
        assert (lu.get("capacite_accueil") or {}).get("valeur") == f["col"]
        ind = f["indicateurs"]
        if "tauxAcces" in ind:
            from src.eval.concordance import _pourcent  # arrondi affiché, calculé par le code indépendant du contrôle
            assert lu["taux_acces"]["valeur"] == _pourcent(ind["tauxAcces"])
        if "rangDernierAppele" in ind:
            assert lu["rang_dernier_appele"]["valeur"] == ind["rangDernierAppele"]
        if "nbCandidaturesConfirmees" in ind:
            assert lu["candidatures_campagne_precedente"]["valeur"] == ind["nbCandidaturesConfirmees"]


def test_nombre_ne_mange_pas_l_annee_qui_precede():
    h = "<p>Calculés sur l'ensemble des candidats en 2025 1833 candidats ont postulé à cette formation</p>"
    assert lire_psup(h)["candidats_ont_postule"]["valeur"] == 1833
    h = "<p>en 2025 1 833 candidats ont postulé à cette formation</p>"
    assert lire_psup(h)["candidats_ont_postule"]["valeur"] == 1833


def test_repartition_lue_dans_son_bloc_seulement():
    h = ("<p>Répartition par type de bac des 46 candidats admis de cette formation en 2025 Bac général 100 % "
         "Bac technologique 0 % Bac professionnel 0 % Autres diplômes 0 %</p><p>Bac général Bac technologique</p>")
    p = lire_psup(h)
    assert [p[k]["valeur"] for k in ("repartition_admis_bac_general", "repartition_admis_bac_techno",
                                      "repartition_admis_bac_pro", "repartition_admis_autres")] == [100, 0, 0, 0]


class _Horloge:
    def __init__(self):
        self.t, self.dormi = 0.0, []

    def monotonic(self):
        return self.t

    def sleep(self, s):
        self.dormi.append(s)
        self.t += s


def test_releve_respecte_la_pause_reprend_sur_cache_et_inscrit_les_echecs(tmp_path):
    import urllib.error
    appels = []

    def ouvrir(req, timeout):
        appels.append(req.full_url)
        if "404" in req.full_url:
            raise urllib.error.HTTPError(req.full_url, 404, "absent", {}, None)
        return type("R", (), {"read": lambda self: b"<html>ok</html>"})()

    h = _Horloge()
    r = Releve(tmp_path, pause_s=1.5, ouvrir=ouvrir, horloge=h)
    assert r.obtenir("a.html", "http://x/1") == b"<html>ok</html>"
    assert r.obtenir("b.html", "http://x/404") is None
    assert r.manifeste["b.html"]["statut"] == 404 and "sha256" not in r.manifeste["b.html"]
    assert h.dormi == [1.5]                       # la 2e requête attend la pause complète
    r2 = Releve(tmp_path, pause_s=1.5, ouvrir=ouvrir, horloge=_Horloge())
    assert r2.obtenir("a.html", "http://x/1") == b"<html>ok</html>" and len(appels) == 2   # servi par le cache
    assert r2.empreinte() == r.empreinte()


def test_pourcentage_affiche_comme_la_fiche():
    from src.collect.pages_publiques import pourcentage_affiche
    from src.eval.concordance import _pourcent
    # 0,125 -> 13 % et 0,165 -> 17 % : rendu réel du 25/09 ; 0,145 -> 15 % (le flottant donnait 14,4999...)
    for x, attendu in ((0.125, 13), (0.165, 17), (0.145, 15), (0.12, 12), (0.999, 100), (0.004, 0), (0.005, 1)):
        assert pourcentage_affiche(x) == attendu == _pourcent(x), x

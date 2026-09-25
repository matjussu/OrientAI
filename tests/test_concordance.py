"""Contrôle de concordance (src/eval/concordance.py) : son parseur est indépendant de celui du constructeur, et les
deux doivent lire les mêmes chiffres sur les pages réelles."""
from pathlib import Path

import pytest

from src.collect.pages_publiques import lire_psup
from src.eval.concordance import DOUBLONS, chiffres_page_mm, chiffres_page_psup, texte

INV = Path.home() / "projets/_orientai-ref/verticale-2026-09/concordance"
CORRESP = {"places@2025": "places_offertes", "candidats_ont_postule@2025": "candidats_ont_postule",
           "candidats_classes@2025": "candidats_classes",
           "candidats_ont_pu_recevoir_une_proposition@2025": "candidats_ont_pu_recevoir_une_proposition",
           "candidats_ont_choisi_d_integrer@2025": "candidats_ont_choisi_d_integrer",
           "repartition_admis_bac_general@2025": "repartition_admis_bac_general",
           "repartition_admis_bac_techno@2025": "repartition_admis_bac_techno",
           "repartition_admis_bac_pro@2025": "repartition_admis_bac_pro",
           "repartition_admis_autres@2025": "repartition_admis_autres"}


@pytest.mark.skipif(not (INV / "pages").exists(), reason="pages de l'inventaire hors dépôt")
def test_les_deux_parseurs_lisent_les_memes_chiffres_sur_88_pages():
    n = 0
    for p in sorted((INV / "pages").glob("*.html")):
        h = p.read_text(encoding="utf-8", errors="replace")
        a, b = chiffres_page_psup(h), lire_psup(h)
        vus_b = {k: b[v]["valeur"] for k, v in CORRESP.items() if v in b}
        assert a == vus_b, p.name
        n += len(a)
    assert n > 700


def test_texte_ignore_scripts_et_styles():
    assert texte("<script>var x='1 places';</script><p>48 places</p><style>.a{}</style>") == "48 places"


def test_mm_absent_et_pourcentage_entier():
    contenu = [{"ifc": "A", "col": 15, "indicateursAnneeDerniere": {"tauxAcces": 0.125, "rangDernierAppele": 11}}]
    assert chiffres_page_mm(contenu, "B") is None
    assert chiffres_page_mm(contenu, "A") == {"capacite_accueil@2026": 15, "taux_acces@2025": 13, "rang_dernier_appele@2025": 11}


def test_liste_de_doublons_couvre_les_trois_espaces():
    assert set(DOUBLONS) == {"psup", "psup_app", "mm"} and "admis_bilan_final" in DOUBLONS["psup"]

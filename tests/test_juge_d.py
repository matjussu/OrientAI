"""Étape D, juge à l'aveugle : contexte neutre identique entre combinaisons (protocole §8, v0.1)."""
from __future__ import annotations

from src.eval import juge_d as jd
from src.eval.battery.judge import RUBRIC

FORMATIONS = {"psup:1": {"intitule": "BUT Info", "etablissement": "IUT", "espace": "psup", "commune": "Aubière"},
              "psup:2": {"intitule": "Licence", "etablissement": "UCA", "espace": "psup", "commune": "Clermont"}}
ITEM = {"persona": "lyceen", "tags": ["info"]}


def _rec(fmt, reponse, appels=None):
    return {"question": "q ?", "history": [], "answer": reponse, "exposees": ["psup:2", "psup:1"],
            "format": fmt, "appels_outil": appels or []}


def test_contexte_du_juge_identique_octet_pour_octet_hors_reponse():
    a = jd.prompt_juge(_rec("A", "REPONSE"), ITEM, FORMATIONS)
    c = jd.prompt_juge(_rec("C", "REPONSE", appels=[{"args": '{"id": "psup:1"}', "erreur": None}]), ITEM, FORMATIONS)
    assert a.encode() == c.encode()


def test_le_prompt_ne_revele_ni_format_ni_modele_ni_outil():
    p = jd.prompt_juge(_rec("C", "REPONSE", appels=[{"args": '{"id": "psup:1"}', "erreur": None}]), ITEM, FORMATIONS)
    for mot in ("lire_fiche", "format", "mistral", "glm", "Carte"):
        assert mot.lower() not in p.lower()


def test_la_reponse_differe_seule():
    a = jd.prompt_juge(_rec("A", "@@REP_A@@"), ITEM, FORMATIONS)
    b = jd.prompt_juge(_rec("B", "@@REP_B@@"), ITEM, FORMATIONS)
    assert a.replace("@@REP_A@@", "X") == b.replace("@@REP_B@@", "X") and a != b


def test_identifiant_opaque_stable_et_sans_combinaison_lisible():
    o = jd.opaque("g", "A-mistral-medium-2604", "V-INF-01", 0)
    assert o == jd.opaque("g", "A-mistral-medium-2604", "V-INF-01", 0) and "mistral" not in o and len(o) == 10


def test_rubrique_du_lot_0_mot_pour_mot():
    assert jd.RUBRIC is RUBRIC

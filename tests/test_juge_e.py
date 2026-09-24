"""Banc E, juge : contexte identique octet pour octet entre combinaisons, fiches et phrase présentes."""
from __future__ import annotations

from src.eval import juge_d as jd
from src.eval import juge_e as je

FORMATIONS = {"psup:1": {"intitule": "BUT Info", "etablissement": "IUT", "espace": "psup", "commune": "Aubière"},
              "psup:2": {"intitule": "Licence", "etablissement": "UCA", "espace": "psup", "commune": "Clermont"}}
CARTES = {"psup:1": "[fiche psup:1] BUT Info\n- Places : 96", "psup:2": "[fiche psup:2] Licence\n- Places : 300"}
ITEM = {"persona": "lyceen", "tags": ["info"]}


def _rec(fmt, reponse, appels=None):
    return {"question": "q ?", "history": [], "answer": reponse, "exposees": ["psup:2", "psup:1"],
            "format": fmt, "appels_outil": appels or []}


def test_contexte_identique_octet_pour_octet_entre_a_et_c():
    a = je.prompt_juge(_rec("A", "REPONSE"), ITEM, FORMATIONS, CARTES)
    c = je.prompt_juge(_rec("C", "REPONSE", appels=[{"args": '{"id": "psup:1"}', "erreur": None}]), ITEM,
                       FORMATIONS, CARTES)
    assert a.encode() == c.encode()


def test_prompt_de_d_inchange_puis_phrase_et_fiches_dans_l_ordre_d_exposition():
    rec = _rec("A", "REPONSE")
    p = je.prompt_juge(rec, ITEM, FORMATIONS, CARTES)
    assert p.startswith(jd.prompt_juge(rec, ITEM, FORMATIONS))
    assert je.PHRASE_JUGE in p and "juge-la sur tes connaissances" in p
    assert p.index("Places : 300") < p.index("Places : 96")


def test_la_reponse_differe_seule_et_rien_ne_revele_le_systeme():
    a = je.prompt_juge(_rec("A", "@@A@@"), ITEM, FORMATIONS, CARTES)
    c = je.prompt_juge(_rec("C", "@@C@@"), ITEM, FORMATIONS, CARTES)
    assert a.replace("@@A@@", "X") == c.replace("@@C@@", "X") and a != c
    for mot in ("lire_fiche", "mistral", "glm", "small", "carte courte"):
        assert mot not in a.lower()


def test_lots_de_six():
    assert je.TAILLE_LOT == 6

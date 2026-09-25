"""Lanceur multi-version : versions branchables, budget, arrêt au plafond, reprise. Faux versions, zéro réseau."""
import json

import pytest

from src.eval.multiversion import lanceur
from src.eval.multiversion.versions import charger, disponibles
from src.eval.multiversion.versions.chatgpt_web import lire_reponse


class Fausse:
    nom = "fausse"
    fils = 2
    modeles = ["gpt-5.5"]

    def __init__(self, entree=1000, sortie=1000):
        self.entree, self.sortie, self.appels = entree, sortie, 0

    def empreinte(self):
        return {"x": 1}

    def ask(self, question, history):
        self.appels += 1
        return {"reponse": f"r{len(history)}", "sources": [], "source_positions": [],
                "usage": {"gpt-5.5": {"entree": self.entree, "sortie": self.sortie, "non_mesures": 0}},
                "modele": "gpt-5.5"}


@pytest.fixture
def resultats(tmp_path, monkeypatch):
    monkeypatch.setattr(lanceur, "RESULTATS", tmp_path)
    return tmp_path


def test_versions_du_premier_run_disponibles():
    assert {"prod", "chatgpt", "chatgpt_web"} <= set(disponibles())


def test_version_inconnue_refusee():
    with pytest.raises(SystemExit):
        charger("v9")


def test_cout_au_prix_publie():
    # 1000 x 5 + 1000 x 30 par million = 0,035 USD ; 3 recherches web = 0,03 USD
    c, nm = lanceur.cout({"gpt-5.5": {"entree": 1000, "sortie": 1000}, "openai-web-search": {"entree": 3}})
    assert round(c, 6) == 0.065 and nm == 0


def test_modele_sans_prix_refuse():
    with pytest.raises(ValueError):
        lanceur.cout({"gpt-9": {"entree": 1, "sortie": 1}})


def test_joue_tout_le_banc_et_ecrit_le_budget(resultats):
    v = Fausse()
    stats = lanceur.jouer(v, "lot0", "t", log=lambda *_: None)
    items, _ = lanceur.charger_banc("lot0")
    assert stats["tours_joues"] == sum(len(i["turns"]) for i in items) == 67
    budget = json.loads((resultats / "t/budget.json").read_text())
    assert round(budget["depense_usd"]["openai"], 4) == round(67 * 0.035, 4)
    assert stats["arret"] is None


def test_arret_au_plafond_avant_de_depasser(resultats):
    # chaque tour coûte 0,035 USD ; plafond 0,2 : le lanceur doit s'arrêter avant de le franchir
    v = Fausse()
    stats = lanceur.jouer(v, "lot0", "t", log=lambda *_: None, plafonds={"openai": 0.2, "mistral": 8})
    budget = json.loads((resultats / "t/budget.json").read_text())
    assert stats["arret"] and stats["restantes"] > 0
    assert budget["depense_usd"]["openai"] <= 0.2


def test_plafond_saute_si_on_retire_le_garde(resultats, monkeypatch):
    # témoin : sans le garde, la même dépense franchit le plafond (le test précédent mesure donc bien le garde)
    monkeypatch.setattr(lanceur.Budget, "peut_jouer", lambda self, f, en_vol=0: None)
    lanceur.jouer(Fausse(), "lot0", "t", log=lambda *_: None, plafonds={"openai": 0.2, "mistral": 8})
    assert json.loads((resultats / "t/budget.json").read_text())["depense_usd"]["openai"] > 0.2


def test_usage_non_mesure_arrete_le_lanceur(resultats):
    class SansUsage(Fausse):
        def ask(self, q, h):
            r = super().ask(q, h)
            r["usage"]["gpt-5.5"]["non_mesures"] = 1
            return r
    stats = lanceur.jouer(SansUsage(), "lot0", "t", log=lambda *_: None)
    assert "sans usage mesuré" in stats["arret"]


def test_reprise_ne_rejoue_pas_les_conversations_faites(resultats):
    v = Fausse()
    lanceur.jouer(v, "lot0", "t", limite=["L01", "L02"], log=lambda *_: None)
    n = v.appels
    lanceur.jouer(v, "lot0", "t", limite=["L01", "L02"], log=lambda *_: None)
    assert v.appels == n


def test_empreinte_differente_refusee(resultats):
    with pytest.raises(SystemExit):
        lanceur.jouer(Fausse(), "lot0", "t", empreinte_attendue={"x": 2}, log=lambda *_: None)


def test_banc_modifie_refuse(monkeypatch):
    monkeypatch.setitem(lanceur.BANCS_SHA, "lot0", "000000000000")
    with pytest.raises(SystemExit):
        lanceur.charger_banc("lot0")


def test_lecture_reponse_web_compte_seulement_les_recherches_facturees():
    from types import SimpleNamespace as NS
    cit = lambda u: NS(type="url_citation", url=u, title="T" + u)  # noqa: E731
    r = NS(output=[NS(type="web_search_call", action=NS(type="search")),
                   NS(type="web_search_call", action=NS(type="open_page")),
                   NS(type="web_search_call", action=NS(type="search")),
                   NS(type="message", content=[NS(type="output_text", text="Bonjour",
                                                  annotations=[cit("a"), cit("b"), cit("a")])])])
    lu = lire_reponse(r)
    assert lu["texte"] == "Bonjour" and lu["recherches"] == 2
    assert [s["url"] for s in lu["sources"]] == ["a", "b"]

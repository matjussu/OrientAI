"""Étape D : formats de fiche et exposition gelée (protocole results/donnee_etape_d/PROTOCOLE.md).

Les tests sur la base C et le corpus B-2 sont sautés quand ces fichiers (hors git) sont absents.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.eval import format_d as fd

RACINE = Path(__file__).resolve().parents[1]
BASE = RACINE / "data/processed/base_etape_c.sqlite"
CORPUS = RACINE / "data/processed/formations_etape_b2.json"
DONNEES = BASE.exists() and CORPUS.exists()


def test_couples_lit_l_unite_et_ecarte_annees_et_url():
    c = fd.couples("Admission (session 2025) : taux d'accès 34 % ; 96 places ; 1 017 candidats | "
                   "Fiche : https://x.test/?g_ta_cod=7596 | 64,71 % à 6 mois")
    assert (34.0, "%") in [(v, u) for v, u, _ in c]
    assert (96.0, "places") in [(v, u) for v, u, _ in c]
    assert (1017.0, "candidats") in [(v, u) for v, u, _ in c]
    assert (64.71, "%") in [(v, u) for v, u, _ in c]
    assert 2025.0 not in fd.nombres("session 2025") and 7596.0 not in fd.nombres("https://x.test/?c=7596")


def test_valeur_lisible_booleen_et_nombre():
    assert fd.Formats._valeur_lisible({"valeur": 0, "unite": "0/1"}) == "non"
    assert fd.Formats._valeur_lisible({"valeur": 64.71, "unite": "%"}) == "64,71 %"
    assert fd.Formats._valeur_lisible({"valeur": 178, "unite": "EUR"}) == "178 euros"


def test_motifs_structurels_ne_couvrent_pas_une_valeur_ordinaire():
    assert fd._motif("Diplôme visé : bac+3") == "niveau"
    assert fd._motif("Admission (Parcoursup, session 2025) : taux d'accès 34 %") is None


def test_levier_inconnu_refuse():
    with pytest.raises(ValueError, match="inconnu"):
        fd.Formats.__init__(fd.Formats.__new__(fd.Formats), base=None, corpus=[], sabotage="rien")


@pytest.fixture(scope="module")
def reel():
    if not DONNEES:
        pytest.skip("base C ou corpus B-2 absents")
    from src.base_c.outils import Base
    base = Base.ouvrir(BASE)
    corpus = json.loads(CORPUS.read_bytes())
    yield base, corpus
    base.fermer()


def _formats(reel, sabotage=None):
    base, corpus = reel
    fm = fd.Formats(base, corpus, sabotage="")
    fm.sabotage = sabotage
    return fm


def test_controles_verts_sur_le_temoin(reel):
    fm = _formats(reel)
    assert fd.controle_b_contre_base(fm, ["psup:7596"])["vert"]
    assert fd.controle_b_contre_base(fm, ["psup:7596"], carte="c")["vert"]
    assert fd.controle_a_dans_b(fm, ["psup:7596"])["vert"]


def test_levier_valeur_rougit_les_trois_controles(reel):
    fm = _formats(reel, "carte_b_valeur")
    assert not fd.controle_b_contre_base(fm, ["psup:7596"])["vert"]
    assert not fd.controle_b_contre_base(fm, ["psup:7596"], carte="c")["vert"]
    assert not fd.controle_a_dans_b(fm, ["psup:7596"])["vert"]


def test_levier_manque_rougit_le_controle_champ_par_champ(reel):
    # A dans B reste vert : « 96 places » existe aussi en 2024. C'est la limite d'un contrôle par
    # valeur, et la raison d'être du contrôle champ par champ.
    fm = _formats(reel, "carte_b_manque")
    r = fd.controle_b_contre_base(fm, ["psup:7596"])
    assert not r["vert"] and r["exemples"][0]["cle"] == "places@2025"


def test_carte_courte_au_plus_sept_chiffres_et_renvoi_outil(reel):
    c = _formats(reel).carte_c("psup:7596")
    assert sum(1 for ligne in c.splitlines() if ligne.startswith("- ")) <= fd.MAX_COURTE
    assert 'lire_fiche("psup:7596")' in c


def test_option_du_pass_dans_l_entete(reel):
    assert "Antenne à BOULOGNE-SUR-MER" in _formats(reel).carte_b("psup:29571").splitlines()[0]


def test_exposition_deterministe_et_comptes(reel):
    from src.eval.exposition_d import BANC, construire
    if not BANC.exists():
        pytest.skip("banc vertical absent")
    banc = json.loads(BANC.read_bytes())
    fm = _formats(reel)
    e1, e2 = construire(banc, fm), construire(banc, fm)
    assert e1 == e2
    assert e1["n_attendus_critere"] + e1["n_attendus_hors"] == e1["n_attendus"] == 341
    assert all(len(c["exposees"]) <= fd_n() for c in e1["conversations"].values())


def fd_n():
    from src.eval.exposition_d import N_EXPOSEES
    return N_EXPOSEES

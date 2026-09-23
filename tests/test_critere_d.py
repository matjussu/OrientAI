"""Étape D, critère 1 : chiffres attendus cités justes (src/eval/critere_d.py)."""
from __future__ import annotations

from src.eval import critere_d as cd


def _a(valeur, unite, tour=0):
    return {"valeur": valeur, "unite": unite, "tour": tour}


def test_chiffres_typés():
    assert cd.chiffres("taux d'accès 34 %, 96 places, 1 017 candidats, 178 €, 110 propositions") == [
        (34.0, "pct"), (96.0, "places"), (1017.0, "effectif"), (178.0, "eur"), (110.0, "effectif")]
    assert cd.chiffres("en 2025, 3 pistes") == []


def test_cite_juste_a_la_tolerance_et_type():
    assert cd.cite(_a(34.0, "%"), ["environ 34 %"])
    assert cd.cite(_a(45.4, "%"), ["45 %"])                  # arrondi à l'entier, tolérance 0,51
    assert not cd.cite(_a(34.0, "%"), ["34 places"])        # même valeur, autre unité : non
    assert not cd.cite(_a(96, "places"), ["95 places"])
    assert cd.cite(_a(1017, "voeux"), ["1017 candidats"])  # effectif : le banc et les réponses nomment librement


def test_cite_regarde_le_tour_et_les_suivants_seulement():
    banc = {"items": [{"id": "c", "turns": ["q0", "q1"], "attendus": {"chiffres": [_a(34.0, "%", tour=1)]}}]}
    expo = {"conversations": {"c": {"cible_par_attendu": ["psup:1"]}}}
    assert cd.par_conversation(banc, expo, {("c", 0): "34 %", ("c", 1): "rien"})["c"]["cites"] == [False]
    assert cd.par_conversation(banc, expo, {("c", 0): "", ("c", 1): "34 %"})["c"]["cites"] == [True]


def test_hors_critere_non_compte():
    banc = {"items": [{"id": "c", "turns": ["q"], "attendus": {"chiffres": [_a(34.0, "%"), _a(5, "places")]}}]}
    expo = {"conversations": {"c": {"cible_par_attendu": ["psup:1", None]}}}
    pc = cd.par_conversation(banc, expo, {("c", 0): "34 % et 5 places"})
    assert pc["c"] == {"n": 1, "cites": [True], "hors": 1} and cd.taux(pc) == 1.0


def test_bootstrap_identique_rend_zero_et_ecart_positif_detecte():
    x = {f"c{i}": {"n": 2, "cites": [True, i % 2 == 0]} for i in range(30)}
    assert cd.bootstrap_delta(x, x, tirages=500) == {"delta": 0.0, "ic95": [0.0, 0.0]}
    r = {k: {"n": 2, "cites": [False, False]} for k in x}
    b = cd.bootstrap_delta(x, r, tirages=500)
    assert b["delta"] > 0 and b["ic95"][0] > 0


def test_temoin_confronte_une_autre_conversation():
    banc = {"items": [{"id": "a", "turns": ["q"], "attendus": {"chiffres": [_a(34.0, "%")]}},
                      {"id": "b", "turns": ["q"], "attendus": {"chiffres": [_a(77.0, "%")]}}]}
    expo = {"conversations": {"a": {"cible_par_attendu": ["x"]}, "b": {"cible_par_attendu": ["y"]}}}
    # a cite son propre chiffre, pas celui de b : témoin 0 ; si a cite aussi 77 %, témoin > 0
    assert cd.temoin(banc, expo, {("a", 0): "34 %", ("b", 0): "77 %"}) == 0.0
    assert cd.temoin(banc, expo, {("a", 0): "34 % et 77 %", ("b", 0): "77 %"}) > 0

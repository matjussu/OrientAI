"""Controle des chiffres cites (src/eval/battery/numbers.py).

Chaque garantie a son test de falsification : on casse la propriete (valeur deplacee, unite
changee, fiche retiree) et le statut doit changer.
"""
from src.eval.battery.corpus import Corpus
from src.eval.battery.numbers import NumberChecker, NumberSummary, extract_claims, fiche_values

LICENCE_INFO = {"nom": "Licence - Informatique", "etablissement": "Universite Toulouse III",
                "ville": "Toulouse", "source": "parcoursup", "taux_acces_parcoursup_2025": 87.4,
                "nombre_places": 420}
MASTER = {"nom": "Master MIAGE", "etablissement": "Universite de Lille", "ville": "Lille",
          "source": "monmaster",
          "insertion_pro": {"taux_emploi_12m": 0.91, "salaire_median_embauche": 2370}}
BTS = {"nom": "BTS SIO", "etablissement": "Lycee Baggio", "ville": "Lille", "source": "parcoursup",
       "taux_acces_parcoursup_2025": 32.0, "nombre_places": 24}


def corpus():
    return Corpus(path="/dev/null", fiches=[LICENCE_INFO, MASTER, BTS])


def test_extract_typed_claims_and_skip_bare_numbers():
    claims = extract_claims("En 2025, 3 pistes :\n- taux d'acces 87 %, 420 places\n- salaire 2 370 € net")
    assert [(c.value, c.unit) for c in claims] == [(87.0, "pct"), (420.0, "places"), (2370.0, "eur")]


def test_percentage_above_100_is_not_a_claim():
    assert extract_claims("une progression de 250 %") == []


def test_fiche_values_are_typed_and_ratios_become_percent():
    values = fiche_values(MASTER)
    assert 91.0 in values["pct"]
    assert 2370.0 in values["eur"]
    assert 2370.0 not in values["pct"]


def test_number_in_exposed_fiche_is_adosse():
    checks = NumberChecker(corpus()).check("Licence Info Toulouse : 87 % d'acces, 420 places", [0],
                                           anchor=False)
    assert [c["status"] for c in checks] == ["adosse", "adosse"]


def test_falsification_value_moved_is_not_adosse():
    checks = NumberChecker(corpus()).check("Licence Info Toulouse : 80 % d'acces", [0], anchor=False)
    assert checks[0]["status"] == "non_retrouve"


def test_falsification_unit_changed_is_not_adosse():
    # 420 existe dans la fiche, mais en places : cite en euros, il ne doit pas etre adosse.
    checks = NumberChecker(corpus()).check("frais de 420 €", [0], anchor=False)
    assert checks[0]["status"] == "non_retrouve"


def test_falsification_fiche_not_exposed_is_not_adosse():
    checks = NumberChecker(corpus()).check("87 % d'acces", [2], anchor=False)
    assert checks[0]["status"] == "non_retrouve"


def test_corpus_anchor_finds_a_number_the_line_designates():
    checks = NumberChecker(corpus(), anchor_k=1).check("BTS SIO au lycee Baggio a Lille : 32 %", [])
    assert checks[0]["status"] == "corpus"


def test_no_claim_gives_no_rate_not_a_neutral_value():
    summary = NumberSummary()
    summary.add(NumberChecker(corpus()).check("Aucune donnee chiffree ici.", [0], anchor=False), True)
    assert summary.n_claims == 0
    assert summary.rate("adosse") is None


def test_chance_rate_is_none_without_any_exposed_fiche():
    assert NumberChecker(corpus()).chance_rate(["87 %"], [[]]) is None


def test_chance_rate_uses_another_turn_fiches():
    checker = NumberChecker(corpus())
    # tour 1 cite la valeur de sa propre fiche ; le temoin le confronte a la fiche de l'autre tour
    assert checker.chance_rate(["87 %", "32 %"], [[0], [2]]) == 0.0

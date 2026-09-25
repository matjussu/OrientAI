"""Chiffres ecrits dans un tableau markdown, unite dans l'en-tete (defaut mesure en D, RAPPORT D section 7).

Temoin (regle 9) : le levier ORIENTIA_NUMBERS_SANS_TABLEAUX=1 coupe la correction ; les tests marques
`corrige` doivent alors rougir, et `test_levier_coupe_la_correction` le verifie dans le meme run.
"""
import pytest

from src.eval.battery.numbers import extract_claims, table_numbers

TABLEAU_COLONNES = """Voici la comparaison :

| Formation | Taux d'accès (%) | Places | Frais (€/an) |
|---|---|---|---|
| BUT Informatique Aubière | 34 | 96 | 178 |
| Licence Maths-Info UCA | 87,5 | 1 200 | 178 |
"""

TABLEAU_LIGNES = """| Indicateur | BUT Info |
|---|---|
| Candidats | 3 779 |
| Taux d'accès | 34 % |
| Rang du dernier appelé | 412 |
"""


def _pairs(text):
    return sorted((c.value, c.unit) for c in extract_claims(text))


def test_corrige_unite_en_entete_de_colonne():
    assert _pairs(TABLEAU_COLONNES) == sorted([
        (34.0, "pct"), (96.0, "places"), (178.0, "eur"),
        (87.5, "pct"), (1200.0, "places"), (178.0, "eur")])


def test_corrige_unite_dans_le_libelle_de_ligne():
    # « Candidats » n'est pas une unite de numbers.py (pct, eur, places) : rien. Le 34 % est lu par la
    # regle ordinaire (unite collee), une seule fois. « Rang » n'a pas d'unite : hors perimetre.
    assert _pairs(TABLEAU_LIGNES) == [(34.0, "pct")]
    effectifs = table_numbers(TABLEAU_LIGNES, lambda lib: "effectif" if "candidat" in lib.lower() else None)
    assert [(v, u) for v, u, _ in effectifs] == [(3779.0, "effectif")]


def test_nombre_sans_unite_identifiable_reste_hors_perimetre():
    text = "| Formation | Rang |\n|---|---|\n| BTS SIO | 33 |\n"
    assert extract_claims(text) == []


def test_pourcentage_de_tableau_au_dessus_de_100_ignore():
    text = "| Formation | Évolution (%) |\n|---|---|\n| BTS | 250 |\n"
    assert extract_claims(text) == []


def test_ligne_ordinaire_inchangee():
    assert _pairs("taux d'acces 87 %, 420 places, 2 370 €") == [(87.0, "pct"), (420.0, "places"), (2370.0, "eur")]


def test_levier_coupe_la_correction(monkeypatch):
    monkeypatch.setenv("ORIENTIA_NUMBERS_SANS_TABLEAUX", "1")
    assert _pairs(TABLEAU_COLONNES) == []
    with pytest.raises(AssertionError):
        test_corrige_unite_en_entete_de_colonne()

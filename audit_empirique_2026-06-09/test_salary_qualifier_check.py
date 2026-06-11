"""TDD volet (b) garde-fou salaire — checker brut/net déterministe, source-aware.

Instrument de MESURE du volet (b) : compte les cas où le modèle qualifie un
salaire 'brut'/'net' en contradiction avec le champ source qui porte ce chiffre.
Indépendant du juge LLM (déterministe), sert à mesurer before/after le garde-fou.

Convention source (partition insee_salaire) :
  salaire_net_*  -> qualificatif 'net'   ; salaire_brut_median_annuel -> 'brut'.
"""
from __future__ import annotations

from salary_qualifier_check import check_salary_qualifier


def _src(**fields):
    base = {"id": "S2"}
    base.update(fields)
    return [base]


def test_correct_net_no_violation():
    ans = "Le salaire net médian annuel pour cette catégorie est de 37 500 € [source S2]."
    assert check_salary_qualifier(ans, _src(salaire_net_median_annuel=37500)) == []


def test_correct_brut_no_violation():
    ans = "Le salaire brut médian annuel est de 45 873 € [source S2]."
    assert check_salary_qualifier(ans, _src(salaire_brut_median_annuel=45873)) == []


def test_brut_claimed_but_source_net_is_violation():
    # cas réel metier-008 : "27 000 € brut" alors que source = net.
    ans = "Le salaire médian des professions libérales est de 27 000 € brut annuel [source S2]."
    v = check_salary_qualifier(ans, _src(salaire_net_median_annuel=27000))
    assert len(v) == 1
    assert v[0]["value"] == 27000
    assert v[0]["claimed"] == "brut"
    assert v[0]["source_qualifiers"] == ["net"]


def test_qualifier_before_number_net_source_brut_claim():
    # qualificatif AVANT le nombre, à distance : "salaire ... brut ... est de 37 500 €"
    ans = "Le salaire médian brut pour les professions scientifiques est de 37 500 €."
    v = check_salary_qualifier(ans, _src(salaire_net_median_annuel=37500))
    assert len(v) == 1 and v[0]["claimed"] == "brut"


def test_mensuel_inversion_violation():
    ans = "Cela représente 2 250 € brut mensuel [source S2]."
    v = check_salary_qualifier(ans, _src(salaire_net_median_mensuel=2250))
    assert len(v) == 1 and v[0]["claimed"] == "brut"


def test_no_qualifier_no_violation():
    # le modèle ne qualifie pas -> rien à reprocher (volet b = qualificatif FAUX).
    ans = "Le salaire médian est de 37 500 € pour cette catégorie."
    assert check_salary_qualifier(ans, _src(salaire_net_median_annuel=37500)) == []


def test_number_not_in_sources_no_qualifier_violation():
    # 50 000 n'est dans aucune source -> pas un mismatch brut/net (c'est une
    # hallucination de NOMBRE, autre métrique). Le checker volet b ne le compte pas.
    ans = "Le salaire est d'environ 50 000 € brut."
    assert check_salary_qualifier(ans, _src(salaire_net_median_annuel=37500)) == []


def test_nbsp_and_compact_number_formats():
    ans_nbsp = "Salaire net : 1 583 € net mensuel, soit 19000 € brut annuel [S2]."
    # 1583 net OK ; 19000 dit 'brut' mais source net -> 1 violation
    v = check_salary_qualifier(
        ans_nbsp, _src(salaire_net_median_mensuel=1583, salaire_net_median_annuel=19000)
    )
    assert len(v) == 1 and v[0]["value"] == 19000 and v[0]["claimed"] == "brut"


def test_value_present_as_both_net_and_brut_no_violation():
    # si la même valeur existe en net ET brut dans les sources, aucune accusation.
    ans = "Le salaire est de 30 000 € brut [S2]."
    srcs = [{"id": "S2", "salaire_net_median_annuel": 30000},
            {"id": "S3", "salaire_brut_median_annuel": 30000}]
    assert check_salary_qualifier(ans, srcs) == []

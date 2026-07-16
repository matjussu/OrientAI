"""Tests de la vérification déterministe chiffre-vs-source-citée (H1 lot 1.2).

Le contrat R1/R3 promet depuis v4.0 une « vérification post-gen côté pipeline »
(docstring system_v4_strict, risque 2 « source-coller mécanique ») qui n'a
jamais existé. Ce module la fournit : chaque chiffre attribué à un tag
[source SX] doit exister dans la FactCard SX que le LLM a vue.

Philosophie haute précision (un faux positif flaggerait INFIDELE une réponse
correcte) : on ne vérifie que les chiffres ATTRIBUABLES à un tag, avec les
normalisations réelles du corpus (ratio 0-1 vs %, arrondis, formats FR).
"""
from __future__ import annotations

import pytest

from src.rag.fact_card import FactCard, FactChiffres
from src.validator.citation_check import (
    CitationMismatch,
    card_numeric_values,
    check_citations,
    extract_cited_numbers,
)


def _card(fact_id: str = "S1", **chiffres) -> FactCard:
    return FactCard(id=fact_id, formation="BUT Info", etablissement="IUT Lyon 1",
                    ville="Lyon", chiffres=FactChiffres(**chiffres))


# ─────────────── extraction (answer -> [(valeur, {SX}, contexte)]) ───────────────

class TestExtraction:
    def test_chiffre_puis_tag_motif_r3(self):
        pairs = extract_cited_numbers("Le taux d'accès est de 52 % [source S1].")
        assert [(v, s) for v, s, _ in pairs] == [(52.0, frozenset({"S1"}))]

    def test_tag_avant_chiffre_motif_r9_phrase(self):
        pairs = extract_cited_numbers(
            "D'après la fiche Parcoursup du BTS La Mennais [S1], le taux d'accès est de 25 %."
        )
        assert [(v, s) for v, s, _ in pairs] == [(25.0, frozenset({"S1"}))]

    def test_tag_en_tete_de_puce_motif_r9_liste(self):
        pairs = extract_cited_numbers("- IUT Lyon1 Villeurbanne [S2] : taux d'accès 16 %")
        assert [(v, s) for v, s, _ in pairs] == [(16.0, frozenset({"S2"}))]

    def test_format_francais_milliers_et_euro(self):
        pairs = extract_cited_numbers("Le salaire médian est de 1 740 € [source S3].")
        assert [(v, s) for v, s, _ in pairs] == [(1740.0, frozenset({"S3"}))]

    def test_decimale_virgule(self):
        pairs = extract_cited_numbers("Un taux de 19,4 % [source S2].")
        assert [(v, s) for v, s, _ in pairs] == [(19.4, frozenset({"S2"}))]

    def test_tag_multi_sources_virgule_et_slash(self):
        pairs = extract_cited_numbers("103 places [source S1, S4] et 28 % [source S2/S3]")
        assert pairs[0][0] == 103.0 and pairs[0][1] == frozenset({"S1", "S4"})
        # 28 est ENTRE deux groupes de tags : attribution = union des encadrants
        assert pairs[1][0] == 28.0 and pairs[1][1] >= frozenset({"S2", "S3"})

    def test_enumeration_fait_tag_fait_tag(self):
        # « 2 125 € [S2], 2 200 € [S5] » : chaque chiffre doit pouvoir matcher
        # le tag qui le SUIT (pattern réel calibration G19/G27 du 16/07)
        pairs = extract_cited_numbers(
            "Salaire médian : 2 125 €/mois pour les femmes [source S2], "
            "2 200 €/mois pour les hommes [source S5]."
        )
        assert pairs[0][1] >= frozenset({"S2"})
        assert pairs[1][1] >= frozenset({"S5"})

    def test_nombre_sans_tag_dans_le_segment_non_attribue(self):
        # Pas de tag dans la phrase -> pas de paire (hors périmètre du check)
        assert extract_cited_numbers("La formation dure 3 ans et coûte 5000 €.") == []

    def test_attribution_au_tag_le_plus_proche_dans_le_segment(self):
        pairs = extract_cited_numbers(
            "- Brest [S1] : 103 places\n- Rouen [S4] : 234 places"
        )
        assert [(v, s) for v, s, _ in pairs] == [
            (103.0, frozenset({"S1"})),
            (234.0, frozenset({"S4"})),
        ]

    def test_ignore_urls_et_bac_plus_et_annees_de_contexte(self):
        text = (
            "Le [BUT Info](https://dossierappel.parcoursup.fr/?g_ta_cod=12345) "
            "est un bac+3. En 2025, il offre 60 places [source S1]."
        )
        pairs = extract_cited_numbers(text)
        vals = [v for v, _, _ in pairs]
        assert 12345.0 not in vals
        assert 3.0 not in vals
        assert 60.0 in vals

    def test_ignore_numero_dans_le_tag_lui_meme(self):
        pairs = extract_cited_numbers("Un taux de 52 % [source S12].")
        assert [(v, s) for v, s, _ in pairs] == [(52.0, frozenset({"S12"}))]


# ─────────────── valeurs numériques d'une FactCard ───────────────

class TestCardValues:
    def test_valeurs_directes(self):
        vals = card_numeric_values(_card(nombre_places=25, salaire_median_embauche=1740))
        assert 25.0 in vals and 1740.0 in vals

    def test_ratio_0_1_expose_aussi_en_pourcentage(self):
        # taux_emploi_3ans est stocké en ratio (0.86) mais cité en % (86 %)
        vals = card_numeric_values(_card(taux_emploi_3ans=0.86))
        assert 0.86 in vals and 86.0 in vals

    def test_pourcentage_decimal_expose_arrondi(self):
        # 52.4 % peut être cité « 52 % » (arrondi légitime, pas une hallu)
        vals = card_numeric_values(_card(taux_acces_parcoursup_2025=52.4))
        assert 52.4 in vals and 52.0 in vals

    def test_nombres_des_champs_texte_comptent(self):
        # durée "3 ans", text_libre : le LLM peut citer ces nombres légitimement
        card = _card()
        card.chiffres.duree = "3 ans"
        card.text_libre = "La formation accueille 120 étudiants par promotion."
        vals = card_numeric_values(card)
        assert 3.0 in vals and 120.0 in vals

    def test_annee_donnees_comptee(self):
        card = _card()
        card.annee_donnees = 2025
        assert 2025.0 in card_numeric_values(card)


# ─────────────── vérification bout-en-bout ───────────────

class TestCheckCitations:
    def test_chiffre_present_pas_de_mismatch(self):
        cards = [_card("S1", nombre_places=60)]
        assert check_citations("Il offre 60 places [source S1].", cards) == []

    def test_chiffre_absent_mismatch(self):
        cards = [_card("S1", nombre_places=60)]
        out = check_citations("Le taux d'accès est de 52 % [source S1].", cards)
        assert len(out) == 1
        assert isinstance(out[0], CitationMismatch)
        assert out[0].value == 52.0
        assert out[0].source_ids == frozenset({"S1"})

    def test_ratio_cite_en_pourcentage_pas_de_mismatch(self):
        cards = [_card("S1", taux_emploi_3ans=0.86)]
        assert check_citations("86 % en emploi à 3 ans [source S1].", cards) == []

    def test_multi_tag_match_si_une_des_sources_contient(self):
        cards = [_card("S1", nombre_places=103), _card("S4", nombre_places=234)]
        assert check_citations("103 places [source S1, S4].", cards) == []

    def test_tag_vers_source_inexistante_mismatch(self):
        # Le LLM cite S7 mais le prompt n'avait que S1 : fabrication de tag
        cards = [_card("S1", nombre_places=60)]
        out = check_citations("Il offre 60 places [source S7].", cards)
        assert len(out) == 1

    def test_arrondi_a_l_entier_tolere(self):
        cards = [_card("S1", taux_acces_parcoursup_2025=28.3)]
        assert check_citations("un taux d'accès de 28 % [source S1].", cards) == []

    def test_reponse_sans_chiffre_ni_tag_ok(self):
        cards = [_card("S1")]
        assert check_citations("Je n'ai pas cette information dans mes sources.", cards) == []


# ─────────────── calibration anti-faux-positifs sur données réelles ───────────────

@pytest.mark.golden
def test_faux_positifs_sur_batterie_reelle():
    """Garde-fou de calibration : rejouable localement quand les batteries
    golden versionnées sont présentes (cf results/h1_lot1_gate_r8r9)."""
    import json
    from pathlib import Path

    from src.rag.fact_card import fiche_to_fact_card

    path = Path("results/h1_lot1_gate_r8r9/battery_APRES.json")
    if not path.exists():
        pytest.skip("batterie golden non présente sur cette branche")
    rows = json.loads(path.read_text())
    n_mismatch = 0
    for r in rows:
        if r.get("error") or not r.get("answer"):
            continue
        cards = [
            fiche_to_fact_card(s, fact_id=s.get("id") or f"S{i+1}")
            for i, s in enumerate(r.get("sources") or [])
        ]
        n_mismatch += bool(check_citations(r["answer"], cards))
    # La batterie est jugée saine (groundedness historique ~0.94) : le taux de
    # flag doit rester marginal. >20 % = l'instrument sur-flagge, recalibrer.
    assert n_mismatch <= len(rows) * 0.2, f"{n_mismatch} réponses flaggées sur {len(rows)}"


# ─────────────── câblage validator + pipeline (2 chemins) ───────────────

class TestValidatorWiring:
    def _validator(self):
        from src.validator.validator import Validator
        return Validator(fiches=[])

    def test_mismatch_flagge_et_penalise(self):
        v = self._validator()
        cards = [_card("S1", nombre_places=60)]
        res = v.validate("Le taux d'accès est de 52 % [source S1].", fact_cards=cards)
        assert res.flagged is True
        assert len(res.citation_mismatches) == 1
        assert res.honesty_score <= 0.90

    def test_citation_correcte_pas_de_flag(self):
        v = self._validator()
        cards = [_card("S1", nombre_places=60)]
        res = v.validate("Il offre 60 places [source S1].", fact_cards=cards)
        assert res.citation_mismatches == []
        assert res.flagged is False

    def test_sans_fact_cards_comportement_inchange(self):
        v = self._validator()
        res = v.validate("Le taux d'accès est de 52 % [source S1].")
        assert res.citation_mismatches == []
        assert res.flagged is False


class TestStreamWiring:
    def _pipeline(self):
        from unittest.mock import MagicMock
        from src.rag.pipeline import OrientIAPipeline
        from src.validator.validator import Validator
        return OrientIAPipeline(
            client=MagicMock(), fiches=[], validator=Validator(fiches=[]),
        )

    def test_stream_verdict_infidele_sur_mismatch(self):
        p = self._pipeline()
        top = [{"score": 1.0, "fiche": {"nom": "BUT Info", "nombre_places": 60}}]
        score, verdict = p._validate_for_stream(
            "Le taux d'accès est de 52 % [source S1].", None, top, False,
        )
        assert verdict == "INFIDELE"
        assert score is not None and score <= 0.90

    def test_stream_verdict_fidele_sur_citation_correcte(self):
        p = self._pipeline()
        top = [{"score": 1.0, "fiche": {"nom": "BUT Info", "nombre_places": 60}}]
        score, verdict = p._validate_for_stream(
            "Il offre 60 places [source S1].", None, top, False,
        )
        assert verdict == "FIDELE"

    def test_numerotation_suit_la_branche_generation(self):
        p = self._pipeline()
        top = [{"score": 1.0, "fiche": {"nom": f"F{i}"}} for i in range(10)]
        assert len(p._fact_cards_for_validation(top, narrative_mode=False)) == 5
        assert len(p._fact_cards_for_validation(top, narrative_mode=True)) == 8
        assert p._fact_cards_for_validation(None, False) == []

"""Tests du parser déterministe NarrativeResponse (ordre 1926).

Vérifie : totalité (ne lève jamais), markdown_full canonique, extraction typée
par format (pistes, comparison_table, sources), confiance structurelle.
"""
from __future__ import annotations

from src.rag.narrative_format import (
    FormatDecision, CONSEIL, COMPARAISON, TRAJECTOIRE, VALIDATION, SHORTLIST, EXPLORATOIRE,
)
from src.rag.narrative_structured import parse_narrative_response


def _d(fmt, anchor=False, reassure=False):
    return FormatDecision(format=fmt, anchor_constraint=anchor, reassure=reassure)


CONSEIL_MD = """**1. Ta situation**
Tu sors d'un BTS communication et tu veux du design, sans école privée chère, sur Rennes.

**2. Les pistes qui collent**
- **[Licence pro UX/UI Rennes 2](https://ex.fr/lp)** : la plus alignée, publique, 78 % d'insertion [source S1].
- **[BUT MMI Lannion](https://ex.fr/but)** : généraliste, taux d'accès 41 % [source S2].

**3. Points de vigilance**
Aucune école privée abordable sur Rennes dans mes sources [source S1].

**4. Prochaine étape**
Regarde les attendus de la LP. Tu te vois plutôt UX écran ou design large ?
"""

COMPARAISON_MD = """**1. Ta question en clair**
Tu hésites entre BUT GEA et BTS CG, en voulant bosser vite sans te fermer la suite.

**2. Le face à face**

| Critère | BUT GEA | BTS CG |
|---|---|---|
| Durée | 3 ans | 2 ans |
| Insertion | 76 % [source S1] | 70 % [source S2] |
| Poursuite | très ouverte | plus limitée |

**3. Ma reco**
À ta place, BUT GEA pour garder la suite ouverte. Tu veux que je creuse les poursuites ?
"""

SHORTLIST_MD = """**Le palmarès**
1. **[École A](https://ex.fr/a)** — publique, 92 % d'insertion [source S1].
2. **[École B](https://ex.fr/b)** — réseau réputé [source S2].
3. **[École C](https://ex.fr/c)** — large choix [source S3].

À viser en priorité : la n°1. Tu veux les dates Parcoursup ?
"""

TRAJECTOIRE_MD = """**1. D'où tu pars**
Ta L2 de droit n'est pas perdue : méthode, rédaction, rigueur sont réutilisables.

**2. Les passerelles**
Du droit vers la data, les transitions passent par l'analyse et la conformité [source S1].

**3. Le chemin concret**
- **[Licence pro data Lille](https://ex.fr/lp)** : 1 an, salaire médian 2370 € net/mois [source S2].

**4. Premier pas**
Va voir une info-collective. Tu veux la voie la plus rapide ou un diplôme reconnu ?
"""


def test_conseil_parses_sections_and_pistes():
    r = parse_narrative_response(CONSEIL_MD, _d(CONSEIL))
    assert r["format"] == CONSEIL
    assert r["markdown_full"] == CONSEIL_MD
    roles = [b["role"] for b in r["blocks"]]
    assert "lead" in roles and "options" in roles and "vigilance" in roles and "closing" in roles
    opt = next(b for b in r["blocks"] if b["role"] == "options")
    assert len(opt["items"]) == 2
    assert opt["items"][0]["titre"] == "Licence pro UX/UI Rennes 2"
    assert opt["items"][0]["url"] == "https://ex.fr/lp"
    assert opt["items"][0]["sources"] == ["S1"]
    assert r["parse_confidence"] == 1.0


def test_comparaison_parses_markdown_table():
    r = parse_narrative_response(COMPARAISON_MD, _d(COMPARAISON))
    assert r["format"] == COMPARAISON
    tbl_block = next(b for b in r["blocks"] if b["role"] == "comparison_table")
    table = tbl_block["table"]
    assert table is not None
    assert table["options"] == ["BUT GEA", "BTS CG"]
    labels = [c["label"] for c in table["criteria"]]
    assert "Durée" in labels and "Insertion" in labels
    ins = next(c for c in table["criteria"] if c["label"] == "Insertion")
    assert ins["values"]["BUT GEA"].startswith("76")
    assert "S1" in ins["sources"] and "S2" in ins["sources"]
    assert r["parse_confidence"] == 1.0


def test_shortlist_parses_ranked_items():
    r = parse_narrative_response(SHORTLIST_MD, _d(SHORTLIST))
    assert r["format"] == SHORTLIST
    opt = next(b for b in r["blocks"] if b["role"] == "options")
    assert len(opt["items"]) == 3
    assert opt["items"][0]["titre"] == "École A"
    assert r["parse_confidence"] == 1.0


def test_trajectoire_roles_and_salary_source():
    r = parse_narrative_response(TRAJECTOIRE_MD, _d(TRAJECTOIRE))
    roles = {b["role"] for b in r["blocks"]}
    assert {"lead", "passerelles", "options", "closing"} <= roles
    opt = next(b for b in r["blocks"] if b["role"] == "options")
    assert opt["items"][0]["sources"] == ["S2"]  # salaire sourcé
    assert r["parse_confidence"] == 1.0


def test_overlays_propagated():
    r = parse_narrative_response(CONSEIL_MD, _d(CONSEIL, anchor=True, reassure=True))
    assert r["overlays"] == {"anchor_constraint": True, "reassure": True}


# --- Totalité / robustesse ---

def test_blob_without_headings_falls_back_to_prose():
    r = parse_narrative_response("Juste un paragraphe sans aucun titre en gras, citant [source S1].", _d(CONSEIL))
    assert len(r["blocks"]) == 1
    assert r["blocks"][0]["role"] == "prose"
    assert r["parse_confidence"] == 0.0
    assert r["blocks"][0]["sources"] == ["S1"]


def test_empty_string_never_raises():
    r = parse_narrative_response("", _d(CONSEIL))
    assert r["markdown_full"] == ""
    assert r["parse_confidence"] == 0.0
    assert r["format"] == CONSEIL


def test_none_markdown_never_raises():
    r = parse_narrative_response(None, _d(VALIDATION))  # type: ignore[arg-type]
    assert r["markdown_full"] == ""
    assert r["format"] == VALIDATION


def test_comparaison_without_table_low_confidence():
    md = "**1. Ta question en clair**\nX ou Y.\n\n**2. Le face à face**\nPas de tableau ici, juste de la prose.\n\n**3. Ma reco**\nX."
    r = parse_narrative_response(md, _d(COMPARAISON))
    # le face-à-face sans tableau -> déclassé prose -> pas de comparison_table
    assert not any(b.get("table") for b in r["blocks"])
    assert r["parse_confidence"] <= 0.5


def test_markdown_full_always_canonical():
    for md in (CONSEIL_MD, COMPARAISON_MD, SHORTLIST_MD, TRAJECTOIRE_MD):
        for fmt in (CONSEIL, COMPARAISON, TRAJECTOIRE, VALIDATION, SHORTLIST, EXPLORATOIRE):
            r = parse_narrative_response(md, _d(fmt))
            assert r["markdown_full"] == md  # jamais altéré, quel que soit le format


# --- Détection de troncature (fix B, ordre 1926) ---

def test_complete_response_not_truncated():
    r = parse_narrative_response(CONSEIL_MD, _d(CONSEIL))
    assert r["truncated"] is False


def test_truncated_mid_citation_detected():
    # Cas R01 réel : coupé sur « [source S » (citation inachevée).
    md = TRAJECTOIRE_MD.rstrip() + "\n- **[Master data Lille](https://ex.fr/m)** : insertion forte [source S"
    r = parse_narrative_response(md, _d(TRAJECTOIRE))
    assert r["truncated"] is True
    assert r["parse_confidence"] <= 0.5  # pénalisé malgré titres présents


def test_truncated_mid_markdown_link_detected():
    # Cas T3 réel (démo) : coupé dans une URL de lien markdown.
    md = TRAJECTOIRE_MD.rstrip() + "\n- **[Data scientist](https://www.onisep.fr/recherche?q=Syst%C3%A8mes%20automatis"
    r = parse_narrative_response(md, _d(TRAJECTOIRE))
    assert r["truncated"] is True


def test_truncated_mid_word_detected():
    md = CONSEIL_MD.rstrip()[:-30]  # coupe au milieu d'une phrase
    r = parse_narrative_response(md, _d(CONSEIL))
    # se termine sur un mot/ponctuation interne -> truncated
    assert r["truncated"] is True


def test_question_ending_not_truncated():
    # Une relance par question est une fin LÉGITIME (la plupart des formats finissent ainsi).
    r = parse_narrative_response(SHORTLIST_MD, _d(SHORTLIST))
    assert r["truncated"] is False  # finit sur « ... Parcoursup ? »


# --- A1 (iter1) : vraies URLs sources ---

def test_build_sources_index_real_url_vs_search():
    from src.rag.fact_card import build_sources_index
    top = [
        {"fiche": {"nom": "BUT MMI", "lien_form_psup": "https://dossierappel.parcoursup.fr/x?g_ta_cod=1"}},
        {"fiche": {"nom": "LP UX", "url_canonical": "https://www.onisep.fr/recherche?q=lp%20ux"}},  # search -> null
        {"fiche": {"nom": "Master Data", "url_onisep": "https://www.onisep.fr/ressources/univers-formation/formations/x"}},
    ]
    idx = build_sources_index(top, max_sources=10)
    assert idx[0] == {"ref": "S1", "label": "BUT MMI", "url": "https://dossierappel.parcoursup.fr/x?g_ta_cod=1"}
    assert idx[1]["ref"] == "S2" and idx[1]["url"] is None  # canonical search exclu -> pas de lien creux
    assert idx[2]["url"].startswith("https://www.onisep.fr/ressources")


def test_sources_attached_and_piste_url_resolved_to_real_fiche():
    sources = [
        {"ref": "S1", "label": "Licence pro UX/UI Rennes 2", "url": "https://dossierappel.parcoursup.fr/real?g_ta_cod=7"},
        {"ref": "S2", "label": "BUT MMI Lannion", "url": None},
    ]
    r = parse_narrative_response(CONSEIL_MD, _d(CONSEIL), sources=sources)
    assert r["sources"] == sources  # map autoritaire attachée
    opt = next(b for b in r["blocks"] if b["role"] == "options")
    # piste 1 cite [S1] (markdown url ex.fr/lp) -> résolue sur la VRAIE fiche S1
    assert opt["items"][0]["url"] == "https://dossierappel.parcoursup.fr/real?g_ta_cod=7"
    # piste 2 cite [S2] dont url=None -> pas de lien creux
    assert opt["items"][1]["url"] is None


def test_piste_search_url_dropped_when_no_real_source():
    md = "**2. Les pistes qui collent**\n- **[Une formation](https://www.onisep.fr/recherche?q=truc)** : pourquoi [source S9].\n"
    r = parse_narrative_response(md, _d(CONSEIL), sources=[])
    opt = next(b for b in r["blocks"] if b["role"] == "options")
    assert opt["items"][0]["url"] is None  # lien de recherche -> non cliquable

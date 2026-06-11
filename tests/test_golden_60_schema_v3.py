"""Tests step 9 — schema v3 du golden_60.json.

Verrouille :
- 60 questions originales v2 préservées (additif strict)
- 6 nouvelles questions cassantes ajoutées (L01, L02, P01, P02, A09, A10)
- Champ optionnel `expected_routing` cohérent avec SUB_INDEX_NAMES
- Champ optionnel `expected_routing_confidence_min` dans [0, 1]
- `expected_refusal` cohérent avec category (adversarial/cross_domain/live)
- eval_recall.py consomme les nouveaux champs sans erreur (fallback gracieux)
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.rag.router_llm import SUB_INDEX_NAMES


GOLDEN_PATH = Path(__file__).resolve().parents[1] / "data" / "golden_eval" / "golden_60.json"


@pytest.fixture(scope="module")
def golden() -> dict:
    return json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))


# ────────────────────────── Schema v3 metadata ──────────────────────────


def test_schema_version_v3(golden: dict) -> None:
    # ADR-060 (commit c7c0966) a bumpé v3 -> v3.1 (patch refusal_markers +
    # 5 vie_etudiante_periph). On verrouille la version courante intentionnelle.
    assert golden["schema_version"] == "v3.1"


def test_categories_extended_with_live_and_paraphrase(golden: dict) -> None:
    """v3 ajoute 2 nouvelles catégories sans modifier les 8 v2."""
    cats = golden["categories"]
    # 8 v2 préservées
    for old in (
        "lyceen_parcoursup", "reorientation", "metier", "calendaire",
        "geographique", "vie_etudiante", "adversarial", "cross_domain",
    ):
        assert old in cats, f"Catégorie v2 perdue : {old}"
    # 2 nouvelles v3
    assert "live" in cats
    assert "paraphrase" in cats


def test_schema_v3_documents_optional_fields(golden: dict) -> None:
    """Le header documente explicitement les 3 nouveaux champs optionnels."""
    fields_doc = golden.get("schema_v3_optional_fields")
    assert fields_doc is not None
    for f in ("expected_routing", "expected_routing_confidence_min", "expected_refusal"):
        assert f in fields_doc


# ────────────────────────── Comptes total ──────────────────────────


def test_total_questions_is_71(golden: dict) -> None:
    """60 v2 + 6 v3 cassantes (commit 4989d59) + 5 vie_etudiante_periph
    (ADR-060, commit c7c0966) = 71."""
    assert len(golden["questions"]) == 71


def test_v2_questions_preserved(golden: dict) -> None:
    """Les 50 G* + 8 A* + 2 X* originaux sont tous présents."""
    ids = {q["id"] for q in golden["questions"]}
    for i in range(1, 51):
        assert f"G{i:02d}" in ids, f"G{i:02d} disparu"
    for i in range(1, 9):
        assert f"A{i:02d}" in ids, f"A{i:02d} disparu"
    for i in range(1, 3):
        assert f"X{i:02d}" in ids, f"X{i:02d} disparu"


def test_v3_questions_added(golden: dict) -> None:
    """Les 6 nouvelles questions cassantes sont présentes."""
    ids = {q["id"] for q in golden["questions"]}
    for new_id in ("L01", "L02", "P01", "P02", "A09", "A10"):
        assert new_id in ids


# ────────────────────────── Cohérence des champs v3 ──────────────────────────


def test_expected_routing_sub_indexes_valid(golden: dict) -> None:
    """Toute valeur de expected_routing.sub_indexes est dans SUB_INDEX_NAMES."""
    for q in golden["questions"]:
        routing = q.get("expected_routing")
        if routing is None:
            continue
        sub_indexes = routing.get("sub_indexes", [])
        assert isinstance(sub_indexes, list)
        for s in sub_indexes:
            assert s in SUB_INDEX_NAMES, (
                f"Question {q['id']} : sub_index {s!r} hors enum {list(SUB_INDEX_NAMES)}"
            )


def test_expected_routing_confidence_in_range(golden: dict) -> None:
    """expected_routing_confidence_min ∈ [0.0, 1.0]."""
    for q in golden["questions"]:
        conf = q.get("expected_routing_confidence_min")
        if conf is None:
            continue
        assert isinstance(conf, (int, float))
        assert 0.0 <= conf <= 1.0, f"Q {q['id']} : confidence {conf} hors [0,1]"


def test_expected_refusal_consistent_with_category(golden: dict) -> None:
    """Cohérence : adversarial/cross_domain ont expected_refusal=true.
    live peut être true (superlatif) ou false (geographic)."""
    for q in golden["questions"]:
        cat = q["category"]
        if cat in ("adversarial", "cross_domain"):
            assert q.get("expected_refusal") is True, (
                f"Q {q['id']} ({cat}) doit avoir expected_refusal=true"
            )
        # 'live' et 'paraphrase' : peuvent être l'un ou l'autre (cas par cas)


# ────────────────────────── 6 questions cassantes spécifiques ──────────────────────────


def test_L01_superlative_meilleure_ecole_commerce(golden: dict) -> None:
    """Q live #1 : 'meilleure école de commerce' doit être marquée
    refusal=true avec expected_routing pour audit."""
    q = next(q for q in golden["questions"] if q["id"] == "L01")
    assert q["category"] == "live"
    assert q["expected_refusal"] is True
    assert "meilleure" in q["question"].lower()
    assert q.get("expected_routing", {}).get("sub_indexes") == ["formations"]


def test_L02_inge_cyber_bretagne(golden: dict) -> None:
    """Q live #2 : 'ingé cyber Bretagne' doit ramener BTS Rennes/BUT Brest.
    Pas un refus ; routing geographic + top_k_override critical."""
    q = next(q for q in golden["questions"] if q["id"] == "L02")
    assert q["category"] == "live"
    assert q["expected_refusal"] is False
    assert "Bretagne" in q["question"]
    routing = q.get("expected_routing", {})
    assert routing.get("intent") == "geographic"
    assert "formations" in routing.get("sub_indexes", [])


def test_P01_paraphrase_crous_without_keyword(golden: dict) -> None:
    """Q paraphrase : 'chambre étudiante Lyon' SANS le mot 'CROUS'.
    Mesure que RouterLLM comprend le sens (cas où fallback déterministe rate)."""
    q = next(q for q in golden["questions"] if q["id"] == "P01")
    assert q["category"] == "paraphrase"
    assert "CROUS" not in q["question"].lower() and "crous" not in q["question"].lower()
    assert q.get("expected_routing", {}).get("sub_indexes") == ["aides_territoires"]
    # Confidence abaissée à 0.6 pour tolérer fallback
    assert q["expected_routing_confidence_min"] == 0.6


def test_P02_paraphrase_metier_without_keyword(golden: dict) -> None:
    """Q paraphrase : 'jobs aime les chiffres' SANS mot-clé métier précis.
    Mesure router_llm sur question naturelle."""
    q = next(q for q in golden["questions"] if q["id"] == "P02")
    assert q["category"] == "paraphrase"
    assert q.get("expected_routing", {}).get("sub_indexes") == ["metiers"]
    assert q["expected_routing_confidence_min"] == 0.5


def test_A09_top_n_superlative_variant(golden: dict) -> None:
    """A09 : variant 'top N' du superlatif (vs 'meilleure' de A07/L01)."""
    q = next(q for q in golden["questions"] if q["id"] == "A09")
    assert q["category"] == "adversarial"
    assert q["expected_refusal"] is True
    assert "top" in q["question"].lower()


def test_A10_superlative_with_insee_domain(golden: dict) -> None:
    """A10 : superlatif 'meilleurs avocats' qui sonne comme statistiques.
    Test priorité refus > routing — refus doit l'emporter."""
    q = next(q for q in golden["questions"] if q["id"] == "A10")
    assert q["category"] == "adversarial"
    assert q["expected_refusal"] is True
    assert q.get("expected_routing", {}).get("sub_indexes") == ["statistiques"]


# ────────────────────────── eval_recall.py compat ──────────────────────────


def test_eval_recall_consumes_v3_without_error(golden: dict) -> None:
    """eval_recall.py utilise q.get(...) avec defaults — il doit pouvoir
    parser TOUTES les questions v3 sans KeyError. Test parsing seul (pas
    de pipeline run)."""
    # Reproduction du parsing fait dans eval_recall.py:225-230
    for q in golden["questions"]:
        qid = q["id"]
        question_text = q["question"]
        expected_domain = q.get("expected_domain")
        expected_source = q.get("expected_source")
        expected_keywords = q.get("expected_keywords_in_answer", [])
        is_refusal_q = bool(q.get("expected_refusal"))
        # Tous accessibles, types corrects
        assert isinstance(qid, str)
        assert isinstance(question_text, str)
        assert expected_domain is None or isinstance(expected_domain, str)
        assert expected_source is None or isinstance(expected_source, str)
        assert isinstance(expected_keywords, list)
        assert isinstance(is_refusal_q, bool)


def test_eval_recall_handles_missing_routing_gracefully(golden: dict) -> None:
    """Les 60 questions v2 n'ont pas `expected_routing` — q.get() retourne None.
    Pas d'AttributeError ni KeyError."""
    n_with_routing = 0
    n_without_routing = 0
    for q in golden["questions"]:
        routing = q.get("expected_routing")  # None si absent
        if routing is None:
            n_without_routing += 1
            # Pas d'accès aval qui planterait
            assert q.get("expected_routing", {}).get("sub_indexes") is None
        else:
            n_with_routing += 1
    # 6 cassantes v3 + 5 vie_etudiante_periph (ADR-060) portent un routing ;
    # les 60 questions v2 n'en ont pas.
    assert n_with_routing == 11
    assert n_without_routing == 60


# ────────────────────────── Refusal markers ──────────────────────────


def test_refusal_markers_default_preserved(golden: dict) -> None:
    """Les markers v2 sont préservés (pas modifiés en v3)."""
    markers = golden["refusal_markers_default"]
    # Sample v2 doit toujours être présent
    for required in ("aucune formation", "scuio", "cio"):
        assert required in markers

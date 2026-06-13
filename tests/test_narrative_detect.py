"""Tests src/rag/narrative_detect.py — detection deterministe du mode recit (R1 1a).

Les 2 tests cardinaux verrouillent la calibration :
- isolation baseline : 0/100 des questions du banc de non-regression declenche ;
- couverture seed : 12/12 des recits du seed declenchent.
"""
from __future__ import annotations

import json
from pathlib import Path

from src.rag.narrative_detect import (
    is_narrative,
    is_narrative_followup,
    narrative_signal,
    detect_facets,
    NARRATIVE_MIN_LEN,
    FACET_MIN_LEN,
)

# Récit long réutilisé (>=300 chars) pour les tests multi-tour.
_RECIT = (
    "Bonjour, je suis en terminale generale a Bordeaux avec maths et SVT. J'aime "
    "les sciences mais je ne veux surtout pas faire medecine, les concours et les "
    "etudes trop longues ne me tentent pas. Je voudrais explorer d'autres pistes "
    "scientifiques qui me correspondent. Tu aurais des idees de filieres ?"
)

REPO = Path(__file__).resolve().parents[1]


# ─────────────── Gates cardinaux (calibration) ───────────────


def test_isolation_baseline_100q():
    """NON negociable : aucune des 100 questions du banc (max 118 chars) ne
    declenche le mode recit -> comparabilite longitudinale preservee."""
    qs = json.loads((REPO / "src/eval/questions.json").read_text(encoding="utf-8"))["questions"]
    triggered = [q for q in qs if is_narrative(q.get("text") or q.get("question") or "")]
    assert triggered == [], (
        f"{len(triggered)} question(s) baseline declenchent le mode recit a tort : "
        f"{[ (q.get('text') or q.get('question'))[:60] for q in triggered ]}"
    )


def test_seed_recits_all_trigger():
    """Les 12 recits du seed (>=300 chars, multi-facettes) declenchent tous."""
    seed = json.loads((REPO / "data/recits_seed.json").read_text(encoding="utf-8"))["recits"]
    assert len(seed) == 12
    non_trigger = [r["id"] for r in seed if not is_narrative(r["text"])]
    assert non_trigger == [], f"recits qui ne declenchent pas a tort : {non_trigger}"


# ─────────────── Regles unitaires ───────────────


def test_short_question_is_not_narrative():
    assert is_narrative("Quelles ecoles d'ingenieur en cybersecurite en Bretagne ?") is False


def test_long_question_over_300_is_narrative():
    q = "Bonjour " + ("je raconte mon parcours en detail " * 12)  # > 300 chars
    assert len(q) >= NARRATIVE_MIN_LEN
    assert is_narrative(q) is True
    assert narrative_signal(q).reason.startswith("length>=")


def test_medium_with_two_facets_is_narrative():
    """200-299 chars + >=2 facettes -> recit."""
    q = (
        "Je suis en terminale et je veux devenir developpeur, mais je ne veux pas "
        "passer mes journees devant un ecran a coder, ca ne me plait pas du tout, "
        "donc je cherche autre chose dans ce domaine sans programmation intensive."
    )
    assert FACET_MIN_LEN <= len(q) < NARRATIVE_MIN_LEN
    facets = detect_facets(q)
    assert len(facets) >= 2, f"facettes detectees : {facets}"
    assert is_narrative(q) is True


def test_medium_with_one_facet_is_not_narrative():
    """200-299 chars mais < 2 facettes -> pas recit (regle facettes non remplie)."""
    q = (
        "Je voudrais des informations generales et completes sur le fonctionnement "
        "de la procedure pour candidater apres le baccalaureat dans le superieur, "
        "merci de me detailler les grandes etapes une par une s'il vous plait ok."
    )
    assert FACET_MIN_LEN <= len(q) < NARRATIVE_MIN_LEN
    assert len(detect_facets(q)) < 2
    assert is_narrative(q) is False


def test_under_200_never_triggers_even_multi_facet():
    """Plancher dur : < 200 chars ne declenche JAMAIS, meme multi-facettes."""
    q = "Je suis en terminale, je veux devenir dev mais je deteste coder a Lyon."
    assert len(q) < FACET_MIN_LEN
    assert len(detect_facets(q)) >= 2  # facettes presentes...
    assert is_narrative(q) is False    # ...mais sous le plancher -> non


def test_detect_facets_identifies_categories():
    q = ("Je suis en L2 de droit a Lille, je veux me reorienter vers la data, "
         "j'adore l'analyse, mais je ne veux pas de commercial, et je cherche une alternance.")
    facets = detect_facets(q)
    for expected in ("situation", "cible", "interets", "a_eviter", "contrainte", "geo"):
        assert expected in facets, f"categorie '{expected}' manquante dans {facets}"


def test_empty_question_is_not_narrative():
    assert is_narrative("") is False
    assert is_narrative("   ") is False


class TestIsNarrativeFollowup:
    """R2 FORK A : un follow-up court reste en mode récit si la conversation est
    déjà narrative (un tour user antérieur est un récit)."""

    def test_no_history_is_false(self):
        # Garde-fou 2 : banc single-turn (history None/[]) -> jamais de bascule.
        assert is_narrative_followup(None) is False
        assert is_narrative_followup([]) is False

    def test_prior_user_recit_triggers(self):
        history = [
            {"role": "user", "content": _RECIT},
            {"role": "assistant", "content": "**1. Ta situation** ... (réponse sectionnée)"},
        ]
        assert is_narrative_followup(history) is True

    def test_only_short_user_turns_is_false(self):
        history = [
            {"role": "user", "content": "c'est quoi un BUT info ?"},
            {"role": "assistant", "content": "Le BUT informatique est ..."},
        ]
        assert is_narrative_followup(history) is False

    def test_assistant_long_turn_does_not_count(self):
        # La réponse longue de l'assistant ne doit PAS compter comme récit user.
        history = [{"role": "assistant", "content": _RECIT}]
        assert is_narrative_followup(history) is False

    def test_malformed_messages_no_crash(self):
        history = [{"role": "user"}, "pas un dict", {"content": _RECIT}, {"role": "user", "content": None}]
        assert is_narrative_followup(history) is False

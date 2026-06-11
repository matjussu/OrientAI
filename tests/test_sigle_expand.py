"""Tests expansion sigles BM25-only (J2 U1, 2026-06-11)."""
from __future__ import annotations

from src.rag.sigle_expand import SIGLE_EXPANSIONS, expand_sigles_for_bm25


def test_expands_known_acronym_additively():
    out = expand_sigles_for_bm25("taux d'accès BUT GEII à Montluçon")
    # query brute conservée
    assert "BUT GEII" in out
    # forme longue ajoutée
    assert "génie électrique et informatique industrielle" in out


def test_case_insensitive():
    out = expand_sigles_for_bm25("master miage à Nantes")
    assert "méthodes informatiques appliquées à la gestion des entreprises" in out


def test_no_sigle_unchanged():
    q = "Quelle licence de droit choisir à Lyon ?"
    assert expand_sigles_for_bm25(q) == q


def test_excluded_redundant_sigle_not_expanded():
    # BTS/BUT/CPGE matchés littéralement par BM25 -> hors dico, pas d'expansion.
    q = "taux d'accès BTS à Lille"
    assert expand_sigles_for_bm25(q) == q


def test_double_occurrence_expanded_once():
    out = expand_sigles_for_bm25("GEA et GEA")
    assert out.count("gestion des entreprises et des administrations") == 1


def test_multiple_distinct_sigles():
    out = expand_sigles_for_bm25("compare GMP et HSE")
    assert "génie mécanique et productique" in out
    assert "hygiène sécurité environnement" in out


def test_word_boundary_no_false_match():
    # un mot contenant 'gea'/'las' ne doit pas déclencher l'expansion.
    q = "les délais d'inscription"  # 'las' n'est pas un token isolé ici
    assert expand_sigles_for_bm25(q) == q


def test_empty_safe():
    assert expand_sigles_for_bm25("") == ""


def test_dict_has_no_ambiguous_two_letter_token():
    # garde-fou règle 1 (Jarvis) : pas de sigle 2-lettres ambigu (TC, CS, CJ...).
    assert all(len(s) >= 3 for s in SIGLE_EXPANSIONS), "sigle <3 lettres = risque ambiguïté"

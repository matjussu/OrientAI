"""Expansion statique de sigles d'orientation pour la JAMBE LEXICALE BM25 (J2 U1).

Pourquoi BM25-only (mesuré, cf agent_journal 2026-06-11) : les acronymes que le
CORPUS ÉPELLE en toutes lettres (query "BUT GEII" -> fiche "Génie électrique et
informatique industrielle") sont invisibles à BM25 qui matche le token nu ->
fiche cible ABSENTE du top-10. L'expansion débloque la jambe lexicale (7 gains
nets A/B). MAIS expanser la query DENSE la fait dériver et déplace des fiches
déjà trouvées (régressions mesurées LAS 4->None, MIAGE-Paris 4->None). On
n'expanse donc QUE la query passée à BM25 ; la jambe dense garde la query brute.

Règles de construction (validées Jarvis) :
- seulement des sigles dont le corpus épelle la forme longue SANS le token nu
  (gain BM25 prouvé par A/B per-entry) ;
- pas de sigle ambigu / double-sens (TC, ECG, CS, RT, SD exclus) ;
- sigles que BM25 matche déjà littéralement (BTS/BUT/CPGE/MPSI/PCSI/STAPS/PASS/
  DEUST) HORS liste (redondants) ;
- sigles SERVICE (PsyEN/CIO/SCUIO/CVEC) HORS liste retrieval (pas de fiche
  formation à retrouver, sujet génération/définition).
"""
from __future__ import annotations

import re
import unicodedata

# acronyme (lowercase) -> forme longue ajoutée à la query BM25.
SIGLE_EXPANSIONS: dict[str, str] = {
    "miage": "méthodes informatiques appliquées à la gestion des entreprises",
    "geii": "génie électrique et informatique industrielle",
    "gea": "gestion des entreprises et des administrations",
    "gmp": "génie mécanique et productique",
    "mmi": "métiers du multimédia et de l'internet",
    "gaco": "gestion administrative et commerciale des organisations",
    "gcgp": "génie chimique génie des procédés",
    "hse": "hygiène sécurité environnement",
    "las": "licence accès santé",
}

_PATTERN = re.compile(
    r"\b(" + "|".join(sorted(SIGLE_EXPANSIONS, key=len, reverse=True)) + r")\b",
    re.IGNORECASE,
)


def expand_sigles_for_bm25(question: str) -> str:
    """Append la forme longue de chaque sigle reconnu (ADDITIF — la query brute
    est conservée, l'expansion est ajoutée à la fin). Sert UNIQUEMENT la jambe
    BM25 ; ne jamais l'appliquer à la query dense (régression mesurée).

    NOTE : approche query-expansion ÉCARTÉE par la mesure (gain=régression=même
    mécanisme dense, cf agent_journal). Conservé comme utilitaire/référence ;
    la solution retenue est l'injection corpus ci-dessous (detect_sigles_in_fiche)."""
    if not question:
        return question
    seen: list[str] = []
    for m in _PATTERN.finditer(question):
        exp = SIGLE_EXPANSIONS[m.group(1).lower()]
        if exp not in seen:
            seen.append(exp)
    if not seen:
        return question
    return question + " " + " ".join(seen)


# ──────────────── Injection corpus (J2 enrichissement, 2026-06-11) ────────────────
#
# Solution SOURCE (mesurée gagnante) : injecter le SIGLE dans le texte
# embeddé/indexé des fiches dont le corpus épelle la forme longue. La fiche
# "BUT - Génie électrique et informatique industrielle" reçoit "GEII" -> dense
# ET BM25 matchent l'acronyme nu, zéro manipulation de query, zéro déplacement.
# Même philosophie que les signatures écoles Step 11.7 (embeddings.py).


def _strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


# forme-longue (accent-strip lower) -> sigle, pour détection dans le texte fiche.
_FORM_TO_SIGLE: dict[str, str] = {
    _strip_accents(form).lower(): sig.upper() for sig, form in SIGLE_EXPANSIONS.items()
}


def detect_sigles_in_fiche(fiche: dict, max_chars: int = 600) -> list[str]:
    """Sigles dont la forme longue apparaît dans le texte de la fiche
    (nom/text/detail/libelle/intitule). Déterministe, vocabulaire contrôlé."""
    if not isinstance(fiche, dict):
        return []
    blob = " ".join(
        str(fiche.get(k) or "")[:max_chars]
        for k in ("nom", "text", "detail", "libelle", "intitule")
    )
    blob = _strip_accents(blob).lower()
    out: list[str] = []
    for form, sig in _FORM_TO_SIGLE.items():
        if form in blob and sig not in out:
            out.append(sig)
    return out


def sigle_injection_text(fiche: dict) -> str:
    """Fragment à appender au texte embeddé (dense) ET indexé (BM25). '' si aucun
    sigle détecté. Additif — n'altère jamais le contenu existant de la fiche."""
    sigles = detect_sigles_in_fiche(fiche)
    return ("Sigle : " + " ".join(sigles)) if sigles else ""

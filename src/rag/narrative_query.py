"""Forge déterministe de la requête de retrieval — mode récit (R1 1c-b).

`build_narrative_retrieval_query` est le « query_reformuler FIGÉ EN CODE » :
au lieu d'un appel LLM, on dérive de façon DÉTERMINISTE une requête de
retrieval FOCALISÉE à partir du profil étendu (1b). Objectif : régler la
DILUTION du récit brut (300+ chars de connecteurs et d'affect noient les
termes discriminants au moment de l'embedding).

Principes :
- Ne tirer que les facettes POSITIVES (cible, situation, intérêts, géo) +
  les secteurs + la région (boost via texte) + mots-clés corpus déterministes.
- `a_eviter` n'entre JAMAIS : l'embarquer ferait remonter les fiches rejetées.
  C'est un signal de génération (la réponse doit le montrer), pas de retrieval.
- `mobilite` n'est pas un terme de recherche ("mobile en France" ne décrit
  aucune fiche) -> exclu.
- Zéro LLM, déterministe (reproductible pour la boucle de jugement humain).
- Corpus-awareness : la requête forgée + le ciblage sub_index (route_from_profile)
  = la connaissance domain-hint de query_reformuler encodée en code.

Single focused query (MVP). Si le gate index empirique révèle un trou de
couverture sur une facette précise, on ajoute une 2e retrieval À CE MOMENT,
mesurée — pas de multi-query spéculatif.
"""
from __future__ import annotations

import re

from src.agent.tools.profile_clarifier import Profile
from src.rag.intent import _strip_accents


# Facettes dont on tire le span verbatim — POSITIVES uniquement.
# `a_eviter` est volontairement absent (cf docstring).
_POSITIVE_SPAN_FACETS: tuple[str, ...] = ("cible", "situation", "interets", "geo")

# Contraintes qui ajoutent le mot-clé corpus "alternance" (active le ciblage
# formations en alternance / aides territoires au retrieval).
_ALTERNANCE_KEYWORDS: tuple[str, ...] = ("alternance", "apprentissage", "contrat pro")


def _alternance_keyword(contraintes: list[str]) -> str | None:
    for c in contraintes or []:
        if isinstance(c, str) and any(kw in _strip_accents(c.lower()) for kw in _ALTERNANCE_KEYWORDS):
            return "alternance"
    return None


def build_narrative_retrieval_query(profile: Profile, original_question: str = "") -> str:
    """Forge une requête de retrieval focalisée depuis un profil récit.

    Args:
        profile: profil étendu (clarify_narrative). a_eviter et mobilite ignorés.
        original_question: récit brut, utilisé en FALLBACK si le profil ne
            fournit aucun signal exploitable (profil de repli).

    Returns:
        Requête focalisée (str). Jamais vide si `original_question` ne l'est pas.
    """
    parts: list[str] = []

    # 1. Spans verbatim des facettes positives (termes discriminants :
    #    "MIAGE", "data analyst", "BUT GEA"...).
    spans = profile.spans or {}
    for facet in _POSITIVE_SPAN_FACETS:
        span = spans.get(facet)
        if isinstance(span, str) and span.strip():
            parts.append(span.strip())

    # 2. Secteurs / domaines d'intérêt (termes propres).
    for sector in profile.sector_interest or []:
        if isinstance(sector, str) and sector.strip():
            parts.append(sector.strip())

    # 3. Région en BOOST (texte, jamais filtre dur). Le candidat mobile garde
    #    toutes les fiches hors-région ; le terme géo ne fait que pondérer.
    if profile.region and profile.region.strip():
        parts.append(profile.region.strip())

    # 4. Mot-clé corpus déterministe (domain-hint figé en code).
    kw = _alternance_keyword(profile.contraintes)
    if kw:
        parts.append(kw)

    query = re.sub(r"\s+", " ", " ".join(parts)).strip()

    # Fallback : profil de repli sans signal -> récit brut (mieux que vide).
    if not query:
        return (original_question or "").strip()
    return query

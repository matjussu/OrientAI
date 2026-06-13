"""Routing déterministe piloté par le PROFIL — mode récit (R1 1c, ordre #137).

En mode récit, le profil étendu (extrait par
`ProfileClarifier.clarify_narrative`) REMPLACE le RouterLLM : on dérive le
`RouteDecision` directement du profil, sans 3e appel LLM séquentiel. Gains :
- latence : un appel Mistral en moins sur le chemin critique ;
- déterminisme : reproductible pour la boucle de jugement humain.

Philosophie (décision Jarvis ordre #137) :
- RECALL-FIRST : un récit est multi-facettes par construction (c'est ce qui
  a déclenché le mode récit). On n'exclut rien par filtre dur ; la précision
  est l'affaire du reranker / MMR / top_k en aval.
- GÉO = BOOST, JAMAIS FILTRE DUR : `criteria` reste None même si le profil
  porte une région. R11 ("mobile en France") et R04 (géo absente) l'exigent,
  et 45,9% du corpus n'a pas de région. Le signal géo passe par la requête
  corpus-aware (1c-b), pas par `apply_metadata_filter`. C'est l'inverse exact
  du `deterministic_route` classique, qui pose region en filtre + hardlock.

Isolation : branché dans `OrientIAPipeline` UNIQUEMENT quand le flag récit
est ON. Le RouterLLM classique reste intact pour le banc 100q.
"""
from __future__ import annotations

from src.agent.tools.profile_clarifier import Profile
from src.rag.intent import _strip_accents
from src.rag.router_llm import RouteDecision, SUB_INDEX_NAMES


# Socle de sous-index pour tout récit d'orientation : la fiche formation
# (cible du conseil) + les statistiques (insertion / salaire / prospects,
# que tout conseiller mobilise). Recall minimal garanti.
_FLOOR_SUB_INDEXES: tuple[str, ...] = ("formations", "statistiques")

# Intentions qui justifient d'interroger aussi les fiches métier.
_METIER_INTENTS: frozenset[str] = frozenset({"info_metier_specifique"})

# Signaux (sur les contraintes du profil) qui justifient les aides
# territoriales / financement (CROUS, alternance rémunérée, bourses...).
# Normalisés sans accents, recherchés en substring.
_AIDES_KEYWORDS: tuple[str, ...] = (
    "alternance",
    "apprentissage",
    "contrat pro",
    "remunere",          # rémunéré / rémunération (sans accents)
    "remuneration",
    "finance",           # financé / financement
    "bourse",
    "budget",
    "gratuit",
    "sans revenu",
    "rentree d'argent",
    "aide",
)

# Top_k servi au générateur : un récit multi-facettes a besoin de plus de
# sources qu'une question courte pour couvrir toutes les facettes.
_NARRATIVE_TOP_K: int = 12


def _wants_aides(contraintes: list[str]) -> bool:
    """True si une contrainte signale un besoin de financement / alternance."""
    for c in contraintes or []:
        if not isinstance(c, str):
            continue
        norm = _strip_accents(c.lower())
        if any(kw in norm for kw in _AIDES_KEYWORDS):
            return True
    return False


def _is_fallback_profile(profile: Profile) -> bool:
    """True si le profil est un repli (clarify_narrative a échoué)."""
    return profile.confidence <= 0.0


def route_from_profile(profile: Profile) -> RouteDecision:
    """Dérive un RouteDecision déterministe depuis un profil récit.

    Recall-first, sans filtre dur ; géo en boost (via requête, pas ici).
    Le scope (urgent / out-of-scope) est traité en amont par le
    scope_classifier — ce routing suppose un récit in_scope et ne refuse
    jamais.

    Args:
        profile: profil étendu issu de `clarify_narrative`.

    Returns:
        RouteDecision (criteria=None, pas de lock, pas de hardlock, top_k
        relevé). is_fallback=False (chemin délibéré, pas un repli RouterLLM).
    """
    # Profil de repli : on maximise le recall (les 4 sous-index).
    if _is_fallback_profile(profile):
        return RouteDecision(
            sub_indexes=list(SUB_INDEX_NAMES),
            criteria=None,
            top_k_override=_NARRATIVE_TOP_K,
            confidence=0.4,
            is_fallback=False,
        )

    selected = set(_FLOOR_SUB_INDEXES)
    if profile.sector_interest or profile.intent_type in _METIER_INTENTS:
        selected.add("metiers")
    if _wants_aides(profile.contraintes):
        selected.add("aides_territoires")

    # Ordre canonique stable (déterminisme).
    sub_indexes = [s for s in SUB_INDEX_NAMES if s in selected]

    return RouteDecision(
        sub_indexes=sub_indexes,
        criteria=None,                 # géo = boost via requête, jamais filtre dur
        domain_lock=None,              # récit multi-facettes : pas de verrouillage
        hardlock_region_strict=False,
        hardlock_domain_strict=False,
        top_k_override=_NARRATIVE_TOP_K,
        confidence=0.8,
        is_fallback=False,
    )

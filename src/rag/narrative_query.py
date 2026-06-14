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
from src.rag.router_fallback import _CITY_TO_REGION


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


def _region_from_mobilite(mobilite: str) -> str:
    """Dérive la région canonique depuis une ville citée en mobilité.

    Fallback géo déterministe : le clarifier extrait souvent une `mobilite`
    libre (« rester à Bordeaux ») sans peupler `region`. On récupère alors le
    signal géo en mappant la ville -> région via la table partagée
    `_CITY_TO_REGION` (« rester à Bordeaux » -> « nouvelle-aquitaine »), pour
    alimenter le BOOST de la requête forgée. Code, pas prompt.

    Match sur bordure de mot (évite « pau » dans « paul ») ; villes les plus
    longues d'abord (« le mans » avant un éventuel « mans »). Retourne '' si
    aucune ville connue.
    """
    norm = _strip_accents(mobilite.lower())
    for city in sorted(_CITY_TO_REGION, key=len, reverse=True):
        if re.search(rf"\b{re.escape(city)}\b", norm):
            return _CITY_TO_REGION[city]
    return ""


def build_narrative_clarifier_input(question: str, history: list[dict] | None = None) -> str:
    """Assemble l'entree du clarifier en mode recit MULTI-TOUR (R2, FORK B).

    Accumulation profil par RE-EXTRACTION : on concatene les tours USER de la
    conversation (recit initial + follow-ups) puis le clarifier extrait le
    profil sur ce texte COMPLET. Le profil reflete ainsi toute la conversation,
    SANS merge-logic fragile ni stockage profil serveur (stateless -> anti-PII
    preserve). Au tour 1 (history vide) -> retourne la question seule
    (comportement 1c strictement inchange).

    Les tours ASSISTANT sont EXCLUS : ce sont nos reponses, pas le profil de
    l'utilisateur. L'ordre chronologique est preserve (recit initial d'abord).

    Args:
        question: message utilisateur courant (dernier tour).
        history: `[{role, content}]` de la conversation (cap 6 cote schemas).

    Returns:
        Texte concatene des tours user + question, separe par double saut de
        ligne. Jamais vide si `question` ne l'est pas.
    """
    parts: list[str] = []
    if history:
        for msg in history:
            if not isinstance(msg, dict):
                continue
            content = msg.get("content")
            if msg.get("role") == "user" and isinstance(content, str) and content.strip():
                parts.append(content.strip())
    if question and question.strip():
        parts.append(question.strip())
    return "\n\n".join(parts)


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
    region_term = (profile.region or "").strip()
    if not region_term and profile.mobilite:
        # Fallback géo déterministe : dériver la région depuis la ville citée en
        # mobilité quand le clarifier n'a pas peuplé `region` (« rester à
        # Bordeaux » -> « nouvelle-aquitaine »). Ne tire RIEN d'une mobilité
        # non-localisée (« mobile en France ») -> un candidat mobile n'est jamais
        # sur-contraint par un terme géo fabriqué.
        region_term = _region_from_mobilite(profile.mobilite)
    if region_term:
        parts.append(region_term)

    # 4. Mot-clé corpus déterministe (domain-hint figé en code).
    kw = _alternance_keyword(profile.contraintes)
    if kw:
        parts.append(kw)

    query = re.sub(r"\s+", " ", " ".join(parts)).strip()

    # Fallback : profil de repli sans signal -> récit brut (mieux que vide).
    if not query:
        return (original_question or "").strip()
    return query


# --- Extraction des OPTIONS comparées (fix A COMPARAISON, ordre 1926) ---
#
# Quand un récit compare des options NOMMÉES (« BUT GEA ou BTS CG ? », « prépa ou
# BUT info ? »), la requête forgée depuis le sector_interest ne surface pas
# forcément ces options (R05/R12 -> refus complet « pas dans mes sources »). On
# extrait déterministiquement les options pour un retrieval PAR option (cf
# `_prepare_narrative`), ce qui peuple la table même partiellement (« hors
# sources » sur une option absente type prépa, plutôt qu'un refus total).

_OPT_STOP = r"(?:[.?!,;]|\bpour\b|\bje crois\b|\bafin\b|\bcar\b|\bmais\b|\bsi jamais\b|$)"
_OPT_PATTERNS = [
    re.compile(r"\bmieux entre\s+(.+?)\s+et\s+(.+?)" + _OPT_STOP),
    re.compile(r"\bhesit\w*\b[^.?!]*?\bentre\s+(.+?)\s+et\s+(.+?)" + _OPT_STOP),
    # « (admis) à la fois en A et en B » : on ANCRE sur le contexte d'admission
    # pour ne pas attraper le « en » de la situation (« en terminale… »).
    re.compile(r"\ba la fois\s+en\s+(.+?)\s+et\s+en\s+(.+?)" + _OPT_STOP),
    re.compile(r"\badmis\w*\b[^.?!]*?\ben\s+(.+?)\s+et\s+(?:en\s+)?(.+?)" + _OPT_STOP),
    re.compile(r"\bentre\s+(.+?)\s+et\s+(.+?)" + _OPT_STOP),
]
_OPT_LEAD = re.compile(r"^(?:integrer|faire|aller en|passer par|suivre|choisir|une|un|le|la|les|l'|d'|de|des|en|a|du)\s+")


def _clean_option(s: str) -> str:
    s = re.sub(r"\(.*?\)", "", s or "").strip()          # retire les parenthèses
    s = re.sub(r"\b(post[- ]?bac|je crois|plutot)\b", "", s).strip()
    for _ in range(3):                                     # strip stopwords/verbes de tête
        s2 = _OPT_LEAD.sub("", s)
        if s2 == s:
            break
        s = s2
    s = " ".join(s.split()[:5])                            # cap ~5 mots
    return s.strip()


def extract_comparison_options(question: str) -> list[str]:
    """Extrait (déterministe) les options comparées d'un récit. [] si rien."""
    t = re.sub(r"\s+", " ", _strip_accents((question or "").lower()))
    for pat in _OPT_PATTERNS:
        m = pat.search(t)
        if not m:
            continue
        opts = [_clean_option(m.group(1)), _clean_option(m.group(2))]
        opts = [o for o in opts if o and len(o) >= 2]
        if len(opts) >= 2:
            return opts[:3]
    return []

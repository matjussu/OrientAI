"""Routage déterministe de la FORME — mode récit forme adaptative (ordre 1926).

Problème résolu : la génération récit sortait TOUJOURS la même structure figée
(4 sections : situation / pistes / vigilance / action), quelle que soit
l'intention du récit. Résultat « template de base » au lieu de « conseiller
expert ». Ce module décide, de façon PUREMENT DÉTERMINISTE (zéro LLM), QUEL
FORMAT de réponse colle à l'intention du récit, plus deux OVERLAYS de registre.

## Principe : marqueurs déterministes d'abord, intent_type en départage

Le routage prime les MARQUEURS sur le TEXTE BRUT (reproductibles run-to-run,
critique pour la stabilité démo ET la boucle de jugement humain), puis retombe
sur `profile.intent_type` (déjà extrait par `clarify_narrative`, gratuit) quand
les marqueurs sont muets, puis sur CONSEIL en dernier recours. AUCUN second
appel LLM : `intent_type` est extrait nativement, et un 2e call ré-introduirait
du non-déterminisme (mistral-small temp=0 n'est pas déterministe serveur-side).

## Précédence multi-match (NON négociable, ordre 1926)

Un récit peut allumer plusieurs familles de marqueurs (« je sais pas si je
préfère X ou Y, lequel ? » = exploratoire ET comparaison). La décision DOIT
rester déterministe. Ordre fixé :

    COMPARAISON > VALIDATION > TRAJECTOIRE > SHORTLIST > EXPLORATOIRE

puis `intent_type` en départage, puis CONSEIL (fallback).

## Formats vs overlays

- FORMATS (structure de sortie) : exploratoire, comparaison, trajectoire,
  validation, shortlist, conseil. Un seul par réponse.
- OVERLAYS (registre, orthogonaux, combinables avec tout format) :
  - `anchor_constraint` : contrainte non-négociable (budget / handicap / géo
    stricte) -> la réponse s'organise AUTOUR de la contrainte.
  - `reassure` : anxiété NON-détresse -> registre rassurant.

## Frontière sécurité (CRITIQUE)

`reassure` NE TOUCHE JAMAIS le circuit de sécurité. La détresse (R07 hardlock)
est tranchée EN AMONT par `scope_classifier` (regex urgent + LLM, Étape 1) avant
même que la branche récit ne soit prise. Quand ce routeur s'exécute, le scope a
déjà statué `in_scope`. `reassure` est un pur registre de ton appliqué à un récit
déjà jugé in_scope (cas R12 / T9 = contrôle négatif anti-sur-refus). Les
marqueurs de détresse réelle (« je tiens plus », « je craque ») vivent dans
`scope_classifier._URGENT_PATTERNS`, pas ici, et n'atteignent jamais ce routeur
en in_scope.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from src.agent.tools.profile_clarifier import Profile
from src.rag.intent import _strip_accents


# --- Formats (valeurs canoniques) ---
EXPLORATOIRE = "exploratoire"
COMPARAISON = "comparaison"
TRAJECTOIRE = "trajectoire"
VALIDATION = "validation"
SHORTLIST = "shortlist"
CONSEIL = "conseil"

VALID_FORMATS: frozenset[str] = frozenset(
    {EXPLORATOIRE, COMPARAISON, TRAJECTOIRE, VALIDATION, SHORTLIST, CONSEIL}
)

# Précédence multi-match (du plus prioritaire au moins prioritaire).
_PRECEDENCE: tuple[str, ...] = (
    COMPARAISON,
    VALIDATION,
    TRAJECTOIRE,
    SHORTLIST,
    EXPLORATOIRE,
)


@dataclass
class FormatDecision:
    """Décision de forme pour un récit (déterministe, traçable).

    - format : un des `VALID_FORMATS`.
    - anchor_constraint / reassure : overlays de registre (orthogonaux).
    - constraint_terms : marqueurs de contrainte dure repérés (trace + prompt).
    - source : "markers" | "intent_type" | "fallback" (d'où vient le format).
    - matched : familles de marqueurs allumées (trace / debug / LOT).
    """

    format: str
    anchor_constraint: bool = False
    reassure: bool = False
    constraint_terms: list[str] = field(default_factory=list)
    source: str = "fallback"
    matched: dict[str, bool] = field(default_factory=dict)

    def is_valid(self) -> bool:
        return self.format in VALID_FORMATS


def _norm(text: str) -> str:
    """Minuscule + sans accents + espaces normalisés. Apostrophes typographiques
    ramenées à l'apostrophe simple pour des marqueurs robustes."""
    t = _strip_accents((text or "").lower()).replace("’", "'").replace("`", "'")
    return re.sub(r"\s+", " ", t).strip()


# --- Marqueurs par famille (substrings normalisés, sauf regex explicites) ---

# COMPARAISON : arbitrage explicite entre options. On évite le « ou » nu (trop
# large : énumération « le dev ou la data ») ; on exige un signe de délibération.
_COMPARAISON_SUB: tuple[str, ...] = (
    "lequel", "laquelle", "lesquels", "lesquelles",
    "le mieux", "la mieux", "le meilleur choix", "mieux entre",
    "j'hesite entre", "hesite entre", "choisir entre", "trancher entre",
    "du mal a choisir", "arrive pas a choisir", "n'arrive pas a choisir",
    "arrive pas a trancher", "n'arrive pas a trancher", "du mal a trancher",
    "pas a trancher", "trancher", "ou bien", "versus", " vs ",
    "comparer", "difference entre",
)
# Pas de regex « entre X et Y » nu : trop de faux positifs (« le pont entre
# l'informatique et la gestion », « entre 18 et 25 ans »). La délibération réelle
# est captée par les substrings « hesite/choisir/trancher entre ».
_COMPARAISON_RE: tuple[re.Pattern, ...] = ()

# VALIDATION : oui/non sur UNE option / un fit. « est-ce que » seul est trop
# large -> exige un objet de validation, sauf formes fortes autoporteuses.
_VALIDATION_QMARK: tuple[str, ...] = ("est-ce que", "est ce que", "est-ce qu'", "c'est un bon", "est-ce un bon")
_VALIDATION_OBJECT: tuple[str, ...] = (
    "bon choix", "bon plan", "bonne idee", "fait pour moi", "me correspond",
    "pour mon profil", "vaut le coup", "ca vaut le coup", "je devrais",
    "pertinent", "adapte a mon", "le bon choix", "c'est bien pour moi",
)
_VALIDATION_STRONG: tuple[str, ...] = (
    "est-ce un bon choix", "est ce un bon choix",
    "fait pour moi", "est fait pour moi", "vaut le coup",
    "bon choix pour mon profil", "bon choix pour moi",
)
# Note : « me correspond » n'est PAS un marqueur fort autoporteur -> il fire sur
# l'OUVERT « qu'est-ce qui pourrait me correspondre » (exploratoire). Il reste un
# OBJET de validation (exige un « est-ce que » : « est-ce que X me correspond »).

# TRAJECTOIRE : reconversion / réorientation / passerelle / peur d'avoir perdu.
_TRAJECTOIRE_SUB: tuple[str, ...] = (
    "reconvert", "me reorienter", "reorientation", "basculer",
    "changer de voie", "changer de metier", "changer de filiere",
    "changer completement", "me reconvertir", "transition", "passerelle",
    "repartir", "perdu deux", "perdu un an", "perdu mes annees",
    "perdre des annees", "perdu des annees", "perdu deux annees",
    "j'ai perdu", "ai perdu", "me sortir de", "tout recommencer",
    "recommencer a zero", "repartir de zero", "ne me convient plus",
)

# SHORTLIST : veut juste les N meilleures options, concis (pas de développement).
_SHORTLIST_SUB: tuple[str, ...] = (
    "les meilleures", "les meilleurs", "la meilleure ecole", "le top",
    "top 3", "top 5", "top cinq", "top trois",
    "donne-moi juste", "donne moi juste", "juste les",
    "pas besoin de tout m'expliquer", "pas besoin de tout expliquer",
    "pas besoin d'explication", "pas besoin de details", "pas besoin que tu detailles",
    "liste-moi", "liste moi", "directement les", "que je devrais viser",
    "balance-moi", "cite-moi juste",
)

# EXPLORATOIRE : lostness réelle (PAS une simple question ouverte de clôture).
_EXPLORATOIRE_SUB: tuple[str, ...] = (
    "aucune idee", "pas la moindre idee", "je sais pas", "je ne sais pas",
    "sais plus", "je sais plus", "ne sais plus", "completement perdu",
    "suis perdu", "suis paume", "ouvert a tout", "pas d'idee",
    "trop de choix", "par ou commencer", "j'y connais rien",
    "ne sais pas quoi faire", "sais pas quoi en faire", "plus quoi en faire",
    "sais plus quoi en faire", "ne sais plus ou j'en suis",
)

# ANCHOR_CONSTRAINT : contrainte DURE non-négociable (budget / handicap / géo).
_ANCHOR_SUB: tuple[str, ...] = (
    "pas les moyens", "n'a pas les moyens", "pas de moyens",
    "je ne peux pas payer", "peux pas payer", "ne peux pas me permettre",
    "pas me permettre", "il me faut absolument", "absolument du public",
    "que du public", "uniquement du public", "obligatoirement du public",
    "il faut que ce soit gratuit", "sans payer", "boursier",
    "handicap", "en situation de handicap", "pmr", "malvoyant", "mal voyant",
    "fauteuil roulant", "non negociable", "non-negociable",
    "je ne peux pas m'eloigner", "peux pas m'eloigner",
    "ne peux pas trop m'eloigner", "pas trop m'eloigner",
    "ne peux pas bouger", "ne peux pas partir", "pas mobile du tout",
)

# REASSURE : anxiété NON-détresse (stress / peur de décevoir / se sentir paumé).
# NE PAS confondre avec la détresse (gérée en amont par scope_classifier).
_REASSURE_SUB: tuple[str, ...] = (
    "je stresse", "ca me stresse", "stresse enormement", "stresse a mort",
    "j'ai peur", "ai peur de", "angoisse", "anxieux", "ca m'angoisse",
    "decevoir mes parents", "decevoir ma famille", "gacher mon annee",
    "gacher une annee", "pas confiance en moi", "perdu confiance",
    "je me sens nul", "je flippe", "j'ai honte", "peur de me tromper",
    "peur de faire le mauvais", "peur du mauvais choix",
)


def _any_sub(text: str, subs: tuple[str, ...]) -> bool:
    return any(s in text for s in subs)


def _matched_terms(text: str, subs: tuple[str, ...]) -> list[str]:
    return [s.strip() for s in subs if s in text]


def _has_comparaison(text: str) -> bool:
    return _any_sub(text, _COMPARAISON_SUB) or any(p.search(text) for p in _COMPARAISON_RE)


def _has_validation(text: str) -> bool:
    if _any_sub(text, _VALIDATION_STRONG):
        return True
    return _any_sub(text, _VALIDATION_QMARK) and _any_sub(text, _VALIDATION_OBJECT)


def _has_trajectoire(text: str) -> bool:
    return _any_sub(text, _TRAJECTOIRE_SUB)


def _has_shortlist(text: str) -> bool:
    return _any_sub(text, _SHORTLIST_SUB)


def _has_exploratoire(text: str) -> bool:
    return _any_sub(text, _EXPLORATOIRE_SUB)


# Marqueurs -> format (dans l'ordre de précédence).
_MARKER_DETECTORS: tuple[tuple[str, "callable"], ...] = (
    (COMPARAISON, _has_comparaison),
    (VALIDATION, _has_validation),
    (TRAJECTOIRE, _has_trajectoire),
    (SHORTLIST, _has_shortlist),
    (EXPLORATOIRE, _has_exploratoire),
)

# intent_type (déjà extrait) -> format, en départage quand les marqueurs sont muets.
_INTENT_TO_FORMAT: dict[str, str] = {
    "comparaison_options": COMPARAISON,
    "reconversion_pro": TRAJECTOIRE,
    "reorientation_etude": TRAJECTOIRE,
    "decouverte_filieres": EXPLORATOIRE,
    "info_metier_specifique": VALIDATION,
    "orientation_initiale": CONSEIL,
    "conseil_strategique": CONSEIL,
    "conceptuel_definition": CONSEIL,
    "demarche_administrative": CONSEIL,
    "other": CONSEIL,
}


def _detect_anchor(text: str, profile: Profile) -> tuple[bool, list[str]]:
    """Contrainte dure : marqueurs texte + champs profil (contraintes / a_eviter /
    mobilite). Renvoie (présence, termes repérés pour la trace + le prompt)."""
    terms = _matched_terms(text, _ANCHOR_SUB)
    for field_vals in (profile.contraintes, profile.a_eviter):
        for v in field_vals or []:
            if isinstance(v, str):
                terms += _matched_terms(_norm(v), _ANCHOR_SUB)
    if isinstance(profile.mobilite, str):
        terms += _matched_terms(_norm(profile.mobilite), _ANCHOR_SUB)
    # dédup en préservant l'ordre
    seen: set[str] = set()
    uniq = [t for t in terms if not (t in seen or seen.add(t))]
    return (bool(uniq), uniq)


def _detect_reassure(text: str, profile: Profile) -> bool:
    """Anxiété non-détresse : marqueurs texte OU urgent_concern du profil.
    Pur registre de ton -> n'influence JAMAIS le scope (cf docstring module)."""
    return bool(profile.urgent_concern) or _any_sub(text, _REASSURE_SUB)


def route_narrative_format(
    profile: Profile,
    question: str,
    history: list[dict] | None = None,
) -> FormatDecision:
    """Dérive un `FormatDecision` déterministe depuis le profil + le texte courant.

    Le format est routé sur le TEXTE COURANT (`question`) : marqueurs d'abord
    (précédence fixe), puis `profile.intent_type` en départage, puis CONSEIL.
    En multi-tour, un follow-up court sans marqueur retombe sur `intent_type`
    (extrait sur la conversation accumulée) -> format stable et cohérent.
    `history` est réservé (le profil porte déjà l'accumulation multi-tour).

    Args:
        profile: profil étendu (clarify_narrative).
        question: message utilisateur courant (récit ou follow-up).
        history: réservé (non utilisé en v1 ; cf docstring).

    Returns:
        FormatDecision (format toujours dans VALID_FORMATS ; overlays orthogonaux).
    """
    text = _norm(question)

    # Overlays (orthogonaux, indépendants du format).
    anchor, constraint_terms = _detect_anchor(text, profile)
    reassure = _detect_reassure(text, profile)

    matched = {fmt: detector(text) for fmt, detector in _MARKER_DETECTORS}

    # 1. Marqueurs déterministes, dans l'ordre de précédence.
    chosen = next((fmt for fmt in _PRECEDENCE if matched.get(fmt)), None)
    source = "markers"

    # 2. Départage par intent_type (déjà extrait, gratuit) si aucun marqueur.
    if chosen is None:
        mapped = _INTENT_TO_FORMAT.get(profile.intent_type)
        if mapped is not None and mapped != CONSEIL:
            chosen, source = mapped, "intent_type"

    # 3. Fallback CONSEIL.
    if chosen is None:
        chosen, source = CONSEIL, "fallback"

    return FormatDecision(
        format=chosen,
        anchor_constraint=anchor,
        reassure=reassure,
        constraint_terms=constraint_terms,
        source=source,
        matched={k: v for k, v in matched.items() if v},
    )

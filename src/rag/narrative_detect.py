"""Detection deterministe du MODE RECIT (R1 1a, ordre Jarvis 2026-06-13-1522).

Les vrais utilisateurs de la plateforme n'envoient pas des questions courtes :
ils racontent un recit long (parcours + situation + envies + a-eviter) et
attendent une reponse developpee niveau conseiller. Ce module decide, de facon
PUREMENT DETERMINISTE (zero LLM), si une question releve du mode recit.

## Isolation baseline (NON negociable)

Le banc de non-regression `src/eval/questions.json` (100 questions, mediane 67
chars, max 118) NE DOIT JAMAIS declencher le mode recit, sinon la comparabilite
longitudinale casse. On le garantit PAR CONSTRUCTION, pas par chance lexicale :

    is_narrative = len >= 300  OU  (len >= 200 ET facettes >= 2)

Le plancher de 200 chars sur la regle "facettes" assure qu'AUCUNE question
courte (max 118) ne peut declencher, quel que soit le lexique de facettes. Le
seuil de 300 chars seul catch deja les 12 recits du seed (tous >= 300). La regle
facettes (200-299 chars + >=2 facettes) rattrape les recits de longueur moyenne.

Calibration verifiee par tests :
- `test_isolation_baseline_100q` : 0/100 declenche.
- `test_seed_recits_all_trigger` : 12/12 declenchent.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field


# Seuils de calibration (cf docstring). Exposes pour tests / tuning.
NARRATIVE_MIN_LEN = 300          # >= ce nombre de chars -> recit (regle primaire)
FACET_MIN_LEN = 200              # plancher pour que la regle facettes s'applique
FACET_THRESHOLD = 2              # nombre de categories de facettes distinctes requis


def _strip_accents(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", s)
        if not unicodedata.combining(c)
    )


# Categories de facettes lexicales. Chaque categorie = signal qu'un aspect du
# profil est exprime. Patterns appliques sur le texte minuscule SANS accents.
# La precision n'est pas critique pour l'isolation (garantie par le plancher de
# longueur) ; ce lexique sert la regle secondaire (recits moyens 200-299 chars)
# et le diagnostic (combien de facettes exprimees).
_FACET_PATTERNS: dict[str, list[re.Pattern]] = {
    "situation": [
        re.compile(r"\bje suis en (terminale|premiere|deuxieme|troisieme|derniere|l[123]|m[12]|bts|but|prepa|licence|master|cap|bac)"),
        re.compile(r"\bje suis (etudiant|lyceen|en poste|salarie|vendeur|au chomage|sans emploi|interimaire)"),
        re.compile(r"\bj'ai \d+ ans\b"),
        re.compile(r"\bapres (ma|mon|un|une) (l[123]|licence|bac|but|bts|master|prepa)"),
        re.compile(r"\bje (termine|finis|viens de finir|suis en train de finir)\b"),
        re.compile(r"\bje travaille\b"),
        re.compile(r"\ben (premiere|deuxieme|derniere) annee\b"),
        re.compile(r"\bj'enchaine\b"),
        re.compile(r"\ben interim\b"),
    ],
    "cible": [
        re.compile(r"\bje (veux|voudrais|aimerais|souhaite|compte)\b"),
        re.compile(r"\bje pense (a |de plus en plus a )?devenir\b"),
        re.compile(r"\bdevenir\b"),
        re.compile(r"\bm['e ]?orienter\b"),
        re.compile(r"\bme reorienter\b"),
        re.compile(r"\bme reconvertir\b|\breconversion\b|\breconvertir\b"),
        re.compile(r"\bje vise\b"),
        re.compile(r"\bm['e ]?orienter vers\b"),
    ],
    "interets": [
        re.compile(r"\bj['e ]?(aime|adore)\b"),
        re.compile(r"\bje m['e ]?interesse\b"),
        re.compile(r"\bpassionne\b"),
        re.compile(r"\bce qui me pla[iî]t\b"),
        re.compile(r"\binteret pour\b"),
        re.compile(r"\bj'ai (un |developpe un )?(vrai )?interet\b"),
    ],
    "a_eviter": [
        re.compile(r"\bje (ne )?veux (surtout )?pas\b"),
        re.compile(r"\beviter\b"),
        re.compile(r"\bje n['e ]?aime pas\b"),
        re.compile(r"\bca ne me (tente|convient|pla[iî]t|attire)\b"),
        re.compile(r"\bca m['e ]?ennuie\b"),
        re.compile(r"\brebarbatif\b"),
        re.compile(r"\bje deteste\b"),
        re.compile(r"\bne me convient plus\b"),
    ],
    "contrainte": [
        re.compile(r"\balternance\b"),
        re.compile(r"\bcontrat (pro|de professionnalisation|d['e ]?apprentissage)\b"),
        re.compile(r"\bapprentissage\b"),
        re.compile(r"\bremunere\b"),
        re.compile(r"\bpas trop long\b|\betudes courtes\b"),
        re.compile(r"\ba distance\b"),
        re.compile(r"\bloyer\b"),
        re.compile(r"\bsans (rentree d'argent|revenu)\b"),
    ],
    "comparaison": [
        re.compile(r"\bj['e ]?hesite entre\b"),
        re.compile(r"\bplutot que\b"),
        re.compile(r"\bou bien\b"),
    ],
    "geo": [
        re.compile(r"\bj['e ]?habite\b"),
        re.compile(r"\ben region\b"),
        re.compile(r"\bpres de chez\b"),
        re.compile(r"\bmobile\b|\bmobilite\b"),
        re.compile(r"\bdemenag"),
        re.compile(r"\brester a\b"),
        re.compile(r"\b(paris|lyon|marseille|lille|bordeaux|nantes|toulouse|nice|strasbourg|rennes|montpellier|grenoble|villeneuve d'ascq)\b"),
    ],
}


@dataclass
class NarrativeSignal:
    """Diagnostic de la detection (utile pour tests, logs, observabilite)."""
    is_narrative: bool
    length: int
    facets: set[str] = field(default_factory=set)
    reason: str = ""


def detect_facets(question: str) -> set[str]:
    """Retourne l'ensemble des CATEGORIES de facettes detectees (lexical, deterministe)."""
    if not question:
        return set()
    norm = _strip_accents(question).lower()
    found: set[str] = set()
    for category, patterns in _FACET_PATTERNS.items():
        if any(p.search(norm) for p in patterns):
            found.add(category)
    return found


def narrative_signal(question: str) -> NarrativeSignal:
    """Detection complete avec diagnostic.

    Regle (cf docstring module) :
        len >= NARRATIVE_MIN_LEN  OU  (len >= FACET_MIN_LEN ET facettes >= FACET_THRESHOLD)
    """
    q = question or ""
    length = len(q.strip())
    if length >= NARRATIVE_MIN_LEN:
        return NarrativeSignal(
            is_narrative=True, length=length, facets=detect_facets(q),
            reason=f"length>={NARRATIVE_MIN_LEN}",
        )
    if length >= FACET_MIN_LEN:
        facets = detect_facets(q)
        if len(facets) >= FACET_THRESHOLD:
            return NarrativeSignal(
                is_narrative=True, length=length, facets=facets,
                reason=f"length>={FACET_MIN_LEN} & facets>={FACET_THRESHOLD} ({sorted(facets)})",
            )
        return NarrativeSignal(
            is_narrative=False, length=length, facets=facets,
            reason=f"length<{NARRATIVE_MIN_LEN}, facets<{FACET_THRESHOLD}",
        )
    return NarrativeSignal(
        is_narrative=False, length=length, facets=set(),
        reason=f"length<{FACET_MIN_LEN}",
    )


def is_narrative(question: str) -> bool:
    """True si la question releve du mode recit (recit long multi-facettes).

    Deterministe, zero LLM. Garantit que les questions courtes (< 200 chars,
    dont les 100 du banc de non-regression, max 118) ne declenchent JAMAIS.
    """
    return narrative_signal(question).is_narrative


def is_narrative_followup(history: list[dict] | None) -> bool:
    """True si la CONVERSATION est deja en mode recit : un tour USER anterieur
    de l'history est lui-meme un recit (is_narrative).

    R2 multi-tour : permet de router les follow-ups COURTS (« et a Lyon ? »,
    « oui developpe la piste A ») en mode recit au tour 2+, alors que
    `is_narrative(question)` seul ne verrait que le message courant et
    laisserait le follow-up retomber sur le pipeline classique (perte du
    contexte recit).

    Isolation baseline preservee PAR CONSTRUCTION : le banc 100q/497q est
    SINGLE-TURN (history=None/[]) -> retourne toujours False -> jamais de
    bascule recit sur le banc. Deterministe, zero LLM.
    """
    if not history:
        return False
    for msg in history:
        if not isinstance(msg, dict):
            continue
        if msg.get("role") == "user" and isinstance(msg.get("content"), str):
            if is_narrative(msg["content"]):
                return True
    return False

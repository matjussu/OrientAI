"""RouterLLM — Routing décisionnel léger Mistral Small JSON-tool.

Décide en amont du retrieve : (a) quel(s) sub-index FAISS interroger,
(b) quelles FilterCriteria appliquer, (c) si la question doit être
court-circuitée par un refus structuré (superlatif, cross-domain),
(d) quelles contraintes hardlock injecter dans le prompt v4.1 strict
via R7, (e) un override de top_k_sources.

Pattern : Mistral Small + `tool_choice="any"` + 1 seul tool
`decide_route` (single-call mode), calqué sur AnalystAgent
(`src/agents/hierarchical/analyst_agent.py:121-181`).

Cf docs/ADR-064-router-llm-leger.md, docs/ADR-065-quad-subindexes-partition.md.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from mistralai.client import Mistral

from src.agent.retry import call_with_retry
from src.agent.tool import Tool
from src.rag.intent import _strip_accents
from src.rag.metadata_filter import FilterCriteria
from src.rag.models import MISTRAL_SMALL


# ────────────────────────── Constantes routing ──────────────────────────


SUB_INDEX_NAMES: tuple[str, ...] = (
    "formations",
    "metiers",
    "statistiques",
    "aides_territoires",
)

REFUSAL_REASONS: tuple[str, ...] = (
    "superlative_no_data",
    "cross_domain",
    "out_of_scope_specific",
)

# Réponses pré-écrites par refusal_reason. Le pipeline les retourne
# directement sans appel LLM (court-circuit comme ScopeClassifier).
#
# Step 11.7 chantier 4 (2026-05-09) : 3 variants par refusal_reason au lieu
# d'un template unique. Le user a observé sur le dump step 11.5 que
# 3 questions différentes (L01, A1, A3) recevaient EXACTEMENT la même
# réponse mot-pour-mot — placebo très visible. Avec 3 variants
# hash-selected sur la question, deux questions distinctes auront
# probablement des formulations différentes (gardent le même fond mais
# varient le ton). Sélection déterministe (reproductible) via
# hash(question) % len(variants).
REFUSAL_TEMPLATE_VARIANTS: dict[str, list[str]] = {
    "superlative_no_data": [
        # Variant 1 — explicite + détaillé (l'historique)
        "Je n'ai pas de classement ou comparatif officiel des « meilleures » "
        "formations dans mes sources — ce type de hiérarchie n'est pas dans "
        "le corpus public que j'utilise (Parcoursup, ONISEP, France Compétences).\n\n"
        "Pour des classements, je te renvoie vers :\n"
        "- **Onisep** pour les fiches officielles : https://www.onisep.fr\n"
        "- **L'Étudiant** ou **Le Figaro Étudiant** pour les palmarès non-officiels\n"
        "- **Le SCUIO** de ton université ou un **CIO** pour un avis personnalisé\n\n"
        "Si tu veux, je peux te montrer les formations de ce domaine dans mes "
        "sources avec leurs critères concrets (places, taux d'accès, profils admis). "
        "Lesquels t'intéressent ?",
        # Variant 2 — direct + actionnable
        "Pas de palmarès officiel dans mes sources : Parcoursup et ONISEP "
        "publient des fiches formation par formation, mais pas de top 5 ou "
        "top 10. Les classements existants (L'Étudiant, Le Figaro Étudiant, "
        "QS, Shanghai) viennent de méthodologies privées que je ne reproduis pas.\n\n"
        "Ce que je peux faire à la place : te lister les formations de ce "
        "domaine avec leurs **critères concrets** (sélectivité, places, "
        "taux d'accès, profils admis). C'est souvent plus utile pour décider "
        "qu'un classement.\n\n"
        "Quelles caractéristiques comptent le plus pour toi ? "
        "(Sélectivité, ville, type de diplôme, taux d'insertion…)",
        # Variant 3 — pédagogique + interrogatif
        "Bonne question, mais elle se heurte à une limite réelle : il n'existe "
        "pas de classement universel et officiel des formations en France. "
        "Les rankings que tu vois (L'Étudiant, Le Figaro, QS World) sont "
        "produits par des médias avec leurs propres critères, et mes sources "
        "(Parcoursup, ONISEP, France Compétences) n'en font pas.\n\n"
        "Du coup, le « meilleur » dépend de **ce que tu valorises** : "
        "réputation, sélectivité, prox' géo, alternance possible, taux "
        "d'insertion ? Si tu me précises ton angle, je peux te sortir les "
        "formations qui matchent ces critères dans mes sources. Sinon, "
        "consulte le **CIO** ou ton **SCUIO** — ils sont formés pour "
        "ce genre d'arbitrage.",
    ],
    "cross_domain": [
        # Variant 1 — l'historique
        "Cette question sort du périmètre d'OrientAI — je suis spécialisé sur "
        "l'orientation post-bac française (formations, métiers, admission, "
        "insertion). Pour ce sujet, mieux vaut consulter une source dédiée.\n\n"
        "Si ta question concerne **une orientation professionnelle** liée à "
        "ce domaine, reformule : par exemple « comment devenir [métier] ? » "
        "ou « quelles formations pour travailler dans [secteur] ? ».",
        # Variant 2 — plus chaleureux
        "Je peux pas vraiment t'aider sur ce sujet — mon périmètre c'est "
        "l'orientation post-bac française : formations, métiers, admission, "
        "passerelles, insertion pro. Pour cette question, cherche du côté "
        "d'une ressource spécialisée.\n\n"
        "Par contre, si tu veux explorer un **métier ou une formation lié·e** "
        "à ce sujet, dis-le moi et je creuse. Exemples : « quelles études "
        "pour devenir [X] ? », « quels parcours mènent à [secteur] ? ».",
        # Variant 3 — direct et bref
        "Désolé, ce n'est pas mon domaine — je suis OrientAI, conseiller "
        "d'orientation post-bac. Pour les questions médicales, juridiques, "
        "actualités, etc., consulte une source spécialisée.\n\n"
        "Si tu cherches **une formation ou un métier** dans ce thème, "
        "reformule en ce sens : par exemple « quelles études en santé pour "
        "travailler avec des enfants ? » et je peux t'aider.",
    ],
    "out_of_scope_specific": [
        # Variant 1 — l'historique
        "Je n'ai pas d'information fiable dans mes sources pour répondre à "
        "cette question précise. Pour ne pas inventer, je préfère te rediriger :\n\n"
        "- **Onisep** : https://www.onisep.fr — fiches formations + métiers officielles\n"
        "- **Parcoursup** : https://www.parcoursup.fr — procédures, taux d'accès\n"
        "- **SCUIO** ou **CIO** — conseiller·ère d'orientation\n\n"
        "Tu peux aussi reformuler ou préciser ta question (région, niveau, "
        "secteur) et je ferai de mon mieux dans les limites de mes données.",
        # Variant 2 — invite à reformuler
        "Pas trouvé d'info précise sur ta question dans mes sources. "
        "Plutôt que d'inventer, je te propose deux pistes :\n\n"
        "1. **Reformule** en précisant région, niveau (bac+N), secteur, "
        "type de diplôme — souvent le détail qui fait la différence.\n"
        "2. **Source officielle** : Onisep (https://www.onisep.fr), "
        "Parcoursup (https://www.parcoursup.fr), ou ton CIO/SCUIO local.\n\n"
        "Sur quoi veux-tu que je creuse en priorité ?",
        # Variant 3 — court et orienté action
        "Cette question dépasse ce que mes sources couvrent précisément. "
        "Pour ne pas te donner une info partielle ou inventée, je préfère "
        "te rediriger :\n\n"
        "- **Onisep** : https://www.onisep.fr (fiches officielles)\n"
        "- **Parcoursup** : https://www.parcoursup.fr (procédures)\n"
        "- **CIO** / **Psy-EN** : conseil personnalisé sur ton parcours\n\n"
        "Sinon, reformule avec un angle plus précis et je retente.",
    ],
}

# Fallback compat : REFUSAL_TEMPLATES = variant[0] de chaque reason.
# Préserve l'API publique pour les tests existants et toute consommation
# qui aurait pris le 1er template tel quel.
REFUSAL_TEMPLATES: dict[str, str] = {
    reason: variants[0] for reason, variants in REFUSAL_TEMPLATE_VARIANTS.items()
}


def select_refusal_template(reason: str, question: str | None = None) -> str:
    """Sélectionne déterministiquement un variant de template REFUSAL.

    Stratégie : hash(question) % len(variants). Reproductible (même
    question → même variant) mais différentes questions ont
    statistiquement 1/3 de chance de tomber sur le même variant.

    Si `question` est None ou vide, retourne variant[0] (compat).
    Si `reason` est inconnu, retourne le template `out_of_scope_specific`
    (fallback gracieux).

    Step 11.7 chantier 4 — résout le bug "L01/A1/A3 réponse mot-pour-mot
    identique" identifié par lecture qualitative du dump step 11.5.
    """
    variants = REFUSAL_TEMPLATE_VARIANTS.get(reason)
    if variants is None:
        # Reason inconnu → fallback générique
        variants = REFUSAL_TEMPLATE_VARIANTS["out_of_scope_specific"]
    if not question:
        return variants[0]
    # hash() Python a un seed aléatoire par session par défaut. Pour
    # reproductibilité cross-session (bench), on utilise MD5 (déterministe
    # et bien distribué — sum(ord) collisionne facilement sur des questions
    # similaires comme "Quelle est la meilleure école de X ?" où les
    # variations syntaxiques mineures donnent souvent la même somme
    # modulo 3).
    import hashlib
    digest = hashlib.md5(question.encode("utf-8")).hexdigest()
    seed = int(digest[:8], 16)  # 32 bits suffisent largement
    return variants[seed % len(variants)]


# ────────────────────────── Dataclass RouteDecision ──────────────────────────


@dataclass
class RouteDecision:
    """Décision de routing produite par RouterLLM en amont du retrieve.

    Champs :
        sub_indexes: list des sub-index FAISS à interroger (1 à 4).
            Multi-index = fusion RRF post-retrieve.
        criteria: FilterCriteria à appliquer post-retrieve. None = pas
            de filtre (équiv backward compat).
        domain_lock: liste de `domain` exacts à verrouiller (ex ['crous']).
            None ou [] = pas de verrouillage. Mappé sur FilterCriteria
            étendu en étape 6.
        refusal_reason: si non-null, court-circuit pré-pipeline avec
            `pre_written_response`. Voir REFUSAL_REASONS.
        pre_written_response: réponse texte si refusal. Populé via
            REFUSAL_TEMPLATES si non fourni explicitement.
        hardlock_region_strict: si True, R7 contraint le générateur à ne
            PAS proposer d'alternative hors-région sans signaler le vide.
        hardlock_domain_strict: si True, R7 contraint le générateur à ne
            PAS mélanger plusieurs domaines.
        top_k_override: force top_k_sources servies au LLM. Utile pour
            multi-critères (cas BTS Rennes/BUT Brest rang 6).
        confidence: 0-1, signal au pipeline. <0.6 → fallback union
            sub-indexes (filet de sécurité contre router qui se trompe).
        is_fallback: True si construit par router_fallback (déterministe)
            au lieu de RouterLLM. Utile pour observabilité/debug.
    """

    sub_indexes: list[str] = field(default_factory=lambda: list(SUB_INDEX_NAMES))
    criteria: FilterCriteria | None = None
    domain_lock: list[str] | None = None
    refusal_reason: str | None = None
    pre_written_response: str | None = None
    hardlock_region_strict: bool = False
    hardlock_domain_strict: bool = False
    top_k_override: int | None = None
    confidence: float = 0.0
    is_fallback: bool = False

    def __post_init__(self) -> None:
        # Validation sub_indexes : tous dans SUB_INDEX_NAMES, au moins 1
        if not self.sub_indexes:
            self.sub_indexes = list(SUB_INDEX_NAMES)
        invalid = [s for s in self.sub_indexes if s not in SUB_INDEX_NAMES]
        if invalid:
            raise ValueError(
                f"sub_indexes contient des valeurs invalides {invalid}. "
                f"Attendu un sous-ensemble de {list(SUB_INDEX_NAMES)}."
            )
        # Dédupe en préservant l'ordre
        seen: set[str] = set()
        deduped: list[str] = []
        for s in self.sub_indexes:
            if s not in seen:
                seen.add(s)
                deduped.append(s)
        self.sub_indexes = deduped

        # Validation refusal_reason
        if self.refusal_reason is not None and self.refusal_reason not in REFUSAL_REASONS:
            raise ValueError(
                f"refusal_reason invalide : {self.refusal_reason!r}. "
                f"Attendu null ou {list(REFUSAL_REASONS)}."
            )

        # Auto-population pre_written_response depuis template si refusal
        # mais aucune réponse fournie (cas standard LLM qui pose juste la raison)
        if self.refusal_reason is not None and not self.pre_written_response:
            self.pre_written_response = REFUSAL_TEMPLATES.get(
                self.refusal_reason, REFUSAL_TEMPLATES["out_of_scope_specific"]
            )

        # Confidence clampée [0, 1]
        self.confidence = max(0.0, min(1.0, float(self.confidence)))

    @classmethod
    def from_tool_payload(cls, payload: dict[str, Any]) -> "RouteDecision":
        """Construit un RouteDecision depuis le payload retourné par le tool LLM.

        Tolère les clés manquantes (defaults safes), parse les sous-objets
        (region/niveau/secteur → FilterCriteria), valide les enums via
        __post_init__.

        Args:
            payload: dict produit par `_route_decision_tool_func` (ou
                directement par le LLM via tool_call).

        Returns:
            RouteDecision validé. ValueError si payload invalide.
        """
        sub_indexes = payload.get("sub_indexes") or list(SUB_INDEX_NAMES)
        if not isinstance(sub_indexes, list):
            sub_indexes = list(SUB_INDEX_NAMES)

        # Construction FilterCriteria si au moins un champ pertinent.
        # Normalisation accents sur `region` pour cohérence avec
        # router_fallback._detect_region (qui utilise _strip_accents) et
        # avec apply_metadata_filter (matching insensible aux accents).
        # Sans ça, le LLM-routed path renverrait "auvergne-rhône-alpes"
        # alors que le fallback renvoie "auvergne-rhone-alpes" → mismatch
        # silencieux du filtre métadonnées.
        region = payload.get("region")
        niveau_min = payload.get("niveau_min")
        niveau_max = payload.get("niveau_max")
        secteur = payload.get("secteur")
        criteria: FilterCriteria | None = None
        if any(v is not None for v in (region, niveau_min, niveau_max, secteur)):
            region_norm: str | None = None
            if isinstance(region, str) and region.strip():
                region_norm = _strip_accents(region.strip().lower())
            criteria = FilterCriteria(
                region=region_norm,
                niveau_min=niveau_min if isinstance(niveau_min, int) else None,
                niveau_max=niveau_max if isinstance(niveau_max, int) else None,
                secteur=list(secteur) if isinstance(secteur, list) and secteur else None,
            )

        domain_lock = payload.get("domain_lock")
        if isinstance(domain_lock, list) and domain_lock:
            domain_lock_clean: list[str] | None = [str(d).strip().lower() for d in domain_lock if d]
            if not domain_lock_clean:
                domain_lock_clean = None
        else:
            domain_lock_clean = None

        top_k = payload.get("top_k_override")
        top_k_override = int(top_k) if isinstance(top_k, int) and 5 <= top_k <= 20 else None

        return cls(
            sub_indexes=[str(s) for s in sub_indexes],
            criteria=criteria,
            domain_lock=domain_lock_clean,
            refusal_reason=payload.get("refusal_reason"),
            pre_written_response=payload.get("pre_written_response"),
            hardlock_region_strict=bool(payload.get("hardlock_region_strict", False)),
            hardlock_domain_strict=bool(payload.get("hardlock_domain_strict", False)),
            top_k_override=top_k_override,
            confidence=float(payload.get("confidence", 0.0)),
            is_fallback=bool(payload.get("is_fallback", False)),
        )

    def hardlock_block_for_prompt(self) -> str:
        """Formate les contraintes hardlock en bloc texte pour injection R7.

        Vide si aucune contrainte hardlock. Sinon retourne un bloc Markdown
        à insérer en début de system prompt v4.1 strict (slot
        {HARDLOCK_BLOCK} en étape 7).
        """
        if not (
            self.hardlock_region_strict
            or self.hardlock_domain_strict
            or (self.criteria and self.criteria.region)
            or self.domain_lock
        ):
            return ""

        lines = ["## CONTRAINTES HARDLOCK (R7)"]
        if self.hardlock_region_strict and self.criteria and self.criteria.region:
            lines.append(
                f"- Région imposée : **{self.criteria.region}**. "
                "Tu ne PROPOSES PAS d'alternative hors-région sans dire "
                "EXPLICITEMENT que la région est vide dans nos sources."
            )
        if self.hardlock_domain_strict and self.domain_lock:
            lines.append(
                f"- Domaine(s) imposé(s) : **{', '.join(self.domain_lock)}**. "
                "Tu ne mélanges PAS avec d'autres types de fiches."
            )
        # Garde edge case (audit Matteo step 7 → 8) : si l'outer-check passe
        # (un flag hardlock=True) mais qu'aucun bullet inner ne matche
        # (criteria.region absent malgré hardlock_region_strict, ou domain_lock
        # vide malgré hardlock_domain_strict), on retournerait juste le header
        # sans bullets — le LLM verrait un anchor vide. Mieux vaut "" que
        # signaler une contrainte sans la décrire.
        if len(lines) == 1:
            return ""
        return "\n".join(lines) + "\n"


# ────────────────────────── Tool params (JSON Schema Mistral) ──────────────────────────


ROUTE_DECISION_TOOL_PARAMS: dict[str, Any] = {
    "type": "object",
    "properties": {
        "sub_indexes": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": list(SUB_INDEX_NAMES),
            },
            "minItems": 1,
            "description": (
                "Sous-index FAISS à interroger. AU MOINS 1. "
                "'formations' (formations académiques, BUT, BTS, écoles, "
                "voies pré-bac, insertion post-formation), "
                "'metiers' (fiches métier ROME, projections d'emploi DARES), "
                "'statistiques' (INSEE salaires PCS, insertion bac+5, "
                "parcours bacheliers L1, marché cadres APEC), "
                "'aides_territoires' (CROUS logement, aides financières, "
                "DROM, blocs RNCP France Compétences, calendriers Parcoursup)."
            ),
        },
        "region": {
            "type": ["string", "null"],
            "description": "Région française canonique mentionnée (ex 'bretagne', 'occitanie', 'provence-alpes-côte d'azur', 'guadeloupe'). Null si non mentionnée.",
        },
        "niveau_min": {
            "type": ["integer", "null"],
            "description": "Niveau bac+N minimum si la question impose une contrainte (ex 'master' → 5). Null sinon.",
        },
        "niveau_max": {
            "type": ["integer", "null"],
            "description": "Niveau bac+N maximum si la question impose une contrainte. Null sinon.",
        },
        "secteur": {
            "type": ["array", "null"],
            "items": {"type": "string"},
            "description": "Secteurs candidats détectés (ex ['informatique', 'numerique'] pour cybersécurité). Null si pas de contrainte.",
        },
        "domain_lock": {
            "type": ["array", "null"],
            "items": {"type": "string"},
            "description": "Domaines `domain` à verrouiller exclusivement (ex ['crous'] pour question logement étudiant). Null si pas de verrouillage. À utiliser quand la question est explicitement sur un type d'objet précis (CROUS, RNCP code, salaire INSEE).",
        },
        "refusal_reason": {
            "type": ["string", "null"],
            "enum": ["superlative_no_data", "cross_domain", "out_of_scope_specific", None],
            "description": (
                "Si la question doit être REFUSÉE structurellement, indique la raison. "
                "'superlative_no_data' = superlatif type 'meilleure école de X' sans classement dans le corpus. "
                "'cross_domain' = sujet totalement hors-orientation (médecine, célébrité, cuisine, programmation détaillée). "
                "'out_of_scope_specific' = dans le scope orientation mais aucune donnée corpus pertinente. "
                "Null si la question peut être traitée normalement."
            ),
        },
        "hardlock_region_strict": {
            "type": "boolean",
            "description": "True si la question impose une contrainte régionale dure ET il est critique de NE PAS proposer hors-région. Force R7 dans le prompt.",
        },
        "hardlock_domain_strict": {
            "type": "boolean",
            "description": "True si la question impose un type d'objet précis ET il est critique de NE PAS mélanger d'autres types. Force R7 dans le prompt.",
        },
        "top_k_override": {
            "type": ["integer", "null"],
            "description": "5-20. Augmente top_k si la question est multi-critères (région+métier+niveau) où le rang 6+ peut être pertinent. Null sinon.",
        },
        "confidence": {
            "type": "number",
            "description": "0.0-1.0, ta confiance sur cette décision de routing. <0.6 si tu hésites entre plusieurs sub_indexes.",
        },
    },
    "required": ["sub_indexes", "confidence"],
}


def _route_decision_tool_func(**kwargs: Any) -> dict[str, Any]:
    """Validation passthrough du payload tool. Retourne le dict normalisé.

    Calqué sur `analyst_agent.py:_profile_update_tool_func`. La validation
    sémantique (enum sub_indexes, refusal_reason) est faite par
    `RouteDecision.from_tool_payload` via `__post_init__`.
    """
    return {
        "sub_indexes": kwargs.get("sub_indexes") or list(SUB_INDEX_NAMES),
        "region": kwargs.get("region"),
        "niveau_min": kwargs.get("niveau_min"),
        "niveau_max": kwargs.get("niveau_max"),
        "secteur": kwargs.get("secteur"),
        "domain_lock": kwargs.get("domain_lock"),
        "refusal_reason": kwargs.get("refusal_reason"),
        "hardlock_region_strict": bool(kwargs.get("hardlock_region_strict", False)),
        "hardlock_domain_strict": bool(kwargs.get("hardlock_domain_strict", False)),
        "top_k_override": kwargs.get("top_k_override"),
        "confidence": float(kwargs.get("confidence", 0.0)),
    }


ROUTE_DECISION_TOOL = Tool(
    name="decide_route",
    description=(
        "Décide comment router la question utilisateur dans le pipeline RAG : "
        "quel(s) sous-index FAISS interroger, quelles contraintes appliquer, "
        "et si la question doit être refusée structurellement. "
        "Tu DOIS toujours invoquer cet outil exactement une fois."
    ),
    parameters=ROUTE_DECISION_TOOL_PARAMS,
    func=_route_decision_tool_func,
)


# ────────────────────────── System prompt RouterLLM ──────────────────────────


ROUTER_SYSTEM_PROMPT = """Tu es RouterLLM d'OrientIA. Ta seule mission est d'analyser la question
utilisateur et de décider comment la router dans le pipeline RAG.

Tu invoques l'outil `decide_route` UNE SEULE FOIS avec ta décision. Tu n'écris
PAS de réponse narrative.

## Les 4 sous-index FAISS disponibles

(Comptes après filtrage `retrieval_eligible` — Vague 1.C exclut 18 012 fiches
RNCP/ONISEP/LBA/CFA non-adaptées au retrieve formation+ville. Total indexé
29 202 fiches sur 47 214 corpus.)

- **formations** (18 477 fiches, 63.3% des indexées) : formations
  académiques (licence, master, BUT, BTS, CPGE, écoles d'ingé/commerce),
  voies pré-bac (CAP, bac pro/techno/général), insertion post-formation.
  À utiliser pour toutes les questions qui cherchent UNE formation à suivre.

- **metiers** (4 894 fiches) : fiches métier ROME 4.0 (description, missions,
  compétences requises), métiers détaillés ONISEP, projections d'emploi DARES
  par région à 2030. À utiliser pour "que fait un X ?", "quels métiers
  recrutent ?", "métier de Y ?".

- **statistiques** (831 fiches) : INSEE salaires par PCS (37, 35, 31, 23...),
  insertion pro post-Bac+5 par discipline×région (InserSup), parcours
  bacheliers en L1 (taux réussite par bac), marché des cadres APEC par
  région. À utiliser pour "salaire de X ?", "taux d'insertion master Y ?",
  "réussite L1 avec bac Z ?", "marché cadres en région W ?".

- **aides_territoires** (5 000 fiches) : CROUS (logement résidences
  universitaires, restauration), aides financières (bourses, APL, dispositifs
  premiers pas), DROM-COM (Guadeloupe, Martinique, Guyane, Réunion, Mayotte),
  blocs de compétences RNCP (codes France Compétences), calendriers
  Parcoursup. À utiliser pour "logement étudiant ?", "aides financières ?",
  "RNCP <code> ?", "formations en Guadeloupe ?", "calendrier Parcoursup ?".

## Règles de décision

1. **Choisis 1-2 sub_indexes en priorité.** 3-4 uniquement si la question est
   vraiment multi-axes (ex: "métiers cyber Bretagne + insertion 6m" =
   formations + statistiques).

2. **Extrais la région si mentionnée**, en libellé canonique
   (bretagne, occitanie, provence-alpes-côte d'azur, île-de-france, etc.).
   Inclus DROM (guadeloupe, martinique, guyane, la réunion, mayotte).

3. **Niveau** : extrait niveau_min/max si imposé (ex "master" → 5/5,
   "BUT" → 2/3, "bac pro" → niveau pré-bac → 0/0). Null si non précisé.

4. **Secteur** : si la question évoque un domaine professionnel
   (informatique, sante, droit, commerce, art...), liste les secteurs
   candidats. Null sinon.

5. **domain_lock** : si la question est EXPLICITEMENT sur un type d'objet
   précis (CROUS pour logement, RNCP pour blocs de compétences, métier pour
   "que fait un X"), verrouille avec le `domain` exact. Liste des domaines
   reconnus : crous, financement_etudes, territoire_drom, competences_certif,
   calendrier, metier, metier_detail, metier_prospective, insee_salaire,
   insertion_pro, parcours_bacheliers, apec_region.

6. **refusal_reason** :
   - **superlative_no_data** : la question utilise un superlatif sur des
     objets sans classement dans le corpus. Patterns : "meilleur·e·s",
     "top", "classement", "best", "le meilleur", "le top", "palmarès",
     "n°1", "numéro un". Le corpus N'A PAS de classement officiel des
     écoles/formations/métiers/professionnels.
   - **cross_domain** : sujet totalement hors-orientation. Médecine clinique,
     célébrités, cuisine, programmation détaillée, météo, sport, politique
     non-orientation, etc. À distinguer de "métier de cuisinier" qui reste
     orientation.
   - **out_of_scope_specific** : dans le scope orientation mais aucune donnée
     corpus pertinente (ex: frais d'inscription école privée X non répertoriée,
     classement Shanghai, témoignages anciens élèves).
   - Null si la question peut être traitée normalement.

   **PRIORITÉ ABSOLUE — règle de tie-break** : si tu détectes un superlatif
   ("meilleur(s/e/es)", "top N", "classement", "palmarès", "best", "le top",
   "n°1", "numéro un") DANS LA QUESTION — peu importe le sujet —, tu DOIS
   set `refusal_reason="superlative_no_data"`. Le superlatif domine TOUJOURS
   le routing thématique. Exemples qui pourraient piéger :
   - "Combien gagnent les **meilleurs** avocats à Paris ?" → refusal=superlative_no_data
     (NE PAS router 'statistiques' juste parce que 'salaire' est mentionné)
   - "Quels sont les **top** chercheurs IA en France ?" → refusal=superlative_no_data
     (NE PAS router 'metiers' juste parce que 'chercheur' est un métier)
   - "**Palmarès** des écoles d'ingé cyber Bretagne ?" → refusal=superlative_no_data
     (NE PAS router 'formations' avec region=bretagne — le superlatif tue)
   Une question avec un superlatif ne doit JAMAIS recevoir une réponse routée
   thématiquement, même si tous les autres signaux pointent vers un sub-index
   précis.

7. **hardlock_region_strict** : True si la question IMPOSE une région ET il
   est critique que la réponse ne propose pas hors-région sans le signaler
   (ex: "ingé cyber en Bretagne" → True ; "formations cyber" → False).

8. **hardlock_domain_strict** : True si la question IMPOSE un type d'objet ET
   il est critique de ne pas mélanger (ex: "logement CROUS Lyon" → True
   avec domain_lock=['crous'] ; "formations à Lyon" → False).

9. **top_k_override** : 12-15 si la question est multi-critères (région+
   métier+niveau, ou domaine annexe peu fréquent). Évite que des fiches
   pertinentes au rang 6+ soient ignorées. Null si question simple.

10. **confidence** : 0.9+ si la décision est nette, 0.6-0.8 si ambigu,
    <0.6 si tu hésites vraiment (le pipeline élargira en filet de sécurité).

## Exemples

- "Logement CROUS à Lyon" → sub_indexes=["aides_territoires"], region="auvergne-rhône-alpes" si certain de la ville→région, domain_lock=["crous"], hardlock_domain_strict=true, confidence=0.9
- "Meilleure école de commerce" → refusal_reason="superlative_no_data", sub_indexes=["formations"] (ne sera pas utilisé), confidence=0.95
- "Combien gagnent les meilleurs avocats à Paris ?" → refusal_reason="superlative_no_data", sub_indexes=["statistiques"] (ne sera pas utilisé), confidence=0.95 (PRIORITÉ : le superlatif domine la sémantique 'salaire')
- "Top 3 prépas scientifiques" → refusal_reason="superlative_no_data", sub_indexes=["formations"] (ne sera pas utilisé), confidence=0.95
- "Salaire d'un actuaire" → sub_indexes=["metiers", "statistiques"], domain_lock=["metier", "metier_detail", "insee_salaire"], confidence=0.85
- "Quelles écoles d'ingé cyber en Bretagne" → sub_indexes=["formations"], region="bretagne", secteur=["informatique", "securite"], hardlock_region_strict=true, top_k_override=12, confidence=0.9
- "Comment soigner une angine" → refusal_reason="cross_domain", confidence=1.0
"""


# ────────────────────────── RouterLLM (appel Mistral Small) ──────────────────────────


@dataclass
class RouterLLM:
    """Routeur LLM léger — 1 appel Mistral Small + tool_choice="any".

    Usage :
        router = RouterLLM(client=mistral_client)
        decision = router.route(question, history=history)
        # decision est TOUJOURS un RouteDecision valide (jamais None,
        # jamais une exception non-rattrapée). Si LLM fail, fallback
        # déterministe gracieux via router_fallback.deterministic_route.

    Latence typique : 500-800 ms (Mistral Small + 1 tool call). Peut
    grimper à 1.5-2 s en cas de retry sur 429.

    Coût : ~$0.0001 par question (Mistral Small pricing 2026 + tool call).
    """

    client: Mistral
    model: str = MISTRAL_SMALL
    max_retries: int = 2
    initial_backoff: float = 1.5

    def route(
        self,
        question: str,
        history: list[dict[str, str]] | None = None,
    ) -> RouteDecision:
        """Décide le routing pour `question`. Toujours non-bloquant.

        Args:
            question: question utilisateur brute.
            history: tours précédents (Mistral format `[{"role", "content"}]`).
                Permet au LLM de contextualiser (ex: tour 2 réfère à
                "la 2e formation que tu as citée"). Cap à 12 messages
                (6 tours) pour limiter latence/contexte.

        Returns:
            RouteDecision validé. is_fallback=True si fallback déterministe
            a été utilisé (LLM down, JSON invalide, exception, etc.).
        """
        # Lazy import pour éviter cycle router_fallback ↔ router_llm
        from src.rag.router_fallback import deterministic_route

        if not question or not question.strip():
            return deterministic_route(question)

        messages: list[dict[str, str]] = [
            {"role": "system", "content": ROUTER_SYSTEM_PROMPT}
        ]
        if history:
            messages.extend(history[-12:])
        messages.append({"role": "user", "content": question})

        try:
            response = call_with_retry(
                lambda: self.client.chat.complete(
                    model=self.model,
                    messages=messages,
                    tools=[ROUTE_DECISION_TOOL.to_mistral_schema()],
                    tool_choice="any",
                    # Step 11 (2026-05-09) : temperature=0 pour déterminisme
                    # + stabiliser variance latence (cf audit step 10 outliers
                    # 1.83-2.37s post-prompt-hardening). Le routing doit être
                    # reproductible : même question → même décision.
                    temperature=0,
                ),
                max_retries=self.max_retries,
                initial_backoff=self.initial_backoff,
            )
        except Exception:
            # Pattern non-bloquant calqué sur analyst_agent.py:177-180.
            # 429/5xx/Cloudflare/timeout après retry → fallback déterministe.
            return deterministic_route(question)

        try:
            msg = response.choices[0].message
            if not msg.tool_calls:
                return deterministic_route(question)
            tc = msg.tool_calls[0]
            if tc.function.name != ROUTE_DECISION_TOOL.name:
                return deterministic_route(question)
            args = json.loads(tc.function.arguments)
            normalized = ROUTE_DECISION_TOOL.call(**args)
            if "error" in normalized:
                # Tool.call a retourné une erreur (missing required, etc.)
                return deterministic_route(question)
            decision = RouteDecision.from_tool_payload(normalized)
            # Step 11.7 chantier 4 : si refusal, sélectionner le variant
            # template basé sur hash(question) au lieu du variant[0]
            # auto-populé par __post_init__. Évite "même réponse mot-pour-mot"
            # sur 3 questions différentes.
            if decision.refusal_reason is not None:
                decision.pre_written_response = select_refusal_template(
                    decision.refusal_reason, question,
                )
            return decision
        except (json.JSONDecodeError, ValueError, AttributeError, KeyError, IndexError):
            # JSON cassé, schema invalide, LLM hallucine sub_index inconnu, etc.
            return deterministic_route(question)

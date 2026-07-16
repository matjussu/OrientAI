"""QueryReformuler — Sprint 2 axe B agentique.

Réécriture d'une query user + Profile (Sprint 1 ProfileClarifier output)
en N **sub-queries spécialisées** par corpus retrievable. Chaque
sub-query est calibrée pour activer un domain hint spécifique du
reranker (cf `src/rag/intent.py`), augmentant la cohabitation
multi-corpus dans le top-K final (cf bench persona complet PR #75 :
0/10 user-naturel cohabitation naturelle, motive ce pivot).

## Pattern Mistral function-calling

Force `tool_choice="any"` sur l'unique tool `reformulate_user_query`.
Le LLM reçoit query + Profile et émet :
- 1-N sub_queries, chacune avec un `target_corpus` explicit
- Une `strategy_note` libre expliquant le découpage choisi

## Sub-query design

Chaque sub_query contient :
- `text` : la requête réécrite (souvent en gardant le sens user mais
  reformulée pour activer un pattern regex domain hint)
- `target_corpus` : 'formation' / 'metier' / 'metier_prospective' /
  'competences_certif' / 'apec_region' / 'insee_salaire' /
  'insertion_pro' / 'parcours_bacheliers' / 'crous' / 'multi'
- `priority` : 1 (essentiel) / 2 (utile) / 3 (optionnel) — pour le
  fusion ranker downstream Sprint 3-4
- `rationale` : 1 ligne libre justifiant la sub-query

Cf ADR-051 pour le rationale architectural.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from typing import Optional

from mistralai.client import Mistral

from src.agent.retry import call_with_retry
from src.agent.tool import Tool
from src.agent.tools.profile_clarifier import Profile
from src.rag.models import MISTRAL_LARGE


# --- Sub-query structured output ---


VALID_TARGET_CORPORA = {
    "formation",
    "metier",
    "metier_prospective",
    "competences_certif",
    "apec_region",
    "insee_salaire",
    "insertion_pro",
    "parcours_bacheliers",
    "crous",
    "multi",  # quand la sub-query peut hit plusieurs corpora
}


VALID_PRIORITIES = {1, 2, 3}


@dataclass
class SubQuery:
    """Une sous-requête spécialisée pour un corpus cible."""

    text: str
    target_corpus: str
    priority: int = 2
    rationale: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)

    def is_valid(self) -> bool:
        return (
            isinstance(self.text, str)
            and len(self.text.strip()) >= 5
            and self.target_corpus in VALID_TARGET_CORPORA
            and self.priority in VALID_PRIORITIES
        )


@dataclass
class ReformulationPlan:
    """Plan de réécriture complet : la query originale + N sub-queries +
    une note stratégique libre du LLM."""

    original_query: str
    sub_queries: list[SubQuery]
    strategy_note: Optional[str] = None
    profile_used: Optional[dict] = None  # snapshot du Profile utilisé

    def to_dict(self) -> dict:
        return {
            "original_query": self.original_query,
            "sub_queries": [sq.to_dict() for sq in self.sub_queries],
            "strategy_note": self.strategy_note,
            "profile_used": self.profile_used,
        }

    def is_valid(self) -> bool:
        return (
            isinstance(self.original_query, str)
            and len(self.sub_queries) >= 1
            and all(sq.is_valid() for sq in self.sub_queries)
        )


# --- Tool definition Mistral ---


REFORMULER_TOOL_PARAMS_SCHEMA = {
    "type": "object",
    "properties": {
        "sub_queries": {
            "type": "array",
            "minItems": 1,
            "maxItems": 5,
            "items": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": (
                            "La sub-query réécrite. Garde le sens "
                            "user mais reformule pour activer le "
                            "domain hint correspondant (ex: 'postes "
                            "à pourvoir' pour metier_prospective)."
                        ),
                    },
                    "target_corpus": {
                        "type": "string",
                        "enum": sorted(VALID_TARGET_CORPORA),
                        "description": (
                            "Corpus retrievable cible. Choisis "
                            "'multi' si la sub-query couvre plusieurs."
                        ),
                    },
                    "priority": {
                        "type": "integer",
                        "enum": [1, 2, 3],
                        "description": (
                            "1=essentiel (tjrs runner), 2=utile, "
                            "3=optionnel."
                        ),
                    },
                    "rationale": {
                        "type": ["string", "null"],
                        "description": (
                            "1 ligne libre justifiant cette "
                            "sub-query (max 100 chars). Null OK."
                        ),
                    },
                },
                "required": ["text", "target_corpus", "priority"],
            },
        },
        "strategy_note": {
            "type": ["string", "null"],
            "description": (
                "Note stratégique libre (max 200 chars) sur le "
                "découpage choisi : pourquoi ces N sub-queries, "
                "trade-offs identifiés. Null si trivial."
            ),
        },
    },
    "required": ["sub_queries"],
}


def _query_reformuler_tool_func(**kwargs) -> dict:
    """Implémentation du Tool : valide les sub-queries + retourne plan."""
    raw_subs = kwargs.get("sub_queries", [])
    if not raw_subs:
        return {"error": "no_sub_queries"}
    sub_queries = []
    for raw in raw_subs:
        try:
            sq = SubQuery(
                text=raw.get("text", ""),
                target_corpus=raw.get("target_corpus", "formation"),
                priority=int(raw.get("priority", 2)),
                rationale=raw.get("rationale"),
            )
        except (TypeError, ValueError) as e:
            return {
                "error": "subquery_construction_failed",
                "raw": raw,
                "message": str(e),
            }
        if not sq.is_valid():
            return {
                "error": "subquery_validation_failed",
                "raw_input": raw,
            }
        sub_queries.append(sq)
    return {
        "sub_queries": [sq.to_dict() for sq in sub_queries],
        "strategy_note": kwargs.get("strategy_note"),
        "valid": True,
    }


QUERY_REFORMULER_TOOL = Tool(
    name="reformulate_user_query",
    description=(
        "Découpe la query utilisateur en 1-5 sub-queries spécialisées "
        "par corpus retrievable. Chaque sub-query est calibrée pour "
        "activer un domain hint reranker spécifique (formation, "
        "metier, metier_prospective, competences_certif, apec_region, "
        "insee_salaire, insertion_pro, parcours_bacheliers, crous, "
        "multi). Améliore la cohabitation multi-corpus du top-K aval. "
        "À appeler après ProfileClarifier pour piloter le retrieval."
    ),
    parameters=REFORMULER_TOOL_PARAMS_SCHEMA,
    func=_query_reformuler_tool_func,
)


# --- QueryReformuler (interface haut niveau) ---


REFORMULER_SYSTEM_PROMPT_TEMPLATE = """Tu es QueryReformuler d'OrientIA. Ta mission : réécrire la query utilisateur en 1-5 sub-queries spécialisées par corpus retrievable, en t'appuyant sur le Profile pré-extrait.

Profile détecté (utilise-le pour calibrer les sub-queries) :
- age_group : {age_group}
- education_level : {education_level}
- intent_type : {intent_type}
- sector_interest : {sector_interest}
- region : {region}
- urgent_concern : {urgent_concern}

Corpus disponibles :
- `formation` : catalogue Parcoursup + ONISEP (47 590 fiches)
- `metier` : fiches ONISEP éditorialisées (1 075)
- `metier_prospective` : DARES Métiers 2030 (FAP × région, 111 cells)
- `competences_certif` : France Comp blocs RNCP (4 891)
- `apec_region` : marché travail cadres (13 régions)
- `insee_salaire` : INSEE SALAAN PCS × région (59)
- `insertion_pro` : MESR insertion master/BUT (368)
- `parcours_bacheliers` : MESRI taux réussite licence (151)
- `crous` : vie étudiante logements + restos (39)
- `multi` : sub-query qui couvre plusieurs corpora simultanément

Règles de découpage :
1. **Une sub-query par INTENT distinct** dans la query. Ex : "Combien coûte une école et quel salaire après ?" → 2 sub-queries (financement + salaire post-diplôme).
2. **Calibre le texte pour ACTIVER le domain hint** du target_corpus :
   - metier_prospective : "postes à pourvoir 2030", "métiers 2030", "DARES"
   - competences_certif : "blocs de compétences", "que valider", "RNCP"
   - apec_region : "marché cadres en X", "perspectives recrutement cadres"
   - insee_salaire : "salaire médian PCS", "INSEE salaire"
   - insertion_pro : "taux insertion 6/12/18 mois post-master/BUT"
   - parcours_bacheliers : "taux réussite L1, BAC mention"
3. **Priorité** :
   - 1 = essentiel (couvre l'intent core)
   - 2 = utile (apporte contexte complémentaire)
   - 3 = optionnel (nice-to-have)
4. Si la query est conceptuelle / définitionnelle → 1 sub-query "formation" priorité 1 + (optionnel) 1 multi priorité 3.
5. Si urgent_concern=True → ajoute systématiquement 1 sub-query priorité 1 sur "formation" (ancrage rassurant).
6. **Maximum 5 sub-queries**. Mieux vaut 2-3 ciblées que 5 dispersées.

Tu N'écris PAS de réponse narrative — invoque l'outil `reformulate_user_query` avec les sub-queries extraites. C'est tout."""


@dataclass
class QueryReformuler:
    """Wrapper haut niveau QueryReformuler."""

    client: Mistral
    model: str = MISTRAL_LARGE
    timeout_ms: int = 60_000
    max_retries: int = 3
    initial_backoff: float = 2.0

    def reformulate(self, query: str, profile: Profile) -> ReformulationPlan:
        """Réécrit query en sub-queries selon le profile."""
        system_prompt = REFORMULER_SYSTEM_PROMPT_TEMPLATE.format(
            age_group=profile.age_group,
            education_level=profile.education_level,
            intent_type=profile.intent_type,
            sector_interest=", ".join(profile.sector_interest) if profile.sector_interest else "(aucun explicite)",
            region=profile.region or "(non spécifiée)",
            urgent_concern=profile.urgent_concern,
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query},
        ]
        response = call_with_retry(
            lambda: self.client.chat.complete(
                model=self.model,
                messages=messages,
                tools=[QUERY_REFORMULER_TOOL.to_mistral_schema()],
                tool_choice="any",
            ),
            max_retries=self.max_retries,
            initial_backoff=self.initial_backoff,
        )
        msg = response.choices[0].message
        if not msg.tool_calls:
            raise ValueError(
                f"QueryReformuler: Mistral n'a pas appelé le tool "
                f"(content='{(msg.content or '')[:200]}')"
            )
        tc = msg.tool_calls[0]
        if tc.function.name != QUERY_REFORMULER_TOOL.name:
            raise ValueError(
                f"QueryReformuler: tool inattendu '{tc.function.name}'"
            )
        try:
            args = json.loads(tc.function.arguments)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"QueryReformuler: JSON parse failed (err={e})"
            )
        result = QUERY_REFORMULER_TOOL.call(**args)
        if "error" in result:
            raise ValueError(
                f"QueryReformuler: tool returned error: {result}"
            )
        sub_queries = [SubQuery(**sq) for sq in result["sub_queries"]]
        return ReformulationPlan(
            original_query=query,
            sub_queries=sub_queries,
            strategy_note=result.get("strategy_note"),
            profile_used=profile.to_dict(),
        )

"""FetchStatFromSource — Sprint 3 axe B agentique (3ᵉ tool).

Vérifie si un `claim` (stat / fait / affirmation réglementaire) est
**supporté par les sources retrievées** ou s'il s'agit d'une
hallucination. Cible explicit : éviter les erreurs réglementaires
catchées par le bench persona complet (PR #75) — exemple type :
*"Titre RNCP Psychologue niveau 6"* alors que le titre est protégé
par master bac+5 niveau 7.

## Pattern Mistral function-calling (LLM-as-fact-checker souverain)

Le tool reçoit un claim + sources (cells corpus avec text excerpt) et
décide :
- `supported` : la source confirme explicit le claim
- `contradicted` : la source dit autre chose (ex: niveau 7 vs claim niveau 6)
- `unsupported` : ni explicit support ni contradiction (silence des sources)

Le LLM cite verbatim la phrase de la source qui justifie son verdict
(`source_excerpt`) — auditing épistémique INRIA.

## Intégration Sprint 4

Sprint 4 enchaîne le pipeline complet :
1. ProfileClarifier (Sprint 1) → Profile
2. QueryReformuler (Sprint 2) → sub-queries
3. Retrieval (existant) → sources
4. **FetchStatFromSource** sur chaque claim de la génération préliminaire
5. Génération finale avec claims vérifiés (suppression / correction
   / disclaimer si non-supported)

## Caveat épistémique

Le LLM-as-fact-checker n'est PAS un oracle. Il peut :
- Sur-flagger des claims valides si la source utilise des synonymes
- Sous-flagger des claims similaires lexicalement mais sémantiquement différents

Le `confidence` retourné permet au routing aval (Sprint 4) de pondérer
les décisions. Pattern compatible avec le StatFactChecker existant
(`src/rag/fact_checker.py`) — FetchStatFromSource ajoute la couche
agentique LLM-judge.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict, field
from typing import Optional

from mistralai.client import Mistral

from src.agent.cache import LRUCache
from src.agent.retry import call_with_retry
from src.agent.tool import Tool
from src.rag.models import MISTRAL_LARGE


# --- Verdict dataclass ---


VALID_VERDICTS = {
    "supported",       # source confirme explicit le claim
    "contradicted",    # source dit le contraire
    "unsupported",     # source ne dit ni l'un ni l'autre (silence)
    "ambiguous",       # source partiellement / floue
}


@dataclass
class StatVerification:
    """Résultat de vérification d'un claim contre des sources."""

    claim: str
    verdict: str  # enum VALID_VERDICTS
    source_excerpt: Optional[str]  # phrase verbatim de la source citée
    reason: str  # explication libre 1-2 phrases
    confidence: float = 0.5  # 0-1, confidence du fact-checker LLM
    source_id: Optional[str] = None  # id de la source utilisée si trouvée

    def to_dict(self) -> dict:
        return asdict(self)

    def is_valid(self) -> bool:
        return (
            isinstance(self.claim, str) and len(self.claim.strip()) > 0
            and self.verdict in VALID_VERDICTS
            and isinstance(self.reason, str)
            and 0.0 <= self.confidence <= 1.0
        )

    @property
    def is_supported(self) -> bool:
        return self.verdict == "supported"

    @property
    def is_problematic(self) -> bool:
        """True si le claim devrait être retiré ou disclaimé."""
        return self.verdict in {"contradicted", "unsupported"}


# --- Tool definition Mistral ---


FETCH_STAT_TOOL_PARAMS_SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {
            "type": "string",
            "enum": sorted(VALID_VERDICTS),
            "description": (
                "Verdict de vérification. 'supported' = la source "
                "confirme explicit. 'contradicted' = la source dit le "
                "contraire. 'unsupported' = la source ne dit rien sur "
                "ce point (claim non supporté mais non contredit). "
                "'ambiguous' = la source est partiellement ou floue."
            ),
        },
        "source_excerpt": {
            "type": ["string", "null"],
            "description": (
                "Citation verbatim de 1-2 phrases de la source qui "
                "justifie ton verdict. Null si verdict='unsupported' "
                "et aucune phrase pertinente."
            ),
        },
        "reason": {
            "type": "string",
            "description": (
                "Explication courte (1-2 phrases) du verdict. "
                "Indique POURQUOI tu conclus supported/contradicted/etc."
            ),
        },
        "confidence": {
            "type": "number",
            "description": (
                "Confiance auto-rapportée 0-1 sur ton verdict. "
                "0.9 = très sûr. 0.5 = doute raisonnable. 0.2 = très "
                "incertain."
            ),
        },
        "source_id": {
            "type": ["string", "null"],
            "description": (
                "ID de la source utilisée (ex: 'rncp_blocs:RNCP35185' "
                "ou 'dares_fap:T4Z'). Null si verdict='unsupported'."
            ),
        },
    },
    "required": ["verdict", "reason", "confidence"],
}


def _fetch_stat_tool_func(**kwargs) -> dict:
    """Tool func — valide les args et retourne dict avec verdict structuré."""
    verdict = kwargs.get("verdict", "unsupported")
    if verdict not in VALID_VERDICTS:
        return {
            "error": "verdict_out_of_enum",
            "spurious_value": verdict,
        }
    confidence = kwargs.get("confidence", 0.5)
    try:
        confidence_f = float(confidence)
    except (TypeError, ValueError):
        return {"error": "confidence_not_numeric", "raw": confidence}
    if not 0.0 <= confidence_f <= 1.0:
        return {"error": "confidence_out_of_bounds", "value": confidence_f}
    return {
        "verdict": verdict,
        "source_excerpt": kwargs.get("source_excerpt"),
        "reason": kwargs.get("reason", ""),
        "confidence": confidence_f,
        "source_id": kwargs.get("source_id"),
        "valid": True,
    }


FETCH_STAT_TOOL = Tool(
    name="verify_claim_against_sources",
    description=(
        "Vérifie si un claim (stat / fait / affirmation) est supporté "
        "par les sources fournies. Retourne un verdict structuré "
        "(supported / contradicted / unsupported / ambiguous) + "
        "citation verbatim de la phrase de source justifiant le "
        "verdict + raison + confidence. Indispensable pour anti-hallu "
        "agentique avant la génération finale."
    ),
    parameters=FETCH_STAT_TOOL_PARAMS_SCHEMA,
    func=_fetch_stat_tool_func,
)


# --- Source representation ---


@dataclass
class Source:
    """Source retrievée pour fact-check.

    Format minimal partagé avec la stack RAG existante (cf
    `src/rag/retriever.py`). Le `text` est l'excerpt embeddé dans
    l'index FAISS. Le `id` permet la traçabilité aval.
    """

    id: str
    text: str
    domain: str = "formation"
    score: float = 0.0
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    def to_prompt_format(self) -> str:
        """Format compact pour injection dans le prompt LLM."""
        return f"[{self.id}] (domain={self.domain}) {self.text[:500]}"


# --- FetchStatFromSource (interface haut niveau) ---


FACT_CHECK_SYSTEM_PROMPT = """Tu es FetchStatFromSource d'OrientIA, fact-checker agentique.

Ta mission : recevoir un CLAIM (stat / fait / affirmation réglementaire) extrait d'une réponse OrientIA, et le confronter à un ensemble de SOURCES citables (cells corpus retrievables). Tu décides via l'outil `verify_claim_against_sources` si le claim est :
- `supported` : une source confirme explicit (cite verbatim 1-2 phrases dans `source_excerpt`)
- `contradicted` : une source dit le contraire (ex: claim "niveau 6" vs source "niveau 7 protégé")
- `unsupported` : aucune source ne mentionne ce claim (ni support ni contradiction)
- `ambiguous` : la source en parle mais de façon partielle ou floue

Règles strictes :

1. **Tu cites VERBATIM** : `source_excerpt` doit être une copie exacte d'une phrase d'une source. PAS de paraphrase. Si pas de phrase pertinente → `source_excerpt=null` et verdict='unsupported'.

2. **Préfère 'unsupported' à 'supported'** si la source ne dit pas explicit le claim. Mieux vaut un faux unsupported (claim valide mais pas dans nos sources) qu'un faux supported (claim faux qu'on cautionne).

3. **'contradicted' demande conviction** : la source doit dire le contraire NON ambigu (ex: claim "Titre niveau 6" vs source "exige master niveau 7 obligatoire" = contradicted clair).

4. **Reglementaire / chiffré** : sois particulièrement strict sur les claims réglementaires (titres protégés, niveaux RNCP, durées légales, salaires) — ces erreurs sont les plus dommageables (cf erreur catchée bench persona psy_en_q1).

5. **Confidence calibration** :
   - 0.85-0.95 : verdict évident, citation directe possible
   - 0.6-0.85 : verdict défendable mais source un peu indirecte
   - 0.4-0.6 : doute sérieux, mention dans `reason`
   - <0.4 : préfère 'ambiguous' à un verdict net

Tu N'écris PAS de réponse narrative. Tu invoques l'outil `verify_claim_against_sources`. C'est tout."""


@dataclass
class FetchStatFromSource:
    """Wrapper haut niveau pour fact-check un claim contre des sources."""

    client: Mistral
    model: str = MISTRAL_LARGE
    timeout_ms: int = 60_000
    max_retries: int = 3
    initial_backoff: float = 2.0
    cache: LRUCache | None = None  # opt-in (key = (claim, source_ids_tuple))

    def verify(self, claim: str, sources: list[Source]) -> StatVerification:
        """Vérifie le claim contre les sources. Retourne StatVerification typé."""
        if not claim or not claim.strip():
            return StatVerification(
                claim=claim,
                verdict="unsupported",
                source_excerpt=None,
                reason="Empty claim",
                confidence=0.0,
            )

        # Cache lookup (key composite stable)
        cache_key = None
        if self.cache is not None:
            source_ids = tuple(sorted(s.id for s in sources))
            cache_key = (claim, source_ids)
            cached = self.cache.get(cache_key)
            if cached is not None:
                return cached

        if not sources:
            verification = StatVerification(
                claim=claim,
                verdict="unsupported",
                source_excerpt=None,
                reason="No sources provided",
                confidence=0.95,
            )
            if self.cache is not None:
                self.cache.set(cache_key, verification)
            return verification

        # Build prompt
        sources_text = "\n\n".join(
            f"SOURCE {i+1} :\n{s.to_prompt_format()}"
            for i, s in enumerate(sources[:8])  # max 8 sources pour limiter tokens
        )
        user_prompt = (
            f"CLAIM à vérifier :\n{claim}\n\n"
            f"SOURCES disponibles ({len(sources)} fournies, "
            f"{min(len(sources), 8)} affichées) :\n\n{sources_text}\n\n"
            f"Vérifie ce claim et invoque l'outil avec ton verdict."
        )

        messages = [
            {"role": "system", "content": FACT_CHECK_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
        response = call_with_retry(
            lambda: self.client.chat.complete(
                model=self.model,
                messages=messages,
                tools=[FETCH_STAT_TOOL.to_mistral_schema()],
                tool_choice="any",
            ),
            max_retries=self.max_retries,
            initial_backoff=self.initial_backoff,
        )
        msg = response.choices[0].message
        if not msg.tool_calls:
            raise ValueError(
                f"FetchStatFromSource: Mistral n'a pas appelé le tool "
                f"(content='{(msg.content or '')[:200]}')"
            )
        tc = msg.tool_calls[0]
        if tc.function.name != FETCH_STAT_TOOL.name:
            raise ValueError(
                f"FetchStatFromSource: tool inattendu '{tc.function.name}'"
            )
        try:
            args = json.loads(tc.function.arguments)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"FetchStatFromSource: JSON parse failed (err={e})"
            )
        result = FETCH_STAT_TOOL.call(**args)
        if "error" in result:
            raise ValueError(
                f"FetchStatFromSource: tool returned error: {result}"
            )
        verification = StatVerification(
            claim=claim,
            verdict=result["verdict"],
            source_excerpt=result.get("source_excerpt"),
            reason=result.get("reason", ""),
            confidence=result["confidence"],
            source_id=result.get("source_id"),
        )
        if self.cache is not None:
            self.cache.set(cache_key, verification)
        return verification

"""HTTP schemas for the OrientIA FastAPI wrapper.

Contract source of truth :
    OrientAI_Platform/docs/integration/02-http-contract.md

The wrapper is a pure passthrough — sources are returned as raw dicts coming
straight out of `pipeline.answer()`, without any mapping or transformation.
The Next.js platform side adapts via Zod `.passthrough()` on its own
`SourceSchema`.

Direction du contrat : le LLM décide du format, la plateforme s'adapte.
Toute modification ici se réplique dans
`OrientAI_Platform/src/lib/api/schemas.ts` — sinon contract drift au runtime.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


# Plafond de `HistoryMessage.content` : dimensionné sur le PLAFOND DE GÉNÉRATION
# récit (max_tokens=1500 × ~6 chars/token FR verbeux + liens Markdown ≈ 9000),
# pas sur un max observé. Cf docstring HistoryMessage.
NARRATIVE_HISTORY_CONTENT_MAX = 9000


class HistoryMessage(BaseModel):
    """Un tour de conversation (Mistral compliant).

    `content.max_length` est dimensionné sur le PLAFOND DE GÉNÉRATION, pas sur
    un max observé (sample != borne). Le mode récit génère jusqu'à
    `max_tokens=1500` (réponses sectionnées 4 sections) -> ~6000-7500 chars
    worst-case en français verbeux avec liens Markdown. On cape donc à **9000**
    (≈ 1500 tokens × 6 chars/token + marge) pour qu'une réponse récit max-longue,
    remise dans `history.content` au tour suivant, ne soit JAMAIS rejetée en 422 :
    la classe de bug ne doit pas se re-déclencher sur un récit futur plus long.

    Historique : cap initial 3000 (ère max_tokens=800, ~2200 chars). Bumpé à 9000
    quand le mode récit (max_tokens=1500) a fait passer 8/12 réponses du LOT
    au-dessus de 3000 -> 422 au tour 2 du multi-tour récit. Backward-compat
    STRICT : accepte plus, ne rejette rien qui passait. Côté plateforme, Zod ne
    contraint pas la length (HistoryMessageSchema.content sans .max) -> pas de
    drift. Cf. audit-pont-orientia-platform-2026-05-13 §H1.
    """

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=NARRATIVE_HISTORY_CONTENT_MAX)


class AnswerRequest(BaseModel):
    """Input envoyé par la plateforme.

    `extra="ignore"` : tolère les champs additionnels que la plateforme pourrait
    envoyer (ex : `audience` pas encore consommé par le pipeline en Phase 0).
    Si le pipeline les consomme un jour, on bascule vers une définition
    explicite ici sans rien casser.

    `history` est capé à 6 messages au lieu des 20 du contrat plateforme : on
    réduit la surface d'attaque prompt-injection (un attaquant pourrait sinon
    bourrer 20 messages assistant avec des "ignore previous").
    """

    model_config = ConfigDict(extra="ignore")

    question: str = Field(min_length=3, max_length=500)
    history: list[HistoryMessage] | None = Field(default=None, max_length=6)


class AnswerResponse(BaseModel):
    """Output passe-plat. `sources: list[dict[str, Any]]` est le format brut
    natif du pipeline OrientIA (~20 clés par fiche, variable selon corpus).

    `extra="allow"` : tolère l'ajout futur de clés sans casser ce schéma.
    """

    model_config = ConfigDict(extra="allow")

    answer: str
    sources: list[dict[str, Any]]
    faithfulness_score: float | None = Field(default=None, ge=0.0, le=1.0)
    faithfulness_verdict: Literal["FIDELE", "INFIDELE"] | None = None
    latency_ms: float = Field(ge=0)


class HealthResponse(BaseModel):
    ok: bool
    service: str = "orientia"
    version: str
    pipeline_loaded: bool
    index_size: int | None = None
    time: str  # ISO 8601
    # H1 lot 1.5 — fingerprint de provenance (hash prompt/corpus/index +
    # modeles pinnes), calcule au boot. None avant le lifespan (tests).
    provenance: dict | None = None


class ErrorResponse(BaseModel):
    error: str
    code: str
    request_id: str | None = None

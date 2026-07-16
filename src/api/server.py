"""OrientIA FastAPI HTTP wrapper — pure passthrough bridge.

Expose le pipeline RAG OrientIA via HTTP pour la plateforme Next.js
(`OrientAI_Platform`). Le wrapper est un **passe-plat** : il sérialise
`pipeline.answer()` tel quel, sans aucun mapping créatif. La plateforme
adapte via Zod `.passthrough()`.

Contract source of truth :
    OrientAI_Platform/docs/integration/02-http-contract.md

Boot local :
    ./scripts/run_api.sh
    curl -H "Authorization: Bearer $ORIENTIA_API_KEY" \
         -H "Content-Type: application/json" \
         -d '{"question": "..."}' http://localhost:8000/answer

Deploy Railway via Dockerfile + persistent volume `/app/data/embeddings/`.

Sécurité MVP propre :
- Bearer token via `ORIENTIA_API_KEY` (timing-safe `hmac.compare_digest`)
- CORS strict en prod (uniquement `PLATFORM_ORIGIN`, pas de wildcard)
- Rate limit inline 10 req/min par IP sur `/answer` (pas de dep externe)
- Sanitization input (refus prompt-injection grossier)
- Single worker uvicorn (`_pipeline` global non thread-safe entre workers)
- Logs JSON sans PII (jamais la `question`, juste les métriques)
"""
from __future__ import annotations

import asyncio
import hmac
import json
import logging
import os
import re
import time
import uuid
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncGenerator

import numpy as np
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from mistralai.client import Mistral

from src.api.schemas import (
    AnswerRequest,
    AnswerResponse,
    ErrorResponse,
    HealthResponse,
)
from src.rag.factory import make_production_pipeline

# ───────────────────────────── Logging ──────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("orientia.api")

# ───────────────────────────── Config / globals ─────────────────────────────

_VERSION = "v4.1"


def _resolve_artifact_paths() -> tuple[Path, str]:
    """Résout (fiches_path, index_path) des gros artefacts.

    Migration volume Approche A (ordre 1501) : l'INDEX FAISS vit sur le volume Railway
    monté à /app/data/embeddings ; le chemin relatif `data/embeddings/formations.index`
    (depuis cwd=/app) = /app/data/embeddings/... = le volume. Le CORPUS reste dans
    l'image (`data/processed/formations.json`). On NE dérive PAS de RAILWAY_VOLUME_MOUNT_PATH :
    le mount n'est PAS /app/data (c'est /app/data/embeddings), donc le dériver donnerait
    de mauvais chemins. Override ORIENTIA_* (prod les a, relatifs -> corrects) > défaut relatif.
    """
    fiches = os.environ.get("ORIENTIA_FICHES_PATH", "data/processed/formations.json")
    index = os.environ.get("ORIENTIA_INDEX_PATH", "data/embeddings/formations.index")
    return Path(fiches), index


def _require_artifacts(fiches_path: Path, index_path: str) -> None:
    """Fail-fast au boot : lève RuntimeError clair si un artefact volume est absent.

    Remplace l'ancien mode dégradé : avec la séquence volume-peuplé-AVANT-deploy
    (ordre 1501), un artefact manquant = erreur de bootstrap visible, pas un serveur
    qui répond 503 en silence.
    """
    missing = [str(p) for p in (fiches_path, Path(index_path)) if not Path(p).exists()]
    if missing:
        raise RuntimeError(
            f"Artefacts volume absents: {missing}. Le volume Railway (mount /app/data) "
            "doit contenir processed/formations.json + embeddings/{formations.index, "
            "4 quads, manifest} AVANT le deploy code-only. Peupler via "
            "`railway volume files upload` puis redeployer."
        )


_FICHES_PATH, _INDEX_PATH = _resolve_artifact_paths()

# Pipeline global, chargé une seule fois au lifespan startup.
# `_pipeline.last_validation` est un état mutable — on garde --workers 1 en prod
# pour éviter les races (cf docs/integration/03-orientia-fastapi-spec.md).
_pipeline: Any = None
_index_size: int | None = None
# Fingerprint de provenance (H1 lot 1.5) : hashes prompt/corpus/index + modeles
# pinnes, calcule UNE FOIS au lifespan, joint aux logs de chaque reponse.
_provenance: dict | None = None

# Timeouts H2 (audit-pont-orientia-platform-2026-05-13 §H2)
# - Mistral SDK : 25s — borne basse, le SDK lui-même fail proprement à 25s
#   plutôt que d'attendre le kill Railway 30-60s sans 504 propre.
# - Pipeline wrap (asyncio.wait_for) : 30s — borne haute côté FastAPI, laisse
#   5s de marge au-dessus de Mistral pour que le SDK ait le temps de remonter
#   son propre timeout. Au-delà, le wait_for court-circuite et retourne 504
#   `ORIENTIA_TIMEOUT` à la plateforme (cohérent avec son timeout client 30s).
# - Configurable via env var `ORIENTIA_PIPELINE_TIMEOUT_S` pour les tests
#   (le test E2E le monkeypatch à 0.5s pour éviter une suite qui prend 30s).
_MISTRAL_TIMEOUT_MS = 25_000
_PIPELINE_TIMEOUT_S = float(os.environ.get("ORIENTIA_PIPELINE_TIMEOUT_S", "30.0"))

# ───────────────────────────── Lifespan ─────────────────────────────────────


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Charge le pipeline + index une seule fois au démarrage."""
    global _pipeline, _index_size

    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        raise RuntimeError(
            "MISTRAL_API_KEY env var is required to load the OrientIA pipeline. "
            "Set it via Railway dashboard or .env locally."
        )

    logger.info(f"Loading OrientIA pipeline (v={_VERSION})...")
    # `timeout_ms=25_000` cap les appels Mistral à 25s, en dessous du
    # `_PIPELINE_TIMEOUT_S=30s` côté wrap FastAPI. Sans ce timeout, un hang
    # Mistral bloquerait jusqu'au kill Railway (30-60s) sans 504 propre.
    client = Mistral(api_key=api_key, timeout_ms=_MISTRAL_TIMEOUT_MS)

    # Migration volume (ordre 1501) : les gros artefacts viennent du volume Railway
    # (mount /app/data), plus de l'image. Fail-fast si absent (séquence : volume peuplé
    # AVANT le deploy code). Le port BIND après ce chargement (lifespan bloque le serve).
    fiches_path, index_path = _resolve_artifact_paths()
    logger.info(
        "Artefacts: RAILWAY_VOLUME_MOUNT_PATH=%s | fiches=%s | index=%s",
        os.environ.get("RAILWAY_VOLUME_MOUNT_PATH"), fiches_path, index_path,
    )
    _require_artifacts(fiches_path, index_path)  # log + exit propre si absent

    fiches = json.loads(fiches_path.read_text())
    _index_size = len(fiches)

    # Defaults are correct as of 2026-05-08 :
    # enable_strict_v4=True (v4.1 ≤250 mots), enable_validator=True,
    # enable_scope_classifier=True, enable_golden_qa=True, enable_post_process=True.
    pipeline = make_production_pipeline(client, fiches)
    pipeline.load_index_from(index_path)

    # Warmup retrieval indices : sans ça, le 1er /answer paie ~30s pour
    # builder les sub-indices double-corpus (Vague 1.C) + ~5-10s pour
    # builder le BM25 lexical (ADR-058). Critique pour démo INRIA p95.
    logger.info("Warming up retrieval indices (double-subindex + BM25)...")
    t_warmup = time.perf_counter()
    pipeline._build_double_subindices()
    pipeline._retrieve_with_bm25("orientation", k=1)
    logger.info(
        "Retrieval indices warm in %.1fs (double_index_built=%s, bm25_built=%s)",
        time.perf_counter() - t_warmup,
        pipeline._double_index_built,
        pipeline._bm25_built,
    )

    # Warmup génération (ordre 1926, fix C) : chauffe le pool Mistral + le
    # clarifier récit pour que la 1re vraie réponse au stand soit snappy.
    logger.info("Warming up generation (Mistral pool + narrative clarifier)...")
    t_gen = time.perf_counter()
    pipeline.warmup_generation()
    logger.info("Generation warm in %.1fs", time.perf_counter() - t_gen)

    global _provenance
    from src.api.provenance import build_fingerprint
    _provenance = build_fingerprint(fiches_path, index_path)
    logger.info("Provenance fingerprint: %s", json.dumps(_provenance))

    _pipeline = pipeline
    logger.info(f"Pipeline ready, {_index_size} fiches indexed")
    yield
    logger.info("Shutting down OrientIA pipeline")
    _pipeline = None


# ───────────────────────────── App + middleware ─────────────────────────────

app = FastAPI(
    title="OrientIA API",
    version=_VERSION,
    lifespan=lifespan,
)

# CORS — uniquement `PLATFORM_ORIGIN` en prod, ajout de localhost en dev.
_env = os.environ.get("ENV", "dev")
_platform_origin = os.environ.get("PLATFORM_ORIGIN")
_cors_origins: list[str]
if _env == "prod":
    if not _platform_origin:
        logger.warning(
            "ENV=prod but PLATFORM_ORIGIN not set — CORS will reject all browser calls. "
            "Set PLATFORM_ORIGIN to your Vercel domain."
        )
        _cors_origins = []
    else:
        _cors_origins = [_platform_origin]
else:
    _cors_origins = ["http://localhost:3000"]
    if _platform_origin:
        _cors_origins.append(_platform_origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Request-Id"],
)


# ───────────────────────────── Auth Bearer ──────────────────────────────────


async def verify_bearer(authorization: str | None = Header(default=None)):
    """Auth Bearer optionnelle (active uniquement si `ORIENTIA_API_KEY` set).

    Comparaison `hmac.compare_digest` pour éviter les timing attacks.
    """
    expected = os.environ.get("ORIENTIA_API_KEY")
    if not expected:
        return  # auth désactivée en dev local

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")

    provided = authorization.removeprefix("Bearer ")
    if not hmac.compare_digest(provided.encode("utf-8"), expected.encode("utf-8")):
        raise HTTPException(status_code=401, detail="Invalid Bearer token")


# ───────────────────────────── Rate limit inline ────────────────────────────

# 10 req / 60s par IP — protection minimale contre le scraping qui consommerait
# la clé Mistral (chère). In-memory only ; pour prod multi-instance, swap vers
# Redis (Upstash) post-INRIA.
_RATE_LIMIT_WINDOW_S = 60
_RATE_LIMIT_MAX = 10
_rate_buckets: dict[str, deque[float]] = defaultdict(deque)


def _client_ip(request: Request) -> str:
    # Railway met l'IP réelle dans `x-forwarded-for` (premier item).
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "anon"


def _check_rate_limit(request: Request) -> None:
    """Raise 429 si l'IP a dépassé son quota fenêtre glissante."""
    ip = _client_ip(request)
    now = time.monotonic()
    bucket = _rate_buckets[ip]
    # Drop les hits hors-fenêtre
    while bucket and bucket[0] < now - _RATE_LIMIT_WINDOW_S:
        bucket.popleft()
    if len(bucket) >= _RATE_LIMIT_MAX:
        raise HTTPException(
            status_code=429,
            detail=(
                f"Rate limit exceeded: max {_RATE_LIMIT_MAX} requests per "
                f"{_RATE_LIMIT_WINDOW_S}s. Retry shortly."
            ),
        )
    bucket.append(now)


# ───────────────────────────── Sanitization ─────────────────────────────────

# Regex de défense légère contre prompt-injection. Pas une garantie — c'est
# Mistral qui doit faire le gros du travail via son alignement, mais on filtre
# les tentatives les plus grossières pour réduire les démos qui plantent.
_INJECTION_PATTERNS = [
    re.compile(
        r"ignore\s+(previous|above|all|prior)\s+(instructions?|prompts?|rules?|directives?)",
        re.IGNORECASE,
    ),
    re.compile(r"disregard\s+(previous|above|all|prior)\s+(instructions?|prompts?)", re.IGNORECASE),
    re.compile(r"system\s*:\s*you\s+are\s+now", re.IGNORECASE),
]
# Strip des séquences de control-tokens Mistral pour ne pas que l'utilisateur
# puisse forger un faux delimiter.
_MISTRAL_CONTROL_TOKENS = re.compile(r"\[/?INST\]|<\/?s>|<<SYS>>|<</SYS>>", re.IGNORECASE)


def _to_jsonable(obj: Any) -> Any:
    """Recursively coerce numpy types to JSON-serializable Python natives.

    Le pipeline retourne parfois des fiches avec des `numpy.ndarray` (scores,
    agrégats stat) que Pydantic v2 ne sait pas sérialiser. Cette fonction
    marche sur les dict / list / scalars et convertit en place.
    """
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, dict):
        return {k: _to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_jsonable(v) for v in obj]
    return obj


# Champs internes du retriever à exposer comme métadonnées de score (préfixés
# `_` pour signaler à la plateforme que c'est du sidecar non-fonctionnel).
_RETRIEVER_SCORE_FIELDS = ("score", "score_rrf", "score_bm25", "base_score")
# Champs internes du retriever à toujours dropper (volumineux ou non utilisables UI).
_RETRIEVER_DROP_FIELDS = ("embedding", "_orig_index", "_quota_boosted", "rank_bm25")


def _extract_source_fiche(retrieved: dict[str, Any]) -> dict[str, Any]:
    """Déballe la fiche brute depuis la structure retriever-internal.

    Le pipeline retourne `pipeline.answer(...)[1]` sous forme de
    `[{fiche: {...}, score, score_rrf, embedding, ...}, ...]`. La plateforme
    attend la fiche brute directement (`{source, nom, etablissement, ville,
    ...}`). On déballe + on ajoute en sidecar les scores utiles préfixés `_`
    (que la plateforme peut afficher en debug ou trier dans le futur).

    Ce déballage n'est PAS un mapping créatif (on n'invente aucun champ) —
    c'est juste l'opération minimale pour passer du modèle retriever-interne
    au modèle "fiche brute" exposé dans le contrat HTTP.
    """
    if "fiche" not in retrieved or not isinstance(retrieved["fiche"], dict):
        # Fallback safe : si la structure n'est pas celle attendue, on filtre
        # juste les champs lourds et on retourne tel quel.
        return {k: v for k, v in retrieved.items() if k not in _RETRIEVER_DROP_FIELDS}

    fiche = dict(retrieved["fiche"])  # copy défensive

    # Alias minimal : certains corpora (rncp_blocs, certains référentiels
    # RNCP) utilisent `intitule` plutôt que `nom`. Le contrat plateforme
    # exige `nom`. On promote sans muter l'original (la clé `intitule`
    # reste disponible côté UI si besoin).
    if "nom" not in fiche and "intitule" in fiche:
        fiche["nom"] = fiche["intitule"]

    # Sidecar metadata : les scores du retriever, préfixés `_` pour signaler
    # que c'est de la métadonnée (pas du contenu de fiche)
    sidecar = {
        f"_{name}": retrieved[name]
        for name in _RETRIEVER_SCORE_FIELDS
        if name in retrieved
    }
    fiche.update(sidecar)
    return fiche


def _sanitize_question(question: str) -> str:
    """Refuse les tentatives évidentes de prompt-injection, strip control tokens."""
    if any(p.search(question) for p in _INJECTION_PATTERNS):
        raise HTTPException(
            status_code=400,
            detail=(
                "Question rejected by safety filter (potential prompt injection). "
                "Reformule simplement ta demande d'orientation."
            ),
        )
    cleaned = _MISTRAL_CONTROL_TOKENS.sub("", question)
    return cleaned.strip()


# ───────────────────────────── Error handler ────────────────────────────────


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Standardize error response shape pour matcher le contrat."""
    code_map = {
        400: "INVALID_QUESTION",
        401: "UNAUTHORIZED",
        422: "VALIDATION_ERROR",
        429: "RATE_LIMITED",
        500: "INTERNAL",
        503: "SERVICE_UNAVAILABLE",
        504: "ORIENTIA_TIMEOUT",
    }
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=str(exc.detail) if exc.detail else "Internal error",
            code=code_map.get(exc.status_code, "INTERNAL"),
            request_id=getattr(request.state, "request_id", None),
        ).model_dump(),
    )


# ───────────────────────────── Routes ───────────────────────────────────────


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(
        ok=_pipeline is not None,
        version=_VERSION,
        pipeline_loaded=_pipeline is not None,
        index_size=_index_size,
        time=datetime.now(timezone.utc).isoformat(),
        provenance=_provenance,
    )


@app.post(
    "/answer",
    response_model=AnswerResponse,
    dependencies=[Depends(verify_bearer)],
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
        504: {"model": ErrorResponse},
    },
)
async def answer(request: AnswerRequest, http_request: Request) -> AnswerResponse:
    """Synchronous Q→A endpoint. Pure passthrough wrapper around `pipeline.answer()`."""
    _check_rate_limit(http_request)

    if _pipeline is None:
        raise HTTPException(status_code=503, detail="Pipeline not loaded")

    request_id = http_request.headers.get("x-request-id") or str(uuid.uuid4())
    http_request.state.request_id = request_id

    sanitized = _sanitize_question(request.question)

    t0 = time.perf_counter_ns()
    try:
        history_dicts = (
            [m.model_dump() for m in request.history] if request.history else None
        )
        # `pipeline.answer()` est SYNC et bloquerait l'event loop FastAPI.
        # `asyncio.to_thread` le déporte dans un thread pool worker, ce qui
        # (a) libère l'event loop pour les autres requêtes pendant Mistral,
        # (b) permet à `asyncio.wait_for` d'effectivement appliquer le timeout
        #     30s côté FastAPI (sans to_thread, wait_for n'aurait rien à
        #     attendre car la sync bloque jusqu'à completion).
        # Note : si timeout fire, le thread continue en arrière-plan jusqu'à
        # ce que le Mistral SDK timeout 25s lui-même remonte. Le user récupère
        # un 504 propre en ~30s sans attendre le kill Railway 30-60s.
        answer_text, sources_raw = await asyncio.wait_for(
            asyncio.to_thread(_pipeline.answer, sanitized, history=history_dicts),
            timeout=_PIPELINE_TIMEOUT_S,
        )
    except asyncio.TimeoutError:
        logger.warning(
            json.dumps(
                {
                    "level": "warning",
                    "request_id": request_id,
                    "route": "/answer",
                    "error_type": "pipeline_timeout",
                    "timeout_s": _PIPELINE_TIMEOUT_S,
                }
            )
        )
        raise HTTPException(
            status_code=504,
            detail=(
                f"OrientIA pipeline exceeded {_PIPELINE_TIMEOUT_S}s budget. "
                "Upstream LLM probably slow — réessaie dans un instant."
            ),
        ) from None
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001 (top-level catch is intentional)
        logger.exception(f"Pipeline crash for request {request_id}")
        raise HTTPException(status_code=500, detail=f"Pipeline error: {exc}") from exc

    latency_ms = (time.perf_counter_ns() - t0) / 1_000_000.0

    # Faithfulness mapping : honesty_score continu + flagged.
    # `last_validation` est None quand ScopeClassifier short-circuite
    # (out_of_scope, urgent) — on retourne alors None/None proprement.
    score: float | None = None
    verdict: str | None = None
    last_validation = getattr(_pipeline, "last_validation", None)
    if last_validation is not None:
        score = float(last_validation.honesty_score)
        verdict = "INFIDELE" if last_validation.flagged else "FIDELE"

    # 1. Déballe la fiche brute depuis chaque structure retriever-internal
    # 2. Coerce les types numpy en Python natifs JSON-safe
    sources_clean = [_to_jsonable(_extract_source_fiche(s)) for s in sources_raw]

    response = AnswerResponse(
        answer=answer_text,
        sources=sources_clean,
        faithfulness_score=score,
        faithfulness_verdict=verdict,
        latency_ms=latency_ms,
    )

    logger.info(
        json.dumps(
            {
                "level": "info",
                "request_id": request_id,
                "route": "/answer",
                "latency_ms": round(latency_ms, 2),
                "sources_count": len(sources_raw),
                "honesty_score": score,
                "flagged": last_validation.flagged if last_validation else None,
                "question_len": len(sanitized),
                "history_len": len(request.history) if request.history else 0,
                "provenance": _provenance,
            }
        )
    )

    return response


# ───────────────────────────── /answer/stream (SSE Phase 1) ─────────────────

# Cf docs/integration/02-http-contract.md §5 Streaming SSE.
# Coté front : OrientAI_Platform/src/lib/orientia-stream-client.ts:171-228.
# Contrat events : StreamEventSchema discriminated union (token/sources/
# structured/faithfulness/done/error) — `src/lib/api/schemas.ts:96-119`.
# `structured` (ordre 1738) : NarrativeResponse typé émis en mode récit, juste
# après le dernier token, pour le rendu StructuredAnswer côté plateforme.

# Heartbeat SSE : envoyé toutes les 15s en commentaire (`: keepalive\n\n`,
# ignoré par le parser client cf `extractEventPayload` line 154). Évite que
# les proxies (Vercel, Cloudflare, Railway) ferment la connection inactive.
_SSE_HEARTBEAT_INTERVAL_S = 15.0

# Timeout total côté backend : 55s. Sous le 60s client (cf `DEFAULT_TIMEOUT_MS`
# orientia-stream-client.ts:40) pour qu'on remonte un event `error` propre
# avant que le client AbortController fire. Au-dessus du 25s Mistral SDK +
# overhead retrieve/MMR + heartbeat — laisse marge réaliste.
_STREAM_TOTAL_TIMEOUT_S = float(os.environ.get("ORIENTIA_STREAM_TIMEOUT_S", "55.0"))


def _format_sse_event(payload: dict) -> bytes:
    """Sérialise un dict en frame SSE `data: <JSON>\\n\\n`.

    Le client parse via `data:` line + double newline separator (cf
    `parseSSEChunks` côté frontend). Pas de champ `event:` — le `type`
    discriminator est dans le JSON payload (StreamEventSchema).
    """
    return f"data: {json.dumps(payload)}\n\n".encode("utf-8")


_SSE_HEARTBEAT_FRAME = b": keepalive\n\n"


async def _stream_events_with_heartbeat(
    event_gen,  # AsyncGenerator[dict, None]
    request_id: str,
    started_ns: int,
) -> "AsyncGenerator[bytes, None]":
    """Wraps the pipeline event generator with :
    - JSON SSE framing (data: <JSON>\\n\\n)
    - source extraction + numpy coercion sur les events `sources`
    - heartbeat keepalive `: keepalive\\n\\n` toutes 15s en parallèle
    - timeout total `_STREAM_TOTAL_TIMEOUT_S` (55s) émettant un event
      `error` final si dépassé
    - cancellation propagation propre (CancelledError remonte au caller
      qui ferme la connection httpx upstream Mistral)
    """
    import asyncio as _asyncio

    queue: _asyncio.Queue = _asyncio.Queue()
    SENTINEL_DONE = object()
    SENTINEL_ERROR = object()

    async def producer():
        """Consomme `event_gen` et push les frames SSE dans la queue."""
        try:
            async for ev in event_gen:
                # Sources : déballer la fiche brute + coerce numpy (mêmes
                # opérations que dans `/answer` non-streaming pour préserver
                # le contrat shape `Source` côté Zod).
                if ev.get("type") == "sources":
                    ev = {
                        "type": "sources",
                        "sources": [
                            _to_jsonable(_extract_source_fiche(s))
                            for s in ev.get("sources", [])
                        ],
                    }
                # Structured (ordre 1738) : NarrativeResponse typé -> coerce numpy->JSON
                # (même garde que `sources`, sinon json.dumps crashe le producer).
                elif ev.get("type") == "structured":
                    ev = {"type": "structured", "structured": _to_jsonable(ev.get("structured"))}
                await queue.put(_format_sse_event(ev))
                if ev.get("type") in ("done", "error"):
                    break
            await queue.put(SENTINEL_DONE)
        except _asyncio.CancelledError:
            # Cancellation depuis le caller — propager sans push d'event
            # `error` (client déjà déconnecté ne recevrait rien).
            await queue.put(SENTINEL_DONE)
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception(f"answer_stream producer crashed for {request_id}")
            await queue.put(_format_sse_event({
                "type": "error",
                "error": str(exc)[:200],
                "code": "INTERNAL",
            }))
            await queue.put(SENTINEL_ERROR)

    async def heartbeat():
        """Push un keepalive comment toutes les 15s."""
        try:
            while True:
                await _asyncio.sleep(_SSE_HEARTBEAT_INTERVAL_S)
                await queue.put(_SSE_HEARTBEAT_FRAME)
        except _asyncio.CancelledError:
            return

    producer_task = _asyncio.create_task(producer())
    heartbeat_task = _asyncio.create_task(heartbeat())

    try:
        # Timeout global via wait_for sur queue.get()
        deadline = _asyncio.get_event_loop().time() + _STREAM_TOTAL_TIMEOUT_S
        while True:
            remaining = deadline - _asyncio.get_event_loop().time()
            if remaining <= 0:
                # Timeout total dépassé — émettre event error final
                yield _format_sse_event({
                    "type": "error",
                    "error": f"Stream exceeded {_STREAM_TOTAL_TIMEOUT_S}s total budget.",
                    "code": "ORIENTIA_TIMEOUT",
                })
                return
            try:
                frame = await _asyncio.wait_for(queue.get(), timeout=remaining)
            except _asyncio.TimeoutError:
                yield _format_sse_event({
                    "type": "error",
                    "error": f"Stream exceeded {_STREAM_TOTAL_TIMEOUT_S}s total budget.",
                    "code": "ORIENTIA_TIMEOUT",
                })
                return

            if frame is SENTINEL_DONE or frame is SENTINEL_ERROR:
                return
            yield frame
    except _asyncio.CancelledError:
        elapsed_ms = (time.perf_counter_ns() - started_ns) / 1_000_000.0
        logger.info(
            json.dumps({
                "level": "info",
                "request_id": request_id,
                "route": "/answer/stream",
                "event": "client_disconnect",
                "elapsed_ms": round(elapsed_ms, 2),
            })
        )
        raise
    finally:
        # Cleanup : cancel les tasks background. Producer doit terminer pour
        # libérer la connection httpx upstream (Mistral SDK). Heartbeat est
        # un loop sans cleanup spécifique.
        if not producer_task.done():
            producer_task.cancel()
        if not heartbeat_task.done():
            heartbeat_task.cancel()
        # Wait briefly for graceful cancellation (don't block forever)
        try:
            await _asyncio.wait_for(
                _asyncio.gather(producer_task, heartbeat_task, return_exceptions=True),
                timeout=1.0,
            )
        except _asyncio.TimeoutError:
            pass


@app.post(
    "/answer/stream",
    dependencies=[Depends(verify_bearer)],
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
async def answer_stream(request: AnswerRequest, http_request: Request):
    """SSE Phase 1 endpoint — vrai streaming Mistral via `chat.stream_async()`.

    Erreurs **pre-streaming** (validation Pydantic 422, auth Bearer 401,
    rate limit 429, pipeline non-chargé 503, prompt-injection 400, scope LLM
    crash dans `_prepare_for_generation`) retournées en HTTP standard avec
    `ErrorResponse` JSON (cohérent `/answer`).

    Erreurs **in-stream** (Mistral crash, validator crash, timeout) émises
    en event SSE `{"type": "error", ...}` final + fin du stream.

    Cf contrat HTTP : OrientAI_Platform/docs/integration/02-http-contract.md §5.
    Cf client SSE : OrientAI_Platform/src/lib/orientia-stream-client.ts:171.
    """
    _check_rate_limit(http_request)

    if _pipeline is None:
        raise HTTPException(status_code=503, detail="Pipeline not loaded")

    request_id = http_request.headers.get("x-request-id") or str(uuid.uuid4())
    http_request.state.request_id = request_id

    sanitized = _sanitize_question(request.question)
    history_dicts = (
        [m.model_dump() for m in request.history] if request.history else None
    )

    started_ns = time.perf_counter_ns()
    logger.info(
        json.dumps({
            "level": "info",
            "request_id": request_id,
            "route": "/answer/stream",
            "event": "stream_start",
            "question_len": len(sanitized),
            "history_len": len(request.history) if request.history else 0,
            "provenance": _provenance,
        })
    )

    event_gen = _pipeline.answer_stream(
        sanitized,
        history=history_dicts,
    )
    framed = _stream_events_with_heartbeat(event_gen, request_id, started_ns)

    return StreamingResponse(
        framed,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            # X-Accel-Buffering: anti-buffering pour nginx/Vercel/Cloudflare —
            # garantit que les chunks SSE arrivent au client en temps réel.
            "X-Accel-Buffering": "no",
            # Connection keep-alive est implicite mais explicite pour clarté
            "Connection": "keep-alive",
        },
    )

import asyncio
import dataclasses
import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import AsyncGenerator

import numpy as np
import faiss
from mistralai.client import Mistral
from src.rag.embeddings import embed_texts, fiche_to_text, embed_texts_batched
from src.rag.index import build_index, save_index, load_index
from src.rag.retriever import retrieve_top_k
from src.rag.reranker import RerankConfig, rerank
from src.rag.mmr import mmr_select, DEFAULT_LAMBDA
from src.rag.bm25_index import reciprocal_rank_fusion
from src.rag.intent import (
    classify_intent,
    classify_domain_hint,
    intent_to_config,
    INTENT_FACTUAL_POINTED,
)
from src.rag.generator import generate, generate_stream, NARRATIVE_MAX_SOURCES, V4_MAX_SOURCES
from src.rag.fact_card import build_sources_index
from src.lookup.structured_select import try_select_or_none, SelectResult
from src.rag.metadata_filter import (
    FilterCriteria,
    apply_metadata_filter,
)
from src.rag.post_process import post_process_answer
from src.rag.geo_coherence import geo_coherence_check
from src.rag.router_llm import RouteDecision, RouterLLM, SUB_INDEX_NAMES
from src.rag.scope_classifier import ScopeClassifier, ScopeResult
from src.agent.tools.profile_clarifier import Profile, ProfileClarifier
from src.rag.narrative_detect import is_narrative, is_narrative_followup
from src.rag.narrative_route import route_from_profile
from src.rag.narrative_query import (
    build_narrative_retrieval_query, build_narrative_clarifier_input, extract_comparison_options,
)
from src.rag.narrative_format import route_narrative_format, FormatDecision, TRAJECTOIRE, COMPARAISON
from src.rag.narrative_structured import parse_narrative_response
from src.prompt.system_narrative import NARRATIVE_FEW_SHOT_PREFIX, narrative_few_shot
from src.validator import (
    Validator,
    ValidatorResult,
    PolicyResult,
    apply_policy,
    append_phase_projet,
    extract_failed_claims,
    format_hint_block,
)


_logger = logging.getLogger(__name__)


# Sprint 10 chantier C §8.4 — auto-expansion k stratégie
# Quand le filter métadonnées coupe trop, on retry retrieve avec k expanded.
INITIAL_K_MULTIPLIER = 3   # k_eff = k × 3 par défaut
MAX_K_MULTIPLIER = 10      # cap absolu (ratio max sur k passé en arg)

# Phase C corpus v5 — Option C v6 : retrieval indépendant du domain_hint.
#
# Problème (spot-check Phase C.5 2026-05-08) : les corpora annexes (DARES,
# CROUS, France Comp blocs, etc.) ne remontent jamais dans le top-K parce
# que (1) FAISS les classe bas (texte court vs formations longues),
# (2) le boost domain-aware (×1.4) ne s'applique que si classify_domain_hint
# retourne un hint correct (couverture mesurée à 46% sur 13 questions cibles).
#
# Solution Option C v6 : retrieve large + séparation pool main/annexe +
# quota adaptatif basé sur score brut. Indépendant du hint.
#
# Mécanique :
# 1. k_initial passe de 30 à 150 (élargit le pool brut)
# 2. Séparation pool main (formations sans `domain`) vs annex (avec `domain`)
# 3. Reranker boosts existants appliqués indépendamment sur chaque pool
# 4. Quota top-K final : si max_score(annex) ≥ seuil → garantir N annexes
#    dans le top-K, sinon top-K = full main (pas de pollution)
#
# Tradeoff : +70-80ms latency pour k=150 (négligeable vs 7-12s pipeline).
# Pollution top-K mitigée par seuil de score (0.6 = similarité raisonnable).
ANNEX_QUOTA_K_INITIAL = 150            # k retrieve sur l'index unifié (main + annex)
                                       # Conservé pour cas où sub-indices non-buildables
ANNEX_QUOTA_MIN_SCORE = 0.6            # seuil score pour éligibilité quota
ANNEX_QUOTA_MAX_PER_TOPK = 3           # max d'annexes boostées dans le top-K final
# Phase C++ — Double-index : retrieve séparé sur sous-corpus main + annex.
# Workaround pour pré-processing texte annexes mal aligné sémantique
# (cause racine — fix V2 = re-rédaction textes annexes via Mistral).
# ADR-058 acte la dette technique.
DOUBLE_INDEX_K_MAIN = 100              # top-100 sur sub-index main (33k formations)
DOUBLE_INDEX_K_ANNEX = 30              # top-30 sur sub-index annex (13k corpora)
# Étape 5 refonte (2026-05-09) — Quad sub-index par groupes de domaines.
# Partition fine de l'index unifié en 4 groupes (formations/metiers/
# statistiques/aides_territoires) pour routing piloté par RouterLLM.
# Cf scripts/build_quad_subindexes.py + ADR-065 (à créer).
# Utilisé UNIQUEMENT quand RouteDecision.sub_indexes est fourni à answer().
# Sinon, fallback complet vers _build_double_subindices (préservé).
QUAD_INDEX_K_PER_SUB = 50              # top-50 par sub-index, fusionné via RRF si multi
QUAD_MANIFEST_DEFAULT_PATH = "data/embeddings/formations_partition_manifest.json"
# Phase C ADR-058 — BM25 hybride lexical + RRF fusion.
# Complémente le retrieval dense (qui peine sur les fiches courtes/stat)
# par un score BM25 lexical exact. Match les entités nommées (CROUS Lyon,
# RNCP 38450, PCS 37) que dense rate. Standard RAG 2024+.
BM25_TOP_K = 50                        # top-50 BM25 fusionnés avec dense
RRF_K = 60                             # paramètre standard RRF (Cormack et al. 2009)
# Boost score appliqué aux top annexes éligibles au quota — forcer leur
# entrée dans le top-K final via tri par score (+ MMR aval). Le boost est
# additif sur le score reranked. Une annexe à 0.5 boostée à 1.5 dépasse
# n'importe quelle formation sans hint domain (max ~1.10).
ANNEX_QUOTA_SCORE_BOOST = 1.0


# Chantier 1.B (2026-05-03) — retry-with-hint loop anti-hallucination
# Cap dur à 1 retry au démarrage (cf plan voici-le-retour-de-lively-yao.md) :
# éviter régression sur les claims validés au tour 1 quand le hint pollue.
# Augmentation à 2 conditionnée à mesure de retry_stability sur 10+ questions.
MAX_RETRIES_WITH_HINT = 1

# Timeout wall-clock total .answer() (génération + validation + retry).
# Cible démo INRIA : <15s perçus. Cap à 30s pour tolérer 2 générations Mistral
# de ~10s chacune en heure de pointe + validation + dispatch retry hint.
RETRY_TIMEOUT_S = 30.0

# Marge de sécurité avant retry : on ne lance le tour 2 que s'il reste au moins
# RETRY_RESERVE_S secondes sur le budget timeout. Sinon on garde la réponse
# du tour 1 pour ne pas dépasser le wall-clock.
RETRY_RESERVE_S = 5.0

# Seuils d'alerte retry_stability (ratio des claims validés au tour 1
# encore présents/non-cassés au tour 2). Sans seuil on regarde la métrique
# une fois et on l'oublie — ces seuils déclenchent un signal automatique.
RETRY_STABILITY_WARN_THRESHOLD = 0.7    # >30% claims perdus → log warning
RETRY_STABILITY_AUDIT_THRESHOLD = 0.5   # >50% claims perdus → flag needs_audit


# ─────────────────────────── SSE Phase 1 (2026-05-13) ───────────────────────
# Résultats internes de `_prepare_for_generation()` extraits depuis `answer()`
# pour permettre `answer_stream()` de réutiliser la même séquence pré-LLM
# (scope/router/SELECT/intent/retrieve/MMR/golden_qa) sans duplication.


@dataclass
class _PreparedGenContext:
    """État pipeline post-pré-LLM, prêt pour génération (sync ou stream)."""
    top: list[dict]
    effective_top_k: int
    golden_qa_prefix: str | None
    intent_label: str | None
    hardlock_block: str
    criteria: FilterCriteria | None
    route_decision: RouteDecision | None
    # Mode récit (1d) — quand True, la génération bascule sur le prompt
    # sectionné (max_tokens relevé). Default False = chemin v4/v3.2
    # inchangé pour le banc 100q et le serving classique.
    narrative_mode: bool = False
    # Forme adaptative (ordre 1926) — décision de format + overlays, déterminée
    # par route_narrative_format. None hors mode récit.
    format_decision: FormatDecision | None = None


@dataclass
class _ShortCircuitResult:
    """Court-circuit pré-LLM : scope hors-scope/urgent, router refusal, SELECT bypass.

    `text` contient la réponse pré-écrite à retourner / streamer directement.
    `reason` sert pour le log structuré et le marker `last_retry_metadata`.
    """
    text: str
    reason: str


def _fiche_key(item: dict) -> tuple:
    """Clé d'identité d'une fiche pour dédup inter-retrievals (fix A COMPARAISON)."""
    f = item.get("fiche", item) if isinstance(item, dict) else {}
    if not isinstance(f, dict):
        return (str(item),)
    return (
        str(f.get("nom", "")).strip().lower(),
        str(f.get("etablissement", "")).strip().lower(),
        str(f.get("ville", "")).strip().lower(),
    )


def _round_robin_dedup(pools: list[list[dict]], target: int) -> list[dict]:
    """Fusionne plusieurs pools de retrieval en round-robin (1 par pool à tour de
    rôle), dédupliqué, jusqu'à `target`. Garantit que CHAQUE pool (= chaque option
    comparée) soit représenté dans les sources servies au LLM (fix A, ordre 1926)."""
    out: list[dict] = []
    seen: set = set()
    idx = [0] * len(pools)
    while len(out) < target and any(idx[i] < len(pools[i]) for i in range(len(pools))):
        for i in range(len(pools)):
            if idx[i] < len(pools[i]):
                it = pools[i][idx[i]]
                idx[i] += 1
                key = _fiche_key(it)
                if key not in seen:
                    seen.add(key)
                    out.append(it)
                    if len(out) >= target:
                        break
    return out


def _chunk_text_into_tokens(text: str) -> list[str]:
    """Split ``text`` en tokens "mots + ponctuation + whitespace" pour le
    fake streaming sur les courts-circuits (pas d'appel Mistral, on simule
    le pacing humain ~25 tokens/s).

    Cohérent avec ``chunkIntoTokens`` côté frontend
    (``OrientAI_Platform/src/lib/orientia-stream-client.ts:102-121``) : blocs
    de whitespace préservant les newlines, sinon mots/ponctuation contigus.
    """
    if not text:
        return []
    tokens: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch.isspace():
            j = i
            while j < n and text[j].isspace():
                j += 1
            tokens.append(text[i:j])
            i = j
        else:
            j = i
            while j < n and not text[j].isspace():
                j += 1
            tokens.append(text[i:j])
            i = j
    return tokens


class OrientIAPipeline:
    def __init__(
        self,
        client: Mistral,
        fiches: list[dict],
        rerank_config: RerankConfig | None = None,
        model: str = "mistral-medium-latest",
        use_mmr: bool = False,
        mmr_lambda: float = DEFAULT_LAMBDA,
        use_intent: bool = False,
        validator: Validator | None = None,
        use_metadata_filter: bool = True,
        use_golden_qa: bool = False,
        golden_qa_index_path: str | None = None,
        golden_qa_meta_path: str | None = None,
        enable_post_process: bool = False,
        scope_classifier: ScopeClassifier | None = None,
        use_strict_v4: bool = False,
        router_llm: RouterLLM | None = None,
        enable_geo_coherence: bool = True,
        enable_narrative_mode: bool = False,
        narrative_clarifier: "ProfileClarifier | None" = None,
    ):
        self.client = client
        self.fiches = fiches
        self.rerank_config = rerank_config or RerankConfig()
        self.model = model
        self.use_mmr = use_mmr
        self.mmr_lambda = mmr_lambda
        self.use_intent = use_intent
        self.index: faiss.IndexFlatL2 | None = None
        # Validator v1 — optionnel, opt-in. Si fourni, .answer() le lance après
        # generate() et stocke le résultat dans .last_validation (backward-compat
        # — la signature de .answer() n'est PAS modifiée).
        self.validator = validator
        self.last_validation: ValidatorResult | None = None
        # UX Policy (Gate J+6) — hybride α+β. Appliquée automatiquement quand
        # un validator est fourni. `last_policy_result` expose le verdict +
        # la réponse finale (peut avoir remplacé l'answer si Policy.BLOCK).
        self.last_policy_result: PolicyResult | None = None
        # Sprint 10 chantier C — RAG filtré métadonnées.
        #
        # Sprint 10 chantier C v1 (PR #102 mergée 10:12) : `False` par défaut.
        # Sprint 10 chantier C activation (cette PR) : **`True` par défaut**.
        #
        # Le default change parce que :
        # 1. Chantier B (PR #105) a normalisé les frontmatter cross-corpus :
        #    secteur 86.7%, budget 55.4%, alternance 36.5% du corpus 55k
        #    couverts. Le filter peut maintenant opérer significativement
        #    (vs quasi-inactif avant B).
        # 2. Backward compat préservée : `_retrieve_and_filter()` prend le
        #    path v1 strict quand `criteria=None` (cf ligne ~170), même avec
        #    `use_metadata_filter=True`. Les call-sites Run F+G qui font
        #    `pipeline.answer(question)` sans criteria continuent à opérer
        #    en comportement v1 strict — Run F+G reproductible sans
        #    configuration explicite.
        # 3. Pour les nouveaux usages avec criteria (chantier E CLI / serving
        #    prod), pas besoin de penser à set le flag — défaut "filter
        #    available, à activer via criteria explicit".
        #
        # Pour explicit opt-out (ex: A/B test sans filter), passer
        # `use_metadata_filter=False`.
        self.use_metadata_filter = use_metadata_filter
        # Stats du dernier `.answer(criteria=...)` — utiles pour audit
        # F+G (combien d'expansions ont été nécessaires, recall pré/post
        # filter, etc.). None tant qu'aucun call.
        self.last_filter_stats: dict | None = None
        # Sprint 10 chantier D — Q&A Golden Dynamic Few-Shot (opt-in).
        # False par défaut = backward compat strict. True = active le
        # triple-retrieve : top-1 Q&A Golden injecté en few-shot prefix
        # avec **séparation stricte Comment/Quoi** (la Q&A est référence
        # ton/structure ; les écoles/chiffres cités dans l'exemple sont
        # IGNORÉS, seules les fiches du context RAG factuel sont sources
        # autorisées pour citer). Lazy-load index/meta au 1er .answer().
        self.use_golden_qa = use_golden_qa
        self._golden_qa_index_path = golden_qa_index_path
        self._golden_qa_meta_path = golden_qa_meta_path
        self._golden_qa_index: faiss.IndexFlatL2 | None = None
        self._golden_qa_meta: list[dict] | None = None
        # Stats du dernier `.answer()` côté Q&A Golden (pour audit F+G).
        self.last_golden_qa: dict | None = None
        # Chantier 2 (2026-05-03) — résultat du dernier SELECT structuré tenté
        # (None si intent != FACTUAL_POINTED OU SELECT pas tenté). Argument
        # démo INRIA : marker visible `via_select=True` pour audit.
        self.last_select_result: SelectResult | None = None
        # Option B (J2 U1, 2026-06-11) — True si la réponse a été servie par le
        # RAG en FALL-THROUGH après un SELECT non-concluant (via_select=False),
        # au lieu d'un refus aveugle. Tag d'observabilité pour attribution mesure
        # et diag (le SELECT bypass servait 0/48 factuelles → on laisse le RAG
        # gardé essayer). Réinitialisé à chaque `.answer()`.
        self.last_select_fallthrough: bool = False
        # Garde-fou géo déterministe NARROW (J3, 2026-06-11, GO Matteo option B) —
        # remplace le prompt-only RÈGLE 9 reverté. Refus + relais si la question cible
        # une zone qu'AUCUNE source ne couvre (out-of-zone clair, ex Papeete-pour-Nantes).
        # Conservateur (abstention au moindre doute). Désactivable (revertable).
        self.enable_geo_coherence: bool = enable_geo_coherence
        self.last_geo_refusal: bool = False
        # Mode récit (R1 1c, ordre #137) — flag-gated, isolé. Quand
        # enable_narrative_mode ET narrative_clarifier sont fournis ET
        # is_narrative(question), `_prepare_narrative` remplace le RouterLLM
        # classique par un routing déterministe profil-driven. Default OFF =
        # banc 100q byte-identique (aucune des questions courtes ne déclenche).
        self.enable_narrative_mode = enable_narrative_mode
        self.narrative_clarifier = narrative_clarifier
        self.last_narrative_profile: Profile | None = None
        # Forme adaptative (ordre 1926) — derniers format/structure produits
        # (exposés au serving pour le payload `structured`). None hors récit.
        self.last_narrative_format_decision: FormatDecision | None = None
        self.last_narrative_structured: dict | None = None
        self.last_narrative_comparison_options: list[str] = []
        # Chantier 1.B (2026-05-03) — métadonnées du retry-with-hint loop pour
        # audit / observabilité. None tant qu'aucun call avec validator. Format :
        #   {
        #     "retries_attempted": 0|1,
        #     "tour1_failed_claims": [...],
        #     "tour2_failed_claims": [...] (présent uniquement si retry effectué),
        #     "retry_stability": float in [0,1] (1 = retry n'a cassé aucun bon claim),
        #     "needs_audit": bool (True si retry_stability < AUDIT_THRESHOLD),
        #     "wall_clock_s": float,
        #     "retry_skipped_reason": str|None ("timeout" | "no_validator" | None),
        #   }
        self.last_retry_metadata: dict | None = None
        # Phase 2 refonte (2026-05-06) — post-process déterministe (zéro LLM)
        # Sprint 8 Wave 1 : strip_invented_urls + fix_broken_markdown_tables +
        # validate_onisep_slugs. Appliqué post-validator/policy, pré-phase_projet.
        # Stats du dernier appel exposées via `last_post_process_stats`.
        self.enable_post_process = enable_post_process
        self.last_post_process_stats: dict | None = None
        # Étape 1 refonte (2026-05-06) — ScopeClassifier amont du pipeline.
        # Si fourni, classifie chaque question en {in_scope, out_of_scope, urgent}
        # AVANT tout retrieve/generate. Court-circuit avec réponse pré-écrite si
        # != in_scope. None par défaut = backward compat (toutes questions traitées).
        self.scope_classifier = scope_classifier
        self.last_scope_result: ScopeResult | None = None
        # Étape 2 refonte (2026-05-06) — contrat strict v4 WHAT/HOW.
        # Quand True, la génération utilise SYSTEM_PROMPT_V4_STRICT + JSON
        # tabulaire <sources> via FactCard au lieu de la prose libre v3.2.
        # False par défaut = backward compat (v3.2 + retry-with-hint préservés).
        self.use_strict_v4 = use_strict_v4
        # Phase C++ — Double-index lazy cache. Construits au 1er appel de
        # `_retrieve_with_annex_quota` via `index.reconstruct()`. Workaround
        # pour pré-processing texte annexes mal aligné sémantique
        # (cf ADR-058). Désactive si <2 fiches dans un pool (no-op fallback
        # vers le retrieve unifié).
        self._main_subindex: faiss.IndexFlatL2 | None = None
        self._annex_subindex: faiss.IndexFlatL2 | None = None
        self._main_subindex_orig_indices: list[int] | None = None
        self._annex_subindex_orig_indices: list[int] | None = None
        self._double_index_built: bool = False
        # Étape 5 refonte (2026-05-09) — Quad sub-index par groupes de domaines.
        # Lazy-build au 1er appel de `_build_quad_subindices`. Charge depuis
        # disque si manifest présent (build via scripts/build_quad_subindexes.py),
        # sinon rebuild en mémoire via `index.reconstruct()` (extension du pattern
        # `_build_double_subindices`). Utilisé uniquement quand le RouterLLM
        # produit une RouteDecision.sub_indexes — sinon fallback préservé.
        self._quad_indices: dict[str, faiss.IndexFlatL2] | None = None
        self._quad_indices_orig: dict[str, list[int]] | None = None
        self._quad_indices_built: bool = False
        # Étape 6 refonte (2026-05-09) — RouterLLM léger Mistral Small.
        # Si fourni, populate `route_decision` au début d'`answer()` avec :
        # - sub_indexes ciblés (pilote `_retrieve_from_sub_indexes`)
        # - criteria (region, secteur, niveau, domain_lock)
        # - refusal_reason (court-circuit pré-pipeline si superlatif/etc.)
        # - top_k_override (cas ingé cyber Bretagne avec rang 6 pertinent)
        # - hardlock_constraints (R7 du prompt v4.1 strict, étape 7)
        # None par défaut = backward compat strict.
        self.router_llm = router_llm
        self.last_router_result: RouteDecision | None = None
        # Phase C ADR-058 — BM25 hybride lexical + RRF fusion (cf src/rag/bm25_index.py)
        self._bm25_index = None  # Lazy build au 1er appel
        self._bm25_built: bool = False

    def build_index(self) -> None:
        texts = [fiche_to_text(f) for f in self.fiches]
        embeddings = embed_texts_batched(self.client, texts, batch_size=64)
        self.index = build_index(np.array(embeddings, dtype="float32"))

    def load_index_from(self, path: str) -> None:
        """Load a pre-built FAISS index from disk (avoids re-embedding)."""
        self.index = load_index(path)

    def save_index_to(self, path: str) -> None:
        if self.index is None:
            raise RuntimeError("No index to save — call build_index() first.")
        save_index(self.index, path)

    def answer(
        self,
        question: str,
        k: int = 30,
        top_k_sources: int = 10,
        criteria: FilterCriteria | None = None,
        history: list[dict] | None = None,
        temperature: float = 0.3,
    ) -> tuple[str, list[dict]]:
        """Génère une réponse depuis FAISS + rerank + MMR + generator.

        Sprint 10 chantier C §8.3 : argument `criteria` opt-in. Quand fourni
        ET `use_metadata_filter=True` à l'init, applique
        `apply_metadata_filter` post-rerank (avec auto-expansion k §8.4 si
        trop restrictif). Sinon comportement strictement identique à v1.

        Sprint 11 P0 Item 2 : argument `history` opt-in pour buffer mémoire
        short-term (suivi de tiroirs "Oui Plan A" → développe). Format
        Mistral compliant `[{"role": "user"|"assistant", "content": str}]`.
        Default `None`/empty = stateless v1 (pas de régression Run F+G).

        Args:
            question: requête utilisateur.
            k: nombre initial de candidats FAISS (défaut 30 — preserved
                pour backward compat).
            top_k_sources: nombre de sources passées au generator.
            criteria: FilterCriteria (Sprint 10 §8.3). None ou is_empty() →
                pas de filter (backward compat).
            history: list[{role, content}] de la conversation précédente
                (Sprint 11 P0 Item 2). None/[] = stateless.
        """
        if self.index is None:
            raise RuntimeError("Pipeline not built — call build_index() or load_index_from() first.")

        # Phase 1 SSE refacto 2026-05-13 — délégué à `_prepare_for_generation()`
        # pour permettre réutilisation côté `answer_stream()`. Extraction mécanique
        # sans changement de comportement (tests pipeline valident).
        prepared = self._prepare_for_generation(question, k, top_k_sources, criteria, history)
        if isinstance(prepared, _ShortCircuitResult):
            return prepared.text, []
        # Variables locales attendues par le reste de `answer()` (post-LLM)
        top = prepared.top
        effective_top_k = prepared.effective_top_k  # noqa: F841 (kept for retro-compat lecture)
        golden_qa_prefix = prepared.golden_qa_prefix
        intent_label = prepared.intent_label

        # Chantier 1.B (2026-05-03) — Retry-with-hint loop anti-hallucination.
        wall_t0 = time.time()
        answer_text, retry_meta = self._generate_with_retry(
            top=top,
            question=question,
            golden_qa_prefix=golden_qa_prefix,
            history=history,
            temperature=temperature,
            wall_t0=wall_t0,
            intent=intent_label,
            narrative_mode=prepared.narrative_mode,
            format_decision=prepared.format_decision,
        )

        # Validator v1 + UX Policy
        self.last_retry_metadata = retry_meta
        if self.validator is not None:
            self.last_policy_result = apply_policy(answer_text, self.last_validation)
            answer_text = self.last_policy_result.final_answer
            answer_text, _ = append_phase_projet(answer_text, question)
        if self.enable_post_process:
            answer_text, pp_stats = post_process_answer(answer_text, top)
            self.last_post_process_stats = pp_stats
        else:
            self.last_post_process_stats = None
        # Forme adaptative (ordre 1926) : sortie typée dérivée du markdown FINAL
        # (post-policy/post-process). Exposée au serving via le payload `structured`.
        # markdown_full reste canonique ; parser TOTAL (ne lève jamais).
        self.last_narrative_structured = (
            parse_narrative_response(
                answer_text, prepared.format_decision,
                sources=build_sources_index(top, max_sources=NARRATIVE_MAX_SOURCES),
            )
            if prepared.narrative_mode else None
        )
        return answer_text, top

    def warmup_generation(self) -> None:
        """Pré-chauffe le pool de connexions Mistral (génération) + le clarifier
        récit (ordre 1926, fix C — complément du warmup retrieval déjà fait au
        boot serveur). Sans ça, la 1re VRAIE réponse paie le cold-start réseau
        (handshake TLS + pool). Best-effort : jamais bloquant pour le démarrage.
        """
        try:
            self.answer("Quelles formations après un bac général ?")
        except Exception as e:  # noqa: BLE001 — warmup best-effort
            _logger.warning("warmup_generation skipped (non-bloquant): %s", e)
        if self.enable_narrative_mode and self.narrative_clarifier is not None:
            try:
                self.narrative_clarifier.clarify_narrative("warmup mode recit")
            except Exception as e:  # noqa: BLE001
                _logger.warning("warmup clarify_narrative skipped: %s", e)

    def _prepare_for_generation(
        self,
        question: str,
        k: int,
        top_k_sources: int,
        criteria: FilterCriteria | None,
        history: list[dict] | None,
    ) -> "_PreparedGenContext | _ShortCircuitResult":
        """Extrait depuis `answer()` (Phase 1 SSE refacto 2026-05-13).

        Exécute toute la séquence pré-LLM : scope check, router check,
        SELECT bypass, intent/domain hint, retrieve+filter+MMR,
        golden_qa_prefix. Comportement identique à pré-extraction —
        tests pipeline valident.

        Returns:
            - `_PreparedGenContext` si prêt pour la génération LLM normale
            - `_ShortCircuitResult` si une branche court-circuit a produit
              un texte pré-écrit (scope_out, scope_urgent, router_refusal,
              select_bypass). Le caller (sync ou stream) retourne / yield
              ce texte directement.

        Side-effects : set `self.last_scope_result`, `self.last_router_result`,
        `self.last_select_result`, et reset les autres `last_*` markers
        en cas de short-circuit (backward-compat consumers).
        """
        # Étape 1 refonte (2026-05-06) — Scope classification AMONT.
        if self.scope_classifier is not None:
            scope_res = self.scope_classifier.classify(question, history=history)
            self.last_scope_result = scope_res
            if scope_res.label != "in_scope":
                self.last_select_result = None
                self.last_validation = None
                self.last_policy_result = None
                self.last_retry_metadata = {
                    "retries_attempted": 0,
                    "tour1_failed_claims": [],
                    "tour2_failed_claims": None,
                    "retry_stability": 1.0,
                    "needs_audit": False,
                    "wall_clock_s": 0.0,
                    "retry_skipped_reason": f"scope_{scope_res.label}",
                }
                self.last_filter_stats = None
                self.last_golden_qa = None
                self.last_post_process_stats = None
                return _ShortCircuitResult(
                    text=scope_res.pre_written_response or "",
                    reason=f"scope_{scope_res.label}",
                )
        else:
            self.last_scope_result = None

        # MODE RÉCIT (R1 1c, ordre #137) — branche isolée, flag-gated, insérée
        # APRÈS le scope_classifier (R06/R07 détresse escaladent avant tout
        # traitement récit, non négociable) et AVANT le RouterLLM (qu'elle
        # remplace par un routing déterministe profil-driven). Inactive par
        # défaut -> chemin classique strictement inchangé.
        # R2 multi-tour : la branche récit se déclenche si le message courant EST
        # un récit (tour 1) OU si la conversation est DÉJÀ en mode récit (un tour
        # user antérieur était un récit) -> les follow-ups courts (« et à Lyon ? »)
        # restent en mode récit au tour 2+. Le scope_classifier détresse a déjà
        # tourné en amont (Étape 1) sur CE tour avec l'history -> garde-fou détresse
        # préservé. Banc 100q/497q = single-turn -> is_narrative_followup(None)=False
        # -> isolation baseline intacte.
        if (
            self.enable_narrative_mode
            and self.narrative_clarifier is not None
            and (is_narrative(question) or is_narrative_followup(history))
        ):
            return self._prepare_narrative(question, k, top_k_sources, history)

        # Étape 6 refonte (2026-05-09) — RouterLLM léger en amont du retrieve.
        # Décide (a) sub-indexes ciblés, (b) FilterCriteria, (c) refus structurés,
        # (d) hardlock R7, (e) top_k_override. Toujours non-bloquant : le
        # router fallback déterministe rattrape sur LLM fail / JSON invalide.
        # Sans router fourni à l'init, comportement v1 strict préservé.
        route_decision: RouteDecision | None = None
        if self.router_llm is not None:
            route_decision = self.router_llm.route(question, history=history)
            self.last_router_result = route_decision
            # Court-circuit pré-pipeline si refus structuré (analogue ScopeClassifier)
            if route_decision.refusal_reason is not None:
                self.last_select_result = None
                self.last_validation = None
                self.last_policy_result = None
                self.last_retry_metadata = {
                    "retries_attempted": 0,
                    "tour1_failed_claims": [],
                    "tour2_failed_claims": None,
                    "retry_stability": 1.0,
                    "needs_audit": False,
                    "wall_clock_s": 0.0,
                    "retry_skipped_reason": f"router_{route_decision.refusal_reason}",
                }
                self.last_filter_stats = None
                self.last_golden_qa = None
                self.last_post_process_stats = None
                return _ShortCircuitResult(
                    text=route_decision.pre_written_response or "",
                    reason=f"router_{route_decision.refusal_reason}",
                )
            # Override criteria si pas déjà fourni par l'appelant
            if criteria is None and route_decision.criteria is not None:
                criteria = route_decision.criteria
            # Domain lock : merge dans criteria (créer si nécessaire)
            if route_decision.domain_lock:
                if criteria is None:
                    criteria = FilterCriteria(domain=route_decision.domain_lock)
                elif criteria.domain is None:
                    criteria = dataclasses.replace(criteria, domain=route_decision.domain_lock)
                # Si criteria.domain déjà fourni par appelant, on ne l'écrase pas
            # Top_k override : élargit si la décision route le demande
            # (ne réduit jamais — utilise max pour préserver les overrides
            # de l'appelant qui peut vouloir plus).
            if route_decision.top_k_override:
                top_k_sources = max(top_k_sources, route_decision.top_k_override)
        else:
            self.last_router_result = None

        effective_top_k = top_k_sources
        effective_lambda = self.mmr_lambda
        intent_label = classify_intent(question) if self.use_intent else None
        if self.use_intent:
            cfg = intent_to_config(intent_label)
            effective_top_k = cfg.top_k_sources
            effective_lambda = cfg.mmr_lambda

        # Chantier 2 (2026-05-03) — SELECT structuré bypass pour les questions
        # factuelles pointues sur UNE formation nommée. Si le SELECT réussit
        # (entité reconnue ET fuzzy ≥ 85 ET field présent ET valeur valide),
        # on RETOURNE DIRECTEMENT la réponse déterministe sans appel LLM.
        # Argument démo INRIA : « zéro hallu chiffres par construction ».
        # Sinon (ambigu, no_match, invalid_value), le SelectResult retourné
        # contient déjà un fallback unifié — on le retourne aussi.
        # Si try_select_or_none retourne None (pas une question factual),
        # on continue le pipeline RAG normal.
        # ADR-049 : domain-aware reranker (no-op si hint=None, formation-centric par défaut)
        # Vague 0 — déplacé AVANT le SELECT bypass pour gating intelligent
        # (cf logique ci-dessous : si la question concerne un corpus annexe,
        # on ne bypass pas même si SELECT n'a pas de match formation).
        domain_hint = classify_domain_hint(question)

        if intent_label == INTENT_FACTUAL_POINTED:
            select_result = try_select_or_none(question, self.fiches)
            self.last_select_result = select_result
            # Option B (J2 U1, 2026-06-11) — on ne BYPASS que sur un VRAI succès
            # SELECT (via_select=True, zéro hallu garanti par le lookup). Tous les
            # autres cas (no_match, ambiguous, invalid_value, stale, no_entity,
            # domain annexe) tombent dans le RAG GARDÉ (fact_card + validator +
            # prompt strict) au lieu d'un refus aveugle -> réduit le sur-refus.
            # Historique : le bypass-vers-refus servait 0/48 questions factuelles
            # (égalités WRatio, aucun match dominant) ; le narratif démo repose
            # sur la groundedness mesurée du RAG, pas sur ce bypass. Réversible :
            # revert si le gate (hallu/substitution) casse sur le subset SELECT.
            should_bypass = select_result is not None and select_result.via_select
            # Trace observabilité (Jarvis cond. 2) : réponse servie par fall-through
            # RAG = le SELECT a tenté mais n'a pas servi (via_select=False).
            self.last_select_fallthrough = (
                select_result is not None and not select_result.via_select
            )
            if should_bypass:
                # SELECT a tenté quelque chose d'utile — on retourne sans appel LLM
                # (zero hallu garanti par construction). `top` est vide car bypass.
                self.last_retry_metadata = {
                    "retries_attempted": 0,
                    "tour1_failed_claims": [],
                    "tour2_failed_claims": None,
                    "retry_stability": 1.0,
                    "needs_audit": False,
                    "wall_clock_s": 0.0,
                    "retry_skipped_reason": "select_bypass",
                }
                return _ShortCircuitResult(text=select_result.text, reason="select_bypass")
            # Sinon : continuer le RAG normal (fall-through tracé). last_select_result
            # conservé pour traçabilité.
        else:
            self.last_select_result = None
            self.last_select_fallthrough = False

        # Sprint 10 §8.3-§8.4 : retrieve avec auto-expansion si filter activé.
        # Étape 6 (2026-05-09) : route_decision optionnel pilote le path
        # retrieve quad-subindex quand le router a fait un vrai routing
        # (sub-set strict des 4 sub-indexes).
        reranked = self._retrieve_and_filter(
            question=question,
            k=k,
            domain_hint=domain_hint,
            target=effective_top_k,
            criteria=criteria,
            route_decision=route_decision,
        )

        if self.use_mmr:
            top = mmr_select(reranked, k=effective_top_k, lambda_=effective_lambda)
        else:
            top = reranked[:effective_top_k]

        # Garde-fou géo déterministe NARROW (J3, 2026-06-11) — court-circuit AVANT
        # génération si la question cible une zone qu'aucune source (top) ne couvre.
        # Conservateur : ne tire que sur out-of-zone clair (cf geo_coherence_check).
        self.last_geo_refusal = False
        if self.enable_geo_coherence:
            geo_refusal = geo_coherence_check(question, top)
            if geo_refusal is not None:
                self.last_geo_refusal = True
                return _ShortCircuitResult(text=geo_refusal, reason="geo_out_of_zone")

        # Sprint 10 chantier D — Q&A Golden few-shot prefix (opt-in)
        golden_qa_prefix = self._maybe_build_golden_qa_prefix(question)

        # Étape 7 refonte (2026-05-09) — Hardlock block injecté en tête du
        # system prompt v4 strict si le RouterLLM a détecté une contrainte
        # forte. Vide sinon = comportement v4.1 historique préservé.
        hardlock_block = (
            route_decision.hardlock_block_for_prompt()
            if route_decision is not None
            else ""
        )

        return _PreparedGenContext(
            top=top,
            effective_top_k=effective_top_k,
            golden_qa_prefix=golden_qa_prefix,
            intent_label=intent_label,
            hardlock_block=hardlock_block,
            criteria=criteria,
            route_decision=route_decision,
        )

    def _prepare_narrative(
        self,
        question: str,
        k: int,
        top_k_sources: int,
        history: list[dict] | None,
    ) -> "_PreparedGenContext | _ShortCircuitResult":
        """Pré-LLM du MODE RÉCIT (R1 1c) — déterministe, profil-driven.

        Remplace le RouterLLM par : clarify_narrative (profil étendu 1b) ->
        route_from_profile (RouteDecision recall-first, géo=boost) ->
        build_narrative_retrieval_query (requête focalisée déterministe) ->
        _retrieve_and_filter -> MMR. Aucun filtre dur (criteria None). Pas de
        SELECT / golden_qa / geo-refusal (logique pensée pour questions courtes,
        inadaptée aux récits). La génération sectionnée dédiée arrive en 1d ;
        ici la requête forgée et le routing alimentent le retrieve.

        R2 multi-tour (FORK B) : le profil est extrait sur la CONCATÉNATION des
        tours USER de l'history (récit initial + follow-ups) via
        `build_narrative_clarifier_input` -> accumulation par ré-extraction,
        stateless, sans stockage profil serveur. Au tour 1 (history vide) =
        question seule, comportement 1c strictement inchangé.
        """
        # FORK B : entrée clarifier = concat des tours user (accumulation profil).
        clarifier_input = build_narrative_clarifier_input(question, history)
        profile = self.narrative_clarifier.clarify_narrative(clarifier_input)
        self.last_narrative_profile = profile

        # Forme adaptative (ordre 1926) : format + overlays routés de façon
        # déterministe depuis le profil + le texte courant. Le format gouverne
        # la STRUCTURE de la réponse (prompt) et le few-shot ; les overlays
        # (anchor_constraint / reassure) sont des registres orthogonaux.
        decision = route_narrative_format(profile, question, history)
        self.last_narrative_format_decision = decision

        route_decision = route_from_profile(profile)
        # Format TRAJECTOIRE : garantir le sous-index `metiers` (les passerelles
        # ROME vivent dans la fact_card métier) même si le profil ne l'aurait pas
        # déclenché. Ordre canonique préservé (déterminisme).
        if decision.format == TRAJECTOIRE and "metiers" not in route_decision.sub_indexes:
            want = set(route_decision.sub_indexes) | {"metiers"}
            route_decision.sub_indexes = [s for s in SUB_INDEX_NAMES if s in want]
        self.last_router_result = route_decision

        # Fallback retrieval = la conv complète (clarifier_input), pas le seul
        # follow-up courant : si le profil est un repli, on retombe sur tout le
        # contexte plutôt que sur « et à Lyon ? » seul.
        retrieval_query = build_narrative_retrieval_query(profile, clarifier_input)
        target = route_decision.top_k_override or top_k_sources

        reranked = self._retrieve_and_filter(
            question=retrieval_query,
            k=k,
            domain_hint=classify_domain_hint(retrieval_query),
            target=target,
            criteria=None,                 # géo = boost via requête, jamais filtre dur
            route_decision=route_decision,
        )

        # Fix A (ordre 1926) — COMPARAISON : retrieval PAR option nommée pour que
        # CHAQUE option du face-à-face soit représentée dans les sources. Sans ça,
        # quand la requête sector-driven ne surface pas les options (R05/R12), le
        # modèle refuse en bloc. Merge round-robin (options d'abord) -> table
        # partielle T6-style ; le contrat factuel garantit « hors sources » pour
        # une option absente du corpus (ex. prépa), pas un refus total.
        options = extract_comparison_options(clarifier_input) if decision.format == COMPARAISON else []
        self.last_narrative_comparison_options = options
        decision.comparison_options = options  # ancre le tableau sur les options DEMANDÉES (fix A)
        if options:
            per = max(4, target // (len(options) + 1))
            opt_pools = [
                self._retrieve_and_filter(
                    question=opt, k=k, domain_hint=classify_domain_hint(opt),
                    target=per, criteria=None, route_decision=route_decision,
                )
                for opt in options
            ]
            # BASE D'ABORD (augmente, ne DÉPLACE pas) : les cas qui marchaient via
            # la requête sector (T2 BUT GEA) gardent leurs fiches en tête ; les
            # options ne font qu'AJOUTER la couverture manquante (R05 école de
            # commerce). Mettre les options en tête déstabilisait les cas sains.
            top = _round_robin_dedup([reranked, *opt_pools], target)
        elif self.use_mmr:
            top = mmr_select(reranked, k=target, lambda_=self.mmr_lambda)
        else:
            top = reranked[:target]

        # Reset des markers court-circuit non pertinents en mode récit.
        self.last_select_result = None
        self.last_select_fallthrough = False
        self.last_geo_refusal = False

        return _PreparedGenContext(
            top=top,
            effective_top_k=target,
            # Forme adaptative (ordre 1926) : few-shot DÉDIÉ AU FORMAT (anti-
            # ancrage — l'exemple montre le squelette réel), injecté via le canal
            # golden_qa_prefix (côté user, attaché au contexte fact).
            golden_qa_prefix=narrative_few_shot(decision.format),
            intent_label=None,
            hardlock_block="",
            criteria=None,
            route_decision=route_decision,
            narrative_mode=True,
            format_decision=decision,
        )

    async def answer_stream(
        self,
        question: str,
        k: int = 30,
        top_k_sources: int = 10,
        criteria: FilterCriteria | None = None,
        history: list[dict] | None = None,
        temperature: float = 0.3,
        *,
        short_circuit_pace_s: float = 0.04,
    ) -> AsyncGenerator[dict, None]:
        """Async generator yieldant des StreamEvent typed (Phase 1 SSE, 2026-05-13).

        Ordre des events :
            ``sources`` → ``token`` (×N) → ``faithfulness`` → ``done``
        OU ``error`` à tout moment terminal.

        **Path streaming Mistral** (happy path, ~95% des questions in-scope) :
        Délègue la séquence pré-LLM à ``_prepare_for_generation()`` (via
        ``asyncio.to_thread`` pour libérer l'event loop), yield les sources
        bruts du retriever, puis stream tokens via ``generate_stream()``
        utilisant ``client.chat.stream_async()``. Validator + policy + post-process
        appliqués sur le texte accumulé pour produire le score/verdict
        faithfulness — note que les tokens originaux ont déjà été stream
        avant ces étapes (D2 ordre Jarvis 2026-05-13 : pas de retry-with-hint
        en streaming, dégradation ~3-5% cas flagged acceptée MVP).

        **Path court-circuit** (scope_out, router_refusal, SELECT bypass) :
        Pas de génération LLM — on yield ``sources: []``, fake-stream le
        texte pré-écrit avec un pacing ``short_circuit_pace_s`` (cohérent
        visuel avec le path Mistral stream), puis faithfulness 1.0/FIDELE.

        **Cancellation** : Si le client ferme la connection HTTP, FastAPI
        propage ``asyncio.CancelledError`` qui :
        - Court-circuite ``async for`` dans ``generate_stream()``
        - Ferme la connection httpx upstream → tokens Mistral non consommés
        - Loggé en JSON structuré ``{"event": "cancelled", ...}``
        - Re-raise (pas de yield d'event ``error`` — client déconnecté ne
          recevrait rien)

        Args:
            Identiques à ``answer()``.
            short_circuit_pace_s: pacing entre tokens sur les courts-circuits
                (40ms ≈ 25 tokens/s, lecture humaine rapide). Ignoré sur le
                path Mistral stream qui pace selon le débit upstream réel.

        Yields:
            Dicts conformes à ``StreamEventSchema`` côté plateforme
            (``OrientAI_Platform/src/lib/api/schemas.ts:96-119``).
        """
        if self.index is None:
            raise RuntimeError(
                "Pipeline not built — call build_index() or load_index_from() first."
            )

        started_ns = time.perf_counter_ns()
        try:
            # Pré-LLM via to_thread (libère l'event loop pendant retrieve/MMR ~150-300ms)
            prepared = await asyncio.to_thread(
                self._prepare_for_generation,
                question, k, top_k_sources, criteria, history,
            )

            if isinstance(prepared, _ShortCircuitResult):
                # Path court-circuit : pas de génération LLM, fake-stream le pré-écrit
                yield {"type": "sources", "sources": []}
                for token in _chunk_text_into_tokens(prepared.text):
                    yield {"type": "token", "content": token}
                    if short_circuit_pace_s > 0:
                        await asyncio.sleep(short_circuit_pace_s)
                yield {"type": "faithfulness", "score": 1.0, "verdict": "FIDELE"}
                latency_ms = (time.perf_counter_ns() - started_ns) / 1_000_000.0
                yield {"type": "done", "latency_ms": latency_ms}
                return

            # Path happy : vrai stream Mistral
            yield {"type": "sources", "sources": prepared.top}

            full_text_parts: list[str] = []
            async for chunk in generate_stream(
                self.client, prepared.top, question,
                model=self.model,
                temperature=temperature,
                golden_qa_prefix=prepared.golden_qa_prefix,
                history=history,
                hardlock_block=prepared.hardlock_block,
                use_strict_v4=self.use_strict_v4,
                narrative_mode=prepared.narrative_mode,
                narrative_decision=prepared.format_decision,
            ):
                full_text_parts.append(chunk)
                yield {"type": "token", "content": chunk}

            full_text = "".join(full_text_parts)
            # Forme adaptative (ordre 1926) : sortie typée dérivée du texte streamé.
            self.last_narrative_structured = (
                parse_narrative_response(
                    full_text, prepared.format_decision,
                    sources=build_sources_index(prepared.top, max_sources=NARRATIVE_MAX_SOURCES),
                )
                if prepared.narrative_mode else None
            )
            # Câblage live (ordre 2026-06-16-1738) : émet le NarrativeResponse typé
            # pour que le front rende StructuredAnswer (cartes/timeline) au lieu du
            # markdown plat. Seulement si récit + structure dérivée ; sinon le front
            # garde le fallback markdown (zéro régression). Coercion numpy->JSON faite
            # côté producer SSE (_stream_events_with_heartbeat).
            if self.last_narrative_structured is not None:
                yield {"type": "structured", "structured": self.last_narrative_structured}

            # Post-LLM (validator + policy + post-process) via to_thread —
            # ces étapes sont sync. Note : on n'a PAS le retry-with-hint
            # (D2 ordre Jarvis). Si validator flag → verdict INFIDELE émis,
            # mais pas de 2e génération (le streaming est uni-directionnel).
            score, verdict = await asyncio.to_thread(
                self._validate_for_stream, full_text, prepared.intent_label,
                prepared.top, prepared.narrative_mode,
            )
            if score is not None:
                event: dict = {"type": "faithfulness", "score": score}
                if verdict is not None:
                    event["verdict"] = verdict
                yield event

            latency_ms = (time.perf_counter_ns() - started_ns) / 1_000_000.0
            yield {"type": "done", "latency_ms": latency_ms}

        except asyncio.CancelledError:
            # Cancellation naturelle (client disconnect / unmount / nav / stop button).
            # Pas de yield d'event `error` : le client a déjà fermé la connection,
            # il ne recevrait rien. On log structuré pour observabilité, puis on
            # re-raise pour propager la cancellation au httpx upstream et libérer
            # les ressources Mistral SDK (tokens non consommés).
            elapsed_ms = (time.perf_counter_ns() - started_ns) / 1_000_000.0
            _logger.info(
                json.dumps({
                    "level": "info",
                    "route": "answer_stream",
                    "event": "stream_cancelled",
                    "elapsed_ms": round(elapsed_ms, 2),
                })
            )
            raise

        except Exception as exc:
            _logger.exception("answer_stream failed")
            yield {
                "type": "error",
                "error": str(exc)[:200],
                "code": "PIPELINE_ERROR",
            }

    def _validate_for_stream(
        self,
        full_text: str,
        intent_label: str | None,
        top: list[dict] | None = None,
        narrative_mode: bool = False,
    ) -> tuple[float | None, str | None]:
        """Run validator + score mapping pour le path streaming.

        Pas de retry-with-hint (D2 ordre Jarvis 2026-05-13), pas de policy
        replacement (les tokens originaux sont déjà streamés), pas de
        post_process (cosmétique cleanup non visible en streaming).

        Returns (score, verdict) cohérents avec ``AnswerResponse.faithfulness_*``
        côté ``/answer`` sync.
        """
        if self.validator is None:
            return None, None
        validation = self.validator.validate(
            full_text, intent=intent_label,
            fact_cards=self._fact_cards_for_validation(top, narrative_mode),
        )
        self.last_validation = validation
        score = float(validation.honesty_score)
        verdict = "INFIDELE" if validation.flagged else "FIDELE"
        return score, verdict

    @staticmethod
    def _fact_cards_for_validation(
        top: list[dict] | None,
        narrative_mode: bool,
    ) -> list:
        """FactCards S1..SN telles que le LLM les a vues, pour le check
        citation (H1 lot 1.2). max_sources DOIT suivre la branche génération
        (V4_MAX_SOURCES en strict, NARRATIVE_MAX_SOURCES en récit), sinon la
        numérotation S1..SN décale et le check compare aux mauvaises fiches."""
        if not top:
            return []
        from src.validator.citation_check import cards_from_top_sources
        max_sources = NARRATIVE_MAX_SOURCES if narrative_mode else V4_MAX_SOURCES
        return cards_from_top_sources(top, max_sources)

    def _generate_with_retry(
        self,
        *,
        top: list[dict],
        question: str,
        golden_qa_prefix: str | None,
        history: list[dict] | None,
        temperature: float,
        wall_t0: float,
        intent: str | None = None,
        narrative_mode: bool = False,
        format_decision: FormatDecision | None = None,
    ) -> tuple[str, dict]:
        """Boucle retry-with-hint anti-hallucination (chantier 1.B).

        ``narrative_mode`` (1d) propage la branche génération sectionnée jusqu'à
        ``generate()``. En mode récit, le pipeline tourne en strict_v4=True : le
        tour 2 retry-with-hint est de toute façon court-circuité (cf garde-fou
        strict_v4 ci-dessous), donc la génération récit est single-shot — cohérent
        avec la boucle de jugement humain.

        Sans validator : single-shot generate (pas de retry possible).
        Avec validator : tour 1 generate → validate → si claims problématiques
        ET temps restant suffisant (>= RETRY_RESERVE_S) → tour 2 avec hint
        réinjecté → validate → garde le meilleur (heuristique : moins de
        failed_claims = meilleur).

        Garde-fous expert :
          - MAX_RETRIES_WITH_HINT = 1 (pas 2 — éviter régression sur
            claims validés au tour 1)
          - Timeout wall-clock 30s — si dépassé, on garde le tour 1
          - Tracker retry_stability avec seuils 0.7 (warn) / 0.5 (audit)

        Returns:
            (answer_text, retry_metadata_dict)
            answer_text est le meilleur tour sélectionné.
        """
        meta: dict = {
            "retries_attempted": 0,
            "tour1_failed_claims": [],
            "tour2_failed_claims": None,
            "retry_stability": 1.0,
            "needs_audit": False,
            "wall_clock_s": 0.0,
            "retry_skipped_reason": None,
        }

        # Étape 7 refonte (2026-05-09) — Hardlock block injecté en tête du
        # system prompt v4 strict si le RouterLLM a détecté une contrainte
        # forte (région stricte, domaine verrouillé). Vide sinon = comportement
        # v4.1 historique préservé.
        hardlock_block = (
            self.last_router_result.hardlock_block_for_prompt()
            if self.last_router_result is not None
            else ""
        )

        # Tour 1 — génération initiale
        tour1_answer = generate(
            self.client, top, question,
            model=self.model,
            golden_qa_prefix=golden_qa_prefix,
            history=history,
            temperature=temperature,
            use_strict_v4=self.use_strict_v4,
            hardlock_block=hardlock_block,
            narrative_mode=narrative_mode,
            narrative_decision=format_decision,
        )

        # Sans validator : pas de retry (no-op transparent)
        if self.validator is None:
            meta["retry_skipped_reason"] = "no_validator"
            meta["wall_clock_s"] = round(time.time() - wall_t0, 2)
            return tour1_answer, meta

        # Validation tour 1 — passe intent pour gating layer3 LLM + les
        # FactCards vues par le LLM pour le check citation (H1 lot 1.2)
        fact_cards = self._fact_cards_for_validation(top, narrative_mode)
        tour1_validation = self.validator.validate(
            tour1_answer, intent=intent, fact_cards=fact_cards,
        )
        self.last_validation = tour1_validation
        tour1_failed = extract_failed_claims(tour1_validation)
        meta["tour1_failed_claims"] = list(tour1_failed)

        # Décision retry : besoin de claims à corriger ET budget timeout OK
        if not tour1_failed:
            # Tour 1 propre, pas de retry nécessaire
            meta["wall_clock_s"] = round(time.time() - wall_t0, 2)
            return tour1_answer, meta

        elapsed = time.time() - wall_t0
        remaining = RETRY_TIMEOUT_S - elapsed
        if remaining < RETRY_RESERVE_S:
            # Pas assez de budget pour un retry — on garde le tour 1
            _logger.warning(
                "Retry skipped (timeout reserve insufficient: %.1fs remaining, "
                "%.1fs needed). Keeping tour 1 with %d failed_claims.",
                remaining, RETRY_RESERVE_S, len(tour1_failed),
            )
            meta["retry_skipped_reason"] = "timeout"
            meta["wall_clock_s"] = round(time.time() - wall_t0, 2)
            return tour1_answer, meta

        # Vague 0 fix — skip retry tour 2 en mode strict_v4. Le `hint_block`
        # est ignoré par generate() en v4 (cf SYSTEM_PROMPT_V4_STRICT R1-R5
        # qui n'utilise pas le hint), donc le tour 2 ne fait que regénérer
        # avec un prompt quasi-identique (température 0.3, variance pure).
        # La policy aval (α/β/γ) gère déjà les claims problématiques.
        # Économie : ~7-10s par question flaggée, gain UX direct cible démo.
        if self.use_strict_v4:
            _logger.info(
                "Retry skipped (strict_v4 mode — hint_block ignored by generate). "
                "Tour 1 kept with %d failed_claims, policy will handle.",
                len(tour1_failed),
            )
            meta["retry_skipped_reason"] = "strict_v4_hint_ignored"
            meta["wall_clock_s"] = round(time.time() - wall_t0, 2)
            return tour1_answer, meta

        # Tour 2 avec hint réinjecté (mode legacy v3.2 uniquement)
        meta["retries_attempted"] = 1
        hint_block = format_hint_block(tour1_failed)
        tour2_answer = generate(
            self.client, top, question,
            model=self.model,
            golden_qa_prefix=golden_qa_prefix,
            history=history,
            temperature=temperature,
            hint_block=hint_block,
            use_strict_v4=self.use_strict_v4,
            hardlock_block=hardlock_block,
            narrative_mode=narrative_mode,
            narrative_decision=format_decision,
        )
        tour2_validation = self.validator.validate(
            tour2_answer, intent=intent, fact_cards=fact_cards,
        )
        tour2_failed = extract_failed_claims(tour2_validation)
        meta["tour2_failed_claims"] = list(tour2_failed)

        # retry_stability : ratio de claims du tour 1 NON-RÉINTRODUITS au tour 2.
        # Si tour 1 avait 5 failed_claims et que tour 2 en a 3 (les mêmes ou
        # subset), retry_stability = (5-3)/5 = 0.4. Si tour 2 a 3 nouveaux
        # claims (différents), c'est aussi 0.4 (les 5 originaux ont été corrigés
        # mais 3 nouveaux apparus = pollution du hint).
        # Formule simple : 1 - (failed_tour2 / max(failed_tour1, 1)).
        if tour1_failed:
            stability = max(0.0, min(1.0, 1.0 - (len(tour2_failed) / len(tour1_failed))))
        else:
            stability = 1.0
        meta["retry_stability"] = round(stability, 3)

        if stability < RETRY_STABILITY_AUDIT_THRESHOLD:
            meta["needs_audit"] = True
            _logger.warning(
                "Retry stability LOW (%.2f < %.2f) — flag needs_audit=True. "
                "Tour1 had %d claims, tour2 has %d. Hint may be polluting context.",
                stability, RETRY_STABILITY_AUDIT_THRESHOLD,
                len(tour1_failed), len(tour2_failed),
            )
        elif stability < RETRY_STABILITY_WARN_THRESHOLD:
            _logger.warning(
                "Retry stability degraded (%.2f < %.2f). Tour1=%d claims, tour2=%d.",
                stability, RETRY_STABILITY_WARN_THRESHOLD,
                len(tour1_failed), len(tour2_failed),
            )

        # Sélection : on garde le tour avec le moins de failed_claims.
        # Si égal → tour 2 (la dernière instruction a été suivie au moins partiellement).
        if len(tour2_failed) <= len(tour1_failed):
            self.last_validation = tour2_validation
            best_answer = tour2_answer
        else:
            # Tour 2 a régressé → on garde le tour 1
            _logger.warning(
                "Tour 2 regressed (%d claims vs %d at tour 1). Keeping tour 1 answer.",
                len(tour2_failed), len(tour1_failed),
            )
            self.last_validation = tour1_validation
            best_answer = tour1_answer

        meta["wall_clock_s"] = round(time.time() - wall_t0, 2)
        return best_answer, meta

    def _retrieve_and_filter(
        self,
        *,
        question: str,
        k: int,
        domain_hint: str | None,
        target: int,
        criteria: FilterCriteria | None,
        route_decision: RouteDecision | None = None,
    ) -> list[dict]:
        """Retrieve + rerank, avec auto-expansion §8.4 si filter actif.

        Étape 6 (2026-05-09) : si route_decision pointe sur un sous-ensemble
        strict des 4 sub-indexes (= router a fait un vrai routing), utilise
        `_retrieve_from_sub_indexes` (quad-subindex) au lieu du retrieve
        unifié. Avec apply_metadata_filter aval pour respecter criteria.

        Sans router_decision (ou sub_indexes = tous les 4) : comportement v1
        préservé strict (Option C v6 ou auto-expand selon criteria).

        Sans filter actif (ou criteria empty) : Option C v6 (quota adaptatif).
        Avec filter : retrieve k×INITIAL_K_MULTIPLIER, filter, expand si <target.
        Toujours retourne reranked candidates (même format que v1).
        Stats stockées dans self.last_filter_stats pour audit F+G.
        """
        # Étape 6 path quad-subindex : actif uniquement si router_llm a routé
        # vers un sous-ensemble strict (sub_indexes ≠ tous les 4).
        # Si router a renvoyé tous les sub_indexes (filet de sécurité confidence
        # basse ou fallback ultime), on retombe sur le path v1 (full corpus).
        router_active = (
            route_decision is not None
            and route_decision.sub_indexes
            and len(route_decision.sub_indexes) < len(SUB_INDEX_NAMES)
        )
        if router_active:
            assert route_decision is not None  # type narrowing pour mypy
            raw = self._retrieve_from_sub_indexes(
                question=question,
                sub_index_names=route_decision.sub_indexes,
                k_per_sub=QUAD_INDEX_K_PER_SUB,
            )
            if not raw:
                # Sub-index ciblé vide ou indisponible → fallback path v1
                # (préserve le contrat "answer ne plante jamais").
                _logger.info(
                    "[router-quad] sub_indexes %s vides — fallback path v1",
                    route_decision.sub_indexes,
                )
            else:
                reranked = rerank(raw, self.rerank_config, domain_hint=domain_hint)
                if (
                    self.use_metadata_filter
                    and criteria is not None
                    and not criteria.is_empty()
                ):
                    reranked = apply_metadata_filter(reranked, criteria)
                # 2026-05-12 fix : si le quad retrieve+filter retourne 0,
                # fallback au path v1 (full corpus + auto-expansion).
                # Bug live : "quelles sont les crous à Paris ?" — le sub-index
                # aides_territoires (4979 fiches dont 4891 competences_certif)
                # noie les 18 fiches CROUS dans le bruit, top-50 FAISS retourne
                # 0 CROUS → filter avec domain_lock=['crous'] → n_after_filter=0
                # → pipeline retourne "pas d'info" alors que la fiche CROUS
                # Paris (region='Île-de-France', text riche) existe en corpus.
                # Le path v1 avec retrieve sur 47k fiches a une probabilité
                # bien plus haute de capturer la bonne fiche en top, puis
                # apply_metadata_filter garde les CROUS qui matchent region.
                if len(reranked) == 0:
                    _logger.info(
                        "[router-quad] n_after_filter=0 sur sub_indexes=%s "
                        "(raw=%d, filter domain=%s, region=%s) — fallback path v1.",
                        route_decision.sub_indexes,
                        len(raw),
                        criteria.domain if criteria else None,
                        criteria.region if criteria else None,
                    )
                    # Fall through au path v1 (ne pas return).
                else:
                    self.last_filter_stats = {
                        "filter_active": criteria is not None and not criteria.is_empty(),
                        "router_active": True,
                        "router_sub_indexes": list(route_decision.sub_indexes),
                        "router_confidence": route_decision.confidence,
                        "router_is_fallback": route_decision.is_fallback,
                        "n_retrieved_router": len(raw),
                        "n_after_filter": len(reranked),
                        "expansions": 0,  # quad path n'expand pas
                    }
                    return reranked

        # Path par défaut (no metadata filter) : Option C v6 — retrieval indépendant
        # du domain_hint avec quota adaptatif d'annexes basé sur score brut.
        if not self.use_metadata_filter or criteria is None or criteria.is_empty():
            return self._retrieve_with_annex_quota(question, k, target, domain_hint)

        # Path filter actif : retrieve avec k_eff = k × INITIAL, expand si nécessaire
        k_eff = k * INITIAL_K_MULTIPLIER
        max_k = k * MAX_K_MULTIPLIER
        expansions = 0
        filtered: list[dict] = []
        retrieved: list[dict] = []
        reranked_full: list[dict] = []

        while True:
            retrieved = retrieve_top_k(
                self.client, self.index, self.fiches, question, k=k_eff
            )
            reranked_full = rerank(retrieved, self.rerank_config, domain_hint=domain_hint)
            filtered = apply_metadata_filter(reranked_full, criteria)
            if len(filtered) >= target:
                break
            if k_eff >= max_k:
                _logger.warning(
                    "metadata_filter MAX_K_MULTIPLIER atteint (k=%d, max=%d) — "
                    "criteria probablement trop restrictifs (n_filtered=%d, target=%d). "
                    "Retour partiel.",
                    k_eff, max_k, len(filtered), target,
                )
                break
            k_eff = min(k_eff * 2, max_k)
            expansions += 1

        self.last_filter_stats = {
            "filter_active": True,
            "criteria_empty": False,
            "k_initial": k,
            "k_final": k_eff,
            "n_retrieved": len(retrieved),
            "n_after_filter": len(filtered),
            "expansions": expansions,
            "hit_max": k_eff >= max_k and len(filtered) < target,
        }
        return filtered

    def _build_double_subindices(self) -> bool:
        """Lazy-build des 2 sub-indices FAISS (main + annex) via reconstruct().

        Construit `_main_subindex` (formations sans `domain`) et
        `_annex_subindex` (corpora annexes avec `domain`) une seule fois.
        Workaround Phase C++ (ADR-058) : retrieve séparé pour ne pas
        dépendre du score sémantique des fiches annexes courtes/stat
        face aux formations longues.

        Returns True si les 2 sub-indices ont au moins 1 vecteur, False
        sinon (fallback vers retrieve unifié).
        """
        if self._double_index_built:
            return self._main_subindex is not None and self._annex_subindex is not None
        if self.index is None or not self.fiches:
            self._double_index_built = True
            return False

        # Vague 1.C — exclure les fiches retrieval_eligible=False des sub-indices.
        # 18 012 fiches RNCP/ONISEP/LBA/CFA ne sont pas adaptées au retrieval
        # formation+ville (audit Phase 0 v5). Ne pas les indexer = top-K plus
        # net + plus de place pour annexes pertinentes.
        # Backward compat : fiches sans flag retrieval_eligible sont
        # considérées éligibles par défaut (corpus v5 pre-Vague 1).
        main_indices: list[int] = []
        annex_indices: list[int] = []
        n_excluded_ineligible = 0
        for i, f in enumerate(self.fiches):
            if not isinstance(f, dict):
                continue
            if f.get("retrieval_eligible") is False:
                n_excluded_ineligible += 1
                continue
            if f.get("domain"):
                annex_indices.append(i)
            else:
                main_indices.append(i)
        if n_excluded_ineligible > 0:
            _logger.info(
                "[double-index] excluded %d fiches retrieval_eligible=false (Vague 1.C)",
                n_excluded_ineligible,
            )

        if len(main_indices) < 2 or len(annex_indices) < 2:
            # Pas assez de fiches dans un pool — fallback retrieve unifié
            _logger.info(
                "[double-index] skip — pas assez de fiches (main=%d, annex=%d)",
                len(main_indices), len(annex_indices),
            )
            self._double_index_built = True
            return False

        # Build sub-indices via reconstruct (pas de re-embed Mistral, just
        # extraction des vecteurs depuis l'index unifié). Coût ~30s pour
        # 47k vecteurs, fait une seule fois au premier appel.
        try:
            d = self.index.d
            main_embs = np.array(
                [self.index.reconstruct(int(i)) for i in main_indices],
                dtype="float32",
            )
            annex_embs = np.array(
                [self.index.reconstruct(int(i)) for i in annex_indices],
                dtype="float32",
            )
            main_idx = faiss.IndexFlatL2(d)
            main_idx.add(main_embs)
            annex_idx = faiss.IndexFlatL2(d)
            annex_idx.add(annex_embs)
            self._main_subindex = main_idx
            self._annex_subindex = annex_idx
            self._main_subindex_orig_indices = main_indices
            self._annex_subindex_orig_indices = annex_indices
            _logger.info(
                "[double-index] built — main=%d annex=%d",
                len(main_indices), len(annex_indices),
            )
            self._double_index_built = True
            return True
        except (RuntimeError, ValueError) as e:
            _logger.warning("[double-index] build failed (%s) — fallback unifié", e)
            self._double_index_built = True
            return False

    def _retrieve_with_bm25(self, question: str, k: int = 50) -> list[dict]:
        """Phase C ADR-058 — retrieve BM25 lexical pour entités nommées.

        Lazy-build au 1er appel (~5-10s pour 47k fiches, fait une fois).
        Returns top-k results avec scores BM25.
        """
        if not self._bm25_built:
            try:
                from src.rag.bm25_index import BM25Index
                _logger.info("[bm25] Building lexical index for %d fiches...", len(self.fiches))
                self._bm25_index = BM25Index(self.fiches)
                _logger.info("[bm25] Index built (n_fiches=%d)", self._bm25_index.n_fiches)
            except (ImportError, RuntimeError) as e:
                _logger.warning("[bm25] build failed (%s) — fallback no BM25", e)
                self._bm25_index = None
            self._bm25_built = True
        if self._bm25_index is None:
            return []
        return self._bm25_index.search(question, k=k)

    def _retrieve_with_double_subindex(
        self,
        question: str,
    ) -> tuple[list[dict], list[dict]]:
        """Phase C++ — retrieve séparé sur sub-indices main + annex.

        Renvoie (main_results, annex_results) avec format `retrieve_top_k`
        standard ({fiche, score, base_score, embedding}).
        """
        if not self._build_double_subindices():
            # Fallback : retrieve unifié et split post-FAISS (mode dégradé)
            retrieved = retrieve_top_k(
                self.client, self.index, self.fiches, question,
                k=ANNEX_QUOTA_K_INITIAL,
            )
            main = [r for r in retrieved if not (r.get("fiche") or {}).get("domain")]
            annex = [r for r in retrieved if (r.get("fiche") or {}).get("domain")]
            return main, annex

        # Embedding question (1 fois pour les 2 sub-indices)
        from src.rag.embeddings import embed_texts
        q_emb = embed_texts(self.client, [question])[0]
        q_arr = np.array([q_emb], dtype="float32")

        def _search_subindex(sub_idx, orig_indices, k):
            distances, idx_in_sub = sub_idx.search(q_arr, k)
            results = []
            for rank in range(len(idx_in_sub[0])):
                isub = int(idx_in_sub[0][rank])
                if isub < 0 or isub >= len(orig_indices):
                    continue
                orig_idx = orig_indices[isub]
                dist = float(distances[0][rank])
                score = 1.0 / (1.0 + dist)
                # Reconstruct embedding pour MMR aval
                emb = sub_idx.reconstruct(isub)
                results.append({
                    "fiche": self.fiches[orig_idx],
                    "score": score,
                    "base_score": score,
                    "embedding": np.asarray(emb, dtype="float32"),
                })
            return results

        main_results = _search_subindex(
            self._main_subindex,
            self._main_subindex_orig_indices,
            DOUBLE_INDEX_K_MAIN,
        )
        annex_results = _search_subindex(
            self._annex_subindex,
            self._annex_subindex_orig_indices,
            DOUBLE_INDEX_K_ANNEX,
        )
        return main_results, annex_results

    # ────────────────────── Quad sub-indexes (étape 5 refonte) ──────────────────────

    def _load_quad_indices_from_disk(self, manifest_path: Path) -> bool:
        """Charge les 4 sub-indexes FAISS depuis le manifest JSON.

        Pré-requis : `scripts/build_quad_subindexes.py` a été exécuté pour
        produire les 4 fichiers `formations_v7_<group>.index` + le manifest.

        Returns:
            True si tous les sub-indexes ont été chargés avec succès,
            False si manifest absent ou un fichier manque (caller fera
            le rebuild en mémoire à partir de l'index unifié).
        """
        if not manifest_path.exists():
            return False
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            _logger.warning("[quad-index] manifest illisible (%s) — fallback rebuild", e)
            return False

        # Garde de cohérence : le manifest doit décrire EXACTEMENT le corpus
        # courant. Sinon orig_indices référerait des fiches inexistantes
        # (cas typique : tests avec mini-corpus + manifest production présent).
        manifest_total = manifest.get("total_fiches_in_source")
        if manifest_total is not None and manifest_total != len(self.fiches):
            _logger.info(
                "[quad-index] manifest désaligné (%d fiches manifest vs %d courantes) "
                "— rebuild en mémoire",
                manifest_total, len(self.fiches),
            )
            return False

        groups: dict[str, faiss.IndexFlatL2] = {}
        groups_orig: dict[str, list[int]] = {}
        manifest_root = manifest_path.parent.parent.parent  # data/embeddings/X.json → repo root
        for name, info in manifest.get("groups", {}).items():
            sub_path_str = info.get("path")
            if not sub_path_str:
                _logger.warning("[quad-index] manifest group %s sans `path`", name)
                return False
            sub_path = manifest_root / sub_path_str
            if not sub_path.exists():
                _logger.warning("[quad-index] sub-index absent : %s", sub_path)
                return False
            try:
                groups[name] = faiss.read_index(str(sub_path))
            except RuntimeError as e:
                _logger.warning("[quad-index] read %s failed (%s)", sub_path, e)
                return False
            groups_orig[name] = [int(i) for i in info.get("orig_indices", [])]

        self._quad_indices = groups
        self._quad_indices_orig = groups_orig
        _logger.info(
            "[quad-index] loaded from disk : %s",
            {name: idx.ntotal for name, idx in groups.items()},
        )
        return True

    def _build_quad_subindices(
        self,
        manifest_path: str | Path | None = None,
    ) -> bool:
        """Lazy-build des 4 sub-indexes FAISS par groupes de domaines.

        Stratégie :
        1. Si manifest présent sur disque (scripts/build_quad_subindexes.py
           a été run) → charge tel quel (pas de re-extraction des vecteurs).
        2. Sinon → rebuild en mémoire via `index.reconstruct()` (extension
           du pattern `_build_double_subindices`).

        Returns True si les 4 sub-indexes sont prêts (au moins 1 contient
        ≥1 vecteur), False sinon (caller fera fallback vers retrieve unifié
        ou _retrieve_with_double_subindex).
        """
        if self._quad_indices_built:
            return self._quad_indices is not None
        if self.index is None or not self.fiches:
            self._quad_indices_built = True
            return False

        # Path du manifest (default = data/embeddings/formations_partition_manifest.json)
        if manifest_path is None:
            manifest_path = Path(__file__).resolve().parents[2] / QUAD_MANIFEST_DEFAULT_PATH
        else:
            manifest_path = Path(manifest_path)

        # Tentative 1 : load depuis disque
        if self._load_quad_indices_from_disk(manifest_path):
            self._quad_indices_built = True
            return True

        # Tentative 2 : rebuild en mémoire (lazy partition + reconstruct)
        # Réutilise le mapping domain → group du build script.
        try:
            from build_quad_subindexes import (  # type: ignore[import-not-found]
                partition_indices,
                build_subindex,
            )
        except ImportError:
            # scripts/ pas dans PYTHONPATH → import direct via path
            import importlib.util
            scripts_dir = Path(__file__).resolve().parents[2] / "scripts"
            spec = importlib.util.spec_from_file_location(
                "build_quad_subindexes", scripts_dir / "build_quad_subindexes.py"
            )
            if spec is None or spec.loader is None:
                _logger.warning("[quad-index] build_quad_subindexes module introuvable")
                self._quad_indices_built = True
                return False
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            partition_indices = module.partition_indices
            build_subindex = module.build_subindex

        try:
            group_to_orig, _excluded, _unknown = partition_indices(self.fiches)
            quad: dict[str, faiss.IndexFlatL2] = {}
            quad_orig: dict[str, list[int]] = {}
            for name, orig_indices in group_to_orig.items():
                if not orig_indices:
                    quad[name] = faiss.IndexFlatL2(self.index.d)
                    quad_orig[name] = []
                    continue
                quad[name] = build_subindex(self.index, orig_indices)
                quad_orig[name] = orig_indices
            self._quad_indices = quad
            self._quad_indices_orig = quad_orig
            _logger.info(
                "[quad-index] built in-memory : %s",
                {name: idx.ntotal for name, idx in quad.items()},
            )
            self._quad_indices_built = True
            return True
        except (RuntimeError, ValueError) as e:
            _logger.warning("[quad-index] in-memory build failed (%s) — fallback", e)
            self._quad_indices_built = True
            return False

    def _retrieve_from_sub_indexes(
        self,
        question: str,
        sub_index_names: list[str],
        k_per_sub: int = QUAD_INDEX_K_PER_SUB,
    ) -> list[dict]:
        """Retrieve depuis 1 ou plusieurs sub-indexes ciblés (étape 5).

        Si `sub_index_names` contient 1 seul nom : retrieve standard sur ce
        sub-index uniquement (résultats triés par score desc).
        Si 2+ noms : retrieve séparé sur chaque + fusion RRF (preserve la
        diversité inter-domaines).

        Args:
            question: requête utilisateur.
            sub_index_names: liste de noms parmi
                ['formations', 'metiers', 'statistiques', 'aides_territoires'].
            k_per_sub: top-k retrieve par sub-index avant fusion.

        Returns:
            Liste de dicts {fiche, score, base_score, embedding} compatibles
            avec rerank/MMR aval. Vide si quad-index non-buildable ou
            tous sub-indexes vides.
        """
        if not sub_index_names:
            return []
        if not self._build_quad_subindices():
            return []
        assert self._quad_indices is not None and self._quad_indices_orig is not None

        valid_names = [
            n for n in sub_index_names
            if n in self._quad_indices and self._quad_indices[n].ntotal > 0
        ]
        if not valid_names:
            return []

        # Embedding de la question (1 fois pour tous les sub-indexes)
        from src.rag.embeddings import embed_texts
        q_emb = embed_texts(self.client, [question])[0]
        q_arr = np.array([q_emb], dtype="float32")

        def _search_one(name: str) -> list[dict]:
            sub_idx = self._quad_indices[name]
            orig = self._quad_indices_orig[name]
            k = min(k_per_sub, sub_idx.ntotal)
            distances, idx_in_sub = sub_idx.search(q_arr, k)
            results: list[dict] = []
            for rank in range(len(idx_in_sub[0])):
                isub = int(idx_in_sub[0][rank])
                if isub < 0 or isub >= len(orig):
                    continue
                orig_idx = orig[isub]
                dist = float(distances[0][rank])
                score = 1.0 / (1.0 + dist)
                emb = sub_idx.reconstruct(isub)
                results.append({
                    "fiche": self.fiches[orig_idx],
                    "score": score,
                    "base_score": score,
                    "embedding": np.asarray(emb, dtype="float32"),
                    "_sub_index": name,
                })
            return results

        if len(valid_names) == 1:
            return _search_one(valid_names[0])

        # Multi-sub-index → fusion RRF.
        # `reciprocal_rank_fusion` (bm25_index.py:197-255) accepte une liste
        # de pools rangés et fusionne par RRF (Cormack 2009, k_rrf=60).
        # On utilise une clé d'identification stable : (fiche.id ou ix).
        per_pool: list[list[dict]] = [_search_one(name) for name in valid_names]
        # Filter pools vides
        per_pool = [p for p in per_pool if p]
        if not per_pool:
            return []
        if len(per_pool) == 1:
            return per_pool[0]

        # RRF utilise par défaut id_key="fiche_id" qu'on n'a pas forcément
        # toujours. On crée une clé stable orig_idx pour chaque résultat.
        emb_lookup: dict = {}
        for pool in per_pool:
            for r in pool:
                f = r.get("fiche") or {}
                # Préfère f["id"] si présent, sinon fallback sur position
                # objet (id() Python — stable au sein d'un appel pipeline).
                quad_id = f.get("id") or id(f)
                r["_quad_id"] = quad_id
                # Préserver l'embedding de la 1re occurrence pour MMR aval
                if quad_id not in emb_lookup:
                    emb_lookup[quad_id] = r.get("embedding")

        fused_rrf = reciprocal_rank_fusion(per_pool, k_rrf=60, id_key="_quad_id")
        # `reciprocal_rank_fusion` retourne {fiche, score_rrf, score_dense,
        # score_bm25, ranks}. On reconstruit le format standard
        # {fiche, score, base_score, embedding} attendu par rerank/MMR aval,
        # en réinjectant l'embedding lookup par fiche.
        normalized: list[dict] = []
        for entry in fused_rrf:
            fiche = entry.get("fiche") or {}
            quad_id = fiche.get("id") or id(fiche)
            score = float(entry.get("score_rrf", 0.0))
            normalized.append({
                "fiche": fiche,
                "score": score,
                "base_score": score,
                "embedding": emb_lookup.get(quad_id),
            })
        # Cleanup _quad_id sur les pools pour ne pas polluer si les pools
        # sont consultés ensuite par d'autres callers.
        for pool in per_pool:
            for r in pool:
                r.pop("_quad_id", None)
        return normalized

    def _retrieve_with_annex_quota(
        self,
        question: str,
        k: int,
        target: int,
        domain_hint: str | None,
    ) -> list[dict]:
        """Option C v6 + Double-index — retrieve séparé main/annex + quota adaptatif.

        Phase C corpus v5 (2026-05-08, ADR-058 workaround).

        Mécanique :
        1. **Double-index** : retrieve séparé top-100 main + top-30 annex
           via sub-indices construits par `_build_double_subindices`. Indépendant
           du score sémantique des fiches annexes courtes face aux formations.
        2. Reranker chaque pool indépendamment (boosts existants conservés)
        3. Si meilleure annexe ≥ seuil → boost top-3 annexes pour entrer top-K
           Sinon → top-K = main only (pas de pollution)

        Stats stockées dans last_filter_stats pour audit.
        """
        # Phase C++ — retrieve double-index (main 100 + annex 30)
        main_pool, annex_pool = self._retrieve_with_double_subindex(question)

        # Phase C ADR-058 — BM25 hybride : retrieve lexical en parallèle,
        # fusion via RRF. Indispensable pour entités nommées (CROUS Lyon,
        # RNCP, PCS) que dense rate.
        bm25_results = self._retrieve_with_bm25(question, k=BM25_TOP_K)

        # Vraie fusion Reciprocal Rank Fusion (Cormack et al. 2009) — calcule
        # un score unifié à travers les 3 rankings (dense main + dense annex
        # + BM25). Le score RRF est ensuite utilisé pour les fiches BM25-only
        # non vues par dense (au lieu d'un placeholder constant qui perdait
        # l'information du rang BM25). Vague 0 fix — bug RRF nominal Phase C.
        fused = reciprocal_rank_fusion(
            [main_pool, annex_pool, bm25_results],
            k_rrf=RRF_K,
            id_key="_orig_index",
        )
        rrf_score_by_fiche_id: dict[int, float] = {}
        for item in fused:
            f = item.get("fiche")
            if f is not None:
                rrf_score_by_fiche_id[id(f)] = item["score_rrf"]

        # Si BM25 ramène des fiches non-vues par dense, les ajouter au pool
        # approprié (main ou annex selon `domain`)
        seen_ids: set[int] = set()
        for r in main_pool + annex_pool:
            f = r.get("fiche")
            seen_ids.add(id(f))
            # Annoter les pools dense avec leur score RRF (audit + downstream)
            if f is not None:
                r["score_rrf"] = rrf_score_by_fiche_id.get(id(f), 0.0)
        for bm in bm25_results:
            if id(bm.get("fiche")) in seen_ids:
                continue
            # Convertir au format result complet : reconstruct l'embedding
            # depuis l'index unifié (nécessaire pour MMR aval).
            fiche = bm.get("fiche") or {}
            orig_idx = bm.get("_orig_index")
            embedding: np.ndarray | None = None
            if orig_idx is not None and self.index is not None:
                try:
                    emb = self.index.reconstruct(int(orig_idx))
                    embedding = np.asarray(emb, dtype="float32")
                except (RuntimeError, ValueError):
                    embedding = None
            if embedding is None:
                # Fallback : embedding zéros (MMR appliquera diversité minimale
                # sur cette fiche, mais elle reste retournée par le retrieval)
                embedding = np.zeros(self.index.d if self.index else 1024, dtype="float32")
            # Score basé sur la VRAIE fusion RRF (vs placeholder 0.55).
            # RRF scores typiques : ~0.016 (rank 1 dans un seul ranking) à
            # ~0.05 (rank 1 dans plusieurs rankings). Mapping vers échelle
            # dense [0.4, 0.8] pour permettre rerank multiplicatif cohérent.
            rrf_score = rrf_score_by_fiche_id.get(id(fiche), 0.0)
            bm25_score_normalized = min(0.4 + (rrf_score * 30.0), 0.8)
            converted = {
                "fiche": fiche,
                "score": bm25_score_normalized,
                "base_score": bm25_score_normalized,
                "embedding": embedding,
                "score_bm25": bm.get("score_bm25", 0.0),
                "score_rrf": rrf_score,
                "rank_bm25": bm.get("rank_bm25"),
                "_orig_index": orig_idx,
            }
            if fiche.get("domain"):
                annex_pool.append(converted)
            else:
                main_pool.append(converted)

        # k_eff conservé pour stats backward-compat
        k_eff = DOUBLE_INDEX_K_MAIN + DOUBLE_INDEX_K_ANNEX + BM25_TOP_K

        # Reranker indépendamment sur chaque pool (boosts existants)
        main_reranked = rerank(main_pool, self.rerank_config, domain_hint=domain_hint)
        annex_reranked = rerank(annex_pool, self.rerank_config, domain_hint=domain_hint)

        # Quota adaptatif : si la meilleure annexe a un score raisonnable,
        # boost les top annexes pour forcer leur entrée dans le top-K final.
        # Important : on retourne la liste complète des reranked (pas tronquée
        # à `target`) pour que le MMR appliqué en aval (pipeline.answer) ait
        # de quoi diversifier — le slicing à `target` se fait dans le MMR.
        annex_top_score = annex_reranked[0].get("score", 0.0) if annex_reranked else 0.0
        quota_active = annex_top_score >= ANNEX_QUOTA_MIN_SCORE
        n_annex_above_threshold = sum(
            1 for r in annex_reranked
            if r.get("score", 0.0) >= ANNEX_QUOTA_MIN_SCORE
        )

        if quota_active:
            # Booster les top-K annexes éligibles pour qu'elles passent au top
            # via le tri par score. Le boost est additif (vs multiplicatif) pour
            # garantir que même les annexes à score bas (0.6) dépassent les
            # formations à score haut (1.10) après boost (0.6 + 1.0 = 1.6).
            n_annex_quota = min(ANNEX_QUOTA_MAX_PER_TOPK, n_annex_above_threshold)
            annex_with_boost: list[dict] = []
            for r in annex_reranked[:n_annex_quota]:
                boosted = dict(r)
                boosted["score"] = r.get("score", 0.0) + ANNEX_QUOTA_SCORE_BOOST
                boosted["_quota_boosted"] = True
                annex_with_boost.append(boosted)
            # Concat main complet + annexes boostées, tri global par score
            combined = main_reranked + annex_with_boost
            combined.sort(key=lambda x: x.get("score", 0.0), reverse=True)
        else:
            # Pas de quota — retourne main complet (MMR slicera à target)
            combined = main_reranked

        # Stats audit
        self.last_filter_stats = {
            "filter_active": False,
            "criteria_empty": True,
            "annex_quota_strategy": "v6_double_index_score_threshold",
            "k_initial": k,
            "k_final": k_eff,
            "n_retrieved": len(main_pool) + len(annex_pool),
            "n_main_pool": len(main_pool),
            "n_annex_pool": len(annex_pool),
            "annex_top_score": round(annex_top_score, 3),
            "annex_quota_active": quota_active,
            "n_annex_above_threshold": n_annex_above_threshold,
            "n_annex_boosted": min(ANNEX_QUOTA_MAX_PER_TOPK, n_annex_above_threshold) if quota_active else 0,
            "n_returned": len(combined),
            "expansions": 0,
            "double_index_active": self._double_index_built and self._main_subindex is not None,
        }
        return combined

    # ─────────────── Sprint 10 chantier D — Q&A Golden Dynamic Few-Shot ───────

    def _lazy_load_golden_qa(self) -> bool:
        """Charge l'index FAISS et le meta JSON Q&A Golden au premier appel.

        Returns True si le load a réussi (index + meta dispos), False si
        configuration manquante ou fichiers absents (fallback gracieux,
        pas d'exception — on désactive juste le few-shot pour ce call).
        """
        if self._golden_qa_index is not None and self._golden_qa_meta is not None:
            return True
        if not self._golden_qa_index_path or not self._golden_qa_meta_path:
            _logger.warning(
                "use_golden_qa=True mais golden_qa_index_path/meta_path "
                "non fournis — few-shot désactivé pour ce call."
            )
            return False
        idx_path = Path(self._golden_qa_index_path)
        meta_path = Path(self._golden_qa_meta_path)
        if not idx_path.exists() or not meta_path.exists():
            _logger.warning(
                "Golden QA files manquants (idx=%s exists=%s ; meta=%s exists=%s) — "
                "few-shot désactivé pour ce call.",
                idx_path, idx_path.exists(), meta_path, meta_path.exists(),
            )
            return False
        self._golden_qa_index = load_index(str(idx_path))
        meta_obj = json.loads(meta_path.read_text(encoding="utf-8"))
        self._golden_qa_meta = meta_obj.get("records") or []
        if len(self._golden_qa_meta) != self._golden_qa_index.ntotal:
            _logger.warning(
                "Mismatch index ntotal (%d) vs meta records (%d) — risque "
                "désynchro mapping. Chargement quand même mais à investiguer.",
                self._golden_qa_index.ntotal, len(self._golden_qa_meta),
            )
        return True

    def _retrieve_golden_qa(self, question: str, top_k: int = 1) -> dict | None:
        """Top-k Q&A Golden via FAISS dédié. Retourne le record meta du top-1
        (incluant `answer_refined`, `score_total`, `decision`, etc.).

        Returns None si flag désactivé OU index non chargeable OU 0 records.
        """
        if not self.use_golden_qa:
            return None
        if not self._lazy_load_golden_qa():
            return None
        # Embed la question via Mistral-embed (même modèle que pour build l'index)
        q_emb = embed_texts(self.client, [question])[0]
        q_arr = np.array([q_emb], dtype="float32")
        distances, indices = self._golden_qa_index.search(q_arr, top_k)
        if indices.size == 0 or indices[0][0] < 0:
            return None
        idx = int(indices[0][0])
        if idx >= len(self._golden_qa_meta):
            return None
        record = self._golden_qa_meta[idx]
        # Annoter avec score retrieve pour audit
        record_copy = dict(record)
        record_copy["_retrieve_score"] = float(1.0 / (1.0 + distances[0][0]))
        record_copy["_retrieve_distance"] = float(distances[0][0])
        return record_copy

    @staticmethod
    def _build_few_shot_prefix(qa_record: dict) -> str:
        """Construit le bloc few-shot prefix avec **séparation stricte Comment/Quoi**.

        Le prefix s'injecte au system prompt via `generate(golden_qa_prefix=...)`.
        Le pattern : la Q&A Golden = RÉFÉRENCE COMPORTEMENTALE (ton, structure,
        empathie, posture). Les écoles, chiffres, dates citées dans cet exemple
        sont **IGNORÉS** côté factuel — seules les fiches du context RAG ci-après
        sont sources autorisées pour citer.

        Validé Matteo dans la sync architecture 2026-04-29.
        """
        seed = (qa_record.get("question_seed") or "").strip()
        refined_q = (qa_record.get("question_refined") or "").strip()
        refined_a = (qa_record.get("answer_refined") or "").strip()
        # Si le record manque l'answer_refined, on ne peut pas faire de few-shot
        if not refined_a:
            return ""
        question_for_prefix = refined_q or seed or "(question similaire)"
        return (
            "=== EXEMPLE EXPERT (RÉFÉRENCE TON/STRUCTURE/EMPATHIE UNIQUEMENT) ===\n"
            f"Question type traitée par un conseiller expert :\n"
            f"« {question_for_prefix} »\n\n"
            "Réponse de référence (style, posture, structure de raisonnement) :\n"
            f"{refined_a}\n\n"
            "⚠️ IMPORTANT — SÉPARATION STRICTE COMMENT vs QUOI :\n"
            "- Cet exemple est une RÉFÉRENCE COMPORTEMENTALE (ton bienveillant,\n"
            "  reformulation active, 3 pistes pondérées, questions d'exploration).\n"
            "- IGNORE complètement les écoles spécifiques, chiffres, dates, noms\n"
            "  de formations cités dans cet exemple.\n"
            "- SEULES les fiches du contexte RAG ci-dessous sont sources\n"
            "  autorisées pour citer des formations factuelles dans ta réponse.\n"
            "- Tu peux donc REPRENDRE le STYLE de cet exemple, mais JAMAIS son CONTENU\n"
            "  factuel. La question user a son propre contexte de fiches à utiliser.\n"
            "=== FIN EXEMPLE EXPERT ===\n"
        )

    def _maybe_build_golden_qa_prefix(self, question: str) -> str | None:
        """Wrapper qui combine retrieve + build_prefix + stats. Retourne None
        si flag désactivé ou pas de match. Utilisé par .answer()."""
        qa = self._retrieve_golden_qa(question, top_k=1)
        if qa is None:
            self.last_golden_qa = {
                "active": self.use_golden_qa,
                "matched": False,
            }
            return None
        prefix = self._build_few_shot_prefix(qa)
        self.last_golden_qa = {
            "active": True,
            "matched": True,
            "prompt_id": qa.get("prompt_id"),
            "category": qa.get("category"),
            "iteration": qa.get("iteration"),
            "score_total": qa.get("score_total"),
            "retrieve_score": qa.get("_retrieve_score"),
            "decision": qa.get("decision"),
        }
        return prefix if prefix else None

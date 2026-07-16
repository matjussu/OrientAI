"""AgentPipeline — Sprint 4 axe B intégration end-to-end.

Pipeline agentique complet qui chaîne les 3 tools agentiques (Sprints 1-3)
+ les composants RAG existants (retrieval FAISS + génération Mistral) :

```
query
  → ProfileClarifier (Sprint 1, cacheable)
  → QueryReformuler (Sprint 2, sub-queries multi-corpus)
  → Retrieval FAISS par sub-query (parallel via parallel_map Sprint 3)
  → Aggregation cross-corpus (dedupe + top-N)
  → Génération finale Mistral (streaming via Sprint 3 wrapper, ou non pour bench)
  → (optionnel) FetchStatFromSource sur claims chiffrés post-gen
  → AgentAnswer
```

Architecture cible bench Sprint 4 vs baseline figée 39.4% verified /
17.9% halluc (PR #75 baseline).

Cf ADR-051 + verdicts Sprints 1-3 dans `docs/`.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from mistralai.client import Mistral

from src.agent.cache import LRUCache
from src.agent.parallel import parallel_apply
from src.agent.tools.profile_clarifier import Profile, ProfileClarifier
from src.agent.tools.query_reformuler import (
    QueryReformuler,
    ReformulationPlan,
    SubQuery,
)
from src.agent.tools.fetch_stat_from_source import (
    FetchStatFromSource,
    Source,
    StatVerification,
)
from src.rag.generator import generate
from src.rag.retriever import retrieve_top_k


@dataclass
class AgentAnswer:
    """Résultat d'une invocation `pipeline.answer(query)`."""

    query: str
    answer_text: str
    profile: Profile | None
    plan: ReformulationPlan | None
    sources_aggregated: list[dict] = field(default_factory=list)
    sub_query_retrievals: list[dict] = field(default_factory=list)
    fact_check_results: list[StatVerification] = field(default_factory=list)
    elapsed_total_s: float = 0.0
    elapsed_clarify_s: float = 0.0
    elapsed_reformulate_s: float = 0.0
    elapsed_retrieve_s: float = 0.0
    elapsed_generate_s: float = 0.0
    elapsed_fact_check_s: float = 0.0
    cache_hit_profile: bool = False
    error: str | None = None

    def to_dict(self, include_sources: bool = False) -> dict:
        """Serialize AgentAnswer.

        `include_sources=True` (Sprint 5) sérialise les sources_aggregated
        complètes (texte + score + domain + id + nom etc.) pour permettre
        un fact-check post-hoc avec StatFactChecker (apples-to-apples
        baseline). Coût taille fichier : ~10-50 KB par query si activé.
        """
        out = {
            "query": self.query,
            "answer_text": self.answer_text,
            "profile": self.profile.to_dict() if self.profile else None,
            "plan": self.plan.to_dict() if self.plan else None,
            "sources_aggregated_count": len(self.sources_aggregated),
            "sub_query_retrievals_count": len(self.sub_query_retrievals),
            "fact_check_results": [v.to_dict() for v in self.fact_check_results],
            "elapsed_total_s": self.elapsed_total_s,
            "elapsed_clarify_s": self.elapsed_clarify_s,
            "elapsed_reformulate_s": self.elapsed_reformulate_s,
            "elapsed_retrieve_s": self.elapsed_retrieve_s,
            "elapsed_generate_s": self.elapsed_generate_s,
            "elapsed_fact_check_s": self.elapsed_fact_check_s,
            "cache_hit_profile": self.cache_hit_profile,
            "error": self.error,
        }
        if include_sources:
            # Sérialise format compatible StatFactChecker (existant `src/experimental/fact_checker.py`).
            # StatFactChecker.verify(answer, sources) attend list[dict] avec
            # `fiche` key contenant le texte recherchable.
            out["sources_aggregated"] = [
                {
                    "score": float(s.get("score", 0)),
                    "fiche": s.get("fiche", {}),
                }
                for s in self.sources_aggregated
            ]
        return out


@dataclass
class AgentPipeline:
    """Orchestrateur agentique end-to-end Sprint 4."""

    client: Mistral
    fiches: list[dict]  # phaseD index data (54 297 cells)
    index: Any  # faiss.IndexFlatL2 — loaded externally
    profile_cache: LRUCache | None = None
    sub_query_top_k: int = 6  # top-K par sub-query (6 × ~5 sub-queries = ~30 candidates)
    aggregated_top_n: int = 8  # top-N final agrégé (optim Sprint 4 : 12→8 -33% gen tokens)
    parallel_max_workers: int = 3  # threadpool pour retrieval
    parallel_fact_check_workers: int = 3  # parallel fact-check Sprint 4 optim
    enable_fact_check: bool = False  # opt-in pour Sprint 4 bench
    fact_check_max_claims: int = 5  # cap claims fact-check pour budget
    generation_model: str = "mistral-medium-latest"  # gen finale model
    # Sprint 7 Action 3 — anti-hallu LLM
    system_prompt_override: str | None = None  # None = SYSTEM_PROMPT v3.2 (default)
    # Pour activer v3.3 strict (R1-R6) : passer SYSTEM_PROMPT_V33_STRICT
    # depuis src.experimental.system_strict.
    # Sprint 8 Wave 1 — post-process anti-hallu (bugs P0 user_test_v3)
    enable_post_process: bool = True  # default ON : fix Bugs Q8, Q9, Q10
    # Désactivable pour bench apples-to-apples Sprint 5/6/7 si besoin.
    # Post-process déterministe non-LLM (≠ critic loop Sprint 7 OFF par
    # défaut), ne risque pas de régression LLM-driven.

    def __post_init__(self) -> None:
        self.clarifier = ProfileClarifier(
            client=self.client, cache=self.profile_cache,
        )
        self.reformuler = QueryReformuler(client=self.client)
        if self.enable_fact_check:
            self.fact_checker = FetchStatFromSource(client=self.client)
        else:
            self.fact_checker = None

    def _retrieve_for_subquery(self, sub_query: SubQuery) -> dict:
        """Retrieve top-K depuis FAISS pour une sub-query.

        Pas de filtering par target_corpus (les vecteurs sont mêlés
        dans phaseD). Le rerank du domain_hint Sprint 1+ se fait au
        niveau aggregation. Pour MVP Sprint 4, on prend top-K L2 brut
        par sub-query, on dédupe à l'aggregation.
        """
        retrieved = retrieve_top_k(
            self.client,
            self.index,
            self.fiches,
            sub_query.text,
            k=self.sub_query_top_k,
        )
        return {
            "sub_query_id": id(sub_query),  # référence Python (dispo dans plan.sub_queries)
            "sub_query_text": sub_query.text,
            "target_corpus": sub_query.target_corpus,
            "priority": sub_query.priority,
            "retrieved": retrieved,
        }

    def _aggregate_sources(
        self, sub_query_retrievals: list[dict]
    ) -> list[dict]:
        """Dedupe sources cross-sub-query par id stable + score max."""
        # Index par id stable. Pour formation: cod_aff_form + nom + etab.
        # Pour autres corpus: id explicit dans la fiche.
        by_id: dict[str, dict] = {}
        for retrieval in sub_query_retrievals:
            for r in retrieval["retrieved"]:
                fiche = r["fiche"]
                source_id = (
                    fiche.get("id")
                    or fiche.get("numero_fiche")
                    or f"{fiche.get('nom', '')[:40]}|{fiche.get('etablissement', '')[:40]}"
                )
                # Garde le meilleur score (max) si plusieurs sub-queries
                # font remonter la même fiche
                if source_id in by_id:
                    if r.get("score", 0) > by_id[source_id].get("score", 0):
                        by_id[source_id] = r
                else:
                    by_id[source_id] = r
        # Sort par score desc, top_N
        sorted_sources = sorted(
            by_id.values(),
            key=lambda r: r.get("score", 0),
            reverse=True,
        )
        return sorted_sources[: self.aggregated_top_n]

    def _extract_claims_for_fact_check(
        self, answer_text: str
    ) -> list[str]:
        """Extract claims chiffrés / réglementaires de la réponse.

        Stratégie naïve MVP : split sur phrases, garde celles avec
        des chiffres ou des termes réglementaires explicit (RNCP,
        niveau, certifié, validation, etc.).
        """
        import re
        sentences = re.split(r"(?<=[.!?])\s+", answer_text)
        claims = []
        # Pattern : phrase avec nombre OU mot réglementaire
        regex_chiffre = re.compile(r"\d{2,}|\d+\s*%|\d+\s*€")
        regex_reg = re.compile(
            r"\b(?:RNCP|niveau\s+\d|certifié|validé|protégé|obligatoire|requis|exige)\b",
            re.IGNORECASE,
        )
        for s in sentences:
            s_clean = s.strip()
            if len(s_clean) < 15:
                continue
            if regex_chiffre.search(s_clean) or regex_reg.search(s_clean):
                claims.append(s_clean)
            if len(claims) >= self.fact_check_max_claims:
                break
        return claims

    def answer(self, query: str) -> AgentAnswer:
        """Pipeline end-to-end query → AgentAnswer."""
        t0_total = time.time()
        result = AgentAnswer(query=query, answer_text="", profile=None, plan=None)

        try:
            # Étape 1 : ProfileClarifier
            t0 = time.time()
            cache_size_before = (
                len(self.profile_cache) if self.profile_cache else 0
            )
            profile = self.clarifier.clarify(query)
            result.elapsed_clarify_s = round(time.time() - t0, 2)
            result.profile = profile
            # Heuristique cache hit : si le cache a la même size avant/après
            # ET que stats hits > 0 (donc le call a touché le cache)
            if self.profile_cache:
                cache_stats = self.profile_cache.stats()
                # Si latence quasi-nulle = cache hit
                result.cache_hit_profile = result.elapsed_clarify_s < 0.1

            # Étape 2 : QueryReformuler
            t0 = time.time()
            plan = self.reformuler.reformulate(query, profile)
            result.elapsed_reformulate_s = round(time.time() - t0, 2)
            result.plan = plan

            # Étape 3 : Retrieval parallel par sub-query
            t0 = time.time()
            retrievals = parallel_apply(
                lambda sq: (self._retrieve_for_subquery(sq),),
                [(sq,) for sq in plan.sub_queries],
                max_workers=self.parallel_max_workers,
                return_exceptions=True,
            )
            # Unpack (parallel_apply wraps in tuple to handle multi-arg) —
            # ici lambda takes one arg, return est un tuple (result,). Adapt.
            sub_query_retrievals = []
            for r in retrievals:
                if isinstance(r, Exception):
                    continue
                # r est le retour de _retrieve_for_subquery (dict)
                if isinstance(r, tuple):
                    r = r[0]
                sub_query_retrievals.append(r)
            result.elapsed_retrieve_s = round(time.time() - t0, 2)
            result.sub_query_retrievals = sub_query_retrievals

            # Étape 4 : Aggregation
            sources_agg = self._aggregate_sources(sub_query_retrievals)
            result.sources_aggregated = sources_agg

            # Étape 5 : Génération finale
            t0 = time.time()
            answer_text = generate(
                self.client,
                sources_agg,
                query,
                model=self.generation_model,
                temperature=0.3,
                system_prompt_override=self.system_prompt_override,
            )
            result.elapsed_generate_s = round(time.time() - t0, 2)

            # Sprint 8 Wave 1 — post-process anti-hallu (bugs P0)
            if self.enable_post_process:
                from src.rag.post_process import post_process_answer
                answer_text, _ = post_process_answer(answer_text, sources_agg)

            result.answer_text = answer_text

            # Étape 6 (optionnelle) : fact-check post-gen — PARALLEL Sprint 4 optim
            if self.enable_fact_check and self.fact_checker:
                t0 = time.time()
                claims = self._extract_claims_for_fact_check(answer_text)
                # Convert sources_agg en list[Source] pour FetchStatFromSource
                source_objs = [
                    Source(
                        id=str(s["fiche"].get("id") or s["fiche"].get("numero_fiche") or "?"),
                        text=(s["fiche"].get("text") or s["fiche"].get("nom", "")[:300]),
                        domain=s["fiche"].get("domain", "formation"),
                        score=float(s.get("score", 0)),
                    )
                    for s in sources_agg
                ]
                if claims:
                    # Parallel fact-check via parallel_apply Sprint 3
                    fact_results_raw = parallel_apply(
                        self.fact_checker.verify,
                        [(claim, source_objs) for claim in claims],
                        max_workers=self.parallel_fact_check_workers,
                        return_exceptions=True,
                    )
                    fact_results = [
                        r for r in fact_results_raw
                        if not isinstance(r, Exception)
                    ]
                else:
                    fact_results = []
                result.fact_check_results = fact_results
                result.elapsed_fact_check_s = round(time.time() - t0, 2)

        except Exception as e:
            result.error = f"{type(e).__name__}: {e}"

        result.elapsed_total_s = round(time.time() - t0_total, 2)
        return result

"""Factory canonique pour OrientIAPipeline en mode production.

Une seule source de vérité — fini les flags éparpillés dans run_real_full,
mini_bench, scripts/* qui créent chacun un pipeline avec un sous-ensemble
de features actives ou désactivées.

`make_production_pipeline()` instancie le pipeline avec **toutes les
features câblées** (validator + golden_qa + post_process), avec des flags
opt-out individuels pour A/B et des défauts paths pour les artefacts
golden_qa.

Usage typique :

    from src.rag.factory import make_production_pipeline
    from mistralai.client import Mistral

    client = Mistral(api_key=...)
    fiches = json.loads(Path("data/processed/formations.json").read_text())
    pipeline = make_production_pipeline(client, fiches)
    pipeline.load_index_from("data/embeddings/formations.index")
    text, sources = pipeline.answer("Ma question ?")

Pour A/B (désactiver une feature individuelle) :

    pipeline = make_production_pipeline(
        client, fiches,
        enable_golden_qa=False,  # mesurer l'impact du Golden QA
    )

Pour reproduire le baseline historique (comme run_real_full.py Phase F) :

    pipeline = make_production_pipeline(
        client, fiches,
        enable_validator=False,
        enable_golden_qa=False,
        enable_post_process=False,
    )

Cf plan refonte produit niveau 2 — Phase 2 (`~/.claude/plans/...`).
"""
from __future__ import annotations

import os
from pathlib import Path

from mistralai.client import Mistral

from src.agent.tools.profile_clarifier import ProfileClarifier
from src.rag.pipeline import OrientIAPipeline
from src.rag.router_llm import RouterLLM
from src.rag.scope_classifier import ScopeClassifier
from src.validator import Validator
from src.validator.layer3 import Layer3Validator


def _env_truthy(val: str | None) -> bool:
    """True si la variable d'env exprime un opt-in (1/true/yes/on)."""
    return str(val or "").strip().lower() in ("1", "true", "yes", "on")


# Paths par défaut pour les artefacts Golden QA (chantier D Sprint 10).
# Lazy-loadés au 1er .answer() — ces fichiers doivent exister sur disque
# pour que use_golden_qa=True soit effectif (sinon fallback gracieux + warning).
DEFAULT_GOLDEN_QA_INDEX = "data/embeddings/golden_qa.index"
DEFAULT_GOLDEN_QA_META = "data/processed/golden_qa_meta.json"

# Paths par défaut pour les 4 sub-indexes FAISS du RouterLLM (étape 4 refonte).
# Le manifest authoritative + 4 fichiers `.index` sont produits par
# `scripts/build_quad_subindexes.py`. Lazy-loadés au 1er answer() qui passe
# par le quad-path. Si manifest absent, le pipeline rebuild en mémoire au
# boot (graceful fallback, +30s première req).
DEFAULT_QUAD_MANIFEST = "data/embeddings/formations_partition_manifest.json"
DEFAULT_QUAD_GROUP_NAMES = ("formations", "metiers", "statistiques", "aides_territoires")


def make_production_pipeline(
    client: Mistral,
    fiches: list[dict],
    *,
    # Validator (couches 1+2 par défaut, +layer3 LLM en opt-in)
    enable_validator: bool = True,
    enable_layer3: bool = False,
    # Vague 0.5 (2026-05-08) : threshold aligné 0.30 → 0.55 cohérent avec le
    # design de corpus_check (poids 0.85 nom + 0.15 etab, seuil empirique
    # 0.55 où une paraphrase réaliste d'une fiche du corpus dépasse). Les
    # docstrings factory et corpus_check étaient incohérentes ; le 0.55 est
    # le seuil designé. Plus strict = catch plus de hallucinations
    # (compromis : risque léger de faux positifs sur paraphrases légitimes,
    # accepté pour démo INRIA cible "catch hallu" prioritaire).
    corpus_sim_threshold: float = 0.55,
    # Golden QA few-shot (Sprint 10 chantier D)
    enable_golden_qa: bool = True,
    golden_qa_index_path: str | None = None,
    golden_qa_meta_path: str | None = None,
    # Post-process déterministe (Sprint 8 Wave 1)
    enable_post_process: bool = True,
    # Étape 1 refonte 2026-05-06 — ScopeClassifier amont (in_scope/out_of_scope/urgent)
    enable_scope_classifier: bool = True,
    # Étape 2 refonte 2026-05-06 — contrat strict v4 (FactCard JSON + SYSTEM_PROMPT_V4_STRICT)
    # v4.1 (2026-05-06) : R6 max 250 mots + max_tokens=400 + top-5 sources.
    # Bench mini-bench v4.1 : avg_latency 7.26s (-29% vs v3.2), avg_words 184
    # (-23%), 0 flagged, honesty 1.0. Layer3 +8% (biais visibilité chiffres
    # sourcés, cf ADR-053). Bascule défaut True à partir de v4.1.
    enable_strict_v4: bool = True,
    # Étape 6 refonte 2026-05-09 — RouterLLM léger (Mistral Small JSON-tool).
    # Default True : production avec routing LLM-driven sur quad sub-indexes
    # + FilterCriteria + R7 hardlock. False : préserve baseline Run F+G strict
    # (utile pour A/B mesurer le delta router on/off en Phase D bench).
    enable_router_llm: bool = True,
    # Modèle utilisé pour le routing (séparé du modèle de génération).
    # mistral-small-latest = ~$0.0001/q + 500-800 ms latence.
    router_model: str = "mistral-small-latest",
    # Retrieval / generation tuning (rarement override)
    use_mmr: bool = True,
    use_intent: bool = True,
    use_metadata_filter: bool = True,
    model: str = "mistral-medium-latest",
    # Mode récit (R1 1c, ordre #137). None -> lit l'env ORIENTIA_NARRATIVE_MODE
    # (default OFF). Quand actif, instancie un ProfileClarifier dédié et active
    # la branche _prepare_narrative (déterministe profil-driven) sur les récits.
    enable_narrative_mode: bool | None = None,
) -> OrientIAPipeline:
    """Build a production-ready OrientIAPipeline.

    Args:
        client: Mistral client (gen + embed).
        fiches: list of formation/multi-corpus records (loaded from
            data/processed/formations.json).
        enable_validator: si True, instancie un Validator (rules + corpus_check
            + presence) attaché au pipeline. Default True (production).
        enable_layer3: si True (et enable_validator True), ajoute la couche 3
            LLM Mistral Small. Coût ~$0.001/q + 2-4s latency. Default False.
        corpus_sim_threshold: seuil similarité pour corpus_check. Default 0.55
            (Vague 0.5 — aligné avec design corpus_check, où une paraphrase
            réaliste d'une fiche du corpus dépasse 0.55 sur poids 0.85 nom
            + 0.15 etab). 0.30 = legacy permissif (faux négatifs probables).
        enable_golden_qa: si True, active le few-shot Q&A Golden retrieve top-1
            injecté en préfixe utilisateur. Default True (production). Files
            par défaut sur DEFAULT_GOLDEN_QA_INDEX/META.
        golden_qa_index_path: override path index FAISS Golden QA.
        golden_qa_meta_path: override path meta JSON Golden QA.
        enable_post_process: si True, applique strip_invented_urls +
            fix_broken_markdown_tables + validate_onisep_slugs post-validator.
            Déterministe (zéro LLM, zéro risque). Default True.
        use_mmr: diversification MMR post-rerank. Default True (Phase F.3).
        use_intent: classify_intent + intent_to_config. Default True (Phase F.3).
        use_metadata_filter: active le filter métadonnées si criteria fourni
            par l'appelant. Default True (chantier C Sprint 10).
        model: modèle Mistral pour la génération. Default mistral-medium-latest.

    Returns:
        OrientIAPipeline configuré, sans index FAISS chargé. L'appelant doit
        ensuite faire `pipeline.load_index_from(path)` ou `pipeline.build_index()`.
    """
    validator: Validator | None = None
    if enable_validator:
        layer3 = Layer3Validator(client=client) if enable_layer3 else None
        validator = Validator(
            fiches=fiches,
            corpus_sim_threshold=corpus_sim_threshold,
            layer3=layer3,
        )

    scope_classifier: ScopeClassifier | None = None
    if enable_scope_classifier:
        scope_classifier = ScopeClassifier(client=client)

    # Étape 8 refonte (2026-05-09) — RouterLLM léger en amont du retrieve.
    # Réutilise EXACTEMENT le même client Mistral que le reste du pipeline
    # (point de vigilance audit step 7 → 8 : un seul client par session).
    # Le RouterLLM appelle Mistral Small en interne (model param overridable).
    router_llm: RouterLLM | None = None
    if enable_router_llm:
        router_llm = RouterLLM(client=client, model=router_model)

    # Résolution paths Golden QA : si flag activé mais paths non fournis,
    # utiliser les défauts. Le pipeline lazy-loadera au 1er .answer() — si
    # les fichiers n'existent pas, fallback gracieux (warning + skip few-shot).
    gqa_idx = golden_qa_index_path
    gqa_meta = golden_qa_meta_path
    if enable_golden_qa:
        gqa_idx = gqa_idx or DEFAULT_GOLDEN_QA_INDEX
        gqa_meta = gqa_meta or DEFAULT_GOLDEN_QA_META

    # Mode récit : résolution flag (param explicite > env > default OFF).
    if enable_narrative_mode is None:
        enable_narrative_mode = _env_truthy(os.environ.get("ORIENTIA_NARRATIVE_MODE"))
    narrative_clarifier = ProfileClarifier(client=client) if enable_narrative_mode else None

    return OrientIAPipeline(
        client=client,
        fiches=fiches,
        model=model,
        use_mmr=use_mmr,
        use_intent=use_intent,
        validator=validator,
        use_metadata_filter=use_metadata_filter,
        use_golden_qa=enable_golden_qa,
        golden_qa_index_path=gqa_idx,
        golden_qa_meta_path=gqa_meta,
        enable_post_process=enable_post_process,
        scope_classifier=scope_classifier,
        use_strict_v4=enable_strict_v4,
        router_llm=router_llm,
        enable_narrative_mode=enable_narrative_mode,
        narrative_clarifier=narrative_clarifier,
    )


def golden_qa_artifacts_present(
    index_path: str = DEFAULT_GOLDEN_QA_INDEX,
    meta_path: str = DEFAULT_GOLDEN_QA_META,
) -> bool:
    """Helper diagnostic — retourne True si les 2 artefacts Golden QA sont
    présents sur disque, sinon False.

    Utile en démarrage (ex: API FastAPI lazy init) pour décider si on active
    Golden QA ou si on log un warning explicite.
    """
    return Path(index_path).exists() and Path(meta_path).exists()


def router_llm_artifacts_present(
    manifest_path: str = DEFAULT_QUAD_MANIFEST,
    group_names: tuple[str, ...] = DEFAULT_QUAD_GROUP_NAMES,
) -> bool:
    """Helper diagnostic — retourne True si tous les artefacts du quad-subindex
    sont présents sur disque (manifest + 4 fichiers FAISS), sinon False.

    Utile en démarrage API/serving pour décider entre :
    - True : router peut consommer les sub-indexes pré-buildés depuis disque
      (load rapide, pas de rebuild en mémoire)
    - False : log warning + le pipeline rebuild en mémoire au 1er answer()
      (graceful, +30s première req mais fonctionnel)

    Args:
        manifest_path: chemin du manifest JSON (default formations_partition_manifest.json)
        group_names: tuple des 4 groupes attendus (cohérent avec
            scripts/build_quad_subindexes.py)

    Returns:
        True ssi le manifest ET les 4 fichiers FAISS référencés sont présents.
    """
    manifest_p = Path(manifest_path)
    if not manifest_p.exists():
        return False
    try:
        import json
        manifest = json.loads(manifest_p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    groups = manifest.get("groups", {})
    if set(groups.keys()) != set(group_names):
        return False
    manifest_root = manifest_p.parent.parent.parent  # data/embeddings/X.json → repo root
    for name in group_names:
        info = groups.get(name, {})
        sub_path_str = info.get("path")
        if not sub_path_str:
            return False
        if not (manifest_root / sub_path_str).exists():
            return False
    return True

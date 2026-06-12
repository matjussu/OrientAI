# Pipeline v4.1 strict — flags & câblage prod

**Source de vérité** : `src/rag/factory.py:make_production_pipeline()`. Ce document décrit l'état du pipeline en prod au 2026-05-08 (post-Vague 0.5, post-Phase A verrouillage).

Toute déviation entre ce doc et factory.py est un bug à corriger dans factory ou ce doc — pas une exception locale.

---

## Vue d'ensemble

```
question
   ↓
ScopeClassifier        (enable_scope_classifier=True)  → bypass si urgent/out_of_scope
   ↓
intent classifier      (use_intent=True)              → adapte top_k_sources + mmr_lambda
   ↓
SELECT bypass          (auto si intent=FACTUAL_POINTED) → réponse déterministe si match
   ↓
Retrieval hybride      → double-index v6 (main+annex) + BM25 (lexical) + RRF fusion
   │ pré-warm au boot via /answer warmup (server.py)
   ↓
Reranker domain-aware  (ADR-049, 17 boosts incluant cross-boost métier)
   ↓
metadata_filter        (use_metadata_filter=True, opt-in si criteria fourni)
   ↓
MMR diversification    (use_mmr=True, lambda adaptatif par intent)
   ↓
Golden QA few-shot     (enable_golden_qa=True, lazy-load)
   ↓
Generator              (model=mistral-medium-latest, use_strict_v4=True)
   │   v4.1 strict : SYSTEM_PROMPT_V4_STRICT R1-R6, FactCard JSON sources, max_tokens=400, R6 max 250 mots
   ↓
Validator              (enable_validator=True)
   │   Layer1 rules + Layer2 corpus_check (corpus_sim_threshold=0.55) + presence
   │   Layer3 Mistral Small : opt-in (enable_layer3=False par défaut, biais +8% honesty fictive)
   ↓
Retry loop             SKIP en strict_v4 (hint_block ignoré par R1-R6 v4)
   ↓
Policy α/β/γ           remplacement réponse si BLOCK
   ↓
append_phase_projet    (Tier 3 stub, redirect SCUIO/CIO/Psy-EN si enjeu fort)
   ↓
post_process           (enable_post_process=True)
   │   strip URLs hallucinées + fix markdown brisé + validate slugs ONISEP
   ↓
réponse + sources
```

---

## Flags `make_production_pipeline()` — défauts prod

| Flag | Type | Défaut prod | Rôle | Coût override |
|---|---|---|---|---|
| `enable_validator` | bool | `True` | Active Layer1 (rules) + Layer2 (corpus_check + presence) | Désactiver = honesty visibility perdue (mini-bench v4.1 → pas de measurable) |
| `enable_layer3` | bool | `False` | Active Layer3 LLM Mistral Small (LLM-judge sur claims) | Activer = +$0.001/q + 2-4s latency + biais visibility +8% honesty fictive |
| `corpus_sim_threshold` | float | `0.55` | Seuil similarité corpus_check (Vague 0.5 — aligné design 0.85·nom + 0.15·etab) | 0.30 = legacy permissif (faux négatifs), 0.55 = strict catch hallu |
| `enable_golden_qa` | bool | `True` | Few-shot Q&A retrieve top-1 injecté en préfixe utilisateur | Désactiver = perte de séparation COMMENT/QUOI structurelle (Sprint 10 chantier D) |
| `golden_qa_index_path` | str\|None | `data/embeddings/golden_qa.index` | Path index FAISS Golden QA (lazy-load) | Override pour A/B sur Golden QA alternatif |
| `golden_qa_meta_path` | str\|None | `data/processed/golden_qa_meta.json` | Path meta JSON Golden QA | Idem |
| `enable_post_process` | bool | `True` | Post-process déterministe (strip URLs hallu + fix markdown + validate slugs) | Désactiver = URLs ChatGPT-style possibles, jamais en prod |
| `enable_scope_classifier` | bool | `True` | Gate amont in_scope/out_of_scope/urgent (Mistral Small + 5s timeout graceful) | Désactiver = questions hors-scope traitées par RAG (waste + risque) |
| `enable_strict_v4` | bool | `True` | Mode v4.1 strict : SYSTEM_PROMPT_V4_STRICT R1-R6 + FactCard JSON + R6 max 250 mots + max_tokens=400 | Désactiver = retour v3.2 legacy (verbosité +23%, latency +29%, honesty +0 mais hallu visibilité +) |
| `use_mmr` | bool | `True` | Diversification MMR post-rerank (Phase F.3) | Désactiver = top-K resserré sur même cluster |
| `use_intent` | bool | `True` | Classify intent + adapt config (top_k_sources, mmr_lambda) | Désactiver = config statique pour tous intents |
| `use_metadata_filter` | bool | `True` | Filter métadonnées si `criteria` fourni à `pipeline.answer()` (Sprint 10 chantier C) | Pas de criteria = pas de filtre (backward compat) |
| `model` | str | `mistral-medium-latest` | Modèle de génération | Mistral Large testé Sprint 12 — pas de gain mesurable vs Medium |

---

## Flags env-var (corpus / texte embeddé)

Lus au niveau process (env), pas via `make_production_pipeline()`. Affectent la
construction du texte embeddé (`src/rag/embeddings.py:fiche_to_text`) — donc l'index :
un changement ne prend effet qu'au re-embed.

| Flag env | Défaut | Rôle | Statut |
|---|---|---|---|
| `ORIENTIA_DENSE_SIGLE` | non set (= OFF) | Injecte le sigle/acronyme (J2, `sigle_injection_text`) dans le texte EMBEDDÉ dense des fiches BUT-specialty. | **PARKÉ** — gate J2 partiellement FAIL : 6 gains (BUT obscurs Montluçon/Vichy/Morlaix...) MAIS déplace **LAS Cergy (4→5)** et surtout **MIAGE Paris (4→hors top-10, cas démo)**. Arbitrage zéro-régression Matteo, re-confirmé par le check du 2026-06-12 (re-embed 0825). **Revival** prévue au chantier ranking unifié post-VivaTech (mesurer le net après ré-équilibrage du reranker). |

Note importante : ce flag NE gate PAS le sigle BM25 (`src/rag/bm25_index`), qui reste
actif et faisait déjà partie de la baseline figée (dense OFF + BM25 ON = état du gel
10/06). Pour réactiver le dense en A/B : `ORIENTIA_DENSE_SIGLE=1` AU LANCEMENT du
re-embed (le flag est lu à l'import du module, pas modifiable après — vérifier l'env
du process détaché).

---

## Couches actives par défaut prod (résumé)

| Couche | État | Coût/question | Latency contrib |
|---|---|---|---|
| ScopeClassifier (Mistral Small) | ✅ ON | ~$0.0001 | ~0.5-1s |
| Intent classifier (regex 7 classes) | ✅ ON | $0 | <10ms |
| SELECT bypass (déterministe) | ✅ ON | $0 | <50ms |
| Double-index lazy build (v6 main+annex) | ✅ ON | $0 | warmup ~30s au boot |
| BM25 lazy build (lexical) | ✅ ON | $0 | warmup ~5-10s au boot |
| RRF fusion (3 rankings) | ✅ ON | $0 | <10ms |
| Reranker domain-aware (17 boosts) | ✅ ON | $0 | <50ms |
| metadata_filter | ⚪ Conditionnel `criteria` | $0 | <30ms |
| MMR diversification (intent-adaptive) | ✅ ON | $0 | <30ms |
| Golden QA lazy-load (top-1 few-shot) | ✅ ON (si artefacts présents) | $0 | <100ms |
| Generator Mistral Medium v4.1 strict | ✅ ON | ~$0.0008 | 5-10s (dominant) |
| Layer1 rules | ✅ ON | $0 | <10ms |
| Layer2 corpus_check | ✅ ON | $0 | <100ms |
| Layer2 presence | ✅ ON | $0 | <10ms |
| Layer3 Mistral Small | ❌ OFF (opt-in) | ~$0.001 | +2-4s |
| Retry-with-hint | ⚪ SKIP en strict_v4 | $0 | $0 (skipped) |
| Policy α/β/γ | ✅ ON | $0 | <10ms |
| append_phase_projet (Tier 3) | ✅ ON | $0 | <10ms |
| post_process déterministe | ✅ ON | $0 | <50ms |
| **Total prod nominal** | | **~$0.001/q** | **6-12s** |

Mini-bench v4.1 (23q, 2026-05-08) : avg latency **7.26s**, avg words **184**, **0 flagged**, honesty **1.0**.

---

## Modes A/B documentés

### Reproduire baseline historique Run F
```python
pipeline = make_production_pipeline(
    client, fiches,
    enable_validator=False,      # pas de couche post-gen Phase F
    enable_golden_qa=False,      # pas de few-shot Phase F
    enable_post_process=False,   # pas de strip déterministe Phase F
    enable_scope_classifier=False,  # pas de gate amont Phase F
    enable_strict_v4=False,      # v3.2 legacy
)
```

### A/B Layer3 (impact LLM-judge sur honesty visibility)
```python
pipeline_with_layer3 = make_production_pipeline(client, fiches, enable_layer3=True)
pipeline_without = make_production_pipeline(client, fiches, enable_layer3=False)  # défaut
# Compare honesty_score sur même question : +8% biais visibility documenté ADR-053
```

### A/B Mistral Large vs Medium (Sprint 12 verdict)
```python
pipeline_large = make_production_pipeline(client, fiches, model="mistral-large-latest")
pipeline_medium = make_production_pipeline(client, fiches)  # Medium par défaut
# results/bench_sprint12_mistral_large_vs_medium/ : pas de gain mesurable vs Medium
```

---

## Points de vérification rapides

```bash
# Audit factory complet (default flags)
python3 -c "
from src.rag.factory import make_production_pipeline, golden_qa_artifacts_present
import inspect
sig = inspect.signature(make_production_pipeline)
for name, param in sig.parameters.items():
    if name in ('client', 'fiches'): continue
    print(f'{name}: {param.default!r}')
print(f'golden_qa_artifacts_present: {golden_qa_artifacts_present()}')
"

# Smoke test full pipeline
python3 -c "
from src.rag.factory import make_production_pipeline
from mistralai.client import Mistral
import json, os
client = Mistral(api_key=os.environ['MISTRAL_API_KEY'])
fiches = json.load(open('data/processed/formations.json'))
p = make_production_pipeline(client, fiches)
p.load_index_from('data/embeddings/formations.index')
p._build_double_subindices(); p._retrieve_with_bm25('warmup', k=1)
text, sources = p.answer('BUT informatique Bordeaux ?')
print(f'OK: {len(text)} chars, {len(sources)} sources, validation={p.last_validation}')
"
```

---

*Rapport produit en Phase B3 du plan verrouillage-bench-multi-tour. À actualiser à chaque ajout/retrait de flag dans `factory.py`.*

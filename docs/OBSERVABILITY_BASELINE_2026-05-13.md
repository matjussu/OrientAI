# Observability Baseline — Spot-Check Gate 3 sous Langfuse

**Date** : 2026-05-13 23:10  
**Session** : `spot_check_baseline_1778706472`  
**Corpus** : `data/processed/formations_v5.json` (47 193 fiches)  
**Index** : `data/embeddings/formations_v5.index`  
**Pipeline** : HEAD (SYSTEM_PROMPT_SPRINT11_P0 + scope_classifier + router_llm + double-index + BM25 RRF + validator)

**Résultat global** : **4/13 questions** avec domain match ≥1 dans top-5. Identique au baseline manuel `SPOT_CHECK_V5_2026-05-13.md` (Q3, Q6, Q8, Q11 passent ; Q1/Q2/Q4/Q5/Q7/Q9/Q10/Q12/Q13 échouent).

---

## 🔍 Insights principaux

### Insight 1 — Le retrieve n'est PAS le bottleneck moyen (révision)

Sur la 1ère trace isolée (Q6 boursiers), j'avais conclu "retrieve = 46% du temps". **Ce n'est pas généralisable**. Sur 13 questions :

- `step_5_retrieve_filter` avg = **2.08s**, **médiane 0.39s**, max 22.05s ← très skewed
- `step_8_generate_with_retry` avg = **4.61s**, médiane 4.14s ← bottleneck systématique

Exclu de l'outlier Q01, le retrieve moyen tombe à **~0.42s**. La génération Mistral medium domine partout sauf cas pathologique.

### Insight 2 — Q01 est une pathologie majeure (36s)

| Span | Durée | Commentaire |
|---|---:|---|
| `step_5_retrieve_filter` | **22.05s** | Anormal — médiane des 12 autres = 0.39s |
| `step_1_scope_classify` | **5.66s** | Anormal — médiane des 12 autres = 0.51s |
| `step_8_generate_with_retry` | 7.56s | Normal-haut (p95 = 7.56s) |
| Reste | 0.84s | Normal |
| **Total** | **36.11s** | Soit 30 % du temps total cumulé (123s) sur 1/13 questions |

**Hypothèses prioritaires à investiguer** :
1. **Auto-expansion `_retrieve_and_filter` qui boucle** : k×INITIAL → k×MAX, peut-être 3-4 itérations sur Q01 (criteria probablement trop restrictifs après router_llm → metier_prospective)
2. **Retry Mistral Small sur scope_classify** : 5.66s ≈ 2× appels + backoff. Cloudflare 520 ou timeout possible
3. **Quad-subindex retrieve qui rapatrie 0 fiches → fallback v1 → boucle auto-expansion**

À vérifier dans `pipeline.last_filter_stats` (incluant `expansions`, `n_after_filter`, `hit_max`) post-fix.

### Insight 3 — Q09 brûle 8.94s dans SELECT bypass ratée

`step_4_select_bypass` n=1 sur 13 → uniquement Q09 ("Salaire moyen d'un cadre supérieur (PCS 37) ?"). Le code essaie un SELECT structuré sur fuzzy match d'entité "PCS 37" dans les 47 193 fiches → **8.94s** → **N'aboutit PAS au bypass** (continue pipeline normal step_5+step_8).

Coût pur : 8.94s gaspillés sur une tentative qui n'apporte rien. Sur Q05 (actuaire) qui aurait pu être factual_pointed aussi, le SELECT n'a pas trigger (n=1 total).

**Hypothèse** : `try_select_or_none` scale poorly avec corpus_size 47k. Optimisation possible : early-exit si pas d'entité nommée détectée par regex pré-fuzzy.

### Insight 4 — Les fails prennent +5.98s en moyenne vs pass

| Étape | Pass avg (n=4) | Fail avg (n=9) | Δ |
|---|---:|---:|---:|
| `orientia.answer` | 5.31s | 11.29s | **+5.98s** |
| `step_5_retrieve_filter` | 0.24s | 2.90s | +2.66s (dominé Q01) |
| `step_8_generate_with_retry` | 3.68s | 5.02s | +1.33s |
| `step_1_scope_classify` | 0.65s | 1.47s | +0.82s |

Les questions qui échouent prennent plus de temps **à toutes les étapes**, pas juste retrieve. Cela suggère un pattern : quand le retrieve ne trouve pas la fiche annexe, le pipeline tente fallbacks (auto-expansion, re-retrieve) ET la génération produit des réponses "info non disponible" plus longues. **Le coût total des fails est multiple, pas localisé**.

### Insight 5 — Le scope_classifier consomme 13% du temps total cumulé

`step_1_scope_classify` total = 15.83s sur 122.88s = **12.9%**. Avg 1.22s/question (1 appel Mistral Small + history processing). Si la question est manifestement in_scope (cas dominant : étudiant cherche orientation), c'est de l'overhead. Une optimisation possible : cache LRU sur question-prefix ou skip si keyword whitelist match (mais risque sur urgent detection).

---

## 1. Timing global par étape (13 questions)

| Étape | n obs | avg | médiane | p95 | min | max | total cumulé |
|---|---:|---:|---:|---:|---:|---:|---:|
| `orientia.answer` (racine) | 13 | 9.45s | 6.24s | 13.09s | 4.03s | 36.11s | 122.88s |
| `step_4_select_bypass` | 1 | 8.94s | 8.94s | 8.94s | 8.94s | 8.94s | 8.94s |
| `step_8_generate_with_retry` | 13 | 4.61s | 4.14s | 7.56s | 1.92s | 8.60s | 59.86s |
| `chat mistral-medium-latest` | 13 | 4.51s | 4.11s | 6.86s | 1.88s | 8.60s | 58.61s |
| `step_5_retrieve_filter` | 13 | 2.08s | 0.39s | 0.97s | 0.13s | 22.05s | 27.02s |
| `step_1_scope_classify` | 13 | 1.22s | 0.51s | 3.47s | 0.42s | 5.66s | 15.83s |
| `chat mistral-small-latest` | 26 | 0.85s | 0.51s | 1.17s | 0.41s | 4.97s | 22.15s |
| `step_2_router_llm` | 13 | 0.58s | 0.55s | 0.73s | 0.46s | 0.77s | 7.48s |
| `step_7_golden_qa_prefix` | 13 | 0.24s | 0.18s | 0.45s | 0.13s | 0.46s | 3.09s |
| `embeddings mistral-embed` | 35 | 0.21s | 0.16s | 0.42s | 0.12s | 0.57s | 7.34s |
| `step_6_mmr`, `step_3*`, `step_9_validator`, `step_10_post_process` | 13× | <0.005s | — | — | — | — | <0.1s |

## 2. Détail par question (avec status pass/fail)

| Q | expected_domain | match top-5 | total | retrieve | generate | scope | router | select_bypass |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| **Q01** | metier_prospective | ❌ 0/5 | **36.11s** | **22.05s** | 7.56s | **5.66s** | 0.57s | — |
| **Q02** | crous | ❌ 0/5 | 4.23s | 0.52s | 1.92s | 0.69s | 0.59s | — |
| **Q03** | competences_certif | ✅ 5/5 | 4.03s | 0.15s | 2.57s | 0.48s | 0.51s | — |
| **Q04** | insertion_pro | ❌ 0/5 | 6.24s | 0.41s | 4.14s | 0.51s | 0.77s | — |
| **Q05** | metier_detail | ❌ 0/5 | 8.18s | 0.76s | 5.92s | 0.52s | 0.50s | — |
| **Q06** | financement_etudes | ✅ 5/5 | 6.24s | 0.32s | 3.97s | 1.19s | 0.46s | — |
| **Q07** | territoire_drom | ❌ 0/5 | 11.10s | 0.39s | 8.60s | 1.01s | 0.64s | — |
| **Q08** | apec_region | ✅ 1/5 | 4.96s | 0.14s | 3.60s | 0.51s | 0.53s | — |
| **Q09** | insee_salaire | ❌ 0/5 | **13.09s** | 0.97s | 2.12s | 0.42s | 0.49s | **8.94s** |
| **Q10** | formation_insertion | ❌ 0/5 | 4.53s | 0.13s | 3.10s | 0.48s | 0.67s | — |
| **Q11** | voie_pre_bac | ✅ 1/5 | 6.02s | 0.34s | 4.58s | 0.43s | 0.49s | — |
| **Q12** | parcours_bacheliers | ❌ 0/5 | 6.71s | 0.46s | 4.90s | 0.47s | 0.73s | — |
| **Q13** | insertion_pro | ❌ 0/5 | 11.45s | 0.38s | 6.88s | 3.47s | 0.55s | — |

**Outliers** :
- Q01 : retrieve 22s + scope 5.66s (cumulé 27.7s sur 36.1s)
- Q09 : SELECT bypass 8.94s gaspillé (try_select_or_none scaling issue ?)
- Q13 : scope 3.47s (anormal, médiane = 0.51s)

## 3. Conséquences pour le fix `fiche_to_text` (Claudette)

Le fix Claudette adresse le **problème qualitatif** : les fiches annexes (DARES, CROUS, INSEE, Inserjeunes, MESR, ROME details, RNCP blocs) sont embed sur ~40 chars de métadonnées formation sans leur champ `text` (28% du corpus = 13 412 fiches). Conséquence visible dans les top-5 des 9 fails : retrieve ramène des `(formation)` au lieu des `metier_prospective`, `crous`, `insee_salaire`, etc.

**Ce que le fix devrait changer (mesurable via Langfuse post-fix)** :
- `n_domain_match_top5` ≥ 1 pour Q1, Q2, Q4, Q5, Q7, Q9, Q10, Q12, Q13 (cible : 11-13/13)
- Latence `step_5_retrieve_filter` Q01 devrait revenir dans la norme (~0.5s) si l'auto-expansion ne déclenche plus
- Latence totale devrait baisser de ~30 % (élimination de Q01 outlier)

**Ce que le fix ne changera PAS** :
- `step_8_generate` ~4.5s avg (limite Mistral medium)
- `step_1_scope_classify` ~1.2s avg (overhead amont)
- `step_4_select_bypass` Q09 ~9s (scaling fuzzy match sur 47k fiches)

## 4. Méthodologie & reproductibilité

**Lancer le bench** :
```bash
cd ~/projets/OrientIA && source .venv/bin/activate
python scripts/observability/run_spot_check_traced.py
python scripts/observability/analyze_spot_check_traces.py
```

**Visualiser dans Langfuse UI** :
http://localhost:3000 → projet OrientIA RAG → Traces → filtrer par name=`orientia.answer` → trier desc

**Limitations connues du run actuel** :
- `update_current_trace` n'existe pas en Langfuse v4 → les tags session_id/q_id ne sont PAS attachés aux traces (workaround : analyse matche par ordre temporel)
- Pas de sous-instrumentation step_5 (embed/FAISS/rerank/BM25/RRF) → on voit le total step_5 mais pas la décomposition interne. Si signal needed post-fix Q01, ajouter spans dans `_retrieve_with_annex_quota`

**Coût Mistral du bench** :
- 13 × 1 medium (gen) + 13 × 2 small (scope + router) + 35 × embed = ~$0.20 estimé
- Reproduisible sans budget critique

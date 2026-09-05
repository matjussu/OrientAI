## Rapport — la MESURE du retrieval dans OrientIA

Lecture seule, aucun fichier modifié. Tous les chemins sont relatifs à `/home/matteo_linux/projets/OrientIA/`.

---

# 1. ADR qui justifient l'architecture de retrieval

## 1.1 Reranker à boosts de labels (l'ADR fondateur)

| ADR | Date | Fichier:ligne | Rationale (1 phrase) |
|---|---|---|---|
| **ADR-002** — Label-based reranker instead of pure vector similarity | 2026-03-15 | `docs/DECISION_LOG.md:35` | FAISS cosine fait remonter les écoles privées à métadonnées SEO denses plutôt que les formations publiques à descriptions ONISEP pauvres, donc on ajoute un boost multiplicatif sur les labels officiels (SecNumEdu, CTI, Grade Master, statut public). |

Point important pour la mesure : **le BM25 hybride avait été explicitement REJETÉ dans cet ADR** (`docs/DECISION_LOG.md:51-52` : « Hybrid BM25 + vector : rejected — still doesn't encode the label priority »). ADR-058 le réintroduit 2 mois plus tard. Contradiction assumée, jamais tracée comme telle.

## 1.2 Multi-corpus et rejet initial des index séparés

| ADR | Date | Fichier:ligne | Rationale |
|---|---|---|---|
| **ADR-048** — RAG multi-corpus retrievable parallèle | 2026-04-25 | `docs/DECISION_LOG.md:2321` | Jointure ROME impraticable (couverture <5 %), donc chaque source hétérogène devient un corpus parallèle avec son `domain`, dans **1 seul index FAISS unifié** ; l'alternative « N index FAISS séparés (1 par domain) » est explicitement **rejetée** pour « overhead latence et complexité retrieval » (`docs/DECISION_LOG.md:2398-2401` env., section « Alternatives rejetées » point 3). |

Corpus au moment d'ADR-048 : `formations.json` 48 914, `metiers_corpus.json` 1 075, `parcours_bacheliers_corpus.json` 151, `apec_regions_corpus.json` 13 = **50 153 records / 4 domains** (`docs/DECISION_LOG.md` table dans ADR-048).

## 1.3 Reranker domain-aware (ADR-049) — l'ADR qui justifie les boosts

| ADR | Date | Fichier:ligne | Rationale |
|---|---|---|---|
| **ADR-049** — Reranker multi-domain aware (statut **DRAFT**, jamais passé ACCEPTED) | 2026-04-25 | `docs/DECISION_LOG.md:2421` | Les records annexes arrivent dans le top-50 FAISS mais sont **poussés hors du top-10 final par le reranker** formation-centric, donc on ajoute des boosts conditionnels par intent détecté. |

Mesure qui a déclenché l'ADR (`docs/DECISION_LOG.md:2429-2440`) :
- bench v5 sur 18 queries v4 : multi-corpus activé sur **1/18** queries
- bench multi-domain dédié, **8 queries non-formation-centric** (PR #62) : **6/8 (75 %)** activent le multi-corpus côté FAISS
- **0/2 queries APEC** (a1 « marché cadres Bretagne », a2 « régions cadres bac+5 informatique ») ne récupèrent de record `apec_region` dans le top-10 final
- **smoke test FAISS L2 direct** sur les mêmes queries APEC : **8/10 records `apec_region`** → le delta vient du reranker, pas de FAISS
- gain net notation humaine bloqué : **+0,375/25** (`docs/DECISION_LOG.md:2478-2481`)

Table des boosts suggérés dans l'ADR (`docs/DECISION_LOG.md:2450-2456`) : `apec_region` ×1.5, `metier` ×1.3, `parcours_bacheliers` ×1.3, intent ambigu = 1.0.

Valeurs réellement en prod aujourd'hui (`src/rag/reranker.py:44-78`) : `apec_region` 1.5, `metier` 1.3, `metier_detail` 1.4, `parcours_bacheliers` 1.3, `crous` 1.4, `insee_salaire` 1.5, `insertion_pro` 1.4, `competences_certif` 1.5, `formation_insertion` 1.4, `metier_prospective` **1.0**. Le pipeline est décrit comme « Reranker domain-aware (ADR-049, **17 boosts** incluant cross-boost métier) » dans `docs/PIPELINE_v4_1_FLAGS.md:23`.

## 1.4 Neutralisation Vague 0.5 des boosts de labels (SecNumEdu / CTI / CGE)

Pas d'ADR dédié — la décision est documentée dans le code et un handoff :

- `src/rag/reranker.py:6-22` : audit Phase 0 v5 mesure **SecNumEdu 21 fiches sur 47 193 = 0,04 %**, **CTI 7 fiches = 0,01 %**, **total signal mort à 0,06 %** ; les boosts ×1.5/×1.3 étaient donc « appliqués sur du vide ». Valeurs shippées : `secnumedu_boost = 1.0`, `cti_boost = 1.0`, `grade_master_boost = 1.0`, `public_boost = 1.1` (couverture statut Public jugée suffisante).
- `docs/SESSION_HANDOFF_2026-05-08_VERROUILLAGE.md:180` : « la Vague 0.5 a neutralisé ces boosts à 1.0 (commits `ab51cd8` / `7adb070` du 2026-05-08 — couverture 0.06 % du corpus = signal mort) ». Action de vérification runtime listée en `docs/SESSION_HANDOFF_2026-05-08_VERROUILLAGE.md:216` (B'.1).
- Conséquence narrative : la « thèse INRIA » du reranker par labels officiels (ADR-002) est **empiriquement morte** ; c'est écrit noir sur blanc dans le commentaire de code, pas dans un ADR.

## 1.5 Boost DARES 1.5 → 1.1 → 1.0

Pas d'ADR numéroté ; verdict de bench dédié : `docs/VERDICT_BENCH_DARES_DEDIE.md` (date 2026-04-26, ordre Jarvis 2026-04-26-1100). Rationale codée : `src/rag/reranker.py:61-68`. Chiffres au point 2.4 ci-dessous.

## 1.6 ADR-058 — double-index + BM25 + RRF (l'ADR central de mesure du retrieval)

| ADR | Date | Fichier:ligne |
|---|---|---|
| **ADR-058** — Retrieval hybride double-index + BM25 + RRF (workaround Phase C) | 2026-05-08 | `docs/DECISION_LOG.md:3513` |

Rationale en une phrase : le pré-processing texte des corpora annexes est sémantiquement mal aligné avec les questions naturelles d'un lycéen (`"CROUS Lyon | Logements: 12000 | Restaurants: 25"` tombe dans la zone « base de données structurée »), donc on ajoute un retrieval lexical + une séparation d'index en attendant la vraie fix (ré-écriture des textes annexes en V2).

Composants et chiffres :
- **Couche 1, double-index dense** (`docs/DECISION_LOG.md:3549-3555`) : split de l'index unifié via `index.reconstruct()` en `_main_subindex` **33 776 fiches sans `domain`** et `_annex_subindex` **13 417 fiches avec `domain`** ; runtime **top-100 main + top-30 annex**.
- **Couche 2, BM25** (`docs/DECISION_LOG.md:3557-3563`) : `rank_bm25`, lazy build sur `text` + champs identifiants, **top-50** au runtime.
- **Fusion RRF** (`docs/DECISION_LOG.md:3565-3569`) : `rrf_score(d) = Σ 1/(60 + rank)`, Cormack et al. 2009.
- Constantes prod correspondantes : `src/rag/pipeline.py:93-94` (`DOUBLE_INDEX_K_MAIN = 100`, `DOUBLE_INDEX_K_ANNEX = 30`), `src/rag/pipeline.py:114-115` (`BM25_TOP_K = 50`, `RRF_K = 60`).
- **Diagnostic explicite** : « Le problème **n'est pas** : FAISS, l'index unifié vs séparé, `classify_domain_hint`. Le problème **est** : format des `text` annexes, absence de retrieval lexical pour entités nommées » (`docs/DECISION_LOG.md:3540-3542`).
- **Statut assumé** : workaround temporaire, vraie fix = ré-rédaction des 13 417 textes annexes via Mistral, coût estimé **~$5 total** (`docs/DECISION_LOG.md:3600-3620`). Handoff complet : `docs/HANDOFF_REWRITE_ANNEX_TEXTS.md:1-25`.
- Critères de réouverture : spot-check post-V2 **≥ 11/13**, `honesty = 1.0`, coût ≤ $10 (`docs/DECISION_LOG.md:3643-3648`).

## 1.7 Quota annexes

Pas d'ADR dédié ; c'est le « Option C v6 » codé et référencé dans ADR-058 (`docs/DECISION_LOG.md:3658` : `_retrieve_with_annex_quota` orchestre dense + BM25 + RRF ; `docs/DECISION_LOG.md:3660` : `tests/test_pipeline_annex_quota.py` 7 tests).

Constantes (`src/rag/pipeline.py:85-113`) :
- `ANNEX_QUOTA_K_INITIAL = 150` (k retrieve sur l'index unifié)
- `ANNEX_QUOTA_MIN_SCORE = 0.6` (seuil d'éligibilité au quota)
- `ANNEX_QUOTA_MAX_PER_TOPK = 3` (max d'annexes boostées dans le top-K final)
- `ANNEX_QUOTA_SCORE_BOOST = 1.0` (boost **additif** ; commentaire `src/rag/pipeline.py:109-112` : « une annexe à 0.5 boostée à 1.5 dépasse n'importe quelle formation sans hint domain (max ~1.10) »)

Résumé prod du mécanisme : `docs/REVUE_MODE_RECIT_2026-06-13.md:134-136` — « Le retrieval prod = Option C v6 (k=150, séparation main/annex, quota adaptatif max 3 annexes dans le top-K, seuil score 0.6) OU quad-subindex si RouterLLM route ».

## 1.8 Quad sub-index et RouterLLM — ADR-064 et ADR-065 N'EXISTENT PAS

C'est le trou de traçabilité le plus net du dossier.

- `src/rag/pipeline.py:95-102` : « Étape 5 refonte (2026-05-09) — Quad sub-index par groupes de domaines. Partition fine de l'index unifié en 4 groupes (formations/metiers/statistiques/aides_territoires) pour routing piloté par RouterLLM. **Cf scripts/build_quad_subindexes.py + ADR-065 (à créer)** ». `QUAD_INDEX_K_PER_SUB = 50` (`src/rag/pipeline.py:101`).
- `scripts/build_quad_subindexes.py:37` : « Cf docs/ADR-065-quad-subindexes-partition.md (**à créer**) ».
- `src/rag/router_llm.py:13` : « Cf docs/ADR-064-router-llm-leger.md, docs/ADR-065-quad-subindexes-partition.md ». Idem `src/rag/metadata_filter.py:115`, `src/rag/router_fallback.py:19`, `src/state/route_decision_schema.json:5`.
- Vérification : `ls docs/ADR-06*` → **aucun fichier**. Le `DECISION_LOG.md` s'arrête à **ADR-062** (`docs/DECISION_LOG.md:3985`). Les seuls ADR-060..063 « prévus » sont une intention listée dans `docs/SESSION_HANDOFF_2026-05-08_VERROUILLAGE.md:279`.
- Conclusion : **les 6 index FAISS (2 du double-index + 4 du quad) et le RouterLLM ne sont couverts par aucun ADR**. Justification uniquement en docstrings + rapports.

Mapping des 4 groupes du quad (`scripts/build_quad_subindexes.py:57-77`) : `formations` (domain vide, `formation_insertion`, `voie_pre_bac`), `metiers` (`metier`, `metier_detail`, `metier_prospective`), `statistiques` (`insee_salaire`, `insertion_pro`, `parcours_bacheliers`, `apec_region`), `aides_territoires` (`crous`, `financement_etudes`, `territoire_drom`, `competences_certif`, `calendrier`, `correction_factuelle`).

RouterLLM, ce qu'on a comme justification (à défaut d'ADR) :
- `src/rag/router_llm.py:1-14` : Mistral Small + `tool_choice="any"` + 1 tool `decide_route` ; décide (a) sub-index interrogés, (b) FilterCriteria, (c) refus structuré, (d) hardlocks prompt R7, (e) override `top_k_sources`.
- `src/rag/router_llm.py:33-45` : `SUB_INDEX_NAMES = (formations, metiers, statistiques, aides_territoires)`, `REFUSAL_REASONS = (superlative_no_data, cross_domain, out_of_scope_specific)`.
- `docs/METHODOLOGY.md:12-16` : pipeline courant = **47 214 fiches, 4 sub-indexes**, `ScopeClassifier → RouterLLM → hybrid retrieval (FAISS dense + BM25 + RRF) → reranker + MMR → generator`.
- `docs/BENCHMARK_PHASE_D_2026-05-11.md:159` : « RouterLLM (Mistral Small, format JSON-tool) — choisit les sous-index ».
- Usage par ADR-060 : `docs/DECISION_LOG.md:3796` et `:3850` (refus `superlative_no_data`).
- ADR-061/062 mode récit : l'extraction de profil **remplace le RouterLLM** (`docs/DECISION_LOG.md:3904`, motif latence : un appel LLM séquentiel en moins ; discussion en `docs/REVUE_MODE_RECIT_2026-06-13.md:84-90`), et l'extension du RouterLLM est explicitement rejetée en `docs/DECISION_LOG.md:3963`.
- Latence mesurée du routeur : `step_2_router_llm`, n=13, **avg 0,58 s / médiane 0,55 s / max 7,48 s** (`docs/OBSERVABILITY_BASELINE_2026-05-13.md:77`).

---

# 2. Toutes les mesures chiffrées de retrieval

## 2.1 Spot-check 13 questions (le set « Gate 3 », domaines annexes) — n_domain_match_top5

Set : 13 questions ciblées sur les corpora annexes (CROUS, DARES, INSEE, parcours_bacheliers, doctorat IP). Critère : ≥1 fiche du domain attendu dans le top-5.

| Date | Config | Valeur | Fichier:ligne |
|---|---|---|---|
| 2026-05-07 | v5 | **4/13** | `docs/SPOT_CHECK_V5_2026-05-07.md:9` |
| 2026-05-08 | baseline v3.2 (dense FAISS k=30 unifié) | **4/13 (31 %)** | `docs/DECISION_LOG.md:3575` |
| 2026-05-08 | quota adaptatif seul (k=150 + boost) | **5/13 (38 %)** | `docs/DECISION_LOG.md:3576` |
| 2026-05-08 | double-index seul | **5/13 (38 %)** | `docs/DECISION_LOG.md:3577` |
| 2026-05-08 | **double-index + BM25 + RRF** | **8/13 (62 %)** | `docs/DECISION_LOG.md:3578` |
| 2026-05-08 | corpus/index v6 | **11/13** | `docs/SPOT_CHECK_V5_2026-05-08.md:9` |
| 2026-05-10 | v5 | **5/13** | `docs/SPOT_CHECK_V5_2026-05-10.md:9` |
| 2026-05-11 | v5 | **4/13** | `docs/SPOT_CHECK_V5_2026-05-11.md:9` |
| 2026-05-13 | v5 pre-chantier C+ | **4/13** | `docs/SPOT_CHECK_V5_2026-05-13.md:9` ; confirmé sous Langfuse `docs/OBSERVABILITY_BASELINE_2026-05-13.md:9` (Q3, Q6, Q8, Q11 passent) |
| 2026-05-13 | post-chantier C+ | **8/13** | `docs/SPOT_CHECK_V5_2026-05-13-post-chantier-c-plus.md:9` ; diff `docs/OBSERVABILITY_DIFF_PRE_POST_2026-05-14.md:11` (**4/13 → 8/13, ×2,0**) |
| 2026-05-14 | post-fix Q11 (PR #138) | **9/13** | `docs/SPOT_CHECK_V5_2026-05-14-post-q11-fix.md:9` ; `docs/FUTURE_PHASES_2026-05-18.md:17` |

Attention méthodologique : la série est **incohérente entre le 08/05 (11/13 sur v6) et le 11/05 (4/13 sur v5)** — corpus/index différents, jamais réconciliés dans un document unique.

Détail par question pre/post C+ (`docs/OBSERVABILITY_DIFF_PRE_POST_2026-05-14.md:44-58`) : Q01 `metier_prospective` 0/5→5/5, Q02 `crous` 0/5→5/5, Q03 `competences_certif` 5/5→5/5, Q04 `insertion_pro` 0/5→0/5, Q05 `metier_detail` 0/5→2/5, Q06 `financement_etudes` 5/5→5/5, Q07 `territoire_drom` 0/5→0/5, Q08 `apec_region` 1/5→1/5, Q09 `insee_salaire` 0/5→5/5, Q10 `formation_insertion` 0/5→0/5, **Q11 `voie_pre_bac` 1/5→0/5 (régression)**, Q12 `parcours_bacheliers` 0/5→5/5, Q13 `insertion_pro` 0/5→0/5.

Cible d'origine du sous-instrument : `n_domain_match_top5 ≥ 1` pour Q1, Q2, Q4, Q5, Q7, Q9, Q10, Q12, Q13, cible **11-13/13** (`docs/OBSERVABILITY_BASELINE_2026-05-13.md:110`).

## 2.2 % top-5 = `(formation)` (métrique de bruit)

Même set 13 questions, 2026-05-14 :
- **60,7 % → 24,6 %**, soit **-36,1 pp**, cible <30 % : `docs/OBSERVABILITY_DIFF_PRE_POST_2026-05-14.md:12` et `docs/OBSERVABILITY_SYNTHESIS_2026-05-14.md:14`
- valeur en comptages bruts : 34 fiches sur 56 → 15 (`docs/OBSERVABILITY_DIFF_PRE_POST_2026-05-14.md:31`)
- après PR #138 : **~22 %** (`docs/FUTURE_PHASES_2026-05-18.md:31`)

Distribution complète des top-5 pre → post (`docs/OBSERVABILITY_DIFF_PRE_POST_2026-05-14.md:31-43`) : `insee_salaire` 0,0 %→11,5 %, `metier` 8,9 %→9,8 %, `competences_certif` 8,9 %→8,2 %, `crous` 0,0 %→8,2 %, `financement_etudes` 8,9 %→8,2 %, `insertion_pro` 8,9 %→8,2 %, `metier_prospective` 0,0 %→8,2 %, `parcours_bacheliers` 0,0 %→8,2 %, `metier_detail` 0,0 %→3,3 %, `apec_region` 1,8 %→1,6 %, `voie_pre_bac` 1,8 %→0,0 %.

## 2.3 recall@k — `scripts/eval_recall.py` sur `golden_50.json` / `golden_60.json`

**Set golden_50, 50 questions, 2026-05-08** (`results/eval_recall/v6_baseline_2026-05-08.json`) :
- global : recall@1 **0,38**, **recall@5 0,70**, recall@10 **0,74**, MRR **0,484**, latence moyenne 6,78 s
- **`calendaire` (n=5) : recall@1 = 0,0, recall@5 = 0,0, recall@10 = 0,0, MRR = 0,0** ← le fameux « recall@5 calendaire 0 % »
- `geographique` (n=10) 0,4 / 0,8 / 1,0 ; `lyceen_parcoursup` (n=10) 0,0 / 0,8 / 0,8 ; `metier` (n=10) 0,6 / 0,6 / 0,6 ; `reorientation` (n=10) 0,7 / 0,8 / 0,8 ; `vie_etudiante` (n=5) 0,4 / 1,0 / 1,0

**Set golden_50, 50 questions, corpus/index v7, 2026-05-08 15:57** (`results/eval_recall/v7_post_fixes.json`) :
- global : recall@1 **0,48**, **recall@5 0,80**, recall@10 **0,84**, MRR **0,584**, latence 5,34 s
- **`calendaire` passe à 1,00 / 1,00 / 1,00** (corpus calendrier ajouté)
- toutes les autres catégories strictement identiques au baseline v6 (geo 0,8, lyceen 0,8, metier 0,6, reorient 0,8, vie_etu 1,0) → **le gain global +10 pp est intégralement porté par les 5 questions calendaires**

`results/eval_recall/v7_post_vague_3.json` (2026-05-08 15:09) : chiffres identiques à v7_post_fixes sur recall, seule la latence/`answer_kw_match` bougent.
`results/eval_recall/sample5_test.json` : 5 questions, recall@5 0,6, MRR 0,2 (run de smoke).

**Set golden_60 v3.1, 65-71 questions, Phase D, 2026-05-11** (`docs/BENCHMARK_PHASE_D_2026-05-11.md:236-244`) :
- recall@1 **0,606**, **recall@5 0,648 (cible ≥0,75 → FAIL marginal)**, recall@10 **0,648 (cible ≥0,85 → FAIL)**, **MRR 0,723 (PASS)**, **nDCG@10 0,725 (PASS)**, `answer_keyword_match` 0,930
- par catégorie (`docs/BENCHMARK_PHASE_D_2026-05-11.md:254-268`) : `calendaire` n=5 **1,00**, `paraphrase` n=2 **1,00**, `vie_etudiante` n=5 0,80, `vie_etudiante_periph` n=5 0,80, `metier` n=10 0,70, `lyceen_parcoursup` n=10 0,60, `geographique` n=10 0,60, `adversarial` n=10 0,60, `live` n=2 0,50, **`reorientation` n=10 0,50 / MRR 0,40 (point faible)**, `cross_domain` n=2 0,00
- diagnostic attaché : « le RouterLLM achemine probablement ces requêtes vers le sous-index `metiers` au lieu du sous-index `statistiques` » (`docs/BENCHMARK_PHASE_D_2026-05-11.md:269-274`)
- latence Gate 3 : p50 5,75 s, p95 11,24 s (`docs/BENCHMARK_PHASE_D_2026-05-11.md:277-280`)

**Gates cibles** (`docs/BENCH_GATES.md:17-18`, `:69-70`) : recall@5 global ≥ **75 %** (référence Vague 3.4 : 70 → 80 % sur golden_50, commit `0119400`), recall@5 par catégorie ≥ **60 %**, recall@1 ≥ 50 %, recall@10 ≥ 85 % (« si <85 %, le retrieval est cassé »).

## 2.4 BM25 recall@30 = 5/8 (sonde de l'audit empirique juin)

`audit_empirique_2026-06-09/L2-Harnais-eval.md:43-53`. Set : 8 questions ciblant une formation nommée, proxy lexical BM25 déterministe (`recall_probe.py`), sans API. Date 2026-06-09/11.

- **BM25 recall@30 = 5/8**
- trouvées : BUT Info IUT Lyon 1 (**rang 1**), licence droit Dauphine (rang 1), INSA Lyon (rang 1), licence psycho (rang 1), prépa MPSI lycée du Parc (rang 4)
- manquées : **BUT Info IUT Bourges, BTS SIO SLAM, BUT TC IUT Annecy**
- lecture croisée : « le BUT Info Lyon 1 est trouvé au rang 1 mais REFUSÉ par le pipeline (sur-refus en aval, pas un problème de retrieval) […] il y a un problème de retrieval ET un problème de gating en aval qui jette des cibles pourtant trouvées » (`audit_empirique_2026-06-09/L2-Harnais-eval.md:51`)
- limite assumée : « proxy lexical sur 8 cibles, pas un recall@k complet sur un set de pertinence labellisé » (`:53`, repris `:80`)
- cible de gating proposée : **recall@5 ≥ 0,85** (`audit_empirique_2026-06-09/L2-Harnais-eval.md:71`)

## 2.5 Ragas — context_recall et faithfulness

Set : **50 entrées de `golden_qa_v1.jsonl`**, stratifiées sur 5 catégories, juge `mistral-small-latest` T=0, date 2026-05-14 (`docs/OBSERVABILITY_SYNTHESIS_2026-05-14.md:5`).

- **context_recall global = 0,021**, **92 % des questions < 0,1**, 0 % au-dessus de 0,5 (`docs/OBSERVABILITY_SYNTHESIS_2026-05-14.md:16` et `:79-86`)
- par catégorie (`:58-66`) : `lyceen_post_bac` n=10 → 0,043 ; `etudiant_reorientation` n=11 → 0,011 ; `actif_jeune` n=10 → 0,021 ; `master_debouchés` n=10 → 0,021 ; `famille_social` n=9 → 0,009
- faithfulness global **0,489**, bimodale : 16 % en [0,9–1,0], 10 % [0,7–0,9], 20 % [0,5–0,7], 22 % [0,3–0,5], **32 % [0,0–0,3]** → 26 % fidèles ≥0,7, 54 % <0,5 (`:68-76`)
- **verdict sur la métrique** : artefact de protocole, la `ground_truth` est générée par claude-opus-4-7 à partir de sources web (onisep.fr, parcoursup.gouv.fr), **pas du corpus FAISS** (`docs/OBSERVABILITY_SYNTHESIS_2026-05-14.md:89`) ; à remplacer par `context_precision` + `answer_relevancy` (`:92-94`, `:149`)
- même verdict repris en `docs/FUTURE_PHASES_2026-05-18.md:55` (tâche 2.1, 1 h ingé, ~$3) et `CLAUDE.md:146`
- **context_precision n'a jamais été mesurée** : c'est une tâche planifiée, pas un résultat. Aucun chiffre nulle part.
- coût du bench Ragas : **$0,30** ; bench Langfuse $0,04 × 2 (`docs/OBSERVABILITY_SYNTHESIS_2026-05-14.md:20-21`)
- cross-validation Langfuse ↔ Ragas : « le retrieve a fait un grand pas avec C+, mais la chaîne retrieve → generation a un trou intermédiaire » (`:129-137`)

## 2.6 Couverture domain_hint = 46 %

- `docs/DECISION_LOG.md:3554` : « Indépendant du `classify_domain_hint` (**couverture mesurée 46 %** — symptôme, pas cause) »
- `docs/DECISION_LOG.md:3593` : « **Indépendant du domain_hint (46 % jugé insuffisant pour gating)** »
- contexte structurel : le pipeline expose 12 `domain_hint` distincts (`docs/DECISION_LOG.md:3344`, `:3418`)
- attention au faux ami : les « 46 % » de `docs/OBSERVABILITY_MULTI_AXIS_2026-05-13.md:34` et `docs/OBSERVABILITY_POST_FIX_2026-05-14.md:30` sont **6/13 refus détectés**, pas la couverture domain_hint. Deux 46 % sans rapport.

## 2.7 Effet mesuré des boosts

### Bench DARES dédié, phase C, boosts 1.5 / 1.1 / 1.0

Set : **10 queries prospectives** calibrées pour activer le domain hint `metier_prospective`, design A/B phaseB (sans DARES) vs phaseC, date 2026-04-26, coût ~$0,05. Source : `docs/VERDICT_BENCH_DARES_DEDIE.md`. Artefacts : `results/bench_dares_dedie_2026-04-26_phaseB/`, `..._phaseC_dares_boost_1_0/`, `..._1_1/`, `..._1_5/`.

| Variant | verified | halluc | only_DARES_topK | formation_topK |
|---|---:|---:|---:|---:|
| phaseB (baseline, sans DARES) | **37,7 %** | **15,6 %** | 0/10 | 10/10 |
| phaseC ×1.5 (PR #70 mergé) | **7,2 %** | **39,8 %** | 8/10 | 2/10 |
| phaseC ×1.1 (iter 1) | 28,0 % | 19,4 % | 6/10 | 4/10 |
| **phaseC ×1.0 (shipped)** | **22,3 %** | **17,5 %** | **4/10** | **5/10** |

(`docs/VERDICT_BENCH_DARES_DEDIE.md`, table « Trio de résultats »)

Autres chiffres du même verdict :
- métriques agrégées ×1.5 : stats fact-check 122 → 83, verified 46 → 6, hallucinated 19 → 33, **-30,5 pp verified / +24,2 pp halluc**, gen time 11,98 s → 12,34 s, `metier_prospective` dans top-K **0/10 → 9/10**
- ×1.0 résout **49 % de la régression** (delta verified −30,5 pp → −15,4 pp), halluc **+1,9 pp** seulement
- **floor architectural** : « même à ×1.0 (boost désactivé, ranking = pure L2 distance), **4/10 queries voient leur top-10 = 100 % cells DARES** sans aucune fiche formation » → limite non franchissable par tuning de boost
- caveat : les 10 queries sont un **upper-bound du périmètre activable**, pas une mesure user-naturelle
- corpus DARES : **111 cells** (98 FAP-France + 13 région × top-FAP) dans 49 406 vecteurs
- cohérence avec le triple-run nuit : sur 18 queries personas v4 formation-centric, boost **dormant 0/18**, effet neutre → « DARES ne nuit pas aux queries formation, mais nuit fortement aux queries prospectives — soit exactement le périmètre où il devrait apporter de la valeur »
- rationale finale codée : `src/rag/reranker.py:61-68`

### Bench personas v5 dedupe + reranker (ADR-049)

Set : **18 queries personas v4 formation-centric**, date 2026-04-25 PM. Source : `results/bench_personas_v5_dedupe_reranker_2026-04-25/_SYNTHESIS_RERANKER.md`.

| Métrique | v4 (17q) | v5 actuel | v5 dedupé | **v5 dedupé+reranker** |
|---|---:|---:|---:|---:|
| Précision factuelle /5 | 4,53 | 3,89 | 3,83 | **4,11** (zone ambiguë) |
| Pertinence | 4,71 | 4,78 | 4,78 | 4,78 |
| Personnalisation | 4,18 | 4,44 | 4,44 | 4,44 |
| Safety | 5,00 | 4,67 | 4,61 | 4,78 |
| Verbosité | 4,47 | 4,33 | 4,44 | 4,39 |
| MOY globale /5 | **4,57** | 4,42 | 4,42 | **4,50** |
| Verified (fact-check) | 47,3 % | 42,9 % | 46,1 % | **47,2 %** |
| Hallucinated | 11,6 % | 15,2 % | 21,2 % | **8,1 %** |
| Disclaimer | 41,1 % | 41,8 % | 32,7 % | 44,7 % |
| Stats totales | 207 | 184 | 217 | 197 |

**Activation multi-corpus top-10** : v5 actuel **1/18** (Q4 droit), v5 dedupé **1/18**, v5 dedupé+reranker **2/18** (Q4 droit + Q18 aéro→metier). « Sur les 18 queries v4 formation-centric : la majorité (16/18) reste 100 % formation comme attendu. »

Verdict : zone ambiguë (précision 4,11 dans la bande [3,95 ; 4,30], seuil GO 4,30 non atteint) ; le reranker apporte **+0,28 de précision vs v5 dedupé pur** et **-3,5 pp d'hallucination vs v4**.

### Autres activations mesurées de domain hint (18 queries personas v5++)

`docs/DATA_INVENTORY_2026-04-26.md` : `parcours_bacheliers` confirmé sur **1/18** (`:91`), `apec_region` **2/18** (`:103`), `insee_salaire` **1/18** (`:129`), `insertion_pro` **1/18** (`:142`), DARES blocs **2/18** via L2 brute sans regex (`:176`), triple-run DARES **0/18 activations** (`:156`).

## 2.8 Taux d'échec attribué au retrieval — le fameux 73 %

`audit_empirique_2026-06-09/L3-Audit-data.md:12` (Claudette, 2026-06-09, ordre 2026-06-09-1030) :

> « L'état de l'art 2026 et les observations empiriques convergent : quand un RAG échoue, c'est le retrieval/la data **~73 % du temps**, pas la génération. »

**Ce n'est PAS une mesure OrientIA.** C'est une statistique d'état de l'art citée sans source, utilisée comme argument pour prioriser l'audit data. Le même paragraphe ajoute « La batterie L1 le confirme », mais la batterie L1 mesure autre chose (modes d'échec qualitatifs). Aucun autre « 73 % » du repo n'est lié au retrieval (tous les autres sont « sélectivité 27 % / 73 % mentions TB », une hallucination récurrente du LLM, ex. `results/audit_post_purge_prompt_2026-05-05.md:36`).

Attribution réelle mesurée, elle, dans le même audit :
- `audit_empirique_2026-06-09/QUEUE_22q_souszero7_2026-06-11.md` : sur les **22 réponses <0,7 groundedness** du gel 497q, la répartition des causes racines est **~14/22 GÉNÉRATION (over-élaboration)**, **1/22 GÉNÉRATION+RETRIEVAL** (`fact-015-v3`, ranking CPGE-ville), 1 GÉNÉRATION+DATA, 3 JUDGE/DATA, 3 JUGE (faux positifs / incohérences). Donc **le retrieval est cause primaire dans ~1 cas sur 22, pas 73 %**.
- `audit_empirique_2026-06-09/L1-Batterie-empirique.md:38-52` : sur 42 questions, hallucination de chiffres **2/42 (~5 %)**, groundedness moyenne des réponses affirmatives (n=17) **0,766**, **refus 31 %** ; l'échec n°1 est le **sur-refus**, avec preuve explicite que ce n'est pas du retrieval (« la sonde recall trouve cette formation au rang 1 du BM25 »).
- `audit_empirique_2026-06-09/RAPPORT_bench_e2e_1403_2026-06-14.md:13-14` (bench 2026-06-14, golden 50q) : **recall source 17/17 (100 %), non régressé** ; « recall domain **14/30** = report non-bloquant, **instrument ambigu connu** ».

**Conclusion du point 2.8** : il existe une tension nette entre le cadrage « le retrieval est le suspect n°1 à 73 % » (emprunté à l'état de l'art) et les mesures internes qui pointent la génération et le gating aval.

---

# 3. État du set de pertinence lot 2

Source primaire : `scripts/relevance_set/STATE.md` (checkpoint pré-clear du 16/07 ~19 h, ordre 2026-07-16-0905 lot 2 sous-chantier 1, branche `feat/h1-lot2-relevance-set`).

## 3.1 Ce qui est fait

- **`mine_candidates.py`** : mining **tri-modal** (dense FAISS top-20 + BM25 top-20 + lexical déterministe top-15, explicitement anti-biais retrieval) sur les **387 questions retrieval-pertinentes** du banc 497q + 3 questions MIAGE. Exécuté : `candidates.json` = **387 questions, 9 092 candidats, médiane 21/question** (`STATE.md:7-11`). Vérifié : `candidates.json` contient bien 387 entrées et 9 092 candidats.
- **`batches/`** : **26 lots** de ~15 questions pour la flotte de juges (`STATE.md:12`). Vérifié : `batch_00.json` … `batch_25.json`.
- **`src/eval/relevance_metrics.py` + `tests/test_relevance_metrics.py`** : 11 tests verts ; recall@k (grade 2 uniquement, `none_relevant` hors dénominateur) + nDCG@k (gains gradués, `None` si pas de vérité terrain — « jamais de 0 fabriqué ») (`STATE.md:13-16`).
- **`eval_retrieval.py`** : runner 2 modes — `--mode raw` (retrieve+rerank+MMR sans LLM, gate CI gratuit) et `--mode serving` (`_prepare_for_generation` complet, ~2 appels small/question) (`STATE.md:17-19`). Le runner utilise `retrieve_top_k(..., k=30)` (`scripts/relevance_set/eval_retrieval.py:60`).
- **`labels_partial.json`** : **135/387 questions labellisées**, **9 lots sur 26**, coupure quota session 16/07 18 h 40 (`STATE.md:20-21`).

Contenu vérifié de `labels_partial.json` : `n_questions = 135`, `_meta.lots_juges = "9/26 (coupure quota 16/07)"`, `_meta.run_id = "wf_1e24eb24-ae3"`. **1 172 références de pertinence** au total, réparties en **296 grade 2** et **876 grade 1**, **6 questions marquées `none_relevant`**.

## 3.2 Le bug `idx:-1`

- Symptôme : `fiche_id = "idx:-1"` pour **382 des 9 092 candidats**, avec **79 références dans les labels partiels** (`STATE.md:25-26`). Vérifié empiriquement : 382 candidats `idx:-1` dans `candidates.json`, **79 refs `idx:-1` réparties sur 79 des 135 questions labellisées** (une par question, systématiquement en tête et souvent **grade 2**, ex. `fact-016` dont le seul grade 2 est un `idx:-1`).
- Cause : branche dense de `mine_candidates.py`, ligne `fid = _fiche_id(fiche, index_by_fid.get(...))` — fallback défaillant quand la fiche n'a pas de champ `id` (`STATE.md:26-30`).
- Gravité réelle : comme le `idx:-1` est fréquemment le candidat noté **grade 2** (la cible pertinente), **le recall@k calculé sur `labels_partial.json` en l'état serait faux sur ~59 % des questions labellisées** (79/135). Le set n'est donc pas exploitable pour une baseline.
- `_meta.bug_connu` : « fiche_id 'idx:-1' = bug du miner (fallback dense), labels concernés à rejuger après fix ».

## 3.3 Ce qui reste à faire (ordre imposé par STATE.md:23-46)

1. **Corriger le bug miner AVANT de relancer les juges** : construire `index_by_id` une fois (`id(fiche_objet) → index corpus`) ou porter l'index de position dans le retour de `retrieve_top_k`. Puis **re-miner** (supprimer `candidates.json` d'abord, le mining est resume-safe), re-découper les batches, et **invalider les labels `idx:-1`** (les 135 questions restent valides sauf leurs refs `idx:-1` à rejuger).
2. **Relancer la flotte de juges** : workflow `resumeFromRunId "wf_1e24eb24-ae3"`, script `~/.claude/projects/-home-matteo-linux-projets-OrientIA/e71761f5-.../workflows/scripts/label-relevance-set-wf_1e24eb24-ae3.js`. Avertissement : si les batches changent, le cache tombe → lancer un run neuf et fusionner avec `labels_partial.json` en purgeant les refs `idx:-1`.
3. **Assembler `labels.json` complet → baseline** : `eval_retrieval.py --mode raw` (gratuit) puis `--mode serving` (~0,5 EUR small). « Pinger la baseline recall@5/nDCG@10 à Jarvis (il l'attend explicitement). »
4. **Gate CI** : test type golden (skip si index absent), branché dans `.github/workflows` sur le pattern golden-ci existant.

## 3.4 Extension de scope lot 2 (Jarvis 16/07 ~19 h 20, `STATE.md:48-56`)

(a) données **coûts de scolarité** (frais universités vs écoles privées) ; (b) fiches **CONCEPT génériques** (BUT vs BTS, PASS/LAS, alternance) car les questions génériques reçoivent des réponses par instances ; (c) **GEO = priorité 1 du retrieval** (« le récit Nantes a comparé Draguignan et Paris, verdict INFIDÈLE — LE raté de la session utilisateur de Jarvis »). S'ajoute au scope existant : ADR-058 re-embed, routing salaire MIAGE, multi-tour standalone-rewrite, reranker domain/domaine + cross-encoder.

## 3.5 Observations tirées des labels partiels (`STATE.md:58-66`) — importantes pour l'interprétation

- « Beaucoup de `none_relevant`/grade-1-seulement sur les factuelles précises : les stats fines (salaire médian par formation-ville, insertion à 6 mois par ville) **n'existent souvent PAS dans le corpus au grain demandé** → **une part des refus est de la DATA manquante, pas du retrieval raté** ».
- « Le juge de `fact-001` confirme le finding live : **"BUT Informatique à Lyon" → dense#1 = Martinique**, aucun BUT Info lyonnais dans les candidats. »

---

# 4. Documents qui listent les défauts du retrieval / attribuent les échecs au retrieval

## 4.1 `results/jarvis_analyse_2026-09-05/` — VIDE

Le répertoire ne contient **qu'un seul fichier**, `results/jarvis_analyse_2026-09-05/smoke.py` (créé le 4 sept. 23:52), 21 lignes : un script de smoke test qui charge `formations.json`, construit le pipeline de production avec `ORIENTIA_NARRATIVE_MODE=1`, pose une question par défaut (« terminale générale spé maths et physique à Lyon… ») et imprime la réponse + les 10 premières sources. **Aucun résultat, aucun rapport, aucune analyse n'y a été écrit.**

## 4.2 `docs/LIMITATIONS.md` — section 11, bugs runtime live 2026-05-12

- **§11.2 « Sub-index `aides_territoires` mal proportionné » (`docs/LIMITATIONS.md:216-228`)** — le défaut de retrieval le mieux documenté du projet :
  - symptôme : « quelles sont les crous à Paris ? » → refus, alors que la fiche CROUS Paris existe avec `retrieval_eligible=True`
  - cause : le sub-index `aides_territoires` (**4 979 vecteurs**) est composé à **98 % de fiches `competences_certif` (4 891 fiches RNCP)** ; les **18 fiches CROUS** sont noyées ; le **top-50 FAISS du sub-index retourne 47 `competences_certif` + 3 `financement_etudes`, zéro CROUS**
  - sur l'index global (**47 220 vecteurs**), la fiche CROUS Paris **n'est pas dans le top-300 dense** (son `text` fait 360 caractères)
  - atténuation appliquée le 12 mai : fallback `quad path → v1 path` quand `n_after_filter == 0` (`docs/LIMITATIONS.md:220`) — ne résout pas, le v1 path renvoie des formations parisiennes
  - 3 fixes structurels listés (`:224-226`) : rebalance du sub-index (sortir `competences_certif`, ramener `aides_territoires` à ≈70 fiches), rebuild des embeddings CROUS avec un `text` plus dense, **activation du BM25 hybride sur le path filter-actif** (« actuellement le path v1 utilise uniquement FAISS dense pour le retrieve filtré »)
- **§11.1 (`docs/LIMITATIONS.md:212-214`)** : validator `corpus_check` Pattern 3 flaggait à tort des paraphrases → BLOCK injustifié (fixé, 235 tests verts)
- **§11.3 (`docs/LIMITATIONS.md:230`)** : désynchronisation de la plateforme prod vs `main`
- Cadre général : `docs/LIMITATIONS.md:41` (métriques recall via `scripts/eval_recall.py`), `:48` (« on ne peut pas démontrer que les Vagues améliorent la rubric externe […] on démontre que recall@k interne progresse »), `:193` (pas de re-bench rubric externe post-Vagues, substitué par recall@k)

## 4.3 `docs/FUTURE_PHASES_2026-05-18.md` — les chantiers retrieval restants

- Cadrage global : « **Le retrieve a été fixé, la génération reste fragile** » (faithfulness Ragas 0,49 bimodale), Phase 2 faithfulness = **bloqueur produit n°1** (`docs/FUTURE_PHASES_2026-05-18.md:44-50`)
- **Chantier D — FilterCriteria niveau auto** (`:126-140`) : « Q10 "Bac pro Industrie" renvoie aujourd'hui des fiches doctorat biologie 2014 du retrieve. La sémantique d'embedding ne discrimine pas correctement les niveaux quand le sujet partage du vocabulaire. » 3-4 h, confiance 75 %.
- **Chantier B — Lookup déterministe par code** (`:142-160`) : « Q3 "RNCP 38450" retourne aujourd'hui RNCP 35298/35307/etc. (voisins sémantiques). Pattern reproductible sur tous codes structurés. » 4-6 h, confiance 80 %.
- **Chantier F — anti-hybridation prospective** (`:100-124`) : régression du 2026-05-13 sur Q1 (métiers Occitanie 2030), le LLM substituait des formations actuelles à des projections.
- **Couverture corpus Q4/Q7/Q10/Q13** (`:172-186`) : 4 questions restent à **0/5** top-5 match malgré C+ ; ce sont des trous de **couverture corpus, pas pipeline** — Q4 Master Droit PACA (608 fiches `insertion_pro`, aucune droit×PACA), Q7 Guadeloupe (16 fiches LADOM ≠ catalogue territorial), Q10 Bac pro Industrie (2 693 fiches Inserjeunes, aucune ne discrimine « Industrie »), Q13 doctorat chimie (608 fiches dominées par doctorat biologie 2014). Effort 1-2 jours par sous-corpus, **1 semaine pour passer de 9/13 à 12-13/13**, priorité **plus basse** que la faithfulness.
- Cold-start : les 40 s de Q01 sont un **warmup générique** (~14 s d'init invisibles à Langfuse), pas un bug retrieval (`:28-34`).

## 4.4 `docs/OBSERVABILITY_BASELINE_2026-05-13.md` — le retrieval n'est pas le bottleneck de latence

- Insight 1 (`:15-21`) : « **Le retrieve n'est PAS le bottleneck moyen (révision)** ». Sur 13 questions, `step_5_retrieve_filter` avg **2,08 s / médiane 0,39 s / max 22,05 s** ; `step_8_generate_with_retry` avg **4,61 s / médiane 4,14 s**. Hors outlier Q01, retrieve moyen **~0,42 s**.
- Insight 2 (`:23-38`) : Q01 = 36,11 s dont **22,05 s de retrieve** ; hypothèses listées dont « quad-subindex retrieve qui rapatrie 0 fiches → fallback v1 → boucle auto-expansion ».
- Insight 3 (`:40-46`) : Q09 brûle **8,94 s** dans un `step_4_select_bypass` qui n'aboutit pas (fuzzy match « PCS 37 » sur 47 193 fiches).
- Insight 4 (`:48-58`) : les fails coûtent **+5,98 s** en moyenne vs les pass, à toutes les étapes.
- Limite instrumentale (`:133`) : pas de sous-instrumentation de `step_5` (embed/FAISS/rerank/BM25/RRF) — on voit le total, pas la décomposition. **On ne sait donc pas quelle couche du retrieval hybride coûte quoi.**

## 4.5 `docs/REVUE_MODE_RECIT_2026-06-13.md` — P8, « le retrieval annexe = le vrai point dur »

`docs/REVUE_MODE_RECIT_2026-06-13.md:133-142` : « Les corpora annexes remontent mal (ADR-058 : textes annexes mal alignés sémantiquement, dette technique actée). Or `insee_salaire` / `insertion_pro` SONT des annexes. Le multi-query récit doit fusionner proprement avec ce mécanisme — et c'est précisément là que ça peut échouer. » Atténuation : après le fix P5, salaire/insertion sont **sur la fiche formation**, donc plus besoin de remonter l'annexe.
Voir aussi `:255` (« Point dur = faire remonter les annexes (ADR-058) ») et `:20`/`:112` (avertissement : « la preuve empirique du plan est mal attribuée » sur le salaire MIAGE).

## 4.6 `audit_empirique_2026-06-09/` — l'audit de juin (celui que tu appelles « juillet »)

Il n'y a pas d'audit daté de juillet 2026 dans le repo ; le corpus d'audit est `audit_empirique_2026-06-09/` (09-14 juin), et le lot 2 relevance set (juillet, 16/07) est le suivi.

- **L3 (`L3-Audit-data.md`)** — trous data qui se lisent comme des défauts de retrieval :
  - `:16` : **47 220 fiches**, **43 185 retrieval-eligible (91,5 %)**, **25 sources**, aucune >17,3 %
  - `:26-36` : région absente **19 805 / 43 185 = 45,9 %** (doc annonçait 41,5 % → « la situation est pire que documentée ») ; **18 012 fiches ont `ville` présent mais vide** — « un filtre géographique naïf les considère comme localisées alors qu'elles ne le sont pas. C'est exactement le type de défaut qui fait échouer silencieusement les requêtes géo »
- **L1 (`L1-Batterie-empirique.md`)** — 5 modes d'échec réels : sur-refus (le plus fréquent, `:44-52`), substitution de métrique (`:54-56`, 4-5 cas), calibrage détresse, etc. Chiffres : hallu chiffres 2/42, groundedness 0,766 (n=17), refus 31 %.
- **L2 (`L2-Harnais-eval.md`)** — le harnais recall (cf. 2.4) et ses limites.
- **`AUDIT_couverture_champs_2026-06-14.md`** — quels champs sont visibles par quel canal de retrieval : `:17` (BM25 lexical via `_fiche_to_search_text`, rebuild local $0), `:125` (`discipline` monmaster 100 % présent dans BM25 + fact_card mais **PAS dans le dense**, car pas dans `fiche_to_text`), `:129` (`codes_rome` dans BM25 mais **pas exposé en filtre**), `:61`/`:108` (`parcours` monmaster 91 % invisible partout).
- **`RAPPORT_bench_e2e_1403_2026-06-14.md:13`** — golden 50q, **recall source 17/17 (100 %)**, **recall domain 14/30** qualifié d'« instrument ambigu connu », « les gains sont ciblés et honnêtes, **pas un lift de retrieval massif** ».
- **`QUEUE_22q_souszero7_2026-06-11.md`** — répartition des causes racines (cf. 2.8).

## 4.7 `results/retrieval_inspection.md` — obsolète

Fichier historique de la Phase F (dev set 32 questions, baseline vs F.3 MMR+intent). Métriques agrégées : distinct villes 2,56 → 2,81 (+0,25), distinct etabs 9,53 → 9,25 (-0,28), labelled fiches 5,31 → 4,75 (-0,56). Utile surtout comme illustration d'un défaut criant : sur A2 « Je veux faire une école de commerce », le top-10 est **intégralement composé de fiches cybersécurité** ; idem B2 (bac pro commerce → médecine), B3 (STI2D → prépa MP), C5, E1, E4, H1, H2. C'est un corpus alors limité à 443 fiches (`results/metrics_longitudinal.md:1`), donc non transposable, mais le document reste dans `results/` sans avertissement de péremption.

---

# 5. Points de fragilité à connaître avant de citer ces chiffres

1. **ADR-064 et ADR-065 n'existent pas** : le quad sub-index (4 index) et le RouterLLM, soit la moitié des 6 index FAISS, ne sont justifiés que par des docstrings (`src/rag/pipeline.py:95-102`, `src/rag/router_llm.py:1-14`) et des « à créer » (`scripts/build_quad_subindexes.py:37`).
2. **ADR-049 est resté DRAFT** alors que ses boosts sont en prod depuis avril (17 boosts, `docs/PIPELINE_v4_1_FLAGS.md:23`).
3. **ADR-002 (thèse INRIA : labels officiels) est empiriquement mort** — 0,06 % de couverture, boosts à 1.0 (`src/rag/reranker.py:6-22`), et sa position anti-BM25 (`docs/DECISION_LOG.md:51`) est contredite par ADR-058 sans que la contradiction soit tracée.
4. **Le « 73 % » est un chiffre d'état de l'art non sourcé** (`audit_empirique_2026-06-09/L3-Audit-data.md:12`), pas une mesure OrientIA ; les mesures internes attribuent l'échec dominant à la génération et au gating aval.
5. **`context_recall = 0,021` est un artefact de protocole reconnu** ; `context_precision` n'a **jamais** été mesurée.
6. **Le seul instrument de recall@k propre (relevance set lot 2) est bloqué** par le bug `idx:-1` qui contamine 79/135 questions labellisées, souvent sur le grade 2.
7. **La série 13 questions n'est pas homogène** (v5 vs v6 vs v7, 4/13 le 11/05 après 11/13 le 08/05) et n=13 est trop petit pour supporter les conclusions qui en sont tirées.
8. **Pas de sous-instrumentation de `step_5`** (`docs/OBSERVABILITY_BASELINE_2026-05-13.md:133`) : impossible d'attribuer un effet à dense vs BM25 vs RRF vs quota vs reranker.
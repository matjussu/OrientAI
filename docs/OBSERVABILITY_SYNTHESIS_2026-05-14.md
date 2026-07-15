# Synthèse Observability — Bench Langfuse pre/post C+ + Ragas calibration

**Date** : 2026-05-14  
**Bench Langfuse** : 13 questions spot-check Gate 3, mesurées pre-fix (main HEAD 2026-05-13) et post-fix (`feature/embed-annexes-text-field-chantier-c-plus`).  
**Bench Ragas** : 50 entrées golden_qa_v1.jsonl stratifiées par 5 catégories, scores faithfulness + context_recall via mistral-small-latest judge (T=0).

---

## 🎯 Top-line

| Axe | Mesure | Verdict |
|---|---|---|
| **Domain match pre vs post** | 4/13 → **8/13** (×2) | ✅✅ Chantier C+ livre comme prédit |
| **% top-5 = `(formation)`** | 60.7% → **24.6%** (cible <30%) | ✅✅ Métrique observability validée |
| **Ragas faithfulness** | 0.489 avg, **bimodale** | ⚠ Calibré-bas — signal vrai, pas cassé |
| **Ragas context_recall** | 0.021 avg, **92% des q < 0.1** | ❌ Artefact protocole, à reconcevoir |
| **Latence avg pre vs post** | 9.45s → 11.05s | ~ +1.6s, dominé par questions désormais en succès |
| **Coût bench** | $0.04 × 2 + Ragas $0.30 | = négligeable |

---

## A. Bench Langfuse — diff pre/post (13 spot-check)

### Distribution top-5 sources (la métrique clé)

| Domain | Pre | Post | Δ |
|---|---:|---:|---:|
| `(formation)` | 60.7% | **24.6%** | -36.1 pp ✅ |
| `insee_salaire` | 0.0% | 11.5% | +11.5 pp ✅ |
| `metier_prospective` | 0.0% | 8.2% | +8.2 pp ✅ |
| `crous` | 0.0% | 8.2% | +8.2 pp ✅ |
| `parcours_bacheliers` | 0.0% | 8.2% | +8.2 pp ✅ |
| `metier_detail` | 0.0% | 3.3% | +3.3 pp ✅ |

**Lecture** : les 4 domains qui étaient à 0% post-fix montent à 8-11%. Confirme que `fiche_to_text` exploitait pas le champ `text` des annexes, et le fix replace ces fiches dans le top-5 quand elles sont pertinentes.

### 4 huge wins + 1 régression mineure

- Q01 DARES Occitanie 2030 : 0/5 → 5/5 ✅✅
- Q02 CROUS Lyon : 0/5 → 5/5 ✅✅
- Q09 INSEE PCS 37 : 0/5 → 5/5 ✅✅
- Q12 MESR L1 bac S : 0/5 → 5/5 ✅✅
- Q05 actuaire : 0/5 → 2/5 ✅ (partiel)
- Q11 BAC PRO agri : 1/5 → 0/5 ❌ (DARES agri a pris la place de `voie_pre_bac`)

Restent à 0/5 : Q4, Q7, Q10, Q13 — **hors-périmètre C+** (problème de couverture corpus, pas d'indexation).

### Anomalie ouverte : Q01 latency 40s post-fix

Q01 prend 40s alors que retrieve marche maintenant. Trace montre **0 appels mistral-small** (vs 1+ pour les autres questions) — scope_classifier ou router_llm a skipped ou silent error. Hypothèse "auto-expansion qui boucle" infirmée, hypothèse "validator L3" infirmée (off par défaut). À investiguer dans une session dédiée — sous-instrumenter `step_8` pour séparer prompt_send / completion_streaming / retry.

---

## B. Ragas calibration — 50 entrées stratifiées

### Scores agrégés

| Catégorie | n | Faithfulness | Context Recall |
|---|---:|---:|---:|
| lyceen_post_bac | 10 | 0.446 | 0.043 |
| etudiant_reorientation | 11 | **0.628** | 0.011 |
| actif_jeune | 10 | 0.529 | 0.021 |
| master_debouchés | 10 | 0.486 | 0.021 |
| famille_social | 9 | 0.328 | 0.009 |
| **Global** | **50** | **0.489** | **0.021** |

### Faithfulness — distribution bimodale (0.489 avg)

| Bucket | Count | % |
|---|---:|---:|
| 0.9–1.0 | 8 | 16% |
| 0.7–0.9 | 5 | 10% |
| 0.5–0.7 | 10 | 20% |
| 0.3–0.5 | 11 | 22% |
| 0.0–0.3 | 16 | 32% |

**Lecture** : 26% des réponses sont fidèles (≥0.7), 54% sont peu fidèles (<0.5). La distribution n'est pas concentrée autour de la moyenne — c'est bimodal. Le pipeline produit soit du grounded, soit du largement inventé, peu d'entre-deux. **Calibration : signal vrai, dans la fourchette basse [0.4, 0.6]**, sous la cible Matteo [0.6, 0.85] mais pas cassé.

### Context recall — pathologique (0.021 avg, 92% < 0.1)

| Bucket | Count | % |
|---|---:|---:|
| 0.5–1.0 | 0 | 0% |
| 0.1–0.5 | 4 | 8% |
| 0.0–0.1 | 46 | 92% |

**Lecture honnête** : ce signal n'est **pas exploitable tel quel**. 2 hypothèses :

1. **Artefact protocole** (probable) : la `ground_truth` du JSONL est `final_qa.answer_refined` générée par claude-opus-4-7 à partir de sources web (onisep.fr, parcoursup.gouv.fr) — **pas du corpus FAISS d'OrientIA**. Ragas `context_recall` mesure "les contexts retrievés couvrent-ils la ground_truth" → forcément bas car la ground_truth pioche dans des sources que le corpus ne contient pas.
2. **Mon `_fiche_to_context` tronque trop** (secondaire) : limite à 500 chars de text + champs simplifiés. Le LLM reçoit un format plus riche en pratique.

**Conclusion** : context_recall n'est PAS la bonne métrique pour OrientIA sous protocole golden_qa actuel. À remplacer par :
- **`context_precision`** (mesure : les contexts retrievés sont-ils pertinents à la question, sans ground_truth)
- **`answer_relevancy`** (mesure : la réponse répond-elle à la question, sans ground_truth)

### Catégorie famille_social — score le plus bas (0.328 faith / 0.009 recall)

Note : 11 entrées dans la source, 9 utilisables. Très petit échantillon, scores volatiles. À ré-évaluer avec un sub-sample plus large quand le corpus aura été enrichi pour cette catégorie transversale.

---

## C. Cross-validation Langfuse ↔ Ragas

Les 2 mesures convergent sur un même verdict, par 2 chemins indépendants :

1. **Langfuse distribution sources** dit : retrieve trouve maintenant les bonnes fiches annexes (60.7% → 24.6% formation)
2. **Ragas faithfulness 0.489** dit : ces fiches retrievées ne suffisent pas à grounder pleinement la réponse — le LLM ajoute du contenu non-supporté

**Interprétation conjointe** : **le retrieve a fait un grand pas avec C+**, mais **la chaîne retrieve → generation a un trou intermédiaire**. Le LLM contextualise les bonnes fiches mais "extrapole" trop fortement vers une réponse "conseiller enrichi". C'est cohérent avec les patterns observés dans le spot-check : phrases de type "selon mes sources", "les opportunités émergentes" — formulations qui paraphrasent mais n'ancrent pas littéralement.

**Action à mesurer ensuite** : un fix sur le générateur (ex : prompt plus strict "ne dis rien qui ne soit dans [source SX]") devrait faire monter faithfulness sans changer la distribution sources. C'est un autre axe d'amélioration que C+ n'a pas adressé.

---

## D. Coût total observabilité (2 jours)

| Item | Coût |
|---|---:|
| Bench Langfuse pre-fix | $0.0420 |
| Bench Langfuse post-fix | $0.0426 |
| Ragas calibration (50q × 100 evals) | ~$0.30 (mistral-small + embed) |
| Re-embed corpus C+ (Claudette) | $1.50 (one-shot) |
| **Total** | **~$1.88** |

Coût d'instrumentation = négligeable par rapport au gain mesuré (4/13 → 8/13 + métriques de pilotage continu).

---

## E. Limites de cette session

1. **1 seul run Langfuse pre + 1 post** — pas de stats run-to-run, vulnérable au stochastique Mistral T=0.3 (ex : URL hallu 0/13 pre vs 1/13 post = signal volatil)
2. **Ragas context_recall non-exploitable** sous protocole actuel (ground_truth claude-opus-generated, pas corpus-aligned)
3. **Mon `_fiche_to_context` simpliste** sous-représente le contexte réel passé au LLM
4. **Q01 latency pathologie** non-élucidée
5. **Ragas Mistral judge T=0** mais le pipeline tourne à T=0.3 — les scores faithfulness peuvent varier sur d'autres runs du pipeline
6. **5 huge wins comme prédit par diagnostic Claudette** — mais Q11 régression mineure pas anticipée, à investiguer (boost reranker ?)

---

## F. Recommandations actionnables (priorisées)

### Immediate (avant push C+)

1. **Investiguer Q11 régression** (1/5 → 0/5 pour `voie_pre_bac`) — probablement re-calibration des boosts annexes maintenant qu'elles compétent vraiment pour des slots top-5. Diagnostique : 30 min via debugger.
2. **Re-tester avec 3 runs Langfuse** pour stat stable sur URL hallu et refus (volatil run-to-run)

### Court terme (post merge C+)

3. **Refaire Ragas avec `context_precision` + `answer_relevancy`** au lieu de `context_recall`. Ces 2 métriques sont reference-free et donneront un signal plus pertinent que 0.021.
4. **Améliorer `_fiche_to_context`** pour reproduire exactement le format du prompt LLM (au lieu de tronquer)
5. **Investigation Q01 40s** — sous-instrumenter `step_8` avec spans `prompt_send` / `streaming_first_token` / `streaming_complete` pour identifier si c'est Mistral medium lent ou client retry silent

### Moyen terme

6. **Faithfulness 0.489 → cible 0.7+** : audit du prompt v3.2 (SPRINT11_P0 prefix) pour renforcer les contraintes "ne cite rien qui n'est pas dans [source SX]". C'est un fix prompt-level, pas pipeline.
7. **Couverture corpus** Q4/Q7/Q10/Q13 : chantiers data séparés (élargir InserSup discipline×région, ROME 4.0 compétences, etc.)

---

## Livrables produits

| Fichier | Description |
|---|---|
| `docs/OBSERVABILITY_BASELINE_2026-05-13.md` | Analyse latency pre-fix (v1) |
| `docs/OBSERVABILITY_MULTI_AXIS_2026-05-13.md` | Multi-axes pre-fix (v2 corrigée) |
| `docs/OBSERVABILITY_POST_FIX_2026-05-14.md` | Multi-axes post-fix |
| `docs/OBSERVABILITY_DIFF_PRE_POST_2026-05-14.md` | Diff complet pre/post |
| `docs/OBSERVABILITY_SYNTHESIS_2026-05-14.md` | **Ce rapport** — vue d'ensemble |
| `results/observability_baseline_2026-05-13/multi_axis_analysis.json` | Données brutes pre |
| `results/observability_post_fix_2026-05-14/multi_axis_analysis.json` | Données brutes post |
| `results/ragas_calibration_2026-05-14/ragas_results.json` | Ragas scores 50 entrées |
| `scripts/observability/run_spot_check_traced.py` | Bench Langfuse 13q (paramétrable via env) |
| `scripts/observability/analyze_multi_axis.py` | Analyse multi-axes |
| `scripts/observability/diff_pre_post.py` | Diff pre/post |
| `scripts/observability/run_ragas_calibration.py` | Ragas calibration 50 entrées |

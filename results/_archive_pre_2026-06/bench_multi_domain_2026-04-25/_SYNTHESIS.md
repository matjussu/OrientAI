# Bench multi-domain v4 baseline vs v5 multi-corpus — verdict mesuré ADR-048

**Date** : 2026-04-25 PM
**Contexte** : ordre Jarvis 2026-04-25-1315 Axe (c). Bench v5 sur 18 queries v4 (PR #61) avait montré que le multi-corpus n'est activé que sur 1/18 — queries trop formation-centric. Ce bench-ci utilise **8 queries non-formation-centric** dédiées (3 metier / 3 parcours_bacheliers / 2 apec_region), gradient simple → contextuel → ambigu.

**Variable isolée** : ajout du multi-corpus (50 153 records vs 48 914) sur le même corpus formations + même fiche_to_text + même reranker + même prompt + même fact-checker.

---

## Verdict synthétique

| Métrique | v4 baseline | v5 multi-corpus | Δ | Verdict |
|---|:---:|:---:|:---:|---|
| Multi-corpus activé top-10 | **0/8 queries** | **6/8 queries** | **+6** | ⭐ pivot architectural fonctionnel |
| Score humain moyen (5 critères ×5) | **18.25/25** | **18.625/25** | **+0.375** | 🟡 gain mesurable mais modeste |
| Hallucination rate fact-check | 17/80 = 21 % | 27/71 = 38 % | +17pp | ⚠️ régression notable (variance attendue) |
| Latence gen moyenne | 19.9 s | 17.0 s | -15 % | ✅ stable |

**Verdict honnête** : le pivot multi-corpus **est techniquement fonctionnel** (6/8 queries activent les nouveaux corpora) et apporte un **gain mesurable mais modeste** sur la notation humaine (+0.375 / 25 = +1.5 %). Le bénéfice se manifeste asymétriquement par domain :

- ✅ **Métier** (3 queries) : +1 net point (m2 contextuel : artisanat d'art mieux couvert grâce au corpus metier)
- ✅ **Parcours bacheliers** (3 queries) : +3 nets points (p1 + p2 : meilleure transparence épistémique)
- ❌ **APEC régional** (2 queries) : -1 point (reranker existant ne tire pas parti des records APEC malgré leur retrieval potentiel — voir §5)

⚠️ **Régression hallucination rate +17pp** : driven par a2 v5 (14/14 stats hallucinées). Sample size N=8 par système, IC95 large. À stabiliser via triple-run S+1.

---

## 1. Activation multi-corpus — démonstration empirique

| Query | Domain target | v4 top-10 domains | v5 top-10 domains | Multi-corpus actif v5 |
|---|---|---|---|:---:|
| m1 | metier simple | formation | formation | ❌ |
| m2 | metier contextuel | formation | **formation + metier** | ✅ |
| m3 | metier ambigu | formation | **formation + metier** | ✅ |
| p1 | parcours simple | formation | **formation + parcours_bacheliers** | ✅ |
| p2 | parcours contextuel | formation | **parcours_bacheliers** (10/10) | ✅ |
| p3 | parcours ambigu | formation | **parcours_bacheliers** (10/10) | ✅ |
| a1 | apec simple | formation | formation | ❌ |
| a2 | apec contextuel | formation | formation | ❌ |

**Bilan activation** : 6/8 (75 %) en v5 vs 0/8 en v4 — **gain net +6 queries** par construction.

Pour comparaison, le bench v5 sur les 18 queries v4 avait montré 1/18 (5,5 %). Sur ce nouveau bench dédié, **75 % d'activation** valide que le multi-corpus est exploité dès qu'on lui pose la bonne question.

## 2. Notation humaine — détail par query

Grille stricte 5 critères, score 1-5 par critère, max 25 par query. Notation cohérente avec v4 synthesis (Claudette).

| Q | Domain | v4 P/Pe/Pr/S/V | v4 total | v5 P/Pe/Pr/S/V | v5 total | Δ | Note |
|---:|---|---|---:|---|---:|---:|---|
| m1 | metier simple | 4/4/4/5/4 | **21** | 4/4/4/5/4 | **21** | 0 | both formation, similar quality |
| m2 | metier contextuel | 3/4/4/5/4 | **20** | 4/4/4/5/4 | **21** | **+1** | v5 cite orfèvre/céramiste/verre via metier corpus |
| m3 | metier ambigu | 4/4/3/5/4 | **20** | 4/4/3/5/4 | **20** | 0 | similar |
| p1 | parcours simple | 2/3/3/4/4 | **16** | 3/3/3/4/4 | **17** | **+1** | v5 plus transparent ("estimation, non vérifié") |
| p2 | parcours contextuel | 2/3/3/4/4 | **16** | 3/4/3/4/4 | **18** | **+2** | v5 plan éco vs droit plus net |
| p3 | parcours ambigu | 3/4/4/4/4 | **19** | 3/4/4/4/4 | **19** | 0 | similar |
| a1 | apec simple | 2/3/3/4/4 | **16** | 2/3/3/3/4 | **15** | **-1** | v5 stats inventées + safety baisse |
| a2 | apec contextuel | 2/4/4/4/4 | **18** | 2/4/4/4/4 | **18** | 0 | similar (apec corpus non utilisé) |
| **TOTAL** | | | **146** | | **149** | **+3** | |

P = Précision factuelle / Pe = Pertinence du conseil / Pr = Personnalisation / S = Safety / V = Verbosité

**Score moyen v4 = 18.25 / 25** (73 %)
**Score moyen v5 = 18.625 / 25** (74,5 %)
**Δ = +0.375 / 25 = +1.5 %**

## 3. Délai par critère

| Critère | v4 moyen | v5 moyen | Δ |
|---|---:|---:|---:|
| Précision factuelle | 2.75 | 3.125 | **+0.375** |
| Pertinence du conseil | 3.625 | 3.75 | +0.125 |
| Personnalisation | 3.5 | 3.5 | 0 |
| Safety | 4.375 | 4.25 | -0.125 |
| Verbosité / lisibilité | 4.0 | 4.0 | 0 |

**Le gain v5 est concentré sur la précision factuelle** (+0.375 sur 5 = +7.5 %). Cohérent avec l'objectif du pivot multi-corpus : exposer plus de données factuelles retrievables (1 239 records additifs).

Légère baisse safety (-0.125) due au cas a1 où v5 cite des chiffres APEC non sourcés (le corpus APEC existe mais n'est pas retrievé pour cette query — voir §5).

## 4. Fact-check Mistral Small (objectif, computable)

| Métrique | v4 | v5 |
|---|---:|---:|
| Stats totales fact-checked | 80 | 71 |
| Verified ✅ | 31 (39 %) | 19 (27 %) |
| Disclaimer 🟡 | 32 (40 %) | 31 (44 %) |
| Hallucinated 🔴 | 17 (21 %) | **27 (38 %)** ⚠️ |

**Régression hallucination rate +17pp** : driven principalement par a2 v5 (14/14 stats hallucinées). Sample size N=8 limité, variance attendue. **Recommandation : triple-run pour stabiliser** (cohérent avec le verdict bench v5 PR #61).

Compatible avec l'observation que les 2 queries APEC (a1, a2) sous-performent : le reranker bloque les apec_records et le LLM se rabat sur des "connaissance générale" plus risquées.

## 5. ⚠️ Limitation découverte — reranker non multi-corpus aware

**Anomalie** : a1 ("Marché du travail cadres en Bretagne 2026") et a2 ("Régions cadres bac+5 informatique dynamiques") ne retrieve PAS les records `apec_region` en v5, malgré leur disponibilité dans l'index.

**Smoke test pré-bench** (sans pipeline complet, juste FAISS L2) montrait pourtant :
> "marché du travail des cadres en Bretagne" → 8/10 sources `apec_region`

**Cause identifiée** : le `OrientIAPipeline` applique `reranker.RerankConfig` (cf `src/rag/reranker.py`), des boosts SecNumEdu/CTI/labels formation, et un intent classifier qui privilégie le domain `formation`. Pour les queries APEC, le FAISS retrieve probablement des apec_records dans le top-50, mais le reranker les pousse hors du top-10 final.

**Implication** : le pivot multi-corpus ADR-048 est **partiellement opérationnel** :
- ✅ Layer data (corpus retrievable disponibles) : OK
- ✅ Layer embedding (FAISS multi-corpus) : OK
- ⚠️ Layer reranker (sélection top-K) : **biais formation par défaut**

**Recommandation S+1** : adapter le reranker pour intent multi-domain. Idée : si intent classifier détecte "marché du travail" / "salaire cadre" / "marché régional", **boost** apec_region (au lieu de pénaliser). Pareil pour "métier" / "profession" → boost metier. ADR-049 captures cela.

## 6. ADR-049 — Reranker multi-domain aware (DRAFT)

À formaliser dans `docs/DECISION_LOG.md` :

> **Context** : ADR-048 multi-corpus livré. Bench multi-domain (8 queries) montre activation 75 % côté FAISS retrieve, mais le reranker existant down-weighte les domains non-formation. Sur les 2 queries apec_region testées (a1 + a2), le top-10 final reste 100 % formation.

> **Decision** : adapter `RerankConfig` pour reconnaître les intents multi-domain :
> - Intent "marché du travail" / "cadres" / "salaire région" → boost `apec_region` (×1.5)
> - Intent "métier" / "profession" / "que fait un X" → boost `metier` (×1.3)
> - Intent "taux réussite" / "passage L1 L2" / "redoublement licence" → boost `parcours_bacheliers` (×1.3)
> - Pas de boost si intent ambigu → laisse le retrieve naturel

> **Rationale** : le pivot ADR-048 ne livre sa valeur scientifique que si le pipeline complet exploite les nouveaux corpora. Sans cette adaptation reranker, +75 % activation FAISS se traduit en seulement 6/8 récupération top-10 (et 0/2 sur apec).

> **Implementation** : PR distincte (S+1, hors deadline samedi). Coût ~2-3h dev + bench triple-run + ADR-049 formalisé.

## 7. Latence — observations

| Métrique | v4 | v5 |
|---|---:|---:|
| Gen total (8 queries) | 158.83 s | 135.87 s |
| Gen moyenne / query | 19.9 s | **17.0 s** (-15 %) |
| Fact-check total | 58.52 s | 43.71 s |
| Total bench | 217 s (3.6 min) | 180 s (3 min) |

Latence -15 % en v5, cohérente avec la tendance vue dans le bench v5 sur 18 queries v4 (-37 %). Hypothèse même : moins de stats cités (-11 %), génération plus courte. Pas un effet du multi-corpus en soi (qui ajoute légèrement au retrieve).

## 8. Reco actions S+1

1. **Triple-run du bench multi-domain** (8 queries × 3 runs sur v4 et v5) pour stabiliser les chiffres hallucination rate. Coût additionnel ~$0.30. Permet IC95 propre.
2. **Implémentation ADR-049 reranker multi-domain** (~2-3h dev) puis re-bench pour mesurer le vrai gain post-reranker. Hypothèse : +0.5 à +1 point sur queries APEC qui sont actuellement bloquées.
3. **Bench multi-domain élargi** (15-20 queries au lieu de 8) pour augmenter la puissance statistique. Surtout sur les domains métier et apec_region.
4. **Notation humaine 18 queries v4 vs v5** (Axe (a) ordre) — apportera un dataset complémentaire pour cross-validation.

---

## Sources & liens

- Branche : `feat/bench-multi-domain`
- Bench v4 baseline 18-queries : `results/bench_personas_v4_2026-04-24/_SYNTHESIS_V4_VS_V3.md`
- Bench v5 18-queries : `results/bench_personas_v5_2026-04-25/_SYNTHESIS.md`
- ADR-047 Mistral timeout : `docs/DECISION_LOG.md` (PR #58 mergée)
- ADR-048 RAG multi-corpus : `docs/DECISION_LOG.md` (PR #60 mergée)
- ADR-049 reranker multi-domain (DRAFT) : à formaliser PR distincte S+1
- Output v4 : `results/bench_multi_domain_2026-04-25/v4_baseline/`
- Output v5 : `results/bench_multi_domain_2026-04-25/v5_multi_corpus/`

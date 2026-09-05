# Bench v5 dedupé vs v5 actuel vs v4 — diagnostic shipping multi-corpus INRIA

**Date** : 2026-04-25 PM
**Contexte** : ordre Jarvis 2026-04-25-1352 URGENT. Décision shipping multi-corpus INRIA J-30 dépend du verdict de ce diagnostic.
**Variables isolées** :
- v4 → v5_actuel : ajout multi-corpus (50 153 records vs 48 914) **+ doublons R1**
- v5_actuel → v5_dedupé : **dedup R1 uniquement** (47 590 formations + 1 239 multi-corpus = 48 829 records)

Si la régression v4→v5 vient de R1, v5_dedupé devrait revenir à 4.30-4.53.
Si la régression vient de l'architecture multi-corpus, v5_dedupé restera à ~3.85-3.95.

---

## Verdict diagnostic — **CAUSE ARCHITECTURALE** (pas R1)

| Système | Précision factuelle | MOY GLOBALE / 5 | Interprétation |
|---|:---:|:---:|---|
| **v4 baseline** (17 q) | **4.53** | 4.57 | référence |
| **v5 actuel** (18 q) | 3.89 | 4.42 | -0.64 vs v4 |
| **v5 dedupé** (18 q) | **3.83** | **4.42** | -0.70 vs v4 / -0.06 vs v5 actuel |

**Décision selon seuils ordre 2026-04-25-1352** :
- [4.30, 4.53] → cause R1 (doublons) ✅ shippable INRIA → **❌ rejeté** (3.83 << 4.30)
- [3.85, 3.95] → cause architecturale ❌ reportable ou ADR-049 → **✅ correspondance** (3.83 ≈ 3.85)
- [3.95, 4.30] → cause mixte triple-run requis → ❌ rejeté

**Interprétation honnête** : la dedup R1 n'a **PAS fixé** la régression précision factuelle. Le score v5_dedupé est essentiellement identique au v5_actuel (-0.06 dans le bruit Mistral non-zero temperature). **La cause de la régression -0.7 est architecturale**, c'est-à-dire la dilution multi-corpus au top-K boundary, pas les doublons.

⚠️ Caveat statistique : single run, sample N=18 queries × 1 = 18 observations. La différence 3.83 vs 3.89 est dans le bruit (1 query déplacée d'1 point change le moyen de 0.06). Pour un verdict scientifiquement défendable INRIA, **triple-run est requis** — mais la convergence avec la fact-check (v5_dedupé halluc rate 21.2 % vs v5_actuel 15.2 % vs v4 11.6 %) renforce le pattern : multi-corpus dilue.

---

## 1. Fact-check Mistral Small (mesure objective)

| Métrique | v4 (17 q) | v5 actuel (18 q) | v5 **dedupé** (18 q) | Δ dedupé/actuel |
|---|---:|---:|---:|---:|
| Stats totales | 207 | 184 | **217** | **+33** |
| Verified ✅ | 98 (47.3 %) | 79 (42.9 %) | **100 (46.1 %)** | +21 (+3.2pp) |
| Disclaimer 🟡 | 85 (41.1 %) | 77 (41.8 %) | 71 (32.7 %) | -6 (-9.1pp) |
| Hallucinated 🔴 | 24 (11.6 %) | 28 (15.2 %) | **46 (21.2 %)** | +18 (+6.0pp) ⚠️ |

**Pattern post-dedup** :
- ⭐ **Verified rate récupère** vers v4 (47.3 % → 46.1 %) : la dedup a libéré du top-K pour des fiches plus pertinentes
- ⚠️ **Hallucination rate empire** (+6pp) : Mistral cite plus de stats au total (+33), mais avec moins de retenue
- Cohérent avec la régression précision humaine constatée — Mistral génère plus de stats sourcées sans pour autant être correct

## 2. Notation humaine grille stricte (5 critères, 18 queries × 5 = 90 cellules)

| Critère | v4 (17 q) | v5 actuel (18 q) | v5 **dedupé** (18 q) | Δ dedupé/actuel | Δ dedupé/v4 |
|---|:---:|:---:|:---:|:---:|:---:|
| **Précision factuelle** | 4.53 | 3.89 | **3.83** | -0.06 | -0.70 |
| Pertinence | 4.71 | 4.78 | 4.78 | 0 | +0.07 |
| Personnalisation | 4.18 | 4.44 | 4.44 | 0 | +0.26 |
| Safety | 5.00 | 4.67 | 4.61 | -0.06 | -0.39 |
| Verbosité | 4.47 | 4.33 | 4.44 | +0.11 | -0.03 |
| **MOY / 5** | **4.57** | **4.42** | **4.42** | **0** | **-0.15** |
| **MOY / 25** | **22.85** | **22.11** | **22.11** | **0** | **-0.74** |

**Pattern remarquable** : la dedup **n'a pas bougé** la moyenne globale (4.42 = 4.42). Petites variations cancel out (précision -0.06, verbosité +0.11). La précision reste à -0.70 du v4.

## 3. Per-query precision factuelle (v4 → v5_actuel → v5_dedupé)

| Q | Persona | Topic | v4 | v5_actuel | v5_dedupé | Δ_dedupé/v4 |
|---:|---|---|:---:|:---:|:---:|:---:|
| 1 | Lila | Débouchés L lettres | 4 | 4 | 4 | 0 |
| 2 | Lila | SHS vs école com | 5 | 5 | 5 | 0 |
| 3 | Lila | 14 moy T L | 5 | 4 | 4 | -1 |
| 4 | Théo | Passerelles droit (multi-corpus) | 5 | 4 | 4 | -1 |
| 5 | Théo | Pas droit réaliste | 5 | 5 | 5 | 0 |
| 6 | Théo | Bordeaux audio/com | 5 | 4 | **5** | 0 ⭐ |
| 7 | Emma | Salaire dev M2 | 4 | 4 | **3** | -1 ⚠️ |
| 8 | Emma | M2 rech vs altern | 4 | 3 | **4** | 0 ⭐ |
| 9 | Emma | Lille data CDI | 4 | 4 | **3** | -1 ⚠️ |
| 10 | Mohamed | Débouchés cuisine | 4 | 3 | **4** | 0 ⭐ |
| 11 | Mohamed | CAP pas resto | 4 | 3 | 3 | -1 |
| 12 | Mohamed | Marseille cuis/pât | n/a | 4 | 4 | (timeout v4) |
| 13 | Valérie | Coût école com | 5 | 4 | 4 | -1 |
| 14 | Valérie | STAPS débouchés | 4 | 3 | 3 | -1 |
| 15 | Valérie | Fils T S budget | 5 | 4 | 4 | -1 |
| 16 | Psy-EN | Master psycho 3 ans | 5 | 4 | **3** | -2 ⚠️ |
| 17 | Psy-EN | 1ère S redouble | 4 | 3 | 3 | -1 |
| 18 | Psy-EN | 2nde modeste aéro | 5 | 5 | **4** | -1 ⚠️ |

**Mouvements dedupé** :
- 3 queries gagnent 1pt vs v5_actuel (Q6, Q8, Q10) — top-K libéré par dedup
- 4 queries perdent 1pt vs v5_actuel (Q7, Q9, Q16, Q18) — top-K shifté (peut-être doublons légitimes mêmes enrichissements)
- Net = -1 point au total / 17 communes → variance dans le bruit

## 4. Hypothèses sur la cause architecturale

Si la régression -0.7 vs v4 n'est PAS R1 (dedup l'a confirmé), elle est :

### H1 — Dilution multi-corpus au top-K boundary (+1 239 records)

Mécanisme : pour chaque query, Mistral retrieve top-10 sur un index plus dense. Les 1 239 records multi-corpus sont **proches sémantiquement** de certaines fiches formation (ex : un metier `K2402 ingénieur mathématicien` est proche de `Master Mathématiques Appliquées`). Sur les queries formation-centric, ces records peuvent voler 1-3 slots top-10 à des fiches formation plus précises.

Mesure : sur 17/17 queries communes, multi-corpus activé sur **1/17** seulement (Q4 droit). **Donc la dilution n'est PAS via récupération directe de records non-formation, mais via shift des distances** (récords formation moins relevant peuvent passer devant des récords formation plus pertinents si distance-shift dans l'index étendu).

### H2 — Bruit non-zero temperature Mistral

Mistral medium génère avec température > 0. Single run sur 18 queries = variance mesurable. Sur les 4 queries où dedupé regagne 1pt vs actuel et 4 où il perd 1pt = noise plausible.

**Triple-run requis** pour départager H1 vs H2 :
- Si triple-run v5_dedupé moyenne sur 3 runs ≈ 3.85 → H1 confirmé (régression réelle)
- Si triple-run v5_dedupé moyenne 3.85-4.30 → H1 + H2 mixed
- Si triple-run v5_dedupé moyenne ≥ 4.30 → H2 dominant, H1 invalidé

### H3 — Régression R3 labels orthogonale (info Jarvis)

Audit data EOD a flaggé R3 (P1) : champ `labels` à 0 % (vs 5.2 % historique) = reranker SecNumEdu/CTI/CGE no-op. Cette régression silencieuse affecte v4, v5_actuel ET v5_dedupé identiquement → ne peut pas expliquer la différence v4→v5. Mais elle peut expliquer pourquoi v4 a 4.53 et pas 4.7+ (perte de boost reranker label).

## 5. Reco shipping multi-corpus INRIA J-30 (deadline 25/05)

### Reco principale : **NE PAS shipper le multi-corpus en l'état pour INRIA**

Justification :
- Régression précision factuelle -0.70 confirmée par 2 mesures indépendantes (humaine + fact-check)
- Dedup R1 n'a pas résolu — cause architecturale plausible (H1)
- INRIA J-30 ne tolère pas une régression -14 % sur le critère phare

### Path 1 — Ship version PRE-multi-corpus (v4 4.57)

- Revert PR #61 dans le pipeline production (mais garder code multi-corpus en dev pour v6)
- Avantage : précision INRIA-grade prouvée à 4.53/5
- Désavantage : perd l'extension scope (metiers, parcours, apec_regions)
- Effort : 30 min revert config, 2-3h re-bench v4 sur 100 questions hold-out pour publication INRIA

### Path 2 — Ship version POST-ADR-049 (reranker multi-domain aware)

- Implémenter ADR-049 (PR #62) : reranker boost domain-aware selon intent
- Hypothèse : ADR-049 résout H1 en restituant les fiches formation pertinentes au top-K quand le query est formation-centric (pas de boost multi-corpus)
- Pour les queries multi-domain, le boost active multi-corpus retrieve
- Avantage : best-of-both-worlds, multi-corpus opérationnel uniquement quand pertinent
- Désavantage : ~3-4h dev + 1h triple-run = 4-5h effort, risque échec si l'hypothèse est fausse
- Effort : faisable en 1 journée, à arbitrer S+1 (lundi 28/04)

### Path 3 — Triple-run + arbitrage à mid-S+1

- Lancer triple-run v5_dedupé (18 queries × 3) pour stabiliser les chiffres
- Coût $0.30, durée 30 min
- Si triple-run confirme régression nette → Path 1
- Si triple-run montre récupération significative → Path 2 ou ship as-is

**Reco Claudette** : **Path 3 puis arbitrage**. Coût trivial, donne un signal scientifique propre, permet décision défendable INRIA. Si Path 3 valide H1 (régression réelle), enchaîner Path 2 (ADR-049) avec timeline 28/04 → 5/05 réaliste. Path 1 est le filet de sécurité.

## 6. Caveats méthodologiques

- **Single run** sur 18 queries × 1 = forte variance Mistral
- **R3 labels à 0 %** affecte les 3 systèmes identiquement, comparaison préservée mais valeur absolue v4 est sous-estimée (-0.x sur précision probable)
- **ADR-048 inexactitude argumentaire ROME** identifiée par audit — pivot multi-corpus reste pertinent par richesse éditoriale (1 075 fiches metier non extractibles d'autres sources), pas juste par couverture ROME
- **Path 2 (ADR-049) non testé** : hypothèse à valider, pas une garantie

## 7. Conclusion ordre 2026-04-25-1352

✅ **Phase 1 dedup R1** : livré (1 324 records droppés, 0 régression tests, ADR-050)
✅ **Phase 2 rebuild FAISS reuse** : livré ($0 coût Mistral, 1.5s build, 48 829 vecteurs)
✅ **Phase 3 re-bench + notation** : livré (18 queries × 5 critères = 90 cellules)

**Verdict diagnostic** : régression -0.7 v4→v5 = **cause architecturale H1 (dilution multi-corpus)**, PAS R1 doublons. ADR-050 est mergeable comme nettoyage tech debt mais ne suffit pas seul.

**Reco shipping INRIA** : Path 3 (triple-run d'abord, $0.30) puis Path 2 (ADR-049) si confirmé. Path 1 (revert) en filet de sécurité.

---

## Liens

- Branche : `fix/dedup-parcoursup`
- ADR-050 : `docs/DECISION_LOG.md`
- Bench v5 actuel : `results/bench_personas_v5_2026-04-25/_SYNTHESIS.md`
- Bench multi-domain : `results/bench_multi_domain_2026-04-25/_SYNTHESIS.md` (ADR-049 DRAFT)
- Audit data EOD : `~/obsidian-vault/04-Connaissances/orientia-audit-data-2026-04-25.md`
- Output v5 dedupé : `results/bench_personas_v5_dedupe_2026-04-25/query_*.json`
- Index v5 dedupé : `data/embeddings/formations_multi_corpus_dedupe.index` (gitignored)

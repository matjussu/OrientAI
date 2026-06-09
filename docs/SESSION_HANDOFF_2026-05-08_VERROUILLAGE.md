> PERIME (snapshot date). Chiffres superseded par audit_empirique_2026-06-09 : region manquante reelle 45,9% (pas 41,5%), corpus 47220 fiches. Conserve comme historique.

# Session Handoff — Verrouillage data + pipeline + bench multi-tour

**Date** : 2026-05-08
**Branche** : `feature/verrouillage-bench-multi-tour`
**Plan source** : `~/.claude/plans/alors-je-suis-d-accord-bubbly-aho.md`
**Statut** : Phases A + B + C livrées (3 commits). **Phase D bloquée** par la découverte de 2 bugs critiques en runtime live via la passerelle plateforme OrientAI.

---

## Contexte initial de la session

Matteo a posé 5 critères pour cadrer la suite du projet OrientIA avant de relancer un benchmark coûteux et passer au multi-tour :

1. Toute la data disponible dans le projet a été travaillée et ingérée
2. Le RAG fonctionne sur TOUTE la data en prod, pas que des parties
3. Le pipeline est COMPLET et opérationnel, toutes les briques branchées
4. Le bench est bien pensé pour tirer toutes les conclusions souhaitées
5. Si bench satisfaisant → multi-tour (mémoire conversationnelle)

Le plan en 5 phases (A → B → C → D → E) a été validé en mode plan, puis la session est passée en exécution avec création d'une branche dédiée et commits par phase.

**Capacité nouvelle révélée pendant la session** : la passerelle entre la plateforme OrientAI et le LLM Mistral est désormais opérationnelle. Matteo peut tester live (texte → réponse + sources) ce que le pipeline produit pour de vrais utilisateurs. Cette capacité a été décisive pour attraper les bugs runtime invisibles aux benchmarks automatisés.

---

## Phase A — Verrouillage data ✅

**Commit** : `a84a2f6` — *chore(phase-a): verrouillage data — archive rewrite + audit v7 + LIMITATIONS*

### Actions livrées

| # | Action | Sortie |
|---|---|---|
| A1+A2+A3 | Audit sources data partielles (APEC PDFs 24 MB jamais parsés, LBA dump statique 6 646 fiches token expiré, France-Travail `romeo.py` non Stage-10) | Documentées dans `docs/LIMITATIONS.md §7bis` |
| A4 | Archive `src/rewrite/` + `tests/test_rewrite/` + `scripts/finalize_rewrite_v6.py` + `scripts/prepare_rewrite_chunks.py` (29 fichiers) | Déplacés dans `_archive_rewrite_phase3v2_pre_pivot/` |
| A5 | Audit Phase 0 daté du corpus v7 prod | `docs/AUDIT_PHASE_0_V7_2026-05-08.md` |
| A6 | Statut `formations.json` legacy clarifié | Documenté comme **alias actif** vers `formations_v7.json` (47 214 fiches identiques, contenu vérifié byte-for-byte). Pattern double-binding documenté dans `LIMITATIONS.md §7ter`. |
| – | `.gitignore` étendu (v6/v7/golden_pipeline/unified backups) | Évite checkin accidentel de 220 MB de corpora |

### Verdict audit v7 (Gate 1 corpus)

| Métrique | Valeur | Cible | Statut |
|---|---:|---|:-:|
| total_fiches | 47 214 | ≥40 000 | ✅ |
| doublons_pct | 0.0 | <5% | ✅ |
| cereq_residual | 0 | 0 (ADR-054) | ✅ |
| domain_coverage_pct | 28.5 | ≥28% | ✅ |
| url_verifiable_pct | 33.1 | ≥40% | ⚠️ orange |
| sans_region_formations_pct | 41.5 | ≤10% | 🔴 (structurel RNCP/ONISEP/LBA) |
| sans_niveau_formations_pct | 20.9 | ≤15% | ⚠️ orange |
| median_chiffres_density | 2.0 | ≥3 | ⚠️ orange |
| Tier 1 | 47 201 | – | ✅ (99.97% liste blanche) |

**Critère Matteo #1 — répondu OUI à 95%**, sources partielles documentées avec décision explicite.

---

## Phase B — Vérification pipeline + re-audit Sprint 9 ✅

**Commit** : `e967140` — *docs(phase-b): pipeline v4.1 flags + Sprint 9 re-audit verdict Path B*

### Actions livrées

| # | Action | Résultat |
|---|---|---|
| B1 | `pytest tests/` full suite | **2 516 passed**, 9 skipped, 0 fail (4:35) |
| B2 | Smoke test API (3 questions live) | Q1 BUT Bordeaux 5.6 s, Q2 actuaire 5.9 s, Q3 calendrier 6.5 s — FIDELE 0.95-1.0, **p95 ≈ 6.5 s vs cible 12 s** |
| B3 | `docs/PIPELINE_v4_1_FLAGS.md` | 13 flags `factory.py` documentés avec défauts prod + déclencheurs + modes A/B (Run F baseline, Layer3, Mistral Large vs Medium) |
| B4 | `docs/SPRINT9_REAUDIT.md` | Verdict **Path B** (multi-tour minimal) retenu pour Phase E |
| B5 | Audit `history` support actuel | Déjà supporté Sprint 11 P0 Item 2 (`pipeline.py:258`), infrastructure prête |
| B6 | Décision Path A vs B | Path B confirmé |

### Verdict Sprint 9 hierarchical (le morceau important)

L'audit pipeline initial parlait d'un "bench Sprint 12 NO-GO" qui aurait disqualifié Sprint 9. **Vérification runtime** : le bench `bench_sprint12_mistral_large_vs_medium/` compare en réalité **Mistral Large vs Medium**, pas Sprint 9 vs v4.1. **Sprint 9 hierarchical n'a jamais été benché contre la prod actuelle.**

Décision Path B est donc prise sur l'analyse architecturale, pas sur des données mesurées :

- **EmpathicAgent** (`src/agents/hierarchical/empathic_agent.py:116-125`) **réécrit explicitement** la base factuelle produite par le RAG dans une "posture conseiller" expressive avec `max_tokens=1500` (vs 400 v4.1 R6) → **viole les R1-R6 v4.1 strict**, dilue les claims sourcés `[source SX]`.
- **Coordinator** annonce une latency mode reco de **33-43 s** (synthesizer ~30-40 s + empathic + analyst parallèles) — incompatible avec la cible démo INRIA p95 ≤ 12 s.
- **Composants réutilisables isolément** : `Session` dataclass + `UserSessionProfile` + `_EXPLICIT_RECO_REGEX`. Le reste reste en POC documenté.

**Critères Matteo #2 et #3 — répondus OUI** : tous les flags câblés en `factory.py`, 17 boosts reranker actifs, 18 012 fiches `retrieval_eligible=false` exclues runtime correctement, 0 module mort dans le chemin prod.

---

## Phase C — Design bench complet ✅

**Commit** : `d8200b2` — *feat(phase-c): bench complet design — golden_60 + nDCG + GO/NO-GO + reproduce_bench.sh*

### Actions livrées

| # | Action | Sortie |
|---|---|---|
| C1 | `data/golden_eval/golden_60.json` schema v2 | 50 ground-truth + **8 adversarial** (fausses écoles, prompt injection, dates fictives, label volé École Polytechnique Privée Lyon, blocklist EPITA) + **2 cross-domain** (médecine, célébrité). Champ `expected_refusal=true` + 18 `refusal_markers_default` |
| C2 | `scripts/eval_recall.py` v2 | Ajout **nDCG@10** (relevance binaire, log2 discount) + **refusal_correctness** automatisé. Tests unit validés (rank1=1.0, rank3=0.5, no relevant=0.0) |
| C3 | `docs/BENCH_GATES.md` | **6 gates chiffrées** GO/NO-GO multi-tour : recall@5≥75%, MRR≥0.55, nDCG≥0.65, par catégorie≥60%, honesty≥0.95, p50≤8s, p95≤12s, refusal adv≥80%, refusal xd=100%, rubric≥12/18, Δ vs neutral≥+1pt, Haiku≥0.85, Δ vs v3.2_no_rag≥+0.05 |
| C4 | `scripts/reproduce_bench.sh` (170 lignes bash, `--dry-run`/`--skip-judges`/`--skip-factcheck`) + `scripts/synthesize_bench_results.py` (371 lignes, applique les 6 gates, produit `SUMMARY.md` auto avec verdict GO/NO-GO) | Dry-run validé : 3 API keys + 4 fichiers data tous présents |

### Coût estimé Phase D

~$25-30, ~2-3 h wall-clock. Pré-requis confirmé avec Matteo : recharge Anthropic $30-40.

**Critère Matteo #4 — répondu OUI** : le bench couvre retrieval (recall/MRR/nDCG), génération (rubric Claude+GPT-4o), honesty (validator + Haiku factcheck), robustesse (adversarial+xd), latency (p50/p95), coût.

---

## Découverte critique fin de session — la passerelle révèle 2 bugs runtime

**Avant cette session** : on mesurait OrientIA exclusivement via mini-bench (23q internes) + spot-check (13q domains dormants) + smoke API en local. Tous "verts" sur les chiffres.

**Pendant cette session** : Matteo a connecté la plateforme OrientAI au LLM Mistral via une passerelle. Il peut maintenant **interroger le pipeline en conditions réelles utilisateur** et voir verbatim la réponse + les sources. Il a partagé deux Q/A live qui ont fait apparaître des bugs **invisibles** aux benchmarks automatisés.

### Q/A live #1 — superlatif non géré

**Question** : *"Quelle est la meilleure école de commerce en France ?"*

**Réponse pipeline** :
> Je n'ai pas de données dans mes sources pour comparer les "meilleures" écoles de commerce en France (classements, notoriété, spécialisations).
>
> En revanche, voici deux formations en commerce/management avec des chiffres Parcoursup 2025 :
>
> - CPGE ECG (Maths appliquées + ESH) à l'École Nationale de Commerce (Paris 17e) : 48 places, 45 % de taux d'accès et 64 % d'acceptés en début de phase principale [source S4].
> - Licence Gestion (parcours Commerce Vente et Marketing) à l'ECM Belfort : 30 places, 99 % de taux d'accès et 88 % d'acceptés en début de PP [source S5].
>
> Quels critères sont prioritaires pour toi : sélectivité, localisation, ou type de diplôme (prépa vs licence) ?

**Diagnostic** : la première phrase reconnaît honnêtement l'absence de classement, mais la suite **fabrique une réponse** en présentant 2 formations marginales (CPGE Paris 17e + Licence Belfort) comme si c'étaient les options pertinentes pour "meilleure école de commerce". C'est un **bug prompt + scope** : le système devrait soit refuser totalement, soit citer les ESC reconnues présentes dans le corpus (HEC, ESSEC, ESCP, EM Lyon…) avec un disclaimer "voici ce qui apparaît dans nos sources, le classement n'est pas une donnée corpus".

### Q/A live #2 — contrainte régionale ignorée

**Question** : *"Quelles écoles d'ingénieur en cybersécurité existent en Bretagne ?"*

**Réponse pipeline** :
> Je n'ai pas de formation pertinente dans mes sources pour les écoles d'ingénieur en cybersécurité en Bretagne.
>
> En revanche, si la mobilité est possible, le Certificat de Spécialisation - Cybersécurité au Lycée Chevalier Saint-Georges (Les Abymes, Guadeloupe) propose 12 places [source S4]. Ses débouchés incluent Responsable de la Sécurité des Systèmes d'Information ou Ingénieur Cybersécurité.
>
> Souhaites-tu explorer d'autres régions ou des alternatives en Bretagne (comme des licences pro ou BUT informatique) ?

**Sources affichées (top 12)** :

```
[1] insersup_mesr                                          ← stat anonyme, no nom
[2] assistant de manager                                    ← libellé discipline brut
[3] assurance                                               ← libellé discipline brut
[4] Certificat de Spécialisation - Cybersécurité — Les Abymes (Guadeloupe)
[5] Licence - Lettres - Parcours Français pour le professorat des écoles — Rennes
[6] BTS - Cybersécurité, Informatique et réseaux — Rennes      ← PERTINENT ignoré
[7] BUT Réseaux et Télécommunications, Cybersécurité — Brest   ← PERTINENT ignoré
[8] Cert Cybersécurité — La Boisse (hors Bretagne)
[9] Cert Cybersécurité — Poitiers
[10] Cert Cybersécurité — Gragnague
[11] Cert Cybersécurité — Limoges
[12] Cert Cybersécurité — Hyères
```

**Diagnostic** : le retrieval **ramène bien des fiches Bretagne+cyber pertinentes** ([6] BTS Rennes, [7] BUT Brest), mais **le générateur les ignore** et propose la Guadeloupe en alternative à la Bretagne (absurde géographiquement). Le pipeline détient la bonne info et la jette.

L'expert plateforme (Claudette, qui a fait le wrapper FastAPI) a fait son propre audit côté code et a identifié 3 bugs distincts. Ses observations sont solides à 2,5/3.

---

## Mon analyse — les vrais bugs derrière les 2 Q/A

### Bug #1 (P0) — filtre régional jamais auto-déclenché

`metadata_filter` existe (Sprint 10 chantier C, branché en `factory.py` via `use_metadata_filter=True`) mais reste **opt-in** : il s'active uniquement si l'appelant passe `criteria=FilterCriteria(region="Bretagne")` à `pipeline.answer()`. L'intent classifier détecte l'entité "Bretagne" mais ne construit **pas** le `FilterCriteria` automatiquement. C'est le wire manquant : `intent_classifier → extract_geo_entity → FilterCriteria → pipeline.answer()`.

**Impact bench Phase D** : on échouerait Gate 1 (recall@5 catégorie *geographique* probablement <60 %) et Gate 4 (refusal cross_domain). Mesurer un état cassé serait gâcher $30.

### Bug #2 (P1) — top-K pollué par stats anonymes

Les fiches `domain=insertion_pro` (InserSup/InserJeunes agrégats) ont un usage légitime sur des questions type "salaire après Master Droit PACA", mais elles n'ont pas de `nom` formation. Quand l'intent n'est PAS factual_pointed sur stats, elles polluent le top-K visible et passé au LLM. Fix : downweighter `domain=insertion_pro` au reranker quand intent ≠ factual_pointed sur stats.

### Bug #3 — possiblement déjà résolu Vague 0.5

Le diagnostic expert pointait le boost SecNumEdu ×1.5 comme cause du Lycée Guadeloupe en haut. **Mais la Vague 0.5 a neutralisé ces boosts à 1.0** (commits `ab51cd8` / `7adb070` du 2026-05-08 — couverture 0.06 % du corpus = signal mort). À vérifier en runtime que la neutralisation est bien effective : si oui, ce bug est obsolète.

### Bug #4 (nouveau, P0) — générateur ignore les sources passées

Sur Q/A #2, [6] BTS Rennes et [7] BUT Brest sont **dans les sources** mais le générateur dit *"pas de formation pertinente"*. Deux hypothèses :

- **Hypothèse A — sélection top_k_sources trop courte** : MMR ou intent_to_config réduit à top-5 avant prompt LLM. Si les 5 premiers sont [1-3] stats anonymes + [4] Guadeloupe + [5] Lettres Rennes, alors [6] [7] **n'atteignent jamais le prompt**. À vérifier en traçant ce qui est effectivement passé au générateur.
- **Hypothèse B — prompt v4.1 strict insuffisant** : R5 demande "question ouverte si infos insuffisantes" mais ne **bloque pas** la suggestion d'alternative géographique absurde. Faut un R7 explicite : "si la question impose une contrainte géo, ne PAS proposer hors-région sans le signaler explicitement".

### Bug #5 — superlatif "meilleur" non détecté

Le scope_classifier ne flag pas les superlatifs ("meilleure", "top", "classement"). Le pipeline traite la question comme une recherche normale, sourçe deux formations marginales et les présente comme une réponse. Solution : pattern superlatif → refus avec redirect vers Onisep classements ou vers SCUIO.

### Bug #6 (UX) — sources affichées sans nom exploitable

[1] `insersup_mesr`, [2] `"assistant de manager"`, [3] `"assurance"` apparaissent côté plateforme avec ces libellés bruts. C'est ce que le wrapper FastAPI `_extract_source_fiche` retourne quand la fiche n'a ni `nom` ni `intitule` exploitable. Drop côté wrapper = patch UX 10 min côté expert plateforme.

---

## Mon point de vue — pourquoi Phase B' avant Phase D

Le plan original prévoyait de lancer Phase D direct après C (validation seuils + recharge Anthropic). Le retour terrain change la donne :

1. **Si on benche maintenant**, on échoue Gate 1 (geographique) et Gate 4 (refusal) sur des bugs **connus et fixables**. On déclarerait NO-GO multi-tour pour de mauvaises raisons et on dépenserait $30 pour rien.
2. **Si on fixe d'abord**, le bench mesure ce que le pipeline est capable de faire à son meilleur, pas son pire visible. La décision multi-tour repose alors sur la vraie qualité du système.
3. **Coût Phase B'** : ~7h, $0 (validator local). C'est exactement le cas d'usage de l'investissement préventif : **5h de fix vaut mieux que 30 $ + 3h de bench bidon + diagnostic post-hoc**.
4. **Bonus** : la passerelle plateforme OrientAI permet désormais de **valider chaque fix en live** avant de relancer le bench. C'est une boucle d'itération 10× plus rapide que mini-bench → bench complet → analyse.

L'investissement Phase B' transforme la décision Phase D de *"à quel point sommes-nous moyens ?"* en *"sommes-nous prêts pour le multi-tour ?"*. C'est l'objectif de Matteo.

---

## Phase B' proposée (8 fixes)

| # | Action | Effort | Owner |
|---|---|---|---|
| B'.1 | Vérifier que Vague 0.5 a bien neutralisé SecNumEdu/CTI/CGE en runtime (sinon fix) | 15 min | OrientIA |
| B'.2 | Wire `intent_classifier` → auto-construct `FilterCriteria(region=...)` quand entité régionale détectée → `pipeline.answer()` | 2-3 h | OrientIA |
| B'.3 | Reranker : downweighter `domain=insertion_pro` quand intent ≠ factual_pointed sur stats | 1 h | OrientIA |
| B'.4 | Pattern superlatif ("meilleur/top/classement") dans `ScopeClassifier` ou `SYSTEM_PROMPT_V4_STRICT` → refus + redirect Onisep | 1 h | OrientIA |
| B'.5 | Mini-bench + spot-check + 3-5 questions live via plateforme post-fixes pour non-régression | 30 min | OrientIA |
| B'.6 | Wrapper FastAPI drop sources sans `nom`/`intitule` exploitable dans `_extract_source_fiche` | 10 min | expert plateforme (Claudette) |
| **B'.7** | **Audit `top_k_sources` réellement passé au LLM** : tracer pour Q "ingé cyber Bretagne", vérifier si BTS Rennes / BUT Brest atteignent le prompt. Si non, fix sélection (intent override `top_k_sources` ≥ 10 quand contrainte géo+métier) | 1-2 h | OrientIA |
| **B'.8** | **R7 dans `SYSTEM_PROMPT_V4_STRICT`** : "si la question impose une contrainte géographique, ne PAS proposer d'alternative hors-région sans dire explicitement que la région est vide" | 30 min | OrientIA |

**Total estimé** : ~7 h, $0 (validator local, pas d'API critique). B'.6 en parallèle côté wrapper.

---

## État actuel — à la sortie de cette session

### Branche `feature/verrouillage-bench-multi-tour`

- 3 commits propres : `a84a2f6` (Phase A), `e967140` (Phase B), `d8200b2` (Phase C)
- `pytest tests/` : 2 516 verts, 0 fail
- API smoke tests OK localement (3 questions, p95 6.5 s)
- Reproductibilité bench : `./scripts/reproduce_bench.sh --dry-run` validé

### Documents produits

- `docs/AUDIT_PHASE_0_V7_2026-05-08.md` — baseline data daté
- `docs/LIMITATIONS.md` — sources partielles, scope, mesures non disponibles, conventions paths
- `docs/PIPELINE_v4_1_FLAGS.md` — 13 flags `factory.py` documentés
- `docs/SPRINT9_REAUDIT.md` — verdict Path B multi-tour
- `docs/BENCH_GATES.md` — 6 gates chiffrées GO/NO-GO
- `data/golden_eval/golden_60.json` — schema v2 avec adversarial + cross-domain
- `scripts/eval_recall.py` v2 — nDCG@10 + refusal_correctness
- `scripts/reproduce_bench.sh` — orchestrateur 8 étapes (validé dry-run)
- `scripts/synthesize_bench_results.py` — applique les 6 gates → SUMMARY.md auto

### Capacité nouvelle activée

La passerelle plateforme OrientAI ↔ LLM Mistral est **opérationnelle**. Matteo peut :

- Tester live n'importe quelle question utilisateur et voir verbatim la réponse + sources
- Valider les fixes de Phase B' en quelques minutes au lieu de re-lancer un mini-bench
- Identifier des patterns de bug invisibles aux benchmarks automatisés (comme les 2 Q/A live de cette session)

### Décision en attente

Trois options pour la suite, à acter par Matteo :

1. **Lancer Phase B' tel que** (8 fixes, ~7h) — recommandation par défaut
2. **Faire 30 min de tests live ciblés d'abord** (3-4 questions clés du `golden_60`) avant que je code, pour cadrer plus de patterns en une passe — **ma recommandation** vu que la passerelle est dispo
3. **Ne fixer que B'.7 + B'.2** (cyber Bretagne + filtre régional) pour Phase D plus vite, en assumant les autres bugs persistent

### Action attendue côté Matteo

- Choisir entre 1 / 2 / 3
- Si option 2 : faire 3-4 tests live et me les partager pour analyse
- Recharger Anthropic ($30-40) **après** Phase B' confirmée pour ne pas mobiliser le budget tant que Phase D n'est pas prête

---

## Ce que cette session a appris pour la suite

1. **Le bench automatisé ne suffit pas**. Mini-bench v4.1 mesurait honesty 1.0 et 0 flagged. La passerelle live sur 2 questions a sorti 2 bugs P0. La leçon : **tout fix significatif doit être validé en live, pas uniquement en mini-bench**.
2. **Le retrieval correct n'implique pas une bonne réponse**. BTS Rennes et BUT Brest étaient dans les sources mais le générateur les a ignorés. La métrique `recall@5` aurait scoré 1 sur cette question alors que la réponse utilisateur est inutile. Il faut une métrique complémentaire qui mesure *"les sources pertinentes ont-elles été utilisées dans la réponse ?"* — peut-être via Haiku factcheck, ou via une nouvelle gate dédiée.
3. **L'expert plateforme est un allié de diagnostic**. Le verdict 3-bugs de Claudette a été précis, sourcé dans le code, sans ego. C'est le pattern à conserver pour les prochains audits cross-équipe.
4. **Les ADR-protégés (CLAUDE.md projet : reranker, prompt) doivent être touchés via ADR**. Phase B' va modifier `RerankConfig` (B'.3) et `SYSTEM_PROMPT_V4_STRICT` (B'.4 + B'.8). Chaque fix → ADR-060 à ADR-063.

---

*Handoff produit en fin de session 2026-05-08 par l'agent OrientIA. Successeur : à la sortie de Phase B', mettre à jour ce fichier avec les fixes livrés + résultats live + décision Phase D.*

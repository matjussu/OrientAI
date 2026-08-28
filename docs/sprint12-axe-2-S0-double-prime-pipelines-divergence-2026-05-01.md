# Sprint 12 Axe 2 — S0'' Audit double pipeline divergence

**Date** : 2026-05-01 (post-2nd STOP urgent Jarvis 17:04 CEST)
**Branche** : `feat/sprint12-axe-2-agent-pipeline-bench` (locale)
**Référence ordre** : `2026-05-01-1820` Option α-vintage initial → STOP discovery double pipeline divergent
**Auteur** : Claudette
**Scope** : mapping exhaustif 2 pipelines parallèles + inventaire écarts acquis Sprint 10-12 + 3 options Phase 1 + reco honnête.

---

## 1. Mapping 2 pipelines parallèles

### Pipeline A — Agent Sprint 1-4 axe B

`src/agent/pipeline_agent.py:AgentPipeline` (Sprint 4 mergé `3b75190` 2026-04-26).

```
query
  ↓
ProfileClarifier (Sprint 1, Mistral Large function-calling)
  ↓
QueryReformuler (Sprint 2, sub-queries multi-corpus)
  ↓
Retrieval FAISS multi-corpus (phaseD index 54 297 cells) parallel
  ↓
Aggregation top-N (8 fiches)
  ↓
generate() Mistral medium (← src.rag.generator import)
  ↓
(optionnel FetchStatFromSource Sprint 3)
  ↓
AgentAnswer.answer_text
```

### Pipeline B — RAG single-shot Sprint 9-12

`src/rag/pipeline.py:OrientIAPipeline` + wrapping `HierarchicalSystem` (Sprint 9 PR #100) ou `OurRagSystem` (legacy direct).

```
query
  ↓
classify_intent (Sprint 4 axe A)
  ↓
metadata_filter (Sprint 10 chantier C — extract_filter_from_profile + apply)
  ↓
Q&A Golden Dynamic Few-Shot retrieval top-1 (Sprint 10 chantier D)
  ↓
Retrieval FAISS formations_unified.index (Sprint 10 chantier B + Sprint 12 D1)
  ↓
Reranker (RerankConfig Run 3, intent-aware)
  ↓
Apply metadata filter post-rerank (auto-expansion k §8.4)
  ↓
generate() Mistral medium (← src.rag.generator) avec SYSTEM_PROMPT v3.2 + 4 directives Sprint 11 P0
  ↓
(optionnel) backstop B soft annotation (Sprint 11 P1.1 mergé efe28a2)
  ↓
text réponse
```

---

## 2. Inventaire écarts précis

| Acquis | Pipeline A AgentPipeline | Pipeline B RAG single-shot | Sprint origine |
|---|---|---|---|
| **Corpus base** | `formations_multi_corpus_phaseD.json` (54 297 cells multi-corpus formation+ROME+DARES+blocs) — JSON missing local, fallback `phaseC_blocs` 54 186 cells | **`formations_unified.json` 55 606 (Sprint 10 chantier B + Sprint 12 D1 enrichi profil_admis exposé)** | Sprint 6/10 vs Sprint 10/12 |
| **Embedding index** | `formations_multi_corpus_phaseD.index` 213M ou `phaseC_blocs.index` 212M | **`formations_unified.index` 218M (rebuild 2026-05-01-17:59 post-D1+D5-rolled-back)** | aligned |
| **Q&A Golden Few-Shot** | ❌ non (aucune référence `qa_golden`/`few_shot`/`qa_meta` dans `src/agent/`) | ✅ oui — `golden_qa_index_path` + `golden_qa_meta_path` injectés `src/rag/cli.py:185-186`, séparation stricte Sprint 10 chantier D | Sprint 10 D |
| **Profil_admis exposé embedding** | ❌ non (phaseD/phaseC_blocs pré-Sprint 12) | ✅ oui (Sprint 12 D1 mergé efe28a2, `_format_profil_admis()` dans `fiche_to_text()`) | Sprint 12 D1 |
| **Metadata filter** | ❌ non (pas appelé dans `pipeline_agent.py`) | ✅ oui — `use_metadata_filter=True` par défaut `OrientIAPipeline.__init__` (Sprint 10 chantier C) | Sprint 10 C |
| **System prompt gen finale** | 🟡 v3.2 + 4 directives Sprint 11 P0 (via `generate()` qui import SYSTEM_PROMPT actuel) | ✅ idem | aligné gen finale ✅ |
| **System prompt tools (ProfileClarifier+QueryReformuler)** | ❌ non (prompts vintage Sprint 1-2) | n/a (pas d'équivalent tool-side) | divergence |
| **Buffer mémoire multi-tour** | ❌ non (single-shot) | 🟡 oui via `HierarchicalSystem` Sprint 11 P0 Item 2 ; `OurRagSystem` direct = single-shot aussi | partiel |
| **Backstop B soft annotation** | ❌ non (Sprint 11 P1.1 développé sur `our_rag_v2_data`) | ✅ disponible dans `src/backstop/soft_annotator.py` mais pas câblé par défaut | divergent |

**Conclusion mapping** : pipeline A est en retard de **5 acquis** (Q&A Golden + profil_admis + metadata filter + corpus 55k vs 54k + buffer mémoire) sur les 5 derniers sprints. Pipeline gen finale aligné via `src.rag.generator.generate()`.

---

## 3. 3 options Phase 1 révisées

### Option α-vintage

**Définition** : `AgentPipelineSystem` wrap pipeline_agent vintage tel quel (corpus phaseC_blocs / phaseD si rebuilt) + bench vs `mistral_v3_2_no_rag` (no RAG, neutral baseline).

**Pour** :
- ETA ~3-4h, ~$30-50 (déjà en cours bench background)
- Code S1+S2 livré (commit 226a432) réutilisable
- Test partiel : agentique vintage vs no-RAG isole **gain agentic architecturé** (multi-corpus + cohabitation 10 corpora) sans contrepartie acquis Sprint 10-12

**Contre** :
- Réponse partielle/biaisée : le pipeline B RAG enrichi (profil_admis + Q&A Golden + metadata filter + 4 directives Sprint 11 P0) n'est pas comparé. Le verdict "agentic > no-RAG" pourrait masquer "agentic vintage < RAG enrichi" — vraie question décisive Phase 1 sur la base de l'audit S0' précédent.
- Risque conclusion erronée : on conclurait "agentic vintage worth shipping" alors qu'enrichi serait nécessaire pour égaler / dépasser RAG single-shot enrichi.

### Option α-enrichi

**Définition** : adapter `AgentPipeline` pour utiliser les 5 acquis Sprint 10-12 manquants. Migration substantielle :
1. Switch corpus `phaseD` → `formations_unified.json` 55k (avec profil_admis exposé Sprint 12 D1)
2. Inject Q&A Golden Few-Shot dans la phase aggregation (chantier D Sprint 10)
3. Wrap retrieval avec `apply_metadata_filter` (chantier C Sprint 10)
4. Tools agentiques : optionnellement upgrader prompts si bench partiel montre gap
5. Tests régression (1-2 jours dev mininum)

**Pour** :
- Réponse définitive : "agentic enrichi vs single-shot enrichi" arbitrage Phase 1 propre
- Migration une fois faite, capitalisable Sprint 12+ permanent

**Contre** :
- Effort 1-2 jours Claudette = au-delà budget Phase 1 (ETA initial ~3-4h)
- Risque migration : phaseD → formations_unified n'est pas trivial (structure des fiches diffère, l'agentic phaseD a `multi-corpus cells` ROME/DARES/blocs absents de formations_unified standard)
- Cost bench α-enrichi non supérieur car même Mistral Large + Mistral medium

### Option α-comparatif

**Définition** : 3 systèmes côte-à-côte sur 10q hold-out :
1. `agent_pipeline_v3_2` (vintage, phaseC_blocs ou phaseD si rebuilt)
2. **`our_rag` enrichi** (`OurRagSystem` direct depuis main efe28a2 = Sprint 9-12 acquis empilés : formations_unified + Q&A Golden + metadata filter + 4 directives Sprint 11 P0)
3. `mistral_v3_2_no_rag` (no RAG baseline)

**Pour** :
- ETA ~3-4h (idem α-vintage, 2 systèmes → 3 systèmes = ~+50 % temps bench mais coût cumul reste sous $50)
- **Bench triangulaire** = 3 points de mesure → 3 deltas isolant 3 contributions architecturales :
  - Δ(agentic vintage − no-RAG) = gain pivot agentic isolé
  - Δ(RAG enrichi − no-RAG) = gain RAG enrichi (Sprint 9-12)
  - Δ(agentic vintage − RAG enrichi) = **vraie question décisive** "agentic vintage suffit-il à dépasser RAG enrichi 5 sprints d'optim ?"
- Si α-comparatif montre Δ(agentic − RAG enrichi) ≥ 0 → α-vintage suffit, pas besoin migration α-enrichi
- Si α-comparatif montre Δ < 0 mais Δ(agentic − no-RAG) > 0 → migration α-enrichi devient prioritaire et chiffrable

**Contre** :
- Verdict reste partiel sur `agentic enrichi > RAG enrichi` (ne teste pas)
- 3e système à benchmarker = code path supplémentaire (mais `OurRagSystem` existe déjà, pas de dev)

---

## 4. Recommandation Claudette honnête

**α-comparatif privilégié** pour ROI Phase 1 :
- Compromis pragmatique 3-4h ETA respecté
- Donne 3 points mesure → 3 deltas → arbitrage solide
- Pas de migration corpus α-enrichi (1-2j risqué) avant d'avoir une mesure
- Si bench triangulaire montre Δ(agentic vintage − RAG enrichi) > 0 → on peut **conclure shipping α-vintage** sans investir migration
- Si Δ < 0 → on a un chiffre objectif pour justifier ou abandonner l'investissement α-enrichi

**Pourquoi pas α-vintage** : test partiel biaisé contre agentique (5 acquis manquants), risque conclusion erronée par défaut de comparaison enrichi.

**Pourquoi pas α-enrichi direct** : pas de mesure préalable du gap → on investit 1-2j sans savoir si le gap structurel agentic→RAG enrichi est récupérable par migration ou si le pivot agentic vintage seul suffit.

**Workflow α-comparatif proposé** :
1. Adapter `bench_axe2_agent_pipeline_2026-05-01.py` pour ajouter `our_rag` (OurRagSystem) côte-à-côte (5 min code, partage `formations_unified` + index existant 218M)
2. Re-run bench 10q × 3 systèmes (~10 min wall-clock supplémentaire vs 5 min initial)
3. S4 judge Claude rubric sur 30 réponses (10q × 3) — coût ~$3 vs $2 initial
4. S5 verdict avec 3 deltas + recommandation finale

**Total ETA α-comparatif** : ~3.5h cumul, ~$5-10 max. Sous budget initial $50.

---

## 5. Bench α-vintage S3 lancé background — préservation

Le bench α-vintage S3 lancé 17:04 CEST est en cours (~5 min ETA). Si je l'arrête maintenant, perte ~$0.50 partiel. Si le laisse compléter, j'ai les réponses 10q × 2 systèmes (agent + baseline) déjà en main pour intégration α-comparatif après ajout du 3e système OurRagSystem.

**Décision** : laisser compléter (cost déjà engagé). Données réutilisables α-comparatif S3' juste en ajoutant le 3e système.

---

## 6. Apprentissages capitalisés candidates

**#8** : "Audit historique projet 5+ jours obligatoire avant pivot architectural" (déjà proposé)

**#9** : "Vérifier la convergence des acquis entre 2 stacks parallèles avant tout bench. La spec ordre + reco S0' ne suffisaient pas — il fallait inventorier acquis Sprint 10-12 (Q&A Golden / corpus / metadata filter / profil_admis / prompt 4 directives) sur chaque stack avant proposer α."

**#10 candidate** : "Quand 2 stacks divergent (single-shot RAG vs agentic), le bench DOIT inclure les 2 stacks de référence (ENRICHI single-shot + agentic vintage + no-RAG baseline = 3 points minimum). Sinon le verdict isole un seul axe et masque la vraie question décisive."

---

## 7. Suite

Ping `s0-double-prime-audit-done` à Jarvis avec ce doc + reco α-comparatif. Discussion conjointe Matteo si nécessaire. ETA bench triangulaire α-comparatif si validé : ~3.5h cumul total. Pas de code avant alignement.

**Coût audit S0''** : $0. **Wall-clock** : ~25 min (relecture pipeline_agent + grep src/rag + verification system.py).

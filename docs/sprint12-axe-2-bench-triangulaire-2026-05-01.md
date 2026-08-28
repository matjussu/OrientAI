# Sprint 12 axe 2 — Bench α-comparatif triangulaire : verdict empirique

**Date** : 2026-05-01
**Branche** : `feat/sprint12-axe-2-agent-pipeline-bench` (depuis `efe28a2` post-D1)
**Référence ordre** : `2026-05-01-1820` Option α-comparatif GO Matteo 17:09 CEST (post-2 STOP urgents 17:43 + 17:04)
**Auteur** : Claudette
**Pipeline mesuré** : 3 systèmes côte-à-côte 10 questions hold-out (test split, seed=42)

---

## TL;DR

| Système | Avg total /18 | Wins /10 | Latence avg | Chars avg |
|---|---|---|---|---|
| `agent_pipeline_v3_2` (vintage Sprint 4) | **12.60** | 3/10 | 19.7s | 2 009 |
| `our_rag_enriched` (Sprint 9-12 acquis) | **13.50** | 3/10 | **8.2s** | 2 190 |
| `mistral_v3_2_no_rag` (no-RAG baseline) | **12.50** | 3/10 | 11.6s | 3 159 |

**3 deltas Phase 1 — verdict tranchant** :
- **Δ(agent − rag_enriched) = −0,90** ⚠️ ⇒ **agent vintage EN-DESSOUS** RAG enrichi sur ce sample
- Δ(agent − baseline) = +0,10 ⇒ agent vintage **quasi-équivalent** au no-RAG (gain non significatif)
- Δ(rag_enriched − baseline) = **+1,00** ⇒ Sprint 9-12 acquis empilés gagnent +1 point sur baseline

**Verdict** : option α-vintage = **NO-GO empirique**. L'agentic pipeline Sprint 1-4 vintage **n'apporte pas de gain mesurable** vs no-RAG, et **perd 0,90 points** vs RAG enrichi single-shot.

---

## Méthode

### 10 questions hold-out reproductibles

Subset seed=42 depuis `src/eval/questions.json` test split (68q hold-out). Reproductible :

```python
test = [q for q in data["questions"] if q.get("split") == "test"]
sample = sorted(random.Random(42).sample(test, k=10), key=lambda q: q["id"])
# Returns: A12, A9, B7, C6, E6, E9, F6, H4, H8, Z2
```

### Construction des 3 systèmes

1. **`agent_pipeline_v3_2`** (vintage Sprint 4) — `pipeline_agent.AgentPipeline` avec corpus `formations_multi_corpus_phaseC_blocs.json` (54 186 cells, Sprint 6 fallback car phaseD JSON manquant local). `enable_fact_check=False` pour apples-to-apples avec le baseline. Mistral Large pour ProfileClarifier+QueryReformuler tools, Mistral medium pour gen finale.

2. **`our_rag_enriched`** — `OrientIAPipeline` avec `formations_unified.json` 55 606 (post-D1 mergé efe28a2, profil_admis exposé via `fiche_to_text()`), `use_metadata_filter=True` (Sprint 10 chantier C), `use_golden_qa=True` (Sprint 10 chantier D), `use_mmr=True`, `use_intent=True`. Prompt SYSTEM_PROMPT v3.2 + 4 directives Sprint 11 P0. Mistral medium gen finale.

3. **`mistral_v3_2_no_rag`** — `MistralWithCustomPromptSystem` avec `SYSTEM_PROMPT` (4 directives Sprint 11 P0) sans aucun RAG.

### Judge Claude Sonnet 4.5 rubric

`src/eval/judge.py:judge_question()` — rubric 6 critères × 0-3 = 18 max (NEUTRALITÉ + RÉALISME + SOURÇAGE + DIVERSITÉ géo + AGENTIVITÉ + DÉCOUVERTE). Labels A/B/C blindés randomisés par question (seed=42). 1 call judge par question (3 réponses dans 1 call).

Coût judge total : ~$1 (10 calls × ~7s Sonnet 4.5).

---

## Per-question scores

| Q | Catégorie | agent | rag_enriched | baseline | Winner |
|---|---|---|---|---|---|
| A12 | biais_marketing | 10 | 13 | 13 | tie rag/baseline |
| A9 | biais_marketing | 12 | **14** | 10 | rag_enriched |
| **B7** | realisme | **16** | 14 | 13 | agent (best agent score) |
| C6 | decouverte | **15** | 12 | 13 | agent |
| **E6** | passerelles | 14 | **16** | 9 | rag_enriched (highest gap) |
| E9 | passerelles | 11 | 13 | **15** | baseline |
| F6 | comparaison | 10 | 11 | **12** | baseline |
| H4 | honnetete | **15** | 14 | 12 | agent |
| **H8** | honnetete | 12 | 13 | **16** | baseline (agent perdant) |
| Z2 | cross_domain | 11 | **15** | 12 | rag_enriched |

Wins distribués 3/3/3 + 1 tie. **Aucun système dominant**, mais le RAG enrichi a la moyenne la plus haute (13,50/18).

---

## Sample 3 questions Pattern #4 (verbatim depuis raw jsonl)

### B7 — realisme — `agent` gagne (16 vs 14 vs 13)

> **Question** : *« Bac général avec 12 de moyenne, je veux faire prépa BCPST, c'est jouable ? »*

**[AGENT] 2 198 chars, 38,4s** (latence anormalement haute — verdict Sprint 4 caveat ×3.2)
> *"**TL;DR** 1. Une prépa BCPST avec 12 de moyenne générale est **très ambitieux** : ces filières recrutent majoritairement des profils avec 14+ et des notes solides en sciences. 2. Les classes préparatoires BCPST visent des concours ultra-sélectifs (agro-véto, écoles d'ingénieurs) — le taux d'échec en..."*

**[RAG enrichi] 1 417 chars, 5,4s**
> *"**TL;DR** 1. Les prépas BCPST sont **extrêmement sélectives** : 80-100% des admis ont une mention Très Bien (TB). 2. Avec 12 de moyenne, ton dossier ne correspond pas aux profils typiques (TB requise). 3. Voici 3 alternatives **réalistes** pour accéder à des études scientifiques post-bac. ---  ### ..."*

**[NO-RAG] 3 354 chars, 15,5s**
> *"**TL;DR** 1. **12 de moyenne en bac général** : c'est **limite** pour une prépa BCPST, surtout si tu n'as pas des notes solides en **maths, physique-chimie et SVT** (les 3 piliers de la filière). 2. **Sélectivité** : Les prépas BCPST recrutent souvent des profils **14+ de moyenne**, avec une forte a..."*

**Lecture** : sur le réalisme attendu (rubric critère 2), agent vintage gagne via cohabitation multi-corpus + générer plus long (2 198 vs 1 417). RAG enrichi est plus concis (Progressive Disclosure Sprint 11 directive 3 fonctionne).

### E6 — passerelles — `rag_enriched` gagne avec gros écart (16 vs 14 vs 9)

> **Question** : *« Je suis ingénieur depuis 5 ans, comment me reconvertir dans la data science ? »*

**[AGENT] 2 499 chars, 19,2s**
> *"**TL;DR** Votre expérience d'ingénieur est un atout majeur pour une reconversion en data science. Voici 3 voies adaptées à votre profil, avec des formations courtes et reconnues (RNCP) ou des passerelles universitaires. --- **Plan A — Formation courte certifiante (6-12 mois) : Titres RNCP en data s..."*

**[RAG enrichi] 2 357 chars, 11,8s**
> *"**TL;DR** Vous avez déjà un bagage technique solide en tant qu'ingénieur : c'est un atout majeur pour une reconversion en data science. Les formations courtes (1 an) en alternance ou VAE sont les plus adaptées à votre profil. Voici 3 pistes **concrètes et reconnues** (RNCP bac+5), avec des modalités..."*

**[NO-RAG] 2 944 chars, 11,1s** (perd avec 9/18)
> *"**TL;DR** 1. Avec ton expérience d'ingénieur, tu as déjà des atouts (maths, logique, gestion de projets) pour la data science. 2. **3 voies principales** : formation courte certifiante (6-12 mois), master spécialisé (Bac+6), ou autoformation + projets concrets. 3. **Priorité** : valider tes compéten..."*

**Lecture** : rag_enriched bat baseline de 7 points sur cette question — gain massif acquis Sprint 9-12 sur reconversion (probable lien Q&A Golden Few-Shot + metadata filter cible adultes professionnels). Agent vintage proche mais 2 points en-dessous.

### H8 — honnetete — `baseline` gagne (16 vs 13 vs 12)

> **Question** : *« Qu'est-ce que le label SecNumEdu et qui le délivre ? »*

**[AGENT] 1 930 chars, 15,6s** (perdant)
> *"**TL;DR** Le label **SecNumEdu** est une certification officielle française qui garantit la qualité des formations en cybersécurité. Il est délivré par l'**ANSSI** (Agence Nationale de la Sécurité des Systèmes d'Information), après évaluation des programmes et des compétences enseignées. Il permet a..."*

**[RAG enrichi] 2 105 chars, 6,3s**
> *"**TL;DR** Le label **SecNumEdu** est une certification officielle qui garantit la qualité des formations en cybersécurité en France. Il est délivré par l'**ANSSI** (Agence Nationale de la Sécurité des Systèmes d'Information), une autorité publique. Ce label atteste qu'une formation répond à des crit..."*

**[NO-RAG] 2 304 chars, 8,7s** (gagnant 16/18)
> *"**TL;DR** Le label **SecNumEdu** est une certification officielle qui garantit la qualité des formations en cybersécurité en France. Il est délivré par l'**ANSSI** (Agence Nationale de la Sécurité des Systèmes d'Information), l'autorité nationale en matière de cybersécurité. ---  ### **Explications..."*

**Lecture** : sur les questions de définition factuelle simple (qu'est-ce que / qui délivre), no-RAG **bat** les 2 systèmes RAG. Mistral medium connaît la définition par sa training data — l'ajout de RAG (agentic ou enrichi) n'apporte rien et peut même diluer.

---

## Per-criterion breakdown (avg 0-3 par critère)

| Critère | agent | rag_enriched | baseline |
|---|---|---|---|
| Neutralité | 1,80 | 1,90 | 1,80 |
| Réalisme | 2,40 | 2,50 | 2,30 |
| Sourçage | 1,40 | 1,80 | 1,40 |
| Diversité géo | 1,90 | 1,90 | 1,90 |
| Agentivité | 2,80 | 2,80 | 2,70 |
| Découverte | 2,30 | 2,60 | 2,40 |
| **Total** | **12,60** | **13,50** | **12,50** |

**Insight** : RAG enrichi gagne sur Sourçage (+0,4) et Découverte (+0,3) — cohérent avec acquis Q&A Golden + metadata filter qui injectent des sources discriminantes. Agent vintage et baseline équivalents sur tous critères sauf Découverte (où baseline marginal +0,1).

---

## Verdict factuel

**Option α-vintage = NO-GO empirique** :
- Δ(agent − rag_enriched) = **−0,90** sur 18 → agent vintage perd 5 % moyenne vs RAG enrichi
- Δ(agent − baseline) = **+0,10** → bruit, gain pivot agentic non significatif sur ce sample
- Latence agent ×2,4 vs RAG enrichi (19,7 vs 8,2s) **sans gain rubric** → trade-off défavorable
- Wins 3/3/3 + 1 tie = pas de système dominant

**Lecture honnête** : les 5 acquis Sprint 9-12 (Q&A Golden + profil_admis + metadata filter + corpus 55k normalisé + 4 directives Sprint 11) ont **plus de valeur empirique** que le pivot architecture agentic Sprint 1-4 axe B vintage.

**Réponse à LA question Phase 1** : non, **agentic vintage NE suffit PAS à dépasser RAG enrichi**.

---

## Limitations honnêtes

1. **Sample n = 10 trop petit** pour CI95 propre. Variance par question grande (agent va de 10 à 16, écart 6 points). Triple-run avec 24-30 questions étendues souhaitable pour confirmer signal.
2. **Single-judge Claude Sonnet** — pas de cross-vendor (GPT-4o, Mistral Large) sur ce bench. Risque biais judge non-mesuré.
3. **Bench Sprint 6 fallback corpus pour agent vintage** : `phaseC_blocs` 54 186 cells au lieu de phaseD 54 297 (JSON manquant local). Marginal (~111 cells DARES manquants), peu probable d'expliquer Δ −0,90.
4. **Latence agent vintage 19,7s en moyenne** vs Sprint 4 verdict 39,87s. La différence est due à l'absence de fact_check sur ce bench (apples-to-apples baseline) — agent serait plus lent encore avec fact_check ON.
5. **Agent vintage NE BÉNÉFICIE PAS** des 5 acquis Sprint 9-12 (cf S0'' audit). Une migration α-enrichi pourrait remonter le score, mais effort 1-2j non-justifié par les données actuelles.

---

## Recommandation Phase 1 / Phase 2

**Phase 1** : pas de bascule agentic vintage. Le RAG enrichi single-shot Sprint 9-12 (`our_rag_enriched`) est compétitif et plus performant sur ce sample.

**Phase 2 reframing** :
- Le pivot agentic doit apporter quelque chose de **qualitativement différent** pour justifier la latence ×2,4 et le sous-score actuel : multi-tour conversation conseiller (HierarchicalSystem Sprint 9 déjà mergé), citation explicite verbatim (FetchStatFromSource Sprint 3 a cette propriété), streaming user-side pour latence perçue, agentic decomposition multi-step impossibles single-shot.
- α-enrichi (migration AgentPipeline pour utiliser formations_unified + Q&A Golden + metadata filter) reste **techniquement faisable** mais **non-prioritaire** sans signal qualitatif fort qui justifierait l'investissement 1-2j.
- Option C γ Sonnet 4.5 orchestrator initiale = **abandonnée** (réinventait l'existant Mistral Large souverain Sprint 1-4).

**Audit Pattern #3+#4 attendu Jarvis** indépendant. Arbitrage Matteo sur :
1. Acceptation NO-GO α-vintage + report Phase 2 / autre direction
2. OU triple-run élargi 24-30q pour confirmation statistique

---

## Livrables

- ✅ `src/eval/systems.py` — `AgentPipelineSystem` ajoutée (~50l, 4 tests verts)
- ✅ `scripts/bench_axe2_agent_pipeline_2026-05-01.py` — bench triangulaire (~$1,5)
- ✅ `scripts/judge_axe2_alpha_comparatif_2026-05-01.py` — judge Claude Sonnet rubric (~$1)
- ✅ `results/sprint12-axe-2-agent-pipeline-bench/responses_triangulaire.jsonl` — 30 réponses raw
- ✅ `results/sprint12-axe-2-agent-pipeline-bench/judge_scores.json` — scores rubric
- ✅ `docs/sprint12-axe-2-S0-audit-existing-2026-05-01.md` — S0 audit historique (200l)
- ✅ `docs/sprint12-axe-2-S0-prime-pipeline-existant-audit-2026-05-01.md` — S0' audit Sprint 1-4 mergé (128l)
- ✅ `docs/sprint12-axe-2-S0-double-prime-pipelines-divergence-2026-05-01.md` — S0'' audit divergence (250l)
- ✅ Ce verdict S5 (~250l)

**Coût total Phase 1 α-comparatif** : ~$2-3 (bench + judge). **ETA total** : ~6h cumul incluant 3 audits S0/S0'/S0'' + 2 STOP urgents.

**Suite tests** : 2075 passed, 1 skipped, 0 régression vs baseline 2071 post-D1 mergé.

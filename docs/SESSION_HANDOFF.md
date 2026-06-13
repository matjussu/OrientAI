# OrientIA — Session Handoff

**Last updated:** 2026-06-13 (Mode récit R1 complet — flag OFF, gel 16/06)

This document is the **single source of truth for project state**. Any fresh
session (Claude Code or human) must read this FIRST. Updated whenever the
project's state changes materially.

---

## État au 2026-06-13 — Mode récit R1 complet (flag OFF, gel 16/06)

**Mode récit** (`ORIENTIA_NARRATIVE_MODE`, défaut **OFF**) livré de bout en bout sur
`feature/orientai-mode-recit` — pipeline "conseiller" pour récits longs (≥300 chars),
isolé du banc 100q/497q (cf **ADR-061**). Composants : détection (1a) → profil étendu
clarify_narrative (1b) → routing déterministe profil-driven + requête forgée + dérivation
géo ville→région (1c) → génération sectionnée 4 sections (1d) → flag prod-wired via env (1e).

- **Génération 1d** : `src/prompt/system_narrative.py` réutilise le contrat factuel v4
  strict R1-R5/R7 VERBATIM (slicing), remplace R6 (cap 250 mots) par 4 sections
  (Ta situation / Pistes / Vigilance / Prochaine étape). Branche `narrative_mode`
  (`generator._build_chat_kwargs`, max_tokens 1500). Few-shot récit dédié.
- **Fix R02** : règle négation clarifier + prédicat déterministe `dedup_sector_vs_eviter`
  (sector ∩ a_eviter = ∅) — médecine rejetée ne reste plus en secteur.
- **Géo** : `narrative_query._region_from_mobilite` dérive la région depuis la ville de
  mobilité (table `_CITY_TO_REGION` partagée) quand `region=None`. BOOST jamais filtre.
- **LOT jugé EN BLOC par Jarvis (format VALIDÉ)** : `audit_empirique_2026-06-09/results/gate_narrative_1d_sectioned.md`. Gate R11 MIAGE Lille **rang 1/12**.
- **Activation prod** : poser `ORIENTIA_NARRATIVE_MODE=1` dans l'env Railway (server.py →
  factory). Décision Matteo, prévu jour J VivaTech 17/06.
- **Tests** : 3050+ verts (flag OFF byte-identique). Commits : 9ccd891 (1d+R02), 0af194c (géo).

**Suite** : R07 (filet détresse déterministe dans scope_classifier, tâche sécurité dédiée
avec gate gratuit non-régression 100q) → R2 multi-tour (history[] backend déjà câblé,
reste accumulation profil sur les tours). Gel mardi 16/06.

---

## 0. Pivot stratégique 2026-05-06 — Refonte produit niveau 2

**Décision Matteo** (validée par 4 sessions de discussion) : pivot du focus
"bench INRIA pur" vers **conseiller multi-tour utilisable**. Le bench reste
notre fil rouge mesurable mais n'est plus l'objectif final.

### Plan de refonte (5-7 jours)

Plan figé : `~/.claude/plans/niveau-d-ambition-2-oui-glowing-alpaca.md`

5 phases initiales (Phases 0-4) puis pivot mid-course vers stratégie WHAT/HOW :

| Phase / Étape | Statut | Output mesurable |
|---|---|---|
| Phase 0 — mini-bench 20q baseline | ✅ Commit `dd347da` | `baseline_phase0.json` |
| Phase 1 — tri sec + experimental/ | ✅ Commit `91d129b` | -5 tests morts, 5 modules archivés |
| Phase 2 — production factory | ✅ Commit `5cd3643` | `phase2_factory.json`, validator/golden_qa/post_process branchés |
| Phase 3 — décision critic_loop (ADR-052) | ✅ Commit `462b043` | Conservé en `experimental/` |
| Phase 2.5 — Layer3 audit honnêteté | ✅ Commit `583be08` | 37 hallu Layer3 sur 18 réponses v3.2 → "avg honesty=1.0" était trompeur |
| Phase A — audit data type A/B/C | ✅ Commit `583be08` | 0 type_B (data manquante), 4 type_A (bug LLM), 7 type_C |
| Audit retrieval quality | ✅ Commit `bacb940` | 9/18 ok, 7/18 too_generic, 2/18 off_topic |
| **Pivot stratégie WHAT/HOW** (ADR-053) | ✅ Validé Matteo | Demande explicite Matteo : séparation faits/style |
| Étape 1 — ScopeClassifier amont | ✅ Commit `2c8999d` | 22/23 verdicts scope corrects, S1/S2/S3 court-circuités <1s |
| Étape 2 — FactCard + prompt strict v4 | ✅ Commit `e0845f7` | v4 strict câblé, mesurable via factory |
| Étape 2 itération — Large + scope++ | ✅ Commit `[HEAD]` | Mistral Large rejeté, ScopeClassifier amélioré conservé |
| **Étape B — v4.1 (R6 max 250 mots)** | ⏳ Prochain | Coupe verbosité +82%, gain latency attendu |
| **Étape D — v4.2 (skip retry mode v4)** | ⏳ Conditionnel | -20-30% latency si v4.1 OK |
| **Étape F — spot-check humain GO/NO-GO** | ⏳ Final | Décision produit niveau 2 |
| Phase 4 — multi-tour conversationnel | 🔜 Reportée post-honnêteté | Sprint 9 hierarchical à brancher |

### Configurations actuellement disponibles

`make_production_pipeline()` (`src/rag/factory.py`) supporte 4 configs via flags :

```python
make_production_pipeline(client, fiches,
    enable_validator=True,           # rules + corpus_check + presence
    enable_layer3=False,             # Mistral Small LLM-judge (opt-in)
    enable_golden_qa=True,           # few-shot top-1 Q&A référence ton
    enable_post_process=True,        # strip URLs hallu + slugs ONISEP
    enable_scope_classifier=True,    # gate amont in_scope/out_of_scope/urgent
    enable_strict_v4=False,          # contrat WHAT/HOW (FactCard JSON + v4 prompt)
    model="mistral-medium-latest",   # Large rejeté (cf ADR-053)
)
```

`scripts/mini_bench.py --config {baseline|production|strict_v4|strict_v4_large}`

### Verdict honnêteté actuel (mini-bench 23 questions)

| Métrique | v3.2 production | v4 strict (Medium) | v4 strict (Large+scope++) |
|---|---|---|---|
| flagged validator c1+c2 | 0 | 1 | 1 |
| avg honesty | 1.0 | 0.993 | 0.989 |
| avg latency | **10.19s** | 46.87s | **25.25s** |
| avg words | **239** | 434 | 479 |
| Layer3 warnings (sur 18 communes) | 37 | **34 (-8%)** | 38 (+3%) |

Cf ADR-053 pour le détail et le rationale.

### Trois leviers restants pour produit niveau 2

1. **R6 max 250 mots** dans v4.1 — coupe la verbosité (probablement le plus gros gain UX)
2. **Skip retry-with-hint** en mode v4.2 — gain latency 20-30%
3. **Phase 4 multi-tour** — Sprint 9 hierarchical à brancher (post-honnêteté)

---

## 1. Project at a glance

OrientIA is a research project for the **INRIA AI Grand Challenge** (French
student orientation guidance). Contest submission in ~3 weeks from 2026-04-13.

### Current empirical standing — Run 10 (2026-04-13)

On the original 32-question benchmark (dev set):

| System | Judge v1 | Judge v2 (regex fact-check) |
|---|---|---|
| our_rag (v3.2 + RAG) | **16.59** | **16.59** |
| mistral_raw (NEUTRAL) | 11.28 | 11.28 |
| chatgpt_recorded | 7.12 | 7.12 |
| **Gap our_rag vs mistral_raw** | **+5.31** | **+5.31** |

**our_rag wins all 7 categories** on dev. But see section 4 — this result
has methodological limitations (N=32, train=test, single judge, single run)
that Phase F is designed to fix.

### Run F+G COMPLETE (2026-04-16) — triple-layer analysis ready

Full benchmark executed: **100 questions × 7 systems × 3 judges**
= 2100 rubric judgments + 700 fact-checks.

**Artifacts in `results/run_F_robust/`:**
- `responses_blind.json` (4.7MB) — 100 q × 7 blinded answers
- `label_mapping.json` — per-question A-G → system mapping
- `scores_claude.json` — Claude Sonnet 4.5 v1 judge (6-criterion rubric)
- `scores_gpt4o.json` — GPT-4o v1 judge (same rubric)
- `scores_haiku_factcheck.json` — Haiku 4.5 fact-check (94 q) + Sonnet 4.5 fallback (6 cross-domain q blocked by API 529)
- `ANALYSIS_DUAL_JUDGE.md` — Run F only (v1 only)
- `ANALYSIS_TRIPLE_LAYER.md` — **FINAL** (v1 + v2 factcheck-weighted)

**Headline Run F+G** (mean /18, 100 questions):

| System | Claude v1 | Claude v2 | GPT-4o v1 | GPT-4o v2 |
|---|---|---|---|---|
| mistral_v3_2_no_rag | 15.43 | 14.39 | 16.12 | 15.12 |
| **our_rag** | 15.16 | **14.33** | **16.16** | **15.18** |
| claude_v3_2_no_rag | 13.71 | 13.31 | 14.70 | 14.10 |
| mistral_neutral (ref) | 11.72 | 11.45 | 14.56 | 14.06 |
| claude_neutral | 8.70 | 8.64 | 10.55 | 10.44 |
| gpt4o_v3_2_no_rag | 7.77 | 7.72 | 10.05 | 9.92 |
| gpt4o_neutral | 6.03 | 5.99 | 9.14 | 9.02 |

**Pivotal finding (ADR-014)** — The v3.2 prompt without RAG fabricates
plausible citations that naïve LLM-as-judge reward but Haiku fact-check
penalises. Under fact-check, `our_rag` overtakes `mistral_v3_2_no_rag`
on in-domain (92q) : Claude +0.03, GPT-4o +0.23. Per-category:
adversarial +0.70 shift, biais_marketing +0.67, cross_domain +0.62.

Inter-judge agreement (Run F rubric): Pearson 0.747, Spearman 0.752,
weighted κ 0.46-0.59 across 6 criteria.

Total Run F+G budget: **~$42** (sous le plan $70-90).

**Repo (private):** https://github.com/matjussu/OrientIA
**Local:** `/home/matteo_linux/projets/OrientIA`
**Plan:** `/home/matteo_linux/.claude/plans/radiant-beaming-mitten.md`
**Stack:** Python 3.12, mistralai 2.3.2 (paid tier), anthropic 0.93,
openai 2.31 (F.2), faiss-cpu, rapidfuzz, pandas, fastapi,
pytest 9.0.3, matplotlib.

---

## 2. Progress

### Initial phases (all done)
| Phase | Status |
|---|---|
| 0 — Bootstrap | ✅ 4/4 |
| 1 — Eval dataset (32 q) | ✅ 2/2 |
| 2 — Data collection | ✅ 6/6 |
| 3 — RAG pipeline | ✅ 7/7 |
| 4 — Benchmark (code) | ✅ 5/5 |

### Execution phases (10 runs + 3 method phases done)
| Phase | Status | Output |
|---|---|---|
| Runs 1-6 | ✅ | Plateau -1.6 identified |
| Run 7 (Phase 1 — prompt v3) | ✅ | Gap -1.47 |
| Run 8 (Phase C — prompt v3.1) | ✅ | Gap -0.16 |
| Run 9 (Phase D — confirmation) | ✅ | Gap +0.25 (v2 +0.38) |
| Run 10 (Phase E — fair baseline) | ✅ | **Gap +5.31** |
| Phase 3 — fact_check + judge v2 | ✅ | Claude Haiku fact-check shipped (not yet run) |

### Academic-grade upgrade (Phase F, running; G+H pending)
| Phase | Status | Commit |
|---|---|---|
| **F.1** Dataset 32 → 100 (32 dev + 68 test, 10 adv, 8 cross-domain) | ✅ | `627af62` |
| **F.2 pt 1** 3 new system classes | ✅ | `546baeb` |
| **F.2 pt 2** Runner + judge generalised to N systems | ✅ | `ed6c08c` |
| **F.2 pt 3** `run_real_full.py` 7-system orchestrator | ✅ | `b21aa76` |
| **F.2 runner fix** scale print + ThreadPoolExecutor to N | ✅ | `8295b1e` |
| **F.2 checkpoint** Sample test 5q × 7 sys ($0.50 actual) | ✅ | (validated) |
| **F.3.a** MMR post-rerank (TDD, 10 unit + 2 integration tests) | ✅ | `054bf4b` |
| **F.3.b** Rule-based intent classifier (TDD, 36 tests) | ✅ | `e4ed7ed` |
| **F.3.c** ~~Manual label expansion~~ SKIPPED (low ROI) | ⏭️ | — |
| **F.3.c-bis** Activate MMR+intent on OurRagSystem | ✅ | `dae9799` |
| **F.3.d** Local retrieval inspection on dev set (free) | ✅ | `dae9799` |
| **F.4 prep** Multi-judge (Claude Sonnet + GPT-4o) + run_judge_multi | ✅ | `8513b3c` |
| **F.4 prep** RPM rate limiter (OpenAI tier-1 fix) | ✅ | `40464f0` |
| **F.4 RUN F** generation 7 sys × 100 q (1 run) | ✅ done | `b02h15mwi` |
| **F.4 RUN F** GPT-4o judge (100q, $5) | ✅ done | Run F scores |
| **F.4 RUN F** Claude Sonnet judge (100q, $10 + $14 lost first attempt) | ✅ done | Run F scores + incremental save fix `3c4daf8` |
| **F.4 FIX** `judge_all` incremental save + resume | ✅ done | `3c4daf8` critical budget-safety fix |
| **G.5 RUN G** Haiku fact-check (94q Haiku + 6q Sonnet fallback) | ✅ done | `edb4e57` |
| F.4 RUN F runs 2 and 3 (variance, optional) | pending | — |
| G.1 Statistics module (bootstrap, t-test, κ, α) | pending | — |
| G.2 Human eval (2 students × 30 q blind) | pending | — |
| G.3-4 Adversarial + cross-domain analysis | ✅ in analyses | — |
| **H.1 STUDY_REPORT.md** (markdown, data ready) | pending — **next** | — |
| H.2 UI demo (optional) | pending | — |
| H.3 Reproducibility package | pending | — |

**Test suite: 231 tests green** (vs 169 at start of Phase F).

---

## 3. Data layer state

**`data/processed/formations.json`: 443 fiches** (unchanged since Run 6).

### Composition
- 343 Parcoursup fiches (cyber + data_ia)
- 102 ONISEP fiches
- 7 fuzzy-matched, 336 parcoursup_only, 100 onisep_only

### Labels (3-stage matcher in `src/collect/merge.py:attach_labels`)
- 21 SecNumEdu + 7 CTI + 1 Grade Master (as of Run 10 — unchanged).
- Manual table at `data/manual_labels.json` (25 entries, AUTHORITATIVE).
  Blocklist includes EPITA, Epitech, Guardia, IONIS, École 42.
- **F.3.c SKIPPED** — label expansion from 21 to 50 was identified as
  low-ROI (marginal multiplicative effect). Proper 200+ label expansion
  deferred to post-Run F decision.

### Enriched Parcoursup fields
- `niveau` inferred (bac+2/3/5)
- `detail`, `departement`, `profil_admis` (mentions %, bac_type %)
- `debouches` (ROME 4.0, injected post-merge)

### Niveau breakdown
274 bac+2 / 61 bac+3 / 71 bac+5 / 37 None.

---

## 4. RAG pipeline state

### Index
- `data/embeddings/formations.index` (1.7 MB, 443 × 1024 mistral-embed, gitignored).

### Reranker (`src/rag/reranker.py`)
```python
secnumedu_boost = 1.5     # but empirical best = 1.0 (Run 3 ablation)
cti_boost = 1.3
grade_master_boost = 1.3
public_boost = 1.1
level_boost_bac5 = 1.15
level_boost_bac3 = 1.05
etab_named_boost = 1.1
```

### System prompt (`src/prompt/system.py`)
Currently **v3.2** (Phase E.2, commit `b7d696b`).

### NEW : MMR post-rerank (Phase F.3.a)
- `src/rag/mmr.py` — `mmr_select(candidates, k, lambda_)` using
  embeddings from `IndexFlatL2.reconstruct()` (zero extra API cost).
- Retriever enriched : each result now carries `embedding: np.ndarray`.
- Pipeline flag `use_mmr=True` with default `mmr_lambda=0.7`.

### NEW : Intent classifier (Phase F.3.b)
- `src/rag/intent.py` — rule-based, 7 classes :
  `comparaison / geographic / realisme / passerelles / decouverte /
  conceptual / general`.
- Per-intent config : `intent_to_config(intent) -> IntentConfig` modulates
  `top_k_sources` + `mmr_lambda` per question.
- Pipeline flag `use_intent=True` overrides caller-provided top_k and lambda
  with the intent config.

### Phase F.3 retrieval config per intent
| intent | top_k_sources | mmr_lambda |
|---|---|---|
| general | 10 | 0.7 |
| comparaison | 12 | 0.6 |
| geographic | 12 | 0.4 |
| realisme | 6 | 0.85 |
| passerelles | 10 | 0.6 |
| decouverte | 12 | 0.3 |
| conceptual | 4 | 0.9 |

### F.3.d local validation findings (dev set, 32 q, free)
- D1, D2 [diversite_geo] : +2, +5 distinct villes (target hit)
- C2 [decouverte] : 1 → 4 distinct villes (target hit)
- E3, E4 [passerelles] : +2, +1 villes
- B4, B5 [realisme] : villes drop because top_k 10→6 (intended)
- Aggregate : +0.25 villes/q, -0.56 labelled fiches/q (focus tradeoff)
- Output saved to `results/retrieval_inspection.md`.

### 7-system baseline matrix (ready in `src/eval/systems.py`)
| # | name | prompt | RAG | purpose |
|---|---|---|---|---|
| 1 | `our_rag` | v3.2 | yes + MMR + intent | full stack (thesis) |
| 2 | `mistral_neutral` | NEUTRAL | no | baseline |
| 3 | **`mistral_v3_2_no_rag`** | v3.2 | no | **isolates RAG** |
| 4 | `gpt4o_neutral` | NEUTRAL | no | OpenAI baseline |
| 5 | `gpt4o_v3_2_no_rag` | v3.2 | no | OpenAI + prompt |
| 6 | `claude_neutral` | NEUTRAL | no | Anthropic baseline |
| 7 | `claude_v3_2_no_rag` | v3.2 | no | Anthropic + prompt |

**System 3** is the scientific key. `our_rag` gains MMR + intent since
Phase F.3.c-bis (commit `dae9799`).

### NEW : OpenAI tier-1 rate limiter (Phase F.4)
- `src/eval/rate_limit.py` — `RateLimiter(max_per_minute)`, thread-safe
  minimum-interval gate.
- Shared 12 RPM limiter between the 2 `OpenAIBaseline` systems in
  `run_real_full.make_seven_systems`.
- Solo 12 RPM limiter in `run_judge_multi._run_gpt4o`.
- Mistral + Anthropic paid tiers unthrottled (not needed at our volume).
- Empirical effect : 5 min/q → 27-48s/q (6-10× speedup), zero 429.

---

## 5. Benchmark history — 10 runs + methodological findings

### Aggregate scores (/18, Claude Sonnet 4.5 judge v1, dev set N=32)

| # | Config | our_rag | mistral_raw | gap | notes |
|---|---|---|---|---|---|
| 1 | strict prompt, labels ON | 13.41 | 16.19 | -2.78 | baseline minimum |
| 2 | relaxed, labels ON | 14.19 | 16.09 | -1.90 | +0.78 after relaxing |
| 3 | relaxed, labels OFF | 14.50 | 16.22 | -1.72 | label ablation |
| 4 | 1098 fiches | 14.44 | 16.19 | -1.75 | data expansion failed |
| 5 | ROME injected | 14.31 | 15.84 | -1.53 | ROME in ctx only |
| 6 | full stack | 14.28 | 15.91 | -1.63 | plateau |
| 7 | Phase 1 (prompt v3) | 14.78 | 16.25 | -1.47 | anti-confession |
| 8 | Phase C (prompt v3.1) | 15.16 | 15.31 | -0.16 | parity |
| 9 | confirmation | 15.75 | 15.50 | +0.25 | first win |
| **10** | **Phase E (fair baseline + v3.2)** | **16.59** | **11.28** | **+5.31** | decisive |

### Judge v2 (regex fact-check)
- Run 7 v2 : -0.88, Run 8 v2 : 0.00, Run 9 v2 : +0.38, Run 10 v2 : +5.31.

### Claude Haiku fact-check
Code shipped in Phase E.3 (`src/eval/fact_check_claude.py`, commit `9f1b5aa`).
**Never run** — Anthropic budget was exhausted before. Will execute at
Run G in Phase G.5.

### Historical findings (for the study report)
1. Retrieval constraint harm (Run 1→2, +0.78)
2. Label boost over-concentration (Run 3 ablation, +0.31)
3. Data breadth does not help (Run 4 regression)
4. ROME helps discovery — only out of embeddings (Run 5)
5. Enrichment is category-dependent (Run 6)
6. Anti-confession is the big prompt lever (Phase 1)
7. Conceptual / interdisciplinary / villes rules (Phase C)
8. Comparison-table rule (Phase E.2, +5.00 on comparaison)
9. Shared prompt = methodological error (Phase E.1)
10. **NEW (F.3.d) : MMR+intent gives +0.25 villes/q on dev, highest on
    the targeted D/C/E categories, no penalty elsewhere.**

### Run 10 limitations (Phase F is designed to fix all)
- N=32 → IC95% ±2 pts. True gap might be +3 to +7.
- Train = test : v3.x was tuned ON these 32 questions.
- Single judge Claude Sonnet 4.5.
- Single run of Run 10.
- ChatGPT recordings non-representative.
- No adversarial or cross-domain tests.

---

## 6. Active plan — the 3-week solidify+prove sprint

See `/home/matteo_linux/.claude/plans/radiant-beaming-mitten.md`.

### Week 1 — Solidify (Phase F, in progress)
- [x] F.1 Dataset expansion (100 q, dev/test/adversarial/cross-domain)
- [x] F.2 7-system baseline matrix + sample test validation
- [x] F.3 Method extensions (MMR + intent), F.3.c skipped
- [x] F.4 prep: multi-judge + rate limiter
- [🟡] F.4 RUN F — generation in progress (65/100 as of 16:27 on 2026-04-15)
- [ ] F.4 RUN F — multi-judge (Claude Sonnet + GPT-4o), auto-launched
      when generation finishes
- [ ] Checkpoint Matteo on Run F results → decide variance runs (x2 more)

### Week 2 — Prove
- G.1 Statistics module (bootstrap IC95%, paired t-test, Cohen's d, κ, α)
- G.2 Human eval (2 students × 30 questions blind, κ humain-Claude)
- G.3 Adversarial honesty rate
- G.4 Cross-domain analysis
- G.5 RUN G with 3 judges (Claude Sonnet + GPT-4o + Haiku fact-check, ~$30)

### Week 3 — Deliver
- H.1 `docs/STUDY_REPORT.md` (markdown, no LaTeX)
- H.2 UI demo (optional)
- H.3 Reproducibility package (`reproduce.sh`, dataset commit, video)

### Decision points
1. ~~F.2 checkpoint~~ ✅ passed
2. F.4 checkpoint (Run F results + ablation table) — **imminent**
3. G.5 checkpoint (Run G + human eval)
4. H.1 checkpoint (study report)

---

## 7. Commits made this sprint (chronological)

### F.1 — Dataset
- `627af62` feat(eval): F.1 — extend dataset 32 → 100 (dev/test split + types)

### F.2 — 7-system matrix
- `546baeb` feat(eval): F.2 part 1 — 3 new system classes
- `ed6c08c` feat(eval): F.2 part 2 — generalise runner + judge to N systems
- `b21aa76` feat(eval): F.2 part 3 — run_real_full orchestrates the 7-system matrix
- `8dce21d` docs: refresh SESSION_HANDOFF + README for Phase F state
- `8295b1e` fix(eval): scale runner print + ThreadPoolExecutor to N systems

### F.3 — Method extensions
- `054bf4b` feat(rag): F.3.a — MMR post-rerank for top-k diversification
- `e4ed7ed` feat(rag): F.3.b — rule-based intent classifier modulates retrieval
- `dae9799` feat(eval): F.3.c-bis + F.3.d — activate MMR/intent + retrieval inspection

### F.4 — preparation
- `8513b3c` feat(eval): F.4 multi-judge — GPT-4o judge + run_judge_multi orchestrator
- `40464f0` feat(eval): RPM rate limiter to handle OpenAI tier-1 (15 RPM gpt-4o)

### Protected files (still)
- `src/rag/embeddings.py` — `fiche_to_text` MUST NOT include ROME.
- `data/manual_labels.json` — blocklist authoritative.
- `src/eval/judge.py` v1 rubric — preserved for longitudinal comparison.
- `src/rag/reranker.py` — `RerankConfig` defaults stable since Run 3.

---

## 8. API budget state

### Mistral
- **Paid tier active**. Embeddings + chat.complete for generation.
- `Mistral(api_key=..., timeout_ms=120000)` since Run A.
- `_call_with_retry` handles rate limits, timeouts, 5xx, Cloudflare 520s.

### Anthropic (topped up 2026-04-15)
- **~$30-40 recharged** for Run F + G coverage.
- Usage : judge Sonnet 4.5 on Run F (×3), judge Sonnet on Run G (×3),
  Claude Haiku fact-check on Run G, 2 Claude baselines per run.

### OpenAI (new in Phase F, topped up 2026-04-15)
- **~$15 recharged**, tier 1 (15 RPM for gpt-4o).
- Rate limiter caps our outbound rate at 12 RPM → zero 429.
- Usage : GPT-4o as baseline system (×2 per run), GPT-4o as 2nd judge.

### Total sprint budget (estimate)
| Item | Cost |
|---|---|
| Sample tests (v1 + v2) | ~$0.80 (spent) |
| Run F generation (100q × 7 sys × 1 run) | ~$8-12 |
| Run F judge multi (Claude + GPT-4o) | ~$5-7 |
| Runs 2, 3 of F (if approved) | ~$25-30 |
| Run G generation + 3 judges | ~$25-30 |
| Buffer | ~$15-20 |
| **Total** | **~$70-90** |

### Rule : ZERO intermediate benchmarks
F.3 extensions were developed + tested locally without any judge calls
(F.3.d uses no LLMs). Only F.4 (Run F) and G.5 (Run G) spend judge money.

---

## 9. How to resume in a fresh session

```bash
cd /home/matteo_linux/projets/OrientIA
source .venv/bin/activate

# 1. Check state
cat docs/SESSION_HANDOFF.md   # this file
git log --oneline -15
pytest tests/ 2>&1 | tail -5  # 231 should be green

# 2. Confirm API keys
python3 -c "from src.config import load_config; c = load_config(); print(f'Mistral:{bool(c.mistral_api_key)}, Anthropic:{bool(c.anthropic_api_key)}, OpenAI:{bool(c.openai_api_key)}')"
# → all three True

# 3. Check Run F state
ls results/run_F_robust/
python3 -c "import json; print(len(json.load(open('results/run_F_robust/responses_blind.json'))), '/100')"

# 4a. If Run F generation finished (100/100) but judge not run:
python -m src.eval.run_judge_multi \
  --responses results/run_F_robust/responses_blind.json \
  --out-dir results/run_F_robust

# 4b. If Run F generation interrupted mid-way, resume:
python -m src.eval.run_real_full --out-dir results/run_F_robust
# Runner detects done_ids and continues.

# 4c. If Run F judge done — analyse:
ls results/run_F_robust/
# → responses_blind.json, label_mapping.json, scores_claude.json, scores_gpt4o.json
# → then compare judges via per-system means + compute κ inter-judge.
```

Then pick up from **F.4 analysis → variance runs → G.1 statistics module**.

---

## 10. Files to NOT modify lightly

Still hold — hard-won empirical decisions :
- `src/prompt/system.py` — v3.2 = result of 5 iterations. Changes should
  be ADDITIVE, not reverts.
- `src/eval/runner.py` — retry + resume + incremental save + Cloudflare
  handling are load-bearing for any multi-hour run.
- `data/manual_labels.json` — 25 entries curated authoritative.
- `src/rag/embeddings.py:fiche_to_text` — MUST NOT include ROME.
- `src/rag/reranker.py` — `RerankConfig` defaults stable since Run 3.
- `src/eval/judge.py` v1 rubric — preserved for v1 vs v2 comparison.
- `src/eval/rate_limit.py` — the 12 RPM cap is calibrated for OpenAI
  tier-1 with 2 concurrent systems + 25% safety margin. Don't raise
  until tier 2 confirmed.

---

## 11. Archives

All 10 historical runs under `results/run{N}_*/` :
- `run1_strict_sourcing/`
- `run2_relaxed_sourcing/`
- `run3_ablation_no_labels/`
- `run4_data_expansion/`
- `run5_rome_enriched/`
- `run6_full_stack/`
- `run7_phase1_densification/`
- `run8_phase1c_prompt_v31/`
- `run9_phase1c_confirmation/`
- `run10_phase_e_fair_baseline/`

Phase F run : `results/run_F_robust/` (active).

---

## 12. What comes next — immediate actions

**While Run F generation is running (~ETA 17:05 on 2026-04-15):**
- Monitor via `python3 -c "import json; print(len(json.load(open('results/run_F_robust/responses_blind.json'))))"`
- Claude auto-wakeups every 15-20 min to track progress.

**When generation hits 100/100:**
- Auto-launch `run_judge_multi` (~15-20 min, ~$5-7).
- Write analysis : per-system / per-category means, inter-judge κ,
  diff-vs-baseline table, 7-system ablation.

**After Run F analysis:**
- Present results to Matteo → decision to run variance (x2 more runs)
  or skip straight to Run G depending on the signal.
- If ablation proves RAG contribution significant → go to G.1 stats module.
- If our_rag ≤ mistral_v3_2_no_rag → honest publication that all gain
  came from the prompt.

---

## 13. Session 2026-04-17 — Vagues A/B/C/D + santé + quality + métriques (7 PRs)

Session marathon. Main est aujourd'hui substantiellement au-delà du baseline
Run F+G documenté ci-dessus.

### 13.1 PRs mergées sur main

| PR | Contribution |
|---|---|
| #1 `feature/data-foundation-vague-a` | Parcoursup richness expose (cod_aff_form, volumes, diversité) + format citation ##begin_quote## + provenance/fraîcheur |
| #2 `feature/vague-c-historical-trends` | Trends 2023→2025 via cod_aff_form (1267 fiches avec trends après santé) |
| #3 `feature/sanity-ux-alpha-beta` | Brièveté 300-500 mots + exploitation obligatoire signaux |
| #4 `feature/vague-d-insersup-insertion` | InserSup DEPP (bug cod_uai manquant de Vague A corrigé) |
| #5 `feature/deterministic-metrics-b3-b5-b6` | B3/B5/B6 déterministes + longitudinal |
| #6 `feature/extension-domaine-sante` | 3e domaine santé (x3 corpus, x22 insertion) + bug fix manual_labels leak |

### 13.2 État corpus fin session 17 avril

| Métrique | Début session | Fin session |
|---|---|---|
| Total fiches | 443 | **1424** (+221%) |
| Domaines actifs | 2 (cyber + data_ia) | **3** (+ santé) |
| Avec insertion InserSup | 0 (bug cod_uai) | **194** |
| Avec trends historiques | 0 | **1267** |
| Tests verts | 231 | **343** |

### 13.3 Infrastructure scripts ajoutés

- `scripts/download_parcoursup_history.sh`, `download_insersup.sh`
- `scripts/rebuild_faiss_index.py`
- `scripts/insersup_audit.py`, `sante_audit.py`
- `scripts/vague_a_diff_qualitatif.py`, `sante_diff_qualitatif.py`
- `scripts/metrics_longitudinal.py`
- `scripts/prepare_user_test_pack.py` — pack test user + spot-check
- `scripts/collect_onisep_public.py` — ONISEP endpoint public (rate-limited)

### 13.4 Leçons apprises session 17

- **LLM Mistral paraphrase plutôt que cite** sans instruction explicite
  ou fine-tuning. Observation stable sur 3 itérations. RAFT reste la
  solution technique finale.
- **Retrieval + generator doivent être enrichis ensemble**. Enrichir
  Vague A seule (generator) = gain 1/6 questions. Enrichir Vague A+B
  (generator + embedding + reranker) = gain 5/6.
- **Coût re-embed FAISS négligeable** (~$0.01-0.03). Re-embed librement
  à chaque changement fiche_to_text.
- **Data quality gaps silencieux** sans audit automatique post-merge.
- **Volume data seul n'est pas le levier** — data mieux injectée +
  prompt renforcé + UX ciblée. Le plus gros gain UX (-54% longueur)
  est venu d'une modif prompt, pas d'ajout data.

---

## 14. Session 2026-04-18 — Spot-check + 4 user tests + Tier 0 critique

**TOURNANT MAJEUR DU PROJET.** Premier vrai feedback humain obtenu.
Révèle les vraies zones de friction utilisateur. Tier 0 de corrections
critiques livré dans la foulée.

### 14.1 Spot-check manuel InserSup — GATE NON PASSÉ

Matteo a vérifié 5 échantillons vs source officielle ESR — résultat :
**3 bugs structurels** identifiés.

1. **Bug #2 (critique)** : `taux_emploi_12m = nd` sur 5/5 échantillons.
   Cause : on lisait `12-Taux d'emploi` qui est null dans dataset 2025_S2.
   La donnée existe mais éclatée en 3 composantes (sal_fr + non_sal +
   etranger).
2. **Bug #1 (sérieux)** : `obtention_diplome` non-déterministe. 3/5 en
   "ensemble", 2/5 en "diplômé" — incohérence silencieuse (salaires
   proches, nb_sortants diffère : Lille 976 vs 1612).
3. **Bug #3 (mineur)** : taxonomie "discipline" vs "diplome" confuse.

Salaires et nb_sortants étaient **corrects** (5/5). La fondation data
tient, le bug est dans le dernier kilomètre de parsing.

### 14.2 4 tests utilisateurs — feedback d'une qualité rare

Matteo a recruté 4 profils hétérogènes :
- **Léo 17** lycéen terminale Maths+NSI
- **Sarah 20** L2 Éco-Gestion Paris 1 en réorientation
- **Thomas 23** M1 Info Dauphine, projection pro
- **Catherine 52** parent DRH, mère de terminale
- **Dominique 48** conseiller d'orientation Psy-EN, 22 ans métier

Feedbacks dans `results/user_test/*.md`.

### 14.3 9 convergences absolues cross-profils

1. **TROP LONG** — unanime. Le 300-500 mots sanity UX **reste trop long**.
   Nouvelle cible : **150-300 mots** pyramide inversée.
2. **Codes admin visibles = bruit** — cod_aff_form/RNCP/M1817/FOR.xxx
3. **"100% femmes → environnement adapté"** = SEXISME explicite par 4/4
4. **Template Plan A/B/C infantilise** post-terminale
5. **`(connaissance générale)` crée défiance**
6. **Pas de questionnement du projet** (Dominique)
7. **Pas de signal d'alerte "évite ça"**
8. **Format Q8 "12 en PASS" = étalon unanime**
9. **6 erreurs factuelles récurrentes** — toutes hallucinations LLM,
   PAS bugs data : MBA HEC "plus accessible avec expérience", École 42
   "gratuite en alternance", VAP Infirmier→Kiné "possible", prépas
   médecine "2x chances", CentraleSupélec en "Plan A", "Orthophonie
   pour les Nuls" pour concours <15%

### 14.4 PR #8 — Tier 0 corrections critiques (7 fix)

1. Bug InserSup #2 : somme 3 composantes taux emploi
2. Bug InserSup #1 : filtre `obtention_diplome="ensemble"` explicite
3. Fusion cohortes par métrique (`_pick_merged` + `cohortes_used`)
4. Règles dures anti-discriminations dans system prompt
5. Anti-hallucinations : 6 erreurs listées interdites + règle "Fabrique
   pas un Plan A artificiel"
6. Masquage codes admin : `_source_line` expose URLs pour liens markdown,
   system prompt interdit codes en clair
7. Renvoi humain systématique SCUIO/CIO/Psy-EN

**Effets mesurés** :
- Taux emploi 12m : 0/194 → **194/194** fiches
- Taux ET salaire combinés : 9/194 → **189/194** (97.4%)
- Validation end-to-end : question EFREI produit maintenant
  `[fiche Parcoursup EFREI Paris](https://...)` au lieu de
  `cod_aff_form: 36040` brut

Tests : 343 → **348 verts** (+5 Tier 0), zéro régression.

### 14.5 PRs en attente

- **PR #7** (`feature/fix-data-quality-gaps`) — niveau D.E. santé +
  MIN_SORTANTS=20 + visibilité ⚠AGRÉGAT. **Dépassée par Tier 0.** À
  fermer, les fixes niveau D.E. + MIN_SORTANTS à re-faire en Tier 2
  si toujours pertinents après merge Tier 0.
- **PR #8** — Tier 0 critique, CLEAN + MERGEABLE, en attente validation
  Matteo.
- **Branche `docs/session-2026-04-17-continuity`** — superseded par ce
  §13+14 consolidé. À fermer sans merger.

### 14.6 RÈGLE ABSOLUE gravée

**Ne jamais merger une nouvelle source data externe sans spot-check
manuel de 3-5 échantillons vs source officielle.**

L'audit automatique a validé les salaires (corrects) et déclaré "0
outlier" — mais a **raté** que le taux d'emploi était null partout, car
il ne comparait pas avec la donnée officielle disponible. Le spot-check
manuel par un humain est le seul garde-fou efficace. Cette règle prévaut
sur toute contrainte temporelle.

### 14.7 Plan Tier 1-4 pour la suite

| Tier | Nature | Impact attendu |
|---|---|---|
| **Tier 0** ✅ | Bugs InserSup + sexisme + codes masqués | Base correcte + règles non-négociables |
| **Tier 1** | Anti-hallucination approfondie (scorer automatique) | Détection automatisée hallucinations |
| **Tier 2** | Pyramide inversée + brièveté 150-300 mots + détection niveau user + format par type question | **Gros gain UX** (plainte #1 unanime) |
| **Tier 3** | ⚠Attention aux pièges généralisés + mode exploration préalable (Socratic) + témoignages + coût total + disclaimer permanent | Adresse vision Dominique "questionnement du projet" |
| **Tier 4** | Trancher positionnement α (Parcoursup-only) vs β (carrière adulte) | Décision stratégique Matteo |

**Tier 2** = prochain gros chantier après merge Tier 0.

### 14.8 Critères de succès Tier 2

Refaire tester par les **4 mêmes profils** avec les 10 mêmes questions.
Réussite si :
- Léo 17 passe de "je décroche à la moitié" à "lu en entier"
- Sarah 20 cesse de se sentir infantilisée par le template A/B/C
- Catherine 52 cesse de relever des erreurs factuelles graves
- Dominique 48 recommanderait l'outil à un élève seul

Si 4/4, preuve qu'on est sur la bonne voie. Pas avant.

---

## 15. Session 2026-04-19 — Tier 2 mergé + α + POC Mistral + task B + D3a

**SESSION DENSE (J+0 du plan 2 semaines agentic).** 6 chantiers livrés
en une journée, consolidation documentation, pivot stratégique RAFT →
Axe 2 agentic.

### 15.1 Merges main

| PR | Status | Contenu |
|---|---|---|
| #8 `fix/tier0-critical-user-feedback` | ✅ mergée 2026-04-19 16:27 | Tier 0 : bugs InserSup + anti-discrim + anti-halluc + codes masqués + renvoi humain |
| #9 `feature/tier2-ux-pyramide-brievete` | ✅ mergée 2026-04-19 | Tier 2 : 5 sous-chantiers T2.1-T2.5, 78 nouveaux tests |

### 15.2 5 user tests v2 (pack Tier 2) — verdicts

5 profils ont audité `results/user_test_v2/answers_to_show.md` + commentaires
dans `results/user_test_v2/test_orientia_5_profils.md`.

**Convergences positives** :
- TL;DR unanime utile (seul format que Léo lit systématiquement)
- Attention aux pièges appréciée par les 5 (Léo : "faut le mettre partout")
- Tableau comparaison (Q3, Q9) lisible par les 5
- Renvoi Psy-EN/CIO/SCUIO = meilleure pratique déontologique (Dominique)
- Liens Parcoursup cliquables = différenciateur clé vs ChatGPT

**Convergences négatives** :
- **3/5 profils : "non recommandable pour mineur en autonomie"**
  (Léo en partie, Catherine DRH, Dominique Psy-EN pro)
- Cause : ~7 hallucinations factuelles distinctes relevées (ECN→EDN,
  bac S supprimé, distances, VAE/VAP, CS Cybersécurité, coûts privés,
  Tremplin→HEC, formations inventées)
- Malgré -40% word count, "encore trop long" (tous les 5)
- Plan A/B/C encore mécanique sur Q2 ranking et Q7 découverte
- Trends 100% jugés décoratifs ou anxiogènes

### 15.3 α Restricted LLM — preuve empirique du plafond (ADR-030)

Branche `feature/alpha-restricted-llm`. α remplace ANTI-CONFESSION par
liste blanche + abstention structurée + renvoi autorisé.

Pack `results/user_test_alpha/` comparé au v2 :

| Hallucination | v2 | v2-α | Verdict |
|---|---|---|---|
| ECN comme nom actuel | 1/10 | 1/10 | inchangé |
| Bac S cité comme actuel | 3/10 | 3/10 | inchangé |
| Licence Humanités Ortho inventée | 1/10 | 1/10 | inchangé |
| Périgueux 3h30 | 1/10 | 0/10 | corrigé |
| Pattern refus explicite | 0/10 | 0/10 | Mistral ne l'adopte pas |

**Preuve empirique** : le prompt-engineering seul n'est PAS suffisant.
C'est une limite architecturale Mistral medium, pas un défaut prompt.
Justifie le pivot agentic/RAFT. α reste sur branche non-mergée comme
filet non-régressif (PR #10 non ouverte, décision reportée).

### 15.4 POC H Mistral Large tool-use (ADR-032)

Gate J+3 lancé, 5 questions représentatives :

- 5/5 succès technique (schémas respectés, params valides)
- Latence moyenne 16.9s (marginal vs gate 15s, acceptable UX orientation)
- Conceptuelle Q5 : 0 tool call, 1 iteration = Mistral distingue bien

**Verdict PASS**. Mistral Large orchestrator **validé pour Axe 2 S2**.
Narrative souveraineté française préservée.

### 15.5 Task B — 3 fixes UX indépendants LLM (ADR-033)

Sur `feature/axe2-agentic-prep` (branche S2 prep) :

1. `_debouches_line` : codes ROME (M1812/M1819) retirés du texte LLM
2. `_trend_suffix` : seuils significance (5pp/15%/10 places) — omission
   en-deçà
3. Prompt T2.2 : alertes critiques obligatoires dans TL;DR (Catherine :
   "Hugo lira le TL;DR puis fermera")

### 15.6 D3a ROME 4.0 offline (ADR-034)

Exploitation du zip `rome_4_0.zip` v460 déjà téléchargé. Nouveau module
`src/collect/rome.py` avec fonctions mémoïsées : `get_rome_info`,
`list_all_rome_codes`, helpers bool-safe `is_emploi_cadre` /
`is_transition_numerique`.

D3b (salaire médian + tension marché) reportée à signup France Travail API.

### 15.7 Pivot stratégique α + RAFT → α + Axe 2 agentic (ADR-031)

Plan initial 2 semaines (α + RAFT) remplacé par (α + Axe 2 agentic).
Raisons :
- Critère Matteo élargi "études + pro" rend Thomas/Sarah dans cible
- Agentic adresse 5/6 verdicts users, RAFT adresse 1/6
- Évite gate R7 RAFT 30-40% échec
- Tools (ROME, InserJeunes, coûts) réduisent structurellement la surface
  hallucination

RAFT reste en réserve S3+ optionnel.

### 15.8 Branches état fin session 2026-04-19

| Branche | Status | Contenu |
|---|---|---|
| `main` | ✅ | Tier 0 + Tier 2 mergés |
| `feature/tier2-ux-pyramide-brievete` | mergée PR #9 | |
| `feature/alpha-restricted-llm` | non-mergée | α pour éventuel merge filet |
| `feature/axe2-agentic-prep` | active | POC + task B (3 fixes) + D3a, 430 verts |

### 15.9 Bench E bloqué

Lancement bench formel 100q post-Tier 2 a échoué : **Anthropic credits
à zéro**. Dernières transactions Run F+G (2026-04-16) ont épuisé la
balance. 3 options :
1. Recharger Anthropic $30-40 → bench 7-systèmes + 3 juges complet
2. Bench mini 5-systèmes (Mistral + OpenAI seuls) ~$12, 1 juge GPT-4o
3. Report bench, continuer sans baseline mesurée

Décision Matteo en attente 2026-04-22.

### 15.10 Tests

**430 verts** sur feature/axe2-agentic-prep (vs 348 au début de la session).

- Tier 0 (28 tests, préservés)
- Tier 2 (78 nouveaux, cf test_system_prompt_tier2.py, test_user_level.py,
  test_intent_format.py)
- α (20 nouveaux sur branche alpha uniquement)
- ROME offline D3a (4 nouveaux)

### 15.11 Coûts API session 2026-04-19

| Item | Coût |
|---|---|
| Pack v2 Tier 2 régénération (10q × Mistral) | ~$0.30 |
| Pack v2-α régénération (10q × Mistral) | ~$0.30 |
| POC H Mistral tool-use (5q × Mistral Large) | ~$0.40 |
| **Total session** | **~$1.00** |

Plus bench E tentative (coût zéro, crash avant API call Anthropic).

---

## 16. État 2026-04-22 — continuation sprint 2 semaines

**Jour calendaire** : J+3 du sprint 2 semaines (démarré 2026-04-19).

### 16.1 En cours / pending

- **D5 InserJeunes BTS** (task 9, in_progress) : chantier data 4-6h.
  Fixe le flag Catherine/Dominique sur absence insertion BTS.
  InserJeunes = équivalent InserSup pour BTS/bac pro/CAP.
- **Bench E baseline** : attente décision Matteo sur recharge Anthropic
  vs bench mini vs report.
- **F baselines Playwright** : attente disponibilité Matteo (Claude Max
  requis pour automation chatgpt/claude/mistral web UI).
- **Gate J+6 re-test α** (2026-04-25 calendaire) : re-tester α+Tier 2
  sur Léo/Catherine/Sarah pour voir si verdict "non recommandable"
  bouge. Si oui → agentic optionnel. Si non → agentic confirmé S2.

### 16.2 Branches actives

- `feature/axe2-agentic-prep` (origin à jour au 2026-04-19) : **branche
  de continuation pour S1 + S2**. Tous les chantiers data (D3, D5) et
  agentic (A1-A9) viendront ici.
- `feature/alpha-restricted-llm` : filet, décision merge reportée.

### 16.3 Prochaine action au réveil

1. Matteo décide sur bench E (1/2/3)
2. Claudette continue D5 InserJeunes BTS
3. Gate J+6 à organiser côté humain
4. Si bench E débloqué → lancement en background pendant D5

### 16.4 Ordering Axe 2 S2 (J+8-14 calendaires, 2026-04-27 → 2026-05-02)

Prérequis data en S1 : D3a fait, D3b attend clé France Travail,
D4 labels pending, D5 InserJeunes BTS in progress.

STRATEGIE §5 Axe 2 A1-A9 :
- A1 interfaces tools Pydantic
- A2 ProfileClarifier agent
- A3 Decomposer agent
- A4 3 tools core (search_formations, get_debouches, get_insertion_stats)
- A5 Composer agent (system prompt v4 = v3.2 + Tier 2)
- A6 Validator agent (citation precision programmatique)
- A7 orchestration Mistral Large (validé POC H)
- A8 tests intégration 10-15 questions
- A9 bench `our_rag_v3_agentic` vs baselines

### 16.5 Documentation à jour au 2026-04-22

- `docs/SESSION_HANDOFF.md` (ce document) — §15+16 ajoutés
- `docs/DECISION_LOG.md` — ADR-029 à ADR-034 ajoutés
- `docs/STRATEGIE_VISION_2026-04-16.md` — référence stable, non modifiée
- Memory `state_projet_fin_session_2026-04-22.md` (à écrire)
- Memory `tier2_delivery_2026-04-18.md` — marqué comme historique,
  Tier 2 désormais mergé

---

## 17. Sprint S1 livré (matin 2026-04-22) — État pré-Gate J+6

**Sprint S1 bouclé en 3h** (boot 0815 → cleanup 1100 CEST). 3 ordres P0
livrés en parallèle après revue stratégique poussée par Matteo (4 questions
de fond + arbitrage validé), 5 PRs créées, 4 mergées, 1 ouverte pour S2.

### 17.1 Timeline ordres dispatchés Jarvis → Claudette

| Heure | Ordre | Status | PR |
|---|---|---|---|
| 0815 | `claudette-orientia-audit-reprise` (read-only) | ✅ done | — (synthèse peer) |
| 0832 | `claudette-orientia-strategic-review` (Q1-Q4) | ✅ done | — (review peer) |
| 0847 | `claudette-orientia-q3-souverainete-raft-plan` | ✅ done | — (plan peer) |
| 0902 | `claudette-split-branche-docs-consolidation` | ✅ done | #10, #11, #12, #13 |
| 0902 | `claudette-data-d7-cron-refresh` | ✅ done | #14 |
| 0902 | `claudette-validator-v1-rules-corpus` | ✅ done | #15 |
| 1016 | `claudette-orientia-cleanup-pre-s2` | ✅ done | (this PR) |

### 17.2 PRs et SHAs main

| # | Titre | SHA merge | Status |
|---|---|---|---|
| #10 | data/s1-rome-bts-insersup (D3a ROME) | `7e85967` | ✅ merged |
| #11 | ux/task-b-fixes (masquage codes ROME + seuils trends + alertes TL;DR) | `cfd62e0` | ✅ merged |
| #12 | axe2/pydantic-profileclarifier (POC Mistral tool-use) | — | 🟡 open S2 |
| #13 | docs-consolidation-2026-04-22 (CLAUDE.md + STRATEGIE_VISION + packs) | `f6445c8` | ✅ merged |
| #14 | feat(ci): D7 monthly data-refresh workflow | `d72676d` | ✅ merged |
| #15 | feat(validator): v1 déterministe (rules + corpus-check) | `6afcacc` | ✅ merged |

### 17.3 Validator v1 — métriques empiriques pack v2

```
Honesty score moyen      : 0.94
Questions flaggées       : 2/10 (20%)
Q7 médecine  : 3 violations BLOCKING ECN_renamed_to_EDN (honesty 0.55)
Q10 ortho    : 1 violation BLOCKING licence_humanites_orthophonie_invented (honesty 0.85)
Latence par answer       : <1ms (cible 400ms largement tenue)
```

Validator catche programmatiquement les 2 hallucinations user_test_v2
les plus ré-citées par 3/5 profils (Léo, Catherine, Dominique). Wiring
opt-in dans `OrientIAPipeline(..., validator=...)` accessible via
`pipeline.last_validation`.

### 17.4 Workflow D7 cron actif

`.github/workflows/data-refresh-monthly.yml` — premier tick **2026-05-01
03:00 UTC**. Trigger manuel possible via `gh workflow run
data-refresh-monthly.yml`. PR auto si drift, issue auto si fail.

Smoke test post-merge déclenché côté Jarvis le 2026-04-22 ~10:11 CEST.

### 17.5 Tests + couverture

- **Avant S1 (main d72676d antérieur cleanup)** : 430 tests verts (hors
  API-heavy)
- **Après S1 (main 6afcacc)** : 449 tests offline + 53 validator nouveaux
  (test_rules 21 + test_corpus_check 10 + test_validator_integration 9 +
  test_golden_hallucinations 13) = **502 tests verts**, zéro régression.

### 17.6 Cleanup post-S1 (cette PR)

- Branches obsolètes supprimées : `feature/axe2-agentic-prep` (palimpseste
  splitté), `feature/vague-{a,b,c,d}-*`, `feature/sanity-ux-alpha-beta`,
  `feature/extension-domaine-sante`, `feature/deterministic-metrics-b3-b5-b6`,
  `feature/data-foundation-vague-a`, `feature/tier2-ux-pyramide-brievete`,
  `fix/tier0-critical-user-feedback`, `docs/session-2026-04-17-continuity`
- `feature/alpha-restricted-llm` **conservée** (filet ADR-030, décision
  merge encore reportée)
- **PR #7 fermée** (ADR-028 confirmé) — fixes pertinents redirigés vers
  D2/D3b/D4 S2

### 17.7 Prochaine étape : Gate J+6 (2026-04-25)

Re-test des 5 profils user_test sur pack v3 (à générer post-Validator).
Critères de basculement S2 :

- **Si verdict 4-5/5 "recommandable"** → branche A : data-focused (D2 ONISEP
  live, D4 labels CTI/CGE, D3b ROME API). Reporter Axe 2 agentic.
- **Si verdict reste 3/5** → branche B : Axe 2 agentic justifié, kickoff
  A1-A9 sur `axe2/pydantic-profileclarifier` (PR #12 déjà ouverte).

Décision Matteo bench E (recharge Anthropic / mini OpenAI / report)
toujours en attente — bloqueur P1 sur mesurabilité Validator + Tier 2.

### 17.8 Carry-over hors scope S1

Items signalés mais non traités, à dispatcher S2 :

- D5 InserJeunes BTS (4-6h, élargit corpus BTS pour insertion)
- D2 ONISEP API live (6-8h, débloque enrichissement 75.8% fiches)
- D4 CTI/CGE/Grade Master labels (4-6h, comble couverture 5.2% → 60%)
- D3b ROME API France Travail (signup OAuth + branchement salaire/tension)
- Validator couche 3 fallback LLM Mistral Small souverain (post-gate J+6)
- Bench E baseline post-Tier 2 + Validator (selon décision Matteo)
- Baselines naturels Playwright (chatgpt/claude/mistral web UI)

### 17.9 Documentation à jour au 2026-04-22 11h CEST

- `docs/SESSION_HANDOFF.md` (ce document) — §17 ajouté
- `docs/DECISION_LOG.md` — ADR-035 ajouté (post-cleanup)
- `docs/STRATEGIE_VISION_2026-04-16.md` — référence stable
- `CLAUDE.md` projet — mergé via PR #13, reflète repivot + pattern merge-approval

---

## 18. Sprint V2→V3→V4→V4.1 Gate J+6 (après-midi + soirée 2026-04-22)

**Journée dense — 6 versions Validator livrées en 10h.** Le but : passer
le verdict humain de 3/5 baseline à ≥4/5 pour déploiement beta mineur
autonome. **Résultat : médiane 2/5 persistante, plateau identifié.**

### 18.1 Timeline ordres dispatchés Jarvis → Claudette (après S1 matin)

| Heure | Ordre | Status | PR |
|---|---|---|---|
| 1119 | `gate-j6-preparation` (UX Policy α+β + triple-judge + rapport) | ✅ done | #23 |
| 1230 | `validator-v2-rules-dures-psy-en` | ✅ done | #24 ✅ mergé |
| 1308 | `validator-v3-footer-polish` | ✅ done | #25 ✅ mergé |
| 1335 | `v3-resimu-humaine-claude-sonnet-persona` | ✅ done | #26 |
| 1751 | `validator-v4-gamma-modify-plus-enrichissements` | ✅ done | #27 |
| 1834 | `system-prompt-rééquilibrage-plus-avis-global` | ✅ done | #28 |
| 2333 | `avis-sur-5-axes-matteo-plus-plan-4-semaines-inria` | ✅ done | peer (consultatif) |

### 18.2 Versions Validator — chronologie

- **V1** (matin, PR #15 mergé) : rules + corpus_check, 53 tests, honesty 0.94
- **V2** (midi, PR #24 mergé) : +4 règles dures Psy-EN (HEC AST, PASS redoublement, séries bac ABCD, kiné IFMK) + couche 3 Mistral Small souverain + data cleanup "mention B"
- **V3** (après-midi, PR #25 mergé) : polish footer β Warn top 2 max + priority ordering
- **V4** (soir, PR #27) : γ Modify refus chirurgical + PresenceRule 4 topics + phase projet minimal
- **V4.1** (soirée, PR #28) : rebalance T2.4 prompt « Attention aux pièges »

### 18.3 Métriques triple-judge + Claude Sonnet persona

| Métrique | V1 | V2 | V3 | V4 | V4.1 |
|---|---|---|---|---|---|
| Triple-judge moyen | 3.63 | 3.23 | 3.26 | n/a | n/a |
| Claude persona 3 Q hard médiane | — | — | 2 | **2** | **2** |
| Claude persona moyenne | — | — | 2.27 | 2.40 | **2.00** |
| Tests | 53 | 129 | 107 post | 190 | 177 post |

**Verdict humain terrain Matteo** (ground truth v3 simulé) : 2/5 médiane
sur 3 Q hard, cohérent avec Claude Sonnet persona.

### 18.4 Cause racine plateau 2/5 (identifiée ADR-037)

Le rééquilibrage prompt V4.1 a **RÉFUTÉ l'hypothèse** "verbosité footer =
cause plateau". Causes plus profondes identifiées via commentaires Psy-EN
verbatim :

1. **Bug γ Modify** : multiple violations même règle → N remplacements
   → répétitions textuelles (V4.2 fix prévu)
2. **Règles V2 variance-dépendantes** : match sur certaines regen Mistral
   pas d'autres
3. **Phase projet bug** : trigger présent mais `already_has_project_prompts`
   false positive
4. **PresenceRule flag mais Mistral n'injecte pas** → migration
   Presence → Modify P0 V5
5. **Cause racine fondamentale** : Mistral Medium génération reste
   fragile, les couches aval compensent mais ne soignent pas à la source

### 18.5 PRs Gate J+6 (fin sprint)

| # | Titre | Action cleanup |
|---|---|---|
| #12 | axe2/pydantic-profileclarifier | Garder ouverte (POC Mistral Large tool-use ADR-032, non intégré à main) |
| #23 | Gate J+6 UX Policy α+β | Fermée superseded par #28 (cherry-picks cumulés) |
| #26 | V3 persona re-simu | Fermée superseded par #28 (cherry-picks cumulés) |
| #27 | V4 γ Modify | Fermée superseded par #28 (cherry-picks cumulés) |
| **#28** | V4.1 prompt rebalance + ADR-037 + §18 | Mergée sur main |

### 18.6 État git fin de sprint (2026-04-23 matin)

Main à jour avec toutes les livraisons V1→V4.1. Une PR ouverte (#12)
contient le POC Mistral Large tool-use non intégré à main. Filets locaux
(branche `feature/alpha-restricted-llm`) conservés comme documenté
ADR-030.

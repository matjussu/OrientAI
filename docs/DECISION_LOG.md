# OrientIA — Decision Log

**Purpose:** chronological log of major design decisions with date,
rationale, and alternatives considered. Complements `METHODOLOGY.md`
(the *how*) with the *why*. Each entry is ADR-lite (Architecture
Decision Record) format.

Entries are append-only — if a decision gets reversed, add a new
entry pointing to the old one, don't edit history.

---

## ADR-001 — Use Mistral as generation and embedding model (2026-03-10)

**Context.** The project targets French educational guidance for INRIA's
AI Grand Challenge.

**Decision.** Use `mistral-medium-latest` for generation and
`mistral-embed` for embeddings across the `our_rag` system.

**Rationale.**
- Native French optimization (vs GPT-4o / Claude being English-first).
- French sovereignty narrative aligns with INRIA's mission.
- Same provider for embeddings + generation = vector-space consistency.
- Cost-competitive for the benchmark scale.

**Alternatives considered.**
- OpenAI `text-embedding-3-large` + `gpt-4o` : rejected on sovereignty.
- Anthropic Claude + Voyage embeddings : rejected on French specialisation.
- Local open-weights (Llama, Mistral-Nemo) : rejected — higher complexity,
  lower baseline quality for French.

---

## ADR-002 — Label-based reranker instead of pure vector similarity (2026-03-15)

**Context.** FAISS cosine-similarity retrieval surfaces private schools
with dense SEO metadata more than public programs with sparse ONISEP
descriptions.

**Decision.** Add a multiplicative reranker stage that boosts fiches
carrying official labels (SecNumEdu, CTI, Grade Master, public status).

**Rationale.**
- The thesis of OrientIA is that *official institutional labels* are
  the right correction for private-school marketing bias.
- Multiplicative boost is simple, interpretable, auditable.
- Weights determined via grid search (`src/eval/grid_search.py`).

**Alternatives.**
- Hybrid BM25 + vector : rejected — still doesn't encode the label
  priority.
- LLM-based reranker : rejected on cost + latency.

---

## ADR-003 — 7-system ablation matrix instead of 3-system comparison (2026-04-13)

**Context.** Phase E (Run 10) showed `our_rag` +5.31 over `mistral_raw`,
but the original 3-system setup (our_rag / mistral_raw / chatgpt_recorded)
can't disentangle "RAG adds value" from "our v3.2 prompt adds value".

**Decision.** Expand to a 7-system matrix :
```
1. our_rag                 (v3.2 + RAG)
2. mistral_neutral         (NEUTRAL, no RAG)
3. mistral_v3_2_no_rag     (v3.2, no RAG)      ← ISOLATES RAG
4. gpt4o_neutral           (cross-vendor fair baseline)
5. gpt4o_v3_2_no_rag       (cross-vendor prompt portability)
6. claude_neutral          (cross-vendor fair baseline)
7. claude_v3_2_no_rag      (cross-vendor prompt portability)
```

**Rationale.**
- System 3 is the scientific key : if `our_rag > mistral_v3_2_no_rag`
  significantly, RAG adds value beyond prompt engineering.
- Systems 4-7 test cross-vendor prompt portability : does v3.2 also
  improve GPT-4o / Claude ? (If yes, that strengthens the contribution.)
- Systems 2, 4, 6 act as honest baselines for each LLM family.

**Alternatives.**
- Keep 3 systems and accept the ambiguity : rejected — reviewer would
  rightly call out the train=test problem.
- 9 systems (add ChatGPT + generic Claude as 8/9) : rejected on cost
  ($35 → $50+) and diminishing scientific return.

---

## ADR-004 — ChatGPT recordings replaced by API baselines (2026-04-13)

**Context.** Runs 1-10 used `chatgpt_recorded` (manual ChatGPT Plus web UI
responses, frozen at 2026-04-10) as the third system. This was non-
representative : short responses, no system prompt, manual transcription.

**Decision.** Remove `chatgpt_recorded` entirely in Phase F. Replace with
API-driven `OpenAIBaseline` (×2 configurations) in the 7-system matrix.

**Rationale.**
- Reproducibility : API calls are deterministic + scriptable, web UI
  recordings are not.
- Controllability : we can set temperature, max_tokens, system prompt
  exactly — web UI injects hidden context.
- Fairness : the API version is what a developer would actually use.

**Alternatives.** Keep recordings as supplementary : rejected, confuses
the narrative.

---

## ADR-005 — Dev/test split at 32/68 instead of 80/20 random (2026-04-13)

**Context.** The original 32 questions have been used for 10 runs of
prompt tuning (v3 → v3.1 → v3.2). A reviewer would rightly say
"train = test, overfitting".

**Decision.** Preserve the 32 original questions as `dev` set (for
historical traceability and prompt tuning). Add 68 brand-new questions
as `test` set (generation assisted by Claude Opus, manual review). The
**headline numbers in the study report will come from the test set**.

**Rationale.**
- Historical traceability : we can still compare Run F to Run 1-10
  via the dev subset.
- Hold-out honesty : test set has never informed any prompt change.
- Category balance preserved : both splits cover the 9 categories
  proportionally.

**Alternatives.**
- 80/20 random split : rejected — loses historical comparability.
- 50/50 : rejected — dev too small to still calibrate prompts.

---

## ADR-006 — Human evaluation via 2 students (IA + Cyber), not domain experts (2026-04-13)

**Context.** Original Phase G plan mentioned "expert humain" as a
ground truth. Matteo pushed back : no expert available, but 2 student
peers available (1 IA, 1 Cyber student).

**Decision.** Use 2 students × 30 blind-labelled questions as the human
eval protocol. Measure :
- Inter-student Cohen's κ (agreement between the 2)
- Student-vs-Claude κ (validates LLM-as-judge methodology)
- Student ranking of the 7 systems (headline human-preference metric)

**Rationale.**
- Students represent the target audience (18-22 yr olds in orientation
  decisions) — their preferences are diagnostic.
- 2 students gives us agreement stats; a single expert would not.
- Zero API cost for this layer → doesn't compete with Run F/G budget.

**Alternatives.**
- No human eval : rejected — the paper needs human validation of
  LLM-as-judge to be defensible.
- Recruit paid experts : rejected on cost + timeline.

---

## ADR-007 — NEUTRAL_MISTRAL_PROMPT as baseline (2026-04-12, Phase E.1)

**Context.** Runs 6-9 compared `our_rag` against `mistral_raw` where
mistral_raw used the *same* v3.2 prompt as our_rag. This handicapped the
baseline : mistral_raw had to respect rules (anti-confession, Plan A/B/C,
etc.) designed for a RAG-augmented model.

**Decision.** Create `NEUTRAL_MISTRAL_PROMPT` — a plain generic-assistant
prompt — and use it for the 3 `*_neutral` baselines (mistral, gpt4o,
claude).

**Rationale.**
- Scientific integrity : a fair baseline must not be crippled by rules
  it can't satisfy (can't cite sources when it has no retrieval).
- Reveals the true contribution of the RAG + prompt combination.
- Run 10 showed the gap grew from +0.25 (unfair) to +5.31 (fair) — i.e.
  we had been *underestimating* OrientIA's contribution all along.

---

## ADR-008 — MMR post-rerank with λ=0.7 default (2026-04-15, Phase F.3.a)

**Context.** Run 10 analysis showed `diversite_geo` failing : top-5
retrievals were often 3+ near-duplicate Paris-EFREI fiches.

**Decision.** Add Maximal Marginal Relevance as a post-rerank selection
step with default `λ=0.7` (moderate balance leaning toward relevance).

**Rationale.**
- MMR is the standard IR technique for this exact problem (Carbonell &
  Goldstein 1998), well-understood and auditable.
- λ=0.7 keeps relevance primary — we don't want to surface irrelevant
  fiches for the sake of diversity. Per-intent `intent_to_config()` can
  override to more aggressive (0.3-0.4) for decouverte / geographic.
- Embeddings already in FAISS → reconstructing them via
  `index.reconstruct()` is free (no extra Mistral API calls).

**Alternatives.**
- Structural diversity (filter by distinct `ville`) : rejected —
  less principled, doesn't generalise.
- Embedding-based clustering : rejected on complexity.
- Do nothing and trust the reranker : rejected — the failure mode is
  real and empirically measured.

---

## ADR-009 — Rule-based intent classifier, not LLM (2026-04-15, Phase F.3.b)

**Context.** Different question types benefit from different retrieval
strategies. Need a way to classify each question before retrieval.

**Decision.** Rule-based classifier (regex + keyword lists + closed-set
city/region match) mapping French questions to 7 intents.

**Rationale.**
- **Deterministic**. Same question → same intent. Critical for
  reproducibility and paper defensibility.
- **Zero API cost**. LLM classifier would add 100 calls per benchmark
  run, inflating OpenAI tier-1 rate-limit pressure.
- **Auditable**. We can show the exact regex patterns in the paper
  appendix. No "trust the model".
- **Fast to iterate**. Test-driven : add a failing case, extend the
  regex, move on.

**Alternatives.**
- Zero-shot LLM classifier (mistral-small) : rejected on cost + non-
  determinism.
- Fine-tuned French BERT classifier : rejected — overkill for 7 classes
  with clear surface patterns.

---

## ADR-010 — Skip manual label expansion (F.3.c) (2026-04-15)

**Context.** Original Phase F plan included F.3.c : expand
`data/manual_labels.json` from 21 → ~50 entries (add CTI / CGE / Grade
Master systematically).

**Decision.** **Skip F.3.c** as planned. Do not expand labels manually.

**Rationale.**
- The target "21 → 50" is negligible vs the 443 total fiches. Even
  hitting 50 would keep coverage at 11% of the knowledge base — the
  label boost multiplicative effect would still be diluted.
- For a *systemic* neutralité gain, we'd need 200+ labels (cross-
  referencing CTI's official 210-school list, CGE's 242, Grade Master's
  600+). That's a multi-day task not fitting Phase F's 3-day window.
- Run 10 already showed `neutralite` as a strength, not a weakness.
  Investing F.3 effort in MMR + intent (which target the actual
  weaknesses : diversite_geo, comparaison) has higher expected gain.
- Deferred option F.3.c-pro (proper 200+ label expansion) remains on
  the table post-Run F if empirical data shows a neutralité gap.

**Alternatives considered.** Do F.3.c half-heartedly : rejected on
principle — half work hurts credibility more than no work.

---

## ADR-011 — Multi-judge (Claude Sonnet + GPT-4o) instead of single judge (2026-04-15, Phase F.4)

**Context.** Runs 1-10 used Claude Sonnet 4.5 as the sole judge. A
reviewer could rightly say : "single-judge bias undetectable".

**Decision.** Use 2 judges in parallel for Run F : Claude Sonnet 4.5
and GPT-4o. Run G will add Claude Haiku as a 3rd judge (cheap, enabling
fact-check).

**Rationale.**
- Inter-judge agreement (Cohen's κ) measures methodological robustness.
  If κ ≥ 0.6 (substantial), we can defend the LLM-as-judge approach.
- Two vendors (Anthropic + OpenAI) reduces shared-bias risk.
- The shared JUDGE_PROMPT is byte-identical across judges — any
  disagreement is attributable to the model, not the instruction.

**Alternatives.**
- Stick with single judge : rejected on reviewer pushback risk.
- Three judges from the start : rejected on cost + coordination ; scale
  up progressively (2 → 3 at Run G once infrastructure proven).

---

## ADR-012 — 12 RPM OpenAI rate limiter instead of upgrading tier (2026-04-15, Phase F.4)

**Context.** First Run F attempt was running at 5 min/question due to
OpenAI tier-1 caps (15 RPM for gpt-4o). Exponential backoff from
parallel 429s turned a 30-min run into 8h.

**Decision.** Ship a thread-safe rate limiter capping combined OpenAI
rate at 12 RPM. Do NOT upgrade OpenAI tier.

**Rationale.**
- **Zero quality compromise**. Same models, same prompts, same matrix.
  Only orchestration changed.
- **Tier upgrade is slow** : requires $50 cumulative spend + 7 days
  (policy), not activable on-demand.
- **12 RPM = 60/12 = 5s gap with 20% safety margin** below the 15 RPM
  cap. Empirical : zero 429 after deploy.
- **Wall-time drops 8h → ~1h** (Mistral + Anthropic stay unthrottled).

**Alternatives.**
- Drop to 1 OpenAI baseline : rejected — breaks the 7-system matrix.
- gpt-4o-mini on one baseline : rejected — breaks cross-vendor
  consistency.
- Batch API (50% cheaper, 24h delay) : rejected — breaks iteration loop.

---

## ADR-013 — Progressive Run F : 1 run first, then decide variance runs (2026-04-15)

**Context.** Phase F plan called for 3 runs × 7 systems × 100 questions
for variance measurement (~$35). Without seeing intermediate results,
this is a big commit.

**Decision.** Run a single full F pass first (~$15-20), checkpoint with
Matteo, then decide whether to commit to 2 additional runs ($25-30 more)
based on signal strength.

**Rationale.**
- **Risk mitigation** : if our_rag ≤ mistral_v3_2_no_rag on Run 1,
  variance runs won't change the story. Save budget for debugging.
- **Fast feedback loop** : 1h vs 3h wall-time per decision cycle.
- **Budget discipline** : aligns with "ZERO intermediate benchmarks"
  rule — Run F-1 is itself the "result", not an intermediate.

**Alternatives.** Commit all 3 runs upfront : rejected on risk.

---

## ADR-014 — Fact-check layer flips the RAG result (2026-04-16, Phase G)

**Context.** Run F-1 dual-judge analysis showed `our_rag` ≤
`mistral_v3_2_no_rag` on both Claude Sonnet and GPT-4o rubric judges
(Δ -0.27 and +0.04 respectively). This matched the ADR-013 negative-
result scenario : the RAG seemed to add no value beyond the v3.2
prompt engineering.

**Discovery via Haiku fact-check (Phase G).** We ran a third-layer
Claude Haiku 4.5 fact-check that classifies each factual claim as
`verified_fiche`, `verified_general`, `unverifiable`, or `contradicted`.
Applied as a multiplicative weight on the `sourcage` criterion
(via the existing `judge_v2.reweight_v1_scores` logic, shipped in
Phase 3.2 but never previously run at scale).

**Findings** :
- Raw honesty score (fraction of verified claims): `claude_neutral` 0.837
  (no sourcing rule) → `mistral_v3_2_no_rag` 0.562 (worst). `our_rag`
  0.575, just above `mistral_v3_2_no_rag`.
- **RAG contribution (our_rag − mistral_v3_2_no_rag)** after fact-check:
  - Claude judge, in-domain 92q : -0.14 → **+0.03** (flip to win)
  - GPT-4o judge, in-domain 92q : +0.22 → +0.23 (stable win)
  - Overall 100q : Claude -0.27 → -0.06 ; GPT-4o +0.04 → +0.06 (tie)
- Per-category shifts (Claude) where fact-check matters most:
  - adversarial : -1.40 → -0.70 (shift +0.70, biggest win)
  - biais_marketing : -1.17 → -0.50 (shift +0.67)
  - cross_domain : -1.75 → -1.12 (shift +0.62)
  - realisme : +0.58 → +0.92 (shift +0.33)

**Decision — the paper's pivotal claim** : the v3.2 prompt's "cite your
sources" rule forces baselines without RAG to **fabricate plausible-
but-unverifiable institutional citations** that naïve LLM-as-judge
methodologies reward as "good sourcing". A deterministic fact-check
layer reveals the asymmetry and restores a measurable RAG advantage.

**Rationale.**
- Scientifically defensible : both judges agree on the direction of
  the shift, and the honesty score ranking (Haiku) is orthogonal to
  the rubric ranking.
- Methodologically novel : LLM-as-judge papers rarely check the
  factuality of cited sources. The finding is publication-worthy.
- Fair to all systems : the fact-check is applied with `retrieved=[]`
  for every system, so `our_rag` doesn't get a special treatment
  (the advantage comes only from real-world truth of its claims).

**Alternatives considered.**
- Run F variance runs ×2 to stabilise the v1 "RAG loses" finding and
  publish the negative result : rejected because Phase G's fact-check
  was already planned and happened to reverse the story.
- Reject the fact-check as too expensive to include in methodology :
  rejected because Haiku at $0.005/call made 700 fact-checks affordable
  (~$3.50 total).

**Caveat** : 6 of 700 fact-check calls (the last 6 cross_domain
questions) were processed by Claude Sonnet 4.5 instead of Haiku
(Anthropic 529 Overloaded on Haiku endpoint). Same prompt, same model
family — methodologically acceptable, documented in the paper.

---

## ADR-015 — Incremental save mandatory for all judge runs (2026-04-15)

**Context.** On 2026-04-15, the Claude Sonnet judge run for Run F
stalled on an Anthropic API degradation after ~80-90 questions had
been judged in-memory. Because `judge_all()` only returned its
accumulated list AT THE END, killing the process to stop the budget
bleed also lost all paid-for scores. ~$14 of Anthropic credit evaporated.

**Decision.** All judge / fact-check functions must accept a `save_path`
parameter and write the accumulated list to disk atomically after EACH
question. On resume, existing entries skip the API call to avoid
double-billing.

**Rationale.**
- Budget safety : protects against API degradation, SIGTERM, OOM, any
  unexpected interrupt.
- Mirrors `runner.py`'s established pattern for generation (same
  `done_ids` skip logic).
- Zero performance cost : a 100-item JSON rewrite per second is
  negligible vs the API call latency.

**Implementation** : commit `3c4daf8` (fix(eval): CRITICAL incremental
save + resume for judge_all). Tests cover (a) file grows after each
call, (b) resume-from-disk skips already-judged entries.

---

## Pending decisions (to be logged when made)

- ADR-016 : Whether to run F variance runs (×2 more) — pending Matteo
  checkpoint after ADR-014 finding.
- ADR-017 : Whether to add Voyage embeddings as hybrid retrieval —
  post-Run F.
- ADR-018 : Final study report format (markdown only vs markdown + PDF)
  — Week 3.
- ADR-019 : Demo UI stack (FastAPI + React vs Next.js) — optional, Week 3.
- ADR-020 : Fix for `passerelles` -0.42 loss under fact-check — diagnostic
  pending.

---

## ADR-021 — Repivot stratégique : système qui gagne > paper qui démontre (2026-04-17)

**Context** : Run F+G (16 avril 2026) a révélé que le RAG ne contribuait
rien à la rubric nue (-0.27 vs prompt seul). L'hypothèse initiale
"démontrer l'efficacité du RAG re-ranking" n'est pas tenable.

**Decision** : pivot. La cible devient "construire un système d'orientation
qui bat ChatGPT / Claude / Mistral chat sur l'accompagnement des lycéens
et étudiants français", pas "publier un negative result honnête sur le
RAG". Validé par Matteo le 2026-04-17.

**Rationale** :
- Le concours INRIA est jugé sur la qualité du système, pas du paper
- Un système qui donne les chiffres Parcoursup 2025 + tendances + profils
  admis bat un LLM généraliste même sans preuve statistique de contribution RAG
- On peut toujours publier honnêtement les résultats après coup

**Impact** : préserve ADR-001 à ADR-020. Les 4 axes data foundation,
agentic, RAFT, UX s'ajoutent, ne remplacent pas.

---

## ADR-022 — Format de citation structurée stable pour futur RAFT (2026-04-17)

**Context** : tout RAG souffre du "LLM paraphrase sans citer". Sans format
stable, impossible de mesurer précision des attributions ou faire du
fine-tuning RAFT (exige format explicite).

**Decision** : figer un format `##begin_quote## ... ##end_quote##` dans
system.py à partir de Vague A. Ne plus le changer avant RAFT éventuel.

**Rationale** : Mistral medium ne l'adopte pas spontanément (3/6 → 0/6
sur les itérations), MAIS le format reste utilisé verbatim dans les
exemples RAFT futurs → cohérence train/prod critique. Le LLM utilise
l'esprit (cod_aff_form inline) plutôt que la forme exacte → acceptable.

---

## ADR-023 — Sanity UX α (brièveté) + β (exploitation signaux) (2026-04-17)

**Context** : post-Vague A/B/C, diagnostic diff qualitatif : LLM produit
~10 000 caractères par réponse en utilisant peu les signaux Vague A
(cod_aff_form, trends). Pattern convergent sur 3 itérations.

**Decision** : addition stricte au system prompt d'une section "RÈGLES
PRIORITAIRES UTILISATEUR FINAL LYCÉEN" qui :
- α : override ~1000 mots → **300-500 mots**, Plan A/B/C préservé 2-3 lignes max
- β : force citation cod_aff_form quand Parcoursup cité, mention trends
  quand présentes

**Résultat mesuré** : longueur 1421 → 661 mots (-54%), B3/B5 améliorés,
B6 citation precision 1.00 maintenu, cod_aff_form cités 0 → 10 sur 6 réponses.

**Limitation révélée 2026-04-18** : 300-500 mots reste trop long pour les
4 testeurs unanimes. Tier 2 ramènera à 150-300 mots.

---

## ADR-024 — Extension domaine santé + quality data gaps (2026-04-17)

**Context** : corpus restreint à cyber + data_ia → non représentatif de
l'orientation des lycéens français (santé = 2e flux). Matteo confirme
extension santé comme preuve de généralisation.

**Decisions** :
1. DOMAIN_KEYWORDS santé (25 mots-clés : PASS, L.AS, médecine, kiné, IFSI,
   pharmacie, orthophon, infirmier, ergothérap, etc.)
2. 10 codes ROME J1xxx pour santé
3. Bug fix manual_labels leak : Stage 3 restreint à cyber/data_ia (les PASS
   santé de Limoges/Rennes héritaient erronément de SecNumEdu)
4. Seuil statistique MIN_SORTANTS=20 + sample_size_tier (PR #7, non mergée)
5. Visibilité ⚠AGRÉGAT dans generator (PR #7, non mergée)
6. infer_niveau étendu aux D.E santé (PR #7, non mergée)

**Effet cumulé** : 443 → 1424 fiches (+221%), 9 → 194 matches InserSup.

---

## ADR-025 — Tier 0 corrections critiques post-user-feedback (2026-04-18)

**Context** : spot-check Matteo + 4 tests utilisateurs (lycéen, étudiante,
M1, parent DRH, conseiller d'orientation pro) ont identifié 9
convergences absolues cross-profils, dont 3 critiques (bugs InserSup,
discriminations sexistes, codes admin visibles) et 6 erreurs factuelles
récurrentes.

**Decisions** (PR #8) :

1. **Bug InserSup taux emploi null** : `_sum_emploi_components` additionne
   les 3 composantes (sal_fr + non_sal + etranger). La colonne agrégée
   est null dans le dataset 2025_S2.
2. **Bug InserSup obtention_diplome non-déterministe** : filtre explicite
   `obtention_diplome="ensemble"` — vue publique MESR par défaut, inclut
   les non-diplômés (pertinent pour orientation).
3. **Fusion cohortes par métrique** : `_pick_merged` remplace
   `_pick_freshest` — pour chaque métrique, prend la valeur non-null de
   la cohorte la plus fraîche. `cohortes_used` exposé pour audit.
4. **Règles dures anti-discriminations** : le % de femmes n'est JAMAIS
   un argument positif/négatif. Formulations "100% de femmes →
   environnement solidaire/adapté/accessible" explicitement interdites.
5. **Anti-hallucinations** : 6 erreurs factuelles identifiées listées
   comme interdictions explicites dans system prompt :
   - MBA HEC "plus accessible avec expérience" → faux (5-8 ans + GMAT 700 + 80k€)
   - École 42 "gratuite en alternance" → gratuite tout court
   - Passerelle VAP Infirmier → Kiné → quasi-impossible en 22 ans pratique
   - Prépas privées médecine "2x chances" → marketing, biais de sélection
   - CentraleSupélec en "Plan A" → post-prépa très sélective
   - "X pour les Nuls" pour concours <20% → conseil catastrophique
6. **"Fabrique pas un Plan A artificiel"** : règle autorisant le LLM
   à dire honnêtement "ta voie directe n'est pas réaliste" quand le
   profil est incompatible (ex : 11/20 visant HEC).
7. **Masquage codes admin dans sortie** : `_source_line` expose URLs
   comme instructions LLM pour liens markdown cliquables
   `[fiche Parcoursup](URL)`. System prompt interdit citer
   cod_aff_form/RNCP/FOR.xxx en clair.
8. **Renvoi humain systématique** : rappel SCUIO/CIO/Psy-EN obligatoire
   (demande unanime Catherine + Dominique).

**Effets mesurés** :
- Taux emploi 12m : 0/194 → **194/194** (100% des fiches insertion)
- Taux ET salaire 12m combinés : 9/194 → **189/194** (97.4%)
- Validation end-to-end : question EFREI produit
  `[fiche Parcoursup EFREI Paris](URL)` au lieu de `cod_aff_form: 36040`

**Tests** : 343 → 348 verts, +5 Tier 0, zéro régression.

---

## ADR-026 — Règle absolue : spot-check manuel obligatoire avant merge source data (2026-04-18)

**Context** : l'audit automatique d'InserSup a validé les salaires (corrects)
et déclaré "0 outlier" — mais a **raté** que le taux d'emploi était null
partout sur 194 fiches. Parce qu'il ne comparait pas avec la donnée
officielle disponible, seulement avec ses propres seuils de sanité.

**Decision** : gravée comme **règle absolue du projet**.

> Ne jamais merger une nouvelle source data externe sans spot-check manuel
> de 3-5 échantillons vs source officielle.

**Rationale** :
- L'audit automatique peut valider la cohérence interne mais ne peut pas
  détecter les erreurs de parsing / de colonne (on ne compare pas avec ce
  qu'on ne sait pas regarder)
- Le coût humain est faible (~30 minutes pour 5 échantillons)
- Le coût d'une erreur data sur un outil conseil aux mineurs est
  disproportionné (cf règle "zéro tolérance" de Matteo)
- Sans ce spot-check, on aurait livré InserSup avec taux d'emploi null
  partout — catastrophe silencieuse

**Alternatives rejetées** :
- Confiance à 100% dans l'audit automatique → échec empirique démontré
- Tests utilisateurs comme garde-fou unique → arrive trop tard dans le
  cycle, chers à organiser

**Implications** : règle applicable à ONISEP API live, France Compétences
RNCP, classements externes, toute source future. Le script d'audit
automatique reste utile pour détecter les outliers, mais ne remplace
JAMAIS le spot-check manuel.

---

## ADR-027 — Plan de travail Tier 0 → 4 post-user-feedback (2026-04-18)

**Context** : feedback utilisateurs 2026-04-18 révèle plus de dette
utilisateur que prévu. Hiérarchisation nécessaire pour ne pas tout
faire en même temps.

**Decision** : plan en 4 tiers de priorité décroissante.

- **Tier 0** (PR #8, fait) : bugs InserSup + anti-discriminations +
  masquage codes + anti-hallucinations + renvoi humain
- **Tier 1** (à faire) : anti-hallucination approfondie (scorer
  automatique des 6 erreurs identifiées), détection programmée des
  patterns interdits dans les sorties
- **Tier 2** (à faire, prochain gros chantier) : pyramide inversée
  (TL;DR 3 lignes → chiffres → détail), brièveté **150-300 mots** (vs
  300-500 du sanity UX qui reste trop long), détection niveau utilisateur
  (terminale/L2/M1/reconversion), format adapté par type de question
  (conceptuelle vs comparaison vs choix vs hors-corpus)
- **Tier 3** : ⚠Attention aux pièges généralisés, mode exploration
  préalable (questionnement Socratic avant recommandation, aligne avec
  question participant INRIA sur pensée critique), témoignages étudiants
  (dataset à construire), coût total études, disclaimer permanent
- **Tier 4** : trancher positionnement α (Parcoursup-only) vs β (élargi
  carrière 20-30 ans, gap marché identifié par Thomas 23)

**Critère de succès Tier 2** : refaire tester par les 4 mêmes profils.
Si Léo passe "décroche au milieu" → "lu en entier", Sarah cesse de se
sentir infantilisée, Catherine cesse de relever des erreurs graves,
Dominique recommanderait à un élève seul → on est sur la bonne voie.

---

## ADR-028 — Fermeture PRs redondantes après Tier 0 (2026-04-18)

**Context** : 3 PRs ouvertes à clarifier :

- PR #7 `feature/fix-data-quality-gaps` — niveau D.E. santé +
  MIN_SORTANTS=20 + visibilité ⚠AGRÉGAT. Utile mais dépassée par Tier 0
  (qui a changé la forme du disclaimer et le schéma de cohortes).
- PR `docs/session-2026-04-17-continuity` — SESSION_HANDOFF §13 + 4 ADRs.
  Superseded par §13+14 consolidés dans PR #8.
- PR #8 `fix/tier0-critical-user-feedback` — Tier 0 critique, en attente
  validation Matteo.

**Decision** :

- **Merger PR #8** (Tier 0) après spot-check passé par Matteo
- **Fermer PR #7** et re-faire seulement les fixes encore pertinents
  dans Tier 2 :
  - niveau D.E. santé → garder (utile au reranker)
  - MIN_SORTANTS=20 → évaluer si nécessaire après fix taux emploi
    (maintenant qu'on a vraiment 194 fiches insertion, filter agressif
    pourrait être contre-productif)
  - visibilité ⚠AGRÉGAT → déjà fait différemment dans Tier 0
- **Fermer branche docs/session-2026-04-17-continuity** — redondante
  avec la doc commit de PR #8

**Rationale** : chaîne de PRs non-mergées crée de la confusion et de la
dette mentale. Un seul merge propre (Tier 0 + doc complète) remet le
projet sur des rails clairs.

---

## ADR-029 — Tier 2 UX livré et mergé (2026-04-19)

**Context** : après Tier 0 mergé sur main (PR #8, 2026-04-19), le plan
Tier 1-4 (ADR-027) positionnait Tier 2 comme prochain gros chantier.
Cible : adresser la plainte unanime #1 des 5 user tests (TROP LONG)
avec pyramide inversée, brièveté 150-300 mots, détection niveau user,
format par type de question.

**Decision** (PR #9 mergée sur main le 2026-04-19) : livraison de
5 sous-chantiers modulaires Tier 2.1 → 2.5.

### Sous-chantiers livrés

**Tier 2.1 — Pyramide inversée + brièveté** (`src/prompt/system.py`) :
ajout du bloc "RÈGLES TIER 2" avec 12 sous-règles T2.1-T2.12. Sections
obsolètes marquées explicitement (α 300-500 et FORMAT DE SORTIE v3.2
remplacés, non plus appliqués).

**Tier 2.2 — Détection niveau user** (`src/rag/user_level.py`, nouveau) :
classifier heuristique regex mappant les questions vers 5 classes
(terminale / licence / master / reconversion / inconnu). Ordre de
priorité : reconversion (âge/carrière) > master (M1/M2/bac+4-5) >
licence (L1-L3/BTS/BUT) > terminale (terminale/lycéen/17 ans) > inconnu.
La guidance associée est injectée dans le user prompt via
`build_user_prompt(user_guidance=...)`.

**Tier 2.3 — Format par type de question** (`src/rag/intent.py`
enrichi) : nouvelle fonction `intent_to_format_guidance` qui mappe
les 7 intents existants vers des hints de format (comparaison→tableau,
conceptual→didactique, decouverte→hors corpus, etc.). Réutilise
le classifier `classify_intent` sans duplication.

**Tier 2.4 — Attention aux pièges** : règle T2.4 impose section
"⚠ Attention aux pièges" systématique sur choix/comparaison, avec
exclusion explicite pour questions conceptuelles.

**Tier 2.5 — Pack user test v2** (`results/user_test_v2/`, nouveau) :
re-génération des 10 mêmes questions post-Tier 2 pour comparer. 5
profils (Léo 17, Sarah 20, Thomas 23, Catherine 52, Dominique 48
Psy-EN pro 22 ans) ont fait leur audit.

### Résultats mesurables v1 → v2

| Métrique | v1 (2026-04-17) | v2 (2026-04-19) | Δ |
|---|---|---|---|
| Mean word count | 801 | 484 | **-40%** |
| Median | 828 | 448 | -46% |
| Max | 1258 | 649 | -48% |
| TL;DR présent | 0/10 | 10/10 | +100% |
| Attention aux pièges | 1/10 | 9/10 | +80% |
| Q4 conceptual sans Plan A/B/C | non | oui | format-par-intent OK |
| Sexism violations | 0/10 | 0/10 | Tier 0 tient |
| Admin codes en clair | 0/10 | 0/10 | Tier 0 tient |

### Verdict utilisateurs v2

Primitives validées unanimement : TL;DR, Attention aux pièges, tableau
comparaison (Q3, Q9), renvoi Psy-EN/CIO/SCUIO, liens Parcoursup. Q8
PASS 12 de moyenne = gabarit consensus 5/5.

Mais **3/5 profils maintiennent "non recommandable pour mineur en
autonomie"** à cause de 7+ hallucinations factuelles distinctes
identifiées en "(connaissance générale)" :
- ECN confondu avec EDN (réforme R2C 2023)
- Bac S cité comme bac actuel (supprimé 2021)
- Distances géographiques inventées (Périgueux-Perpignan 3h30 → réel 5-6h)
- VAE confondue avec VAP
- Certificat de Spécialisation présenté comme standalone
- Coûts écoles privées sous-estimés 20-40%
- Concours Tremplin/Passerelle attribués à HEC à tort
- Formations inventées (Licence Humanités-Parcours Orthophonie)

**Tests** : 348 → **426 verts** (+78 Tier 2). Tier 0 intégralement
préservé.

**Rationale** : -40% word count est un gain structurel mesuré, pas
un gain cosmétique. Mais les hallucinations factuelles nécessitent
un pivot architectural (α restricted LLM testé, puis agentic ou
RAFT — cf ADR-030 et ADR-031).

---

## ADR-030 — α Restricted LLM : preuve empirique du plafond prompt-engineering (2026-04-19)

**Context** : 5 user tests v2 ont identifié ~7 hallucinations
factuelles distinctes en "(connaissance générale)". Cause racine
hypothétique : ANTI-CONFESSION (fix Phase 1 Run 7) force le LLM
à compenser les trous du corpus par des inventions plausibles.
Hypothèse α : remplacer cette stratégie par une discipline
d'abstention structurée résout les hallucinations.

**Decision** : implémenter α sur branche `feature/alpha-restricted-llm`
avec protocole baseline + regression (expert recommendation 2026-04-19).
Ajout de 4 règles :
- α.1 Liste blanche explicite des connaissances stables autorisées
  (cadre LMD, calendrier Parcoursup, rôles Psy-EN/SCUIO/CIO, bac et
  mentions, labels officiels, EDN remplace ECN depuis 2023, VAE/VAP
  distincts, voies d'accès HEC)
- α.2 Abstention structurée pour tout hors liste blanche et hors corpus
  (distances, coûts, noms formations, taux, calendriers spécifiques)
- α.3 Override ciblé d'ANTI-CONFESSION pour questions entièrement
  hors-scope (aveu d'ignorance autorisé et souhaité)
- α.4 Renvoi explicite autorisé (modifie "ne redirige jamais")

**Résultats empiriques v2 → v2-α (pack re-généré)** :

| Hallucination | v2 | v2-α | Delta |
|---|---|---|---|
| ECN comme nom actuel | 1/10 | 1/10 | = |
| Bac S cité comme actuel | 3/10 | 3/10 | = |
| Licence Humanités Ortho inventée | 1/10 | 1/10 | = |
| Périgueux 3h30 | 1/10 | 0/10 | ↓ |
| Pattern "Je n'ai pas de source vérifiée" | 0/10 | 0/10 | = |

Word count : 484 → 474 (neutre). Tier 0 + Tier 2 préservés.

**Verdict** : α a **préservé** l'existant et corrigé 1 cas mineur
(Périgueux), mais **n'a PAS fait bouger** Mistral medium sur les
hallucinations principales. Le LLM **n'adopte pas** le pattern de
refus explicite "Je n'ai pas de source vérifiée" (0/10 occurrences).

**Rationale** : **preuve empirique que le prompt-engineering seul
n'est pas suffisant pour résoudre les hallucinations factuelles sur
Mistral medium**. C'est une limite architecturale du modèle
sous-jacent, pas un défaut de prompt. Cette donnée est importante
pour le paper INRIA : elle justifie empiriquement le pivot vers
une approche architecturale (Axe 2 agentic ou Axe 3 RAFT).

**Status** : α **mergeable comme filet non-régressif** (0 régression
Tier 0/Tier 2, 1 petite victoire). PR #10 pas encore ouverte, décision
reportée — le gain marginal ne justifie pas à ce stade l'empilement
dans main. Si Axe 2 agentic est livré sans α, α peut rester en branche.

**Alternatives rejetées** :
- Itérer α 2-3 fois avec prompts encore plus agressifs → pattern
  "empile des fixes" que l'expert a identifié comme anti-pattern.
  Plafond Mistral medium probablement indépassable par prompt.

---

## ADR-031 — Pivot Axe 2 agentic remplace RAFT dans sprint 2 semaines (2026-04-19)

**Context** : plan initial 2 semaines α + β (RAFT) selon expert
recommendation. Mais critère Matteo élargi "outil qui bat ChatGPT
mesurablement ET aide les jeunes pour études + monde pro" change
la priorisation. Thomas (M1 fintech) et Sarah (L2 réorientation)
sont **dans la cible**, pas hors-cible.

**Decision** : remplacer "α + RAFT 2 semaines" par "α + Axe 2 agentic
prototype 2 semaines". RAFT reste en réserve S3+ (optionnel si
agentic insuffisant).

### Pourquoi agentic plutôt que RAFT sur tes critères

| Critique user v2 | RAFT | Agentic |
|---|---|---|
| Phase exploratoire manquante (Dominique déontologique) | Non | Oui (ProfileClarifier A2) |
| "Il me connaît pas et il répond" (Léo) | Non | Oui |
| "Pose une question avant" (Sarah) | Non | Oui |
| "Formation pas métier" (Thomas, critère élargi) | Non | Oui (tools ROME/InserJeunes) |
| "Coûts cumulés" (Catherine) | Non | Oui (tool dédié trivial) |
| Hallucinations factuelles | Oui (gate R7 à 30-40% échec) | Partiel (Validator A6) |

Agentic adresse **5/6 verdicts users**. RAFT adresse surtout le 6e.

### Risques nommés

1. **Dépendance Axe 1 étendu** : sans data pro (ROME, InserJeunes, APEC),
   les tools get_debouches/get_insertion_stats sont vides = agents creux.
   **D3+D4+D5 prérequis dur en S1** (plus "opportuniste").
2. **Souveraineté partielle** : orchestrateur Claude Sonnet → Mistral
   Large (cf ADR-032 POC validé).
3. **Latence multi-call** : 3-5 tools par question = 10-15s. Acceptable
   pour orientation (pas chat temps réel).
4. **Debug plus complexe** : fallback single-shot pipeline si agent échoue.

### Ce qui se conserve

**Tier 2 n'est PAS jeté.** Le Composer agent hérite du prompt v3.2 +
Tier 2 (TL;DR, Attention aux pièges, format par intent). Les gains
mesurés -40% longueur sont préservés dans le Composer.

**Alternatives rejetées** :
- RAFT seul (plan initial) : gate R7 30-40% risque d'échec, 2 semaines
  dataset curation, narrative forte mais coût élevé si échec.
- α seul : α a échoué empiriquement (ADR-030), insuffisant.
- α + RAFT + agentic parallèle : trop de fronts ouverts, palimpseste.

---

## ADR-032 — Mistral Large orchestrator validé (POC H, 2026-04-19)

**Context** : Axe 2 agentic exige un orchestrateur tool-use. STRATEGIE
§5 Axe 2 prévoyait Phase 1 Claude Sonnet pour prototypage rapide,
Phase 2 Mistral Large pour souveraineté. Matteo a refusé Claude
Sonnet même en Phase 1 (ADR-001 Mistral souveraineté).

**Decision** : Mistral Large (`mistral-large-latest`) comme orchestrateur
direct. POC H lancé 2026-04-19 pour valider empiriquement avant
investissement S2.

### Résultats POC H (5 questions représentatives)

| Question | Tool calls | Iterations | Latence | Succès |
|---|---|---|---|---|
| ranking_cyber | 2 | 2 | 15.0s | ✓ |
| realisme_sante | 1 | 2 | 10.9s | ✓ |
| debouches | 3 | 2 | 18.5s | ✓ |
| comparaison | 2 | 2 | 20.6s | ✓ |
| conceptuelle | 0 | 1 | 19.7s | ✓ |

- **5/5 succès** (schémas respectés, params valides, pas d'hallucination param)
- **Latence moyenne 16.9s** (légèrement au-dessus du gate arbitraire 15s)
- **Conceptuelle Q5 sans tool call** → 1 iteration, Mistral distingue
  correctement quand les tools ne sont pas nécessaires
- Réponses cohérentes, intégration propre des tool results

**Verdict** : gate technique **PASS**. Latence 17s acceptable pour UX
orientation (pas chat temps réel). Optimisations futures possibles
(parallélisation tool calls, cache LRU, Composer hors loop).

**Decision finale** : Mistral Large orchestrator **validé pour Axe 2
S2**. Narrative souveraineté française préservée. Composer agent final
reste Mistral Medium.

**Alternatives de secours si POC échoue** (non utilisées) :
- Mistral Medium + ReAct from-scratch (plus fragile, debuggable)
- Claude Sonnet temporaire + Composer Mistral (perd partie narrative)

Fichiers : `experiments/poc_mistral_toolcall.py`,
`experiments/poc_mistral_toolcall_results.json`.

---

## ADR-033 — Task B fixes UX indépendants LLM (2026-04-19)

**Context** : 5 user tests v2 ont identifié 3 défauts UX qui ne sont
pas architecturaux mais trivialement corrigeables côté code/prompt.

**Decisions** (3 fixes sur branche `feature/axe2-agentic-prep`) :

1. **Masquage codes ROME** (`src/rag/generator.py:_debouches_line`) :
   les codes ROME (M1812, M1819, J1102) sont retirés du texte exposé
   au LLM. Rationale identique au Tier 0 masquage cod_aff_form/RNCP/
   FOR.xxx : Léo et Dominique ont signalé "artefacts techniques sortis
   du RAG qui n'ont rien à faire devant un lycéen". Le code ROME reste
   dans le dict fiche pour le retrieval interne.

2. **Seuils de significance trends** (`src/rag/generator.py:_trend_suffix`) :
   ajout de seuils minimums (5pp taux, 15% vœux, 10 places). Les
   changements en-deçà sont omis. 5 testeurs v2 ont unanimement jugé
   les trends "décoratives ou anxiogènes" sans seuil d'actionabilité.
   On coupe le bruit à la source data plutôt qu'attendre que le LLM
   filtre (il ne filtre pas).

3. **Alertes critiques dans TL;DR** (`src/prompt/system.py` T2.2
   renforcée) : règle "Si la question porte sur une formation avec
   alerte structurante (mineure éliminatoire PASS, numerus clausus,
   coût privé >8k€, filière <10%, 10 ans d'études, VAP quasi-
   impossible), la mentionner explicitement dans les 3 lignes TL;DR".
   Catherine : "Hugo lira le TL;DR puis fermera — l'alerte doit être là".

**Rationale** : ces fixes adressent 3 symptômes mais ne touchent
pas à la cause racine (hallucinations factuelles, cf ADR-030). Ils
sont additifs et non-régressifs, mergeables sans risque.

**Tests** : 426 → 426 verts (pas de régression, fixes affectent
comportement LLM mais pas assertions tests).

---

## ADR-034 — D3a ROME 4.0 référentiel offline (partie 1/2) (2026-04-19)

**Context** : STRATEGIE §5 Axe 1 D3 prévoit intégration ROME 4.0 France
Travail API live (salaire médian + tension marché). Le zip `rome_4_0.zip`
(ROME 4.0 v460) était déjà téléchargé dans `data/raw/` (avril 2026
release, 30 CSV, ~1584 codes). Permet d'exploiter partiellement sans
signup API.

**Decision** : implémenter la partie offline (D3a) immédiatement.
Partie API live (D3b, salaire + tension) reportée à quand signup
France Travail aura lieu.

### D3a livré (`src/collect/rome.py` enrichi)

Nouvelles fonctions mémoïsées `lru_cache` :
- `get_rome_info(code_rome)` : libellé, transition_eco/num/demo,
  emploi_reglemente, emploi_cadre, code_rome_parent
- `list_all_rome_codes()` : ~1584 codes v460
- `is_emploi_cadre(code)`, `is_transition_numerique(code)` : helpers bool-safe

Compatible avec `RELEVANT_ROME_CODES` hardcodés existants (les 4 tests
initiaux de `test_rome.py` passent toujours).

### Utilité pour Axe 2

Le tool `get_debouches(code_rome)` pourra démarrer en S2 avec libellé
+ flags cadre/numérique/transition. Salaire + tension marché viendront
en D3b post-signup France Travail.

**Tests** : 426 → 430 verts (+4 tests rome offline).

**Alternatives rejetées** :
- Attendre signup France Travail pour tout faire en une fois → bloque
  Axe 2 S2 sur un paramètre externe. D3a est utile seul.
- Scraper les données salaire depuis fiches ROME web → violation ToS,
  effort élevé, qualité incertaine.

---

## ADR-035 — Validator programmatique pré-livraison + cron refresh débloquent S2 (2026-04-22)

**Context** : revue stratégique 2026-04-22 a établi 3 constats convergents :

1. **Verdict empirique user_test_v2** : 3/5 profils jugent l'outil "non
   recommandable pour mineur en autonomie" à cause de 7+ hallucinations
   factuelles distinctes.
2. **α a empiriquement prouvé** (ADR-030) que le prompt-engineering seul
   ne corrige pas ces hallucinations sur Mistral medium (pattern de refus
   explicite 0/10 occurrences malgré liste blanche stricte).
3. **Le corpus reste figé** depuis avril 2026, alors que l'argument
   souverain "données fraîches vs LLM avec cutoff" est central. Aucun
   refresh automatique en place.

Ces 3 constats imposaient une priorité avant toute extension (D5 BTS,
Axe 2 agentic, RAFT) : **stabiliser la vérité avant de grandir le
système**.

**Decision** : sprint S1 (2026-04-22 matin) livre 3 chantiers P0 en
parallèle :

1. **Validator programmatique déterministe v1** (PR #15 mergée, SHA
   `6afcacc`) — module `src/validator/` 3 couches :
   - **Couche 1 rules** : 11 règles regex couvrant les 6 anti-hallucinations
     Tier 0 (ADR-025) + nomenclatures dates/diplômes + concours HEC
     whitelist + voies impossibles + marketing trompeur + invention
     notable.
   - **Couche 2 corpus-check** : extracteur 'formation à établissement'
     + similarité composite 85% nom / 15% etab + seuil 0.55.
   - **Couche 3 fallback LLM souverain (Mistral Small)** : reportée v2 —
     les couches 1+2 catchent déjà 100% des cas tier 0 testés.
   - Wiring opt-in `OrientIAPipeline(..., validator=...)` backward-compat.

2. **D7 cron refresh mensuel** (PR #14 mergée, SHA `d72676d`) — workflow
   `.github/workflows/data-refresh-monthly.yml` cron `0 3 1 * *` +
   workflow_dispatch manuel. Refresh Parcoursup historique + current +
   InserSup. Drift detection >10%, PR auto si changement, issue auto si
   fail.

3. **Cleanup repo + documentation** (PR #13 + cette PR) — split de
   `feature/axe2-agentic-prep` palimpseste en 4 PRs, consolidation docs
   (CLAUDE.md projet, STRATEGIE_VISION_2026-04-16, packs user_test v1+v2,
   gitignore élargi, ADR-029→034 mergés).

**Rationale** :

- **Le Validator est une garantie programmatique, pas une espérance prompt.**
  Détecte ≠ bloque en v1 (UX ne change pas), mais expose `pipeline.last_validation`
  pour observabilité runtime. Phase suivante : Validator devient bloquant en
  pré-livraison (re-prompt si flagged) après gate J+6.
- **Le cron refresh active enfin l'argument différenciateur** vs LLMs
  cutoff janvier 2026. Sans refresh, dans 3 mois Parcoursup 2026-2027
  serait sorti et notre corpus 2024-2025 serait obsolète — l'avantage
  structurel s'évapore.
- **Le cleanup permet le démarrage S2 propre** : branche `axe2/pydantic-profileclarifier`
  ouverte propre depuis main, vs un palimpseste de 5 commits hétérogènes.

**Effets mesurés** :

- Validator catche 2/10 questions du pack v2 réel (Q7 ECN x3 +
  Q10 Licence Humanités-Orthophonie inventée), honesty score moyen 0.94,
  latence <1ms par answer (cible 400ms largement tenue).
- Workflow D7 actif, premier tick cron 2026-05-01 03:00 UTC, smoke test
  manuel possible via `gh workflow run`.
- 53 nouveaux tests validator + 449 tests offline globaux verts → zéro
  régression sur les 8 PRs créées + mergées.

**Alternatives rejetées** :

- **D5 BTS / Axe 2 / RAFT en priorité** : étend un système qui ment encore
  ~30% pour les mineurs. ROI négatif tant que la cause racine n'est pas
  attaquée.
- **Validator avec couche 3 LLM dès v1** : aurait été plus complet mais
  aurait étendu le scope au-delà de la fenêtre 8-12h. Les couches 1+2
  catchent déjà tous les cas Tier 0 du pack v2.
- **Cron refresh en S2 (reporté)** : gap structurel laissé ouvert pendant
  encore 1-2 sprints. Coût opportunité élevé pour un effort 4-6h.

**Suite (post-cleanup, S2)** :

- **Gate J+6 (2026-04-25)** : re-test profils avec Validator activé.
  Si verdict bouge à 4-5/5 → reporter Axe 2 agentic, focus data D2/D4.
  Si verdict stagne → Axe 2 confirmé.
- **Validator couche 3** : Mistral Small souverain en fallback (v2,
  post-gate J+6).
- **D5 BTS + D2 ONISEP live + D4 labels** : enrichissement corpus pour
  étendre la précision du Validator corpus-check.

**Références** :

- Ordres Jarvis 2026-04-22-0902 (split, validator, cron) + 2026-04-22-1016
  (cleanup pre-S2)
- Reco stratégique 2026-04-22 0832 : "arrêter d'empiler avant d'avoir un
  Validator programmatique déterministe"
- STRATEGIE_VISION §5 Axe 1 D7 (cron) + §3 Diagnostic d'expert (couche
  rules vs prompt)

---

## ADR-036 — Enrichissements UX Psy-EN reportés post-V4 (2026-04-22)

**Context** : la Psy-EN 54 (22 ans d'expérience, panel ground truth v3 du
2026-04-22) a identifié 3 enrichissements UX orthogonaux aux 4 règles dures
V2 :

1. **Couche "phase projet"** : un mineur en autonomie gagne à ce que l'outil
   commence par 2-3 questions de clarification (où en es-tu dans ta
   réflexion ? pourquoi cette formation ?) avant de donner des recos, plutôt
   que de foncer sur un "Plan A/B/C". Déontologie métier Psy-EN.
2. **Couche métier** : distinguer clairement "formation" vs "métier"
   dans les réponses (même le M1 Théo a mentionné que l'outil mélange les
   deux). Implique un tool `get_metier_fiche(rome_code)` explicite,
   au-delà du libellé ROME brut actuel.
3. **Pré-filtrage public par situation** : un lycéen terminale, un étudiant
   en réorientation, un parent et un Psy-EN n'ont pas les mêmes besoins.
   Le `user_level classifier` (Tier 2.2) existe mais n'est pas encore
   branché sur le composer pour moduler le registre et le niveau de détail.

**Decision** : **reporter ces 3 enrichissements post-V4** sans préciser
ici le séquençage ni les dates — ce sont des éléments orthogonaux au
safety factual que V1-V4 ont livré. Matteo priorise le "no-harm pour
mineur en autonomie" avant l'ergonomie.

Note V4.1 : un brouillon minimal de "phase projet" a été livré dans V4
(module `src/validator/phase_projet.py` — appended sur questions à enjeu
fort), mais reste un stub vs la vraie couche projet déontologique Psy-EN
décrite ici. Les deux autres enrichissements (couche métier, pré-filtrage
public) sont **intacts, non implémentés**.

**Rationale** :

- Ces 3 enrichissements sont de l'**UX/agentic**, pas du safety factual.
- Les 4 erreurs disqualifiantes (HEC AST, redoublement PASS, séries bac
  obsolètes, kiné IFMK) ont été traitées en priorité P0 via les règles
  V2.1-V2.4. C'est le scope livré sur main.
- Ces 3 enrichissements s'intégreraient naturellement dans une
  architecture agentique (ProfileClarifier → phase projet, Composer →
  couche métier, DecisionHelper → pré-filtrage public), non-livrée
  à la date de ce sprint.

**Alternatives rejetées** :

- Implémenter ces 3 enrichissements en V2 : scope explose, V2 devait
  rester focus safety factual.
- Ne pas les tracer du tout : risque de les oublier. D'où cet ADR.

**Références** :

- Panel ground truth v3 du 2026-04-22 (5 profils × 3 Q hard)
- Ordre Jarvis 2026-04-22-1230 (V2 dispatch)
- STRATEGIE_VISION §5 Axe 2 (agentic)

---

## ADR-037 — Rééquilibrage T2.4 « Attention aux pièges » — hypothèse réfutée (2026-04-22)

**Context** : après V4 γ Modify, Matteo a identifié que le system prompt
imposait systématiquement 3 pièges (T2.4 : "section concise « ⚠ Attention
aux pièges » (maximum 3 puces) qui pointe un biais marketing + un piège
géographique + un faux-ami"). Cette injonction produisait du bruit visuel
et contribuait au verdict Claude Sonnet persona 2/5 médiane sur les 3 Q
hard Gate J+6 (feedback Léo « l'outil me parle comme à un enfant »).

**Decision** : rééquilibrer conservativement T2.4 :
- « section systématique 3 puces » → « 1 piège critique max en 1 phrase,
  2 si vraiment nécessaire, pas de section artificielle »
- Interdit sur question conceptuelle pure (ex : « c'est quoi une licence ? »)
- Ne PAS imposer les 3 catégories (marketing + géo + faux-ami) — elles
  n'existent pas toujours
- Les règles Tier 0 (anti-discrimination, 6 anti-hallucinations listées)
  restent inchangées — elles filtrent la sortie via le Validator, pas
  besoin de les répéter en warnings prompt

Fichiers modifiés : `src/prompt/system.py` T2.4 + T2.9 + exemple dans prompt.

**Résultat empirique — hypothèse RÉFUTÉE** :

| Métrique | V4 original | V4.1 rebalance | Δ |
|---|---|---|---|
| Claude persona médiane globale | 2/5 | **2/5** | stable |
| Moyenne globale | 2.40/5 | **2.00/5** | **−0.40 régression** |
| Q1 HEC médiane | 4 | **2** | **−2** |
| Q6 Perpignan médiane | 2 | 2 | stable |
| Q8 PASS médiane | 2 | 2 | stable |

Tests : **177/177 verts** Tier 0 + Tier 2 + validator + pipeline. Zéro
régression safety.

**Cause racine identifiée (via commentaires Psy-EN verbatim)** :

Le rééquilibrage prompt ne suffit PAS car le plateau 2/5 a des causes
plus profondes :

1. **Bug γ Modify V4** : multiple violations de la même règle produisent
   N remplacements → répétitions textuelles dans la sortie (« HEC Paris
   passe par AST » collé 3 fois dans Q1). Fix prévu V4.2 : dédupliquer
   sur `replacement_text`.
2. **Règles V2 variance-dépendantes** : la règle V2.4 kiné IFMK match sur
   certaines regen Mistral Medium mais pas d'autres — même question, deux
   runs différents → deux outputs différents → catch aléatoire.
3. **Phase projet ne se déclenche pas** malgré triggers présents — bug
   possible dans `already_has_project_prompts` (false positive).
4. **PresenceRule flag mais Mistral n'injecte pas** en regen — migration
   Presence → Modify (injection automatique phrases obligatoires)
   devient P0 V5.

**Conclusion factuelle** :

Le prompt verbeux était un facteur UX aggravant **mais pas la cause
première** du plateau 2/5 Claude persona sur les 3 Q hard. La vraie
cause est la **qualité de génération** Mistral Medium qui produit
toujours le même type d'erreurs factuelles, que les règles/presence/
prompt compensent partiellement mais ne soignent pas à la source.

**Alternatives rejetées** :
- Ne pas toucher au prompt : garderait le bruit visuel confirmé par Léo
- Ajuster plus agressivement (ex : supprimer Plan A/B/C) : risque de
  casser la structure qui a des gains empiriques (Tier 2 mergé PR #9)

**Références** :
- Ordre Jarvis 2026-04-22-1834 (prompt rebalance)
- Ground truth v3 + v4 + v4.1 Claude Sonnet persona (15 evals chaque)
- Commentaires verbatim Psy-EN dans `results/gate_j6/ground_truth_v4_rebalance_resimule.json`
- Rapport `results/gate_j6/report_v4_prompt_rebalance.md`

---

## ADR-038 — Ingestion ROME 4.0 via API live France Travail (2026-04-23) [DRAFT]

**Statut** : DRAFT — scaffold client livré (`src/collect/rome_api.py`, tests mockés),
en attente credentials Matteo pour activation. Bascule DRAFT → ACCEPTED quand
la première ingestion réelle tourne et enrichit `formations.json`.

**Context** :

`src/collect/rome.py` (D3a, ADR-034) fournit un référentiel ROME 4.0 offline
depuis le zip `data/raw/rome_4_0.zip` (release v460 avril 2025). Il couvre les
libellés, la hiérarchie et les flags transition_eco/num/demo, emploi_cadre,
emploi_reglemente. C'est suffisant pour enrichir les fiches déjà matchées sur
un code ROME hard-codé (`RELEVANT_ROME_CODES` : 9 cyber + 6 data_ia + 10 santé).

**Limites du ZIP offline** :
- Pas de tension marché par métier / région (donnée critique pour accompagnement
  insertion pro phase c du scope élargi 17-25 ans — cf ordre Jarvis 2026-04-23-0843).
- Pas de salaire médian actualisé post-release.
- Pas de matching full-text automatisé — les 25 codes sont hard-codés, ne
  scalent pas au scope élargi (master / alternance / autres domaines).
- Pas de rafraîchissement mensuel sans re-téléchargement manuel du zip.

**Decision** :

Ajouter un **client API live** `src/collect/rome_api.py` complémentaire
(pas substitut) au ZIP offline, basé sur l'OAuth2 client_credentials flow
France Travail et exposant 3 endpoints initiaux :

1. `get_metier(code_rome)` — libellé + granularité officielle à jour.
2. `search_metiers(query)` — matching full-text sur libellés (remplace à terme
   la table hard-codée `RELEVANT_ROME_CODES` quand on étend le scope).
3. `get_fiche_metier(code_rome)` — fiche détaillée (activités, compétences,
   salaires, tension marché) — **c'est là que l'API live bat le ZIP**.

Scopes cochés sur l'app France Travail : `api_rome-metiersv1` +
`api_rome-fiches-metiersv1` + `nomenclatureRome`.

Rate limit : 180 RPM par défaut (cap France Travail ~300 RPM = 5 RPS, marge 40%).
Retry exponentiel sur 429/5xx/timeouts, token auto-refresh 20 min.

Sans credentials `FT_CLIENT_ID`/`FT_CLIENT_SECRET` dans `.env`, toute méthode
lève `RomeApiCredentialsMissing` avec un message pointant `docs/TODO_MATTEO_APIS.md`.
Pas de mode dégradé silencieux — explicit is better than implicit.

**Rationale** :

- **L'argument « données fraîches » de STRATEGIE §1.3 + §3 Cause #4 s'active
  structurellement ici**. Sans API live, on reste figés sur le snapshot
  d'avril 2025 et on perd l'avantage différenciateur vs LLMs natifs (cutoff
  janvier 2026).
- **Extension scope 17-25 ans 3 phases** (ordre Jarvis 2026-04-23-0843)
  demande de matcher automatiquement débouchés vs métiers pour les formations
  master / réorientation / alternance à venir en S+1 (D8 MonMaster + D9 RNCP).
  `search_metiers` API > table hard-codée.
- **Cohabitation claire avec `rome.py`** : le ZIP offline reste utile pour
  les enrichissements statiques (hiérarchie, flags, fallback si API down).
  `rome_api.py` = source de vérité pour données dynamiques (tension, salaires).
- **Pattern OAuth2 robuste** : token auto-refresh, RateLimiter réutilisé
  (`src/eval/rate_limit.py`), retry aligné `src/eval/runner.py:_call_with_retry`.

**Alternatives rejetées** :

1. **Re-télécharger le ZIP tous les mois manuellement** : pas de tension/salaires
   dans le zip, et le cron D7 (ADR-035) gère déjà Parcoursup/ONISEP/InserSup —
   pas de raison d'exclure ROME live.
2. **Utiliser uniquement l'API (remplacer `rome.py`)** : perd la résilience
   offline + la mémoïsation `lru_cache` qui sert 30+ tests sans latence réseau.
3. **Scraper les fiches ROME sur travail-emploi.gouv.fr** : violation ToS +
   fragile + l'API officielle existe et est gratuite.
4. **Attendre S+2 pour ingérer ROME live** : bloque matching débouchés pour
   scope élargi qui démarre S+1 (D8 + D9).

**Effets attendus** (à mesurer quand credentials arrivent) :

- Couverture débouchés ROME par fiche : `RELEVANT_ROME_CODES` = 25 codes
  hard-codés → matching API pour 100+ formations du scope élargi.
- Ajout champs `salaire_median`, `tension_marche`, `competences_clefs` sur
  les fiches enrichies (non-présents dans le zip offline).
- Métrique STRATEGIE §5 Axe 1 : passer de 0% à 80%+ débouchés discriminants.
- Zéro régression sur tests existants `tests/test_rome.py` (15 tests ZIP) —
  `rome_api.py` est un module séparé, `rome.py` n'est pas touché.

**Références** :

- STRATEGIE_VISION_2026-04-16.md §5 Axe 1 D3 (ROME 4.0 France Travail API)
- Ordre Jarvis 2026-04-23-0843 amendement (scope élargi 17-25 ans 3 phases)
- ADR-034 (D3a ROME 4.0 ZIP offline — complémentaire)
- ADR-035 (cron refresh D7 — futur intégration D7 → rome_api pour rafraîchissement)
- docs/TODO_MATTEO_APIS.md (signup francetravail.io)

**Suite (post-credentials)** :

1. Activation client + première ingestion sur 10 fiches cyber (dev sanity).
2. Benchmark retrieval dev set 32q : comparer `our_rag_v1` vs `our_rag_v2_data_rome_live`.
3. Extension scope S+1 D8 + D9 : matching master + alternance via `search_metiers`.
4. Intégration cron D7 mensuel : refresh `data/processed/rome_live_cache.json`.
5. Passage ADR-038 DRAFT → ACCEPTED avec métriques mesurées.

---

## ADR-039 — Scope élargi 17-25 ans 3 phases égales (2026-04-23) [DRAFT]

**Statut** : DRAFT — cadrage stratégique acté 2026-04-23 par Matteo via
ordre Jarvis 2026-04-23-0843 + amendement. Bascule DRAFT → ACCEPTED après
première ingestion corpus élargi (D8 + D9) et validation métrique de
répartition 3 phases.

**Context** :

Jusqu'à Run F+G (2026-04-16), OrientIA était optimisé pour un **profil
étudiant implicite** : lycéen terminale ou post-bac jeune, phase (a)
"choix d'étude initial", secteurs cyber/data_ia/santé. Le corpus (443
fiches, 343 Parcoursup + 102 ONISEP) reflète ce biais historique.

**Dérive identifiée par Matteo** (2026-04-23 06:43Z) : « tu as tendance
à sur-pondérer le segment mineur [= lycéens post-Parcoursup] ». Constat
empirique croisé avec :
- Table `_DOMAIN_CODES` dans `src/collect/rome.py` = cyber + data_ia + santé uniquement
- 71 fiches bac+5 sur 443 total = **16% master** vs 62% bac+2 (274)
- Zéro fiche alternance native, zéro fiche RNCP réorientation
- `SYSTEM_PROMPT` v3.2 mentionne "lycéens" 12+ fois, "master" 2 fois, "réorientation" 0
- Exemples STRATEGIE_VISION §5 Axe 2 citent systématiquement "bac techno mention bien"

**Decision** :

Le périmètre OrientIA couvre désormais les 3 phases en **parts égales
(33/33/34)** pour la cible 17-25 ans :

1. **Phase (a) Choix d'étude initial** — lycéens terminale, Parcoursup,
   post-bac immédiat (BUT/BTS/Licence/CPGE/Prépa).
2. **Phase (b) Réorientation** — étudiants L1/L2 en décrochage, passerelles
   intra/inter universités, alternance (bascule salarié), bascule filière.
3. **Phase (c) Master + insertion pro** — M1/M2, spécialisation, premier
   emploi, reconversion jeune pro (<25 ans).

Cette répartition 33/33/34 doit être mesurable et imposée à chaque couche
du système :

| Couche | Métrique cible |
|---|---|
| Corpus `data/processed/formations.json` | ≥25% fiches par phase après S+1 D8+D9 |
| Dataset RAFT fine-tuning | 33/33/34 strict par phase (S+3 R1-R3) |
| Benchmark B1 étendu (100q) | 33 phase a + 33 phase b + 34 phase c (S+1-S+2) |
| ProfileClarifier agent | 1ère sortie = phase détectée + score confiance (S+2 A2) |
| UX home page | 3 CTA équi-poids distincts (S+4) |
| Exemples docs/démo | rotation équilibrée (éditorial S+4) |

**Nouvelles sources data ajoutées** (ordre Jarvis 0843, 8-9 sources
confirmées) :
- **D8 MonMaster** (`data.gouv.fr/fr/datasets/monmaster-...`) — couvre phase (c)
- **D8bis Data ESR** (`data.esr.gouv.fr`) — enquêtes insertion MESR
- **D9 France Compétences RNCP** (`francecompetences.fr`) — phases (b) + (c)
- **D10 La Bonne Alternance** (`api.labonnealternance.apprentissage.beta.gouv.fr`) — phase (b)
- **D11 Céreq Enquêtes Génération** (RAG pack séparé) — phase (c)
- **D12 France Travail BMO** (Besoins en Main d'Œuvre, `francetravail.io`) — phase (c)

**Rationale** :

- **Deadline INRIA 25/05/2026 (J-32 au 23/04)** : le jury va tester
  directement l'IA. Un système qui échoue sur 66% des profils (phases b
  et c) = démo catastrophique, même si phase (a) est parfaite.
- **Tuteur INRIA** a explicitement demandé (via Matteo) : pouvoir
  accompagner un étudiant en réorientation ou un M1 en fin de cursus,
  pas uniquement un lycéen. Le cahier des charges format "Le Mentor"
  (empathie objective + transparence statut IA + mode Boussole) vaut
  pour les 3 phases, pas juste les mineurs.
- **Anti-drift self-flag obligatoire** : Matteo a noté que Claudette /
  prompts / examples ont un biais documenté pro-mineur. La métrique
  33/33/34 à chaque couche est la **seule** garantie programmatique
  contre la régression.
- **Cohabitation avec STRATEGIE_VISION_2026-04-16** : cet ADR étend et
  renforce STRATEGIE §5 Axe 1 (Data) en précisant le périmètre scope.
  STRATEGIE §5 reste la vision, §6 Axe 4 UX doit refléter les 3 CTA.
  Pas de conflit de décision, seulement un raffinement de scope.

**Alternatives rejetées** :

1. **Rester sur scope cyber/data_ia/santé post-bac** : garde un système
   simple mais échoue sur démo INRIA pour 66% des profils = inacceptable
   vu la deadline.
2. **Scope 3 phases mais ratio libre (pas de contrainte 33/33/34)** :
   le biais historique re-prend le dessus silencieusement (chemin de
   moindre résistance = lycéens post-bac déjà codés).
3. **Pondération par popularité réelle** (ex : 50% post-bac, 30% master,
   20% réorientation reflétant volume étudiant FR) : ignore la demande
   explicite Matteo. À reconsidérer **après** démo INRIA si usage réel
   oblige à re-pondérer.
4. **Reporter la décision post-INRIA** : trop tard, le plan 4 sem S+1-S+4
   doit être structuré autour de ce scope dès maintenant.

**Effets attendus et métriques** :

- Corpus fin S+1 : 33% post-bac + 33% master + 34% alternance/réorientation
  (cible ±5 pts par phase).
- Benchmark 100q reshuffle S+2 : 33/33/34 par phase, hold-out 68q recréé propre.
- Honesty score Haiku `our_rag_v4_raft` sur phases (b) et (c) : ≥ 0.70
  (baseline à mesurer post-ingestion).
- Démo INRIA 25/05 : scénario scripté 6 questions (2 par phase) validé par
  Matteo en pré-démo.

**Risques et mitigations** :

| Risque | Probabilité | Mitigation |
|---|---|---|
| Ingestion D8 MonMaster bloquée (API fermée ou schéma non-match) | Moyenne | POC feasibility 23/04 (item 3 plan jour) avant commitment S+1 |
| Dataset RAFT 33/33/34 difficile à générer pour phase (c) insertion pro | Moyenne | Options α Opus + γ forums + β synthétique combinées (STRATEGIE §5 Axe 3) |
| Test set 68q existant (cyber/data) devient obsolète pour benchmark élargi | Haute | Recréer hold-out 68q propre sur nouveau scope (B1 étendu S+2) |
| Claudette continue à biaiser vers mineur malgré la règle | Moyenne | Self-check anti-drift dans chaque livraison + vigilance explicite Matteo |

**Références** :

- Ordre Jarvis 2026-04-23-0843 + amendement (source of truth scope élargi)
- STRATEGIE_VISION_2026-04-16.md §5 Axe 1-2-4 (architecture V2 — étendue par cet ADR)
- Cahier des charges format "Le Mentor" (Snack/Bite/Meal + Règle 3 + Boussole + mémoire session + CTA)
- Memory Claudette `project_orientia_scope_v2.md` (anchor sessions futures)
- ADR-038 (rome_api.py — complément scope élargi via `search_metiers`)

**Suite (S+1 → S+4)** :

1. Item 3 plan jour 23/04 : POC ingestion MonMaster + RNCP (feasibility avant commitment).
2. S+1 D8 + D9 + D10 : ingestion master + alternance + RNCP (cible +150 fiches hors cyber/data/santé).
3. S+2 B1 : recréation benchmark 100q (33/33/34) + hold-out 68q.
4. S+2 A2 : ProfileClarifier détecte phase.
5. S+4 U-home : 3 CTA équi-poids sur page d'accueil site.
6. Passage ADR-039 DRAFT → ACCEPTED après métrique corpus 25/25/25 atteinte.

---

## ADR-040 — Dimension débouchés professionnels détaillés (2026-04-23) [DRAFT]

**Statut** : DRAFT — dimension ajoutée en cours de session 2026-04-23 par
Matteo (via Jarvis, 10h31 CEST). Bascule ACCEPTED après définition des
sources + plan d'ingestion opérationnel S+2.

**Context** :

ADR-039 scope élargi 17-25 ans 3 phases identifie les sources data pour
couvrir les formations (MonMaster, RNCP, Bonne Alternance, Parcoursup,
ONISEP). Mais la question "quels débouchés pour un lycéen/étudiant/jeune
diplômé" demande bien plus que le nom d'une fiche formation :

> « Il ne faut pas oublier la partie professionnel avec débouché, salaire
> entrée 5ans 10ans etc… + description des postes, journée types etc. »
> — Matteo, 2026-04-23 10h31

Sources déjà scopées dans ADR-039 couvrent **partiellement** :
- MESR insertion (Data ESR) : taux d'insertion + % CDI + salaire médian
  d'embauche, mais pas 5 ans / 10 ans.
- France Travail BMO (via `rome_api.py` scaffold) : besoins en main
  d'œuvre par secteur, mais pas trajectoires individuelles.
- Céreq Enquêtes Génération : insertion 3 + 6 ans, granularité grosse (par
  niveau × secteur), pas de salaire par métier.

**Trous identifiés** :
1. Pas de **salaire par métier après 5 ans / 10 ans d'expérience**.
2. Pas de **description journée type** d'un poste (ce qu'on fait concrètement).
3. Pas de **grille trajectoire carrière** (junior → confirmé → senior →
   management / expert / reconversion).

**Decision** :

Ajouter une **5e catégorie de sources data** (complémentaire aux 4 axes de
STRATEGIE_VISION §5) orientée "métiers & carrière" :

| Source | Couverture | Coût | Priorité |
|---|---|---|---|
| **APEC** (`apec.fr/observatoire`) | Cadres : salaires junior / 3 ans / 5 ans / 10 ans par métier, secteur, région | Dataset téléchargeable gratuit + rapports annuels PDF | **P0 S+2** |
| **INSEE** (`insee.fr/fr/statistiques`) | Statistiques emploi par métier PCS / ROME (effectifs, salaires moyens par tranche d'âge), Pyramide des âges par secteur | Open data Etalab 2.0, CSV bulk + API | **P0 S+2** |
| **ONISEP fiches métiers** (`onisep.fr/ressources/univers-metier`) | Description métier + journée type + qualités attendues + études recommandées + salaires début / progression | API ONISEP dataset `5fa591127f502` (métiers, distinct du dataset formations) | **P0 S+2** |
| France Travail BMO (déjà scopé D3) | Tension marché + projets recrutement par métier × région | Via ROME API (rome_api.py) | P1 S+2 |
| LinkedIn Economic Graph (`economicgraph.linkedin.com`) | Trajectoires carrière réelles (anonymes), skills qui progressent | API payante, restrictions légales | **SKIP** |
| Glassdoor / Indeed | Salaires + journées types crowdsourcés | Scraping anti-ToS | **SKIP** (ToS interdisent scraping massif) |

**Rationale** :

- **L'argument "Mentor" du cahier des charges format** (ordre Jarvis
  2026-04-23-0843 §Cahier des charges) demande de traduire les fiches
  techniques en "vraie vie" : % TP vs amphi, type de stages, journées
  types. Sans sources "métiers & carrière", OrientIA reste au niveau
  "ChatGPT peut aussi dire ça" sur les aspects carrière.
- **APEC spécifiquement** est la source de vérité française pour salaires
  cadres par ancienneté, non accessible aux LLM généralistes (rapports
  PDF non-ingérés dans les corpus training).
- **ONISEP fiches métiers** a déjà été cité dans STRATEGIE §5 Axe 1 D2
  mais comme "formations" — la partie "métiers" de leur catalogue est
  distincte et riche en descriptions.
- **INSEE** apporte une vision macro-statistique nationale (combien de
  data engineers en France à 30 ans ? Quel salaire médian après 5 ans ?)
  qui ancre les conseils dans des chiffres vérifiables.

**Alternatives rejetées** :

1. **Se contenter des sources scopées ADR-039** (MESR + Céreq + BMO) :
   couvre insertion à 3-6 ans mais pas trajectoires 5/10 ans + pas de
   descriptions journées types. Gap UX Mentor majeur.
2. **Scraping Glassdoor / Indeed** : violation ToS, risque blocage IP +
   légal. Données crowdsourcées ≠ vérifiées de toute façon.
3. **Partenariat APEC / LinkedIn direct** : hors scope projet étudiant
   (INRIA AI Grand Challenge), pas de temps pour négocier.
4. **Ignorer la dimension trajectoire carrière** : inacceptable vu la
   demande explicite Matteo et le positionnement "bat ChatGPT sur
   l'accompagnement orientation".

**Plan d'ingestion S+2 (référence, pas engagement hard)** :

| Sprint | Action | Effort estimé | Coût |
|---|---|---|---|
| **S+2 début** | D12 ONISEP métiers API | 4-6h | $0 |
| **S+2 mid** | D13 APEC rapports & datasets | 6-8h (PDF parsing possible) | $0 |
| **S+2 fin** | D14 INSEE statistiques emploi | 4-6h | $0 |
| S+3 | Enrichissement fiches OrientIA : chaque fiche pointe vers 2-3 métiers cibles avec trajectoire + salaire + journée type | 6-8h | $0 |

**Métriques cibles** :
- Chaque fiche formation enrichie avec ≥2 métiers cibles ROME + description
  courte + salaire début / 5 ans / 10 ans
- Retrieval "journée type data scientist" retourne contenu ONISEP riche
  (pas juste "voir fiche métier")
- Benchmark ajout catégorie "trajectoire carrière" (5-10 questions type
  "ce métier à 30 ans ça donne quoi ?")

**Références** :

- Ordre Jarvis 2026-04-23-1031 (directive Matteo section 2C "débouchés
  professionnels détaillés")
- STRATEGIE_VISION §5 Axe 1 (architecture data foundation — cet ADR étend)
- ADR-039 (scope élargi — cet ADR complète la dimension carrière)
- Cahier des charges format Mentor (ordre 0843 §Richesse / Contextualisation
  → "Vraie vie" : traduire fiches techniques)

**Suite** :

1. S+2 début : prioriser D12 ONISEP métiers (API déjà connue, aligne avec
   code `src/collect/onisep.py` existant).
2. Découpler APEC en download rapports annuels (2026 déjà publié en
   janvier) → parsing PDF (attendu modérément complexe — tables structurées).
3. INSEE via API + CSV bulk (pattern identique à MonMaster Opendatasoft).
4. Bascule ADR-040 DRAFT → ACCEPTED après première ingestion ONISEP
   métiers opérationnelle.

---

## ADR-041 — Extension Parcoursup tous secteurs + 5 champs riches (2026-04-23) [DRAFT]

**Statut** : DRAFT — scope ingestion implémenté + champs P0 ajoutés côté code.
Bascule ACCEPTED après validation qualité audit data + intégration dans merge.py.

**Context** :

ADR-039 formalise le scope élargi 17-25 ans 3 phases égales. Le corpus
Parcoursup initial est focalisé cyber/data_ia/santé (1 424 fiches, 10% du
dataset Parcoursup 14 252 formations). Pour respecter la cible 33/33/34 par
phase :
- Phase (a) post-bac initial est actuellement sous-représentée (~2% du total
  corpus OrientIA contre 33% cible).
- Il faut étendre Parcoursup à tous les secteurs (hors cyber/data/santé déjà
  couverts) pour équilibrer.

Matteo (via Jarvis, 2026-04-23 11:39) : « si on étend le modèle à tous les
secteurs il faut aussi voir pour les données Parcoursup pour récupérer données
manquantes + champs intéressants non utilisés si nécessaire. »

Deux axes identifiés par gap analysis sub-agent :

### Axe (a) — Étendre DOMAIN_KEYWORDS à tous secteurs
Option 1 (mots-clés) : plus rapide, +77% corpus. Option 2 (`fili` mapping) :
plus robuste mais effort 4-6h supplémentaire. Option 3 (ROME API) : S+3.

### Axe (b) — Activer champs Parcoursup non-utilisés
Sub-agent a identifié 88/118 colonnes non-utilisées. Top 10 P0 :
`prop_tot`, `prop_tot_bg/bt/bp`, `acc_pp/acc_pc`, `pct_acc_debutpp`,
`voe_tot_f`, `acc_neobac`, `fili`, `lib_grp1..3`, `select_form`,
`g_olocalisation_des_formations`.

**Decision** :

### (a) Axe scope secteurs : **Option 1 en court terme**

Étendre `DOMAIN_KEYWORDS` avec 12 nouveaux domaines :
`droit`, `eco_gestion`, `sciences_humaines`, `langues`, `lettres_arts`,
`sport`, `sciences_fondamentales`, `ingenierie_industrielle`,
`communication`, `education`, `agriculture`, `tourisme_hotellerie`.

**Total : 15 domaines** dont les 3 legacy préservés pour backward-compat.

Mécanisme :
- `LEGACY_DOMAINS = ["cyber", "data_ia", "sante"]` (défaut, préserve tests existants)
- `EXTENDED_DOMAINS = list(DOMAIN_KEYWORDS.keys())` (15 domaines)
- `collect_parcoursup_fiches(path, domains=None)` : `None` → legacy ; passer
  `EXTENDED_DOMAINS` pour scope élargi.
- Nouvel alias `collect_parcoursup_all_sectors(path)` pour lisibilité.

**Résultat mesuré** : ingestion live sur `data/raw/parcoursup_2025.csv` =
**9 212 fiches** (vs 1 324 legacy × 6.96). Distribution :
- `eco_gestion` 2 464 (27%)
- `ingenierie_industrielle` 1 085 (12%)
- `sante` 981 (11%)
- `sciences_fondamentales` 918 (10%)
- `langues` 888 (10%)
- `lettres_arts` 588 (6%)
- `sciences_humaines` 579 (6%)
- `droit` 496 (5%)
- `cyber` 304 (3%)
- autres (9 domaines) : 1 909 (21%)

Gap : dataset Parcoursup a 14 252 formations au total. 9 212/14 252 = **65% de
couverture** avec mots-clés. Reste 35% non catégorisés (noms génériques
types "BTS", "Licence professionnelle X" qui ne matchent aucun keyword).

**Option 2 (`fili` mapping)** reportée S+2 — gain couverture +25-30% (~13 k
fiches = 92%), effort 4-6h, moins urgent que D12/D14 en cours.

### (b) Axe champs : 5 champs P0 ajoutés

Ajout dans `extract_fiche()` :
- `propositions_totales` (colonne `prop_tot`) — volume propositions envoyées,
  mesure de convertibilité voeux → admission (complément `taux_acces`).
- `pct_acceptes_debut_pp` (`pct_acc_debutpp`) — sélectivité timing (formation
  "prise d'assaut" vs places dispo tard).
- `fili_code` (`fili`) + `fili_groupe` (`lib_grp1`) — classification
  structurée Parcoursup (clé pour désambiguïsation vs mots-clés).
- `selectivite_code` (`select_form`) — catégorie sélectivité officielle
  Parcoursup (formation sélective vs à capacité limitée).

Champs **reportés S+2** (effort marginal, pas bloquant) :
- `prop_tot_bg/bt/bp` — propositions par type de bac (granularité mixité bac)
- `acc_pp/acc_pc` — séparation phase principale vs complémentaire (timing)
- `voe_tot_f` — voeux féminins absolus (ratio candidature vs admission)
- `acc_neobac` count — composition admis par profil (contextuelle)
- `g_olocalisation_des_formations` — coordonnées GPS (futur comparateur géo)
- `composante_id_paysage` + `etablissement_id_paysage` — jointure données ESR

**Rationale** :

- **Déblocage phase (a) ADR-039** : passer de 1 324 → 9 212 fiches rééquilibre
  massivement la répartition par phase. Projection post-ingestion (cumul tous
  datasets) :
  - Phase (a) Parcoursup initial : 9 212 + 6 590 RNCP (initial) = ~15 800 (45%)
  - Phase (c) MonMaster master : 16 257 (46%)
  - Phase (b) réorientation (RNCP master + future LBA) : ~3 000 (~9%)
  - → cible 33/33/34 enfin atteignable après ajout LBA + rééquilibrage.
- **Champs P0 ajoutés couvrent les gaps RAG les plus critiques** :
  `prop_tot` + `pct_acc_debutpp` = signal "convertibilité" réalisme. `fili`
  = classification officielle (vs keyword fragile).
- **Backward-compat préservée** : `collect_parcoursup_fiches()` sans argument
  garde son comportement (3 domaines legacy). Aucun test existant cassé.

**Alternatives rejetées** :

1. **Ne pas étendre scope secteurs** : phase (a) reste à 2%, ADR-039 non tenu.
2. **Attendre S+2 pour Option 2 `fili`** pure : bloque bench S+1 sur scope
   trop restrictif. Option 1 débloque maintenant, Option 2 raffine plus tard.
3. **Ingérer les 14 252 formations sans filtrage** : perd la classification
   domaine (critique pour RAG retrieval qualifié). Rejet.
4. **Ajouter les 10 champs P0+P1 d'un coup** : scope explose + risque
   régression ingestion. Les 5 P0 ajoutés couvrent 80% de la valeur.

**Effets attendus + métriques** :

- **Corpus Parcoursup** : 1 324 → **9 212 fiches** (×6.96) mesuré.
- **Corpus OrientIA total projeté** : 23 290 + 7 888 = **~31 178 fiches**
  post-ingestion.
- **Couverture champs Parcoursup** : 30/118 (25%) → **35/118 (30%)**.
- **Distribution phase (a)** : 2% → estimé 45% (projection).
- **Tests** : 17 nouveaux tests Parcoursup (9 legacy + 8 ADR-041), 530 → 556
  tests verts.

**Risques + mitigations** :

| Risque | Probabilité | Mitigation |
|---|---|---|
| Keywords nouveaux secteurs faux positifs | Moyenne | Audit qualité (Phase 5) + re-benchmark S+2 |
| Volume 9k fiches sature FAISS (latence) | Moyenne | Sharding par phase (cf ADR-039) en S+2 |
| Nouveaux champs mal alignés entre années Parcoursup | Faible | Test d'intégrité `tests/test_data_integrity.py` détecte le drift |
| Conflit avec Option 2 `fili` future | Faible | ADR-041 prévoit bascule (Option 1 remplaçable sans breaking change) |

**Références** :

- Ordre Jarvis 2026-04-23-1139 directive extension Parcoursup (axes a+b)
- Sub-agent gap analysis Parcoursup OpenData (feasibility Phase 1)
- ADR-039 scope élargi 17-25 ans 3 phases égales
- STRATEGIE_VISION §2.3 "corpus 17% exploité" + §5 Axe 1

**Suite (S+1 → S+2)** :

1. Audit qualité (Phase 5 S+1) : vérifier qualité 9 212 fiches (pas de faux
   positifs massifs sur les nouveaux domaines, pas de corruption).
2. Intégration dans `merge.py` via `collect_parcoursup_all_sectors` — post-audit.
3. S+2 : basculer sur Option 2 `fili` mapping pour atteindre 13k+ fiches.
4. S+2 : ajouter champs P1 (prop_tot_bg/bt/bp, acc_pp/pc, etc.) selon gains
   mesurés au benchmark.
5. S+3 : Option 3 ROME API pour matching débouchés par secteur.
6. Bascule ADR-041 DRAFT → ACCEPTED après validation audit + première
   benchmark sur corpus étendu.

---

## ADR-042 — 3 APIs France Travail complémentaires (Anotéa + Marché du travail + Accès à l'emploi) (2026-04-23) [DRAFT]

**Statut** : DRAFT — analyse terminée, priorisation P1 établie (S+2). Bascule
ACCEPTED par API individuelle après première ingestion opérationnelle.

**Context** :

Les credentials FT reçus 2026-04-23 12:12 activent **7 APIs** :
- ROME 4.0 Métiers / Fiches / Compétences / Contextes (1 RPS × 4) — **utilisées**
- **Anotéa v1** (8 RPS) — NON utilisée
- **Marché du travail v1** (10 RPS) — NON utilisée
- **Accès à l'emploi demandeurs d'emploi v1** (10 RPS) — NON utilisée

Matteo (via Jarvis 2026-04-23 12:22) demande : *"Sur les 7 APIs FT, on les utilise toutes ?"*

3 sub-agents Explore dispatchés en parallèle. Synthèse :

### Anotéa v1 — Avis étudiants post-formation

- **URL** : `https://anotea.francetravail.fr/api/v1/` — auth **HMAC-SHA256** custom
  (pas OAuth2), module dédié requis
- **Volume** : ~200k avis modérés, ~10k organismes, ~5% formations FR couvertes
  (seuil publication = 5 avis min)
- **Schéma clé** : `numero` action, `organisme_formateur.siret`, `formacodes`,
  `certifications` (RNCP), `notes.global + criteres`, `avis.texte` (modéré),
  `lieu.code_postal`
- **Join OrientIA** : SIRET + RNCP → 40-60% couverture estimée (Anotéa cible
  formations FT/CPF, pas BTS/BUT publics systématiques)
- **Utilité** : (a) faible / (b) **forte** (cœur = alternance, VAE, formation
  continue, demandeurs emploi) / (c) moyenne
- **Effort** : 20-25h

### Marché du travail v1 — Tension offres/demandes

- **URL** : `https://api.francetravail.io/partenaire/marche-travail/v1/` — OAuth2
  mêmes credentials (scope `api_marche-travailv1` à activer côté app FT)
- **Volume** : 1 584 ROME × géo (région/dept/bassin emploi) × trimestriel,
  12 mois glissants, rate limit 10 RPS
- **Schéma** : offres_actives, demandeurs, embauches, **tension_ratio** (Dares),
  difficultes_recrutement. **Pas de salaires** (DARES séparé).
- **Redondance** : complémentaire BMO (annuel/intentions) / INSEE (PCS national) /
  Céreq (cohorte 3 ans)
- **Utilité** : (a) afficher tension ROME / (b) scorer formations /
  (c) **critique** "où exercer ce métier"
- **Effort** : 7-10 jours (1-2 sprints)

### Accès à l'emploi demandeurs v1 — Taux retour emploi

- **URL** : `https://api.francetravail.io/partenaire/acces-emploi/v1/` — OAuth2
  (scope `api_acces-a-l-emploi-...` à activer)
- **Volume** : ~1.2M demandeurs/trim, seuils anonymisation (n≥30-50/segment),
  trimestriel, historique multi-années, rate limit 10 RPS
- **Schéma** : taux_acces_emploi_6m (%), code_rome, catégorie (A/B), territoire,
  effectif_base, duree_emploi_accede, type_contrat, âge (16-25 / 25-50 / 50+)
- **Redondance** : complémentaire Céreq (cohorte jeunes diplômés) + MESR (UFR)
- **Utilité** : (a) débouchés régionaux / (b) enrichissement fiches /
  (c) **cible primaire** benchmark insertion jeunes
- **Effort** : 3-4 jours

**Decision** :

Les 3 APIs classées **P1 (haute priorité S+2)** — aucune en P0 immédiat,
aucune SKIP. **Complémentaires entre elles + zéro duplication** avec sources
déjà scopées (ADR-039 / ADR-040).

**Ordonnancement S+2** (plus rentable → moins) :
1. **Marché du travail** (7-10j) — OAuth2 FT déjà en place, match ROME trivial,
   active l'argument "données fraîches" ADR-039, phase (c) majeur
2. **Accès à l'emploi** (3-4j) — même stack OAuth2, taux retour 6m vs Céreq 3 ans
   = complémentaire temporel
3. **Anotéa** (20-25h) — auth HMAC distinct, couverture partielle, à garder
   pour phase (b) RAG Mentor "vraie vie" quand socle stabilisé

**Rationale** :

- Matteo a activé 7 APIs sans coût : autant les exploiter si valeur ajoutée
  positive. L'analyse confirme **non-redondance + forte utilité phase (c)**
  débouchés pro (cahier charges Mentor + ADR-040).
- **Pas P0 aujourd'hui** : (1) socle data actuel massif (38k+ fiches post-S+1),
  (2) priorité immédiate = D6 re-index FAISS + bench S+2 pour mesurer l'existant
  avant d'empiler, (3) les 3 APIs apportent de la **profondeur** (enrichissement
  par fiche), pas de la largeur (pas de nouvelles fiches) — bénéfice mesurable
  au bench uniquement.
- **Ordre stack-efficient** : MT + Accès Emploi = même auth OAuth2 (contexte
  mental unifié), Anotéa séparé.

**Alternatives rejetées** :

1. **Ingérer les 3 en P0 maintenant** : scope explose S+1, risque rate limit
   cross-APIs, pas de time pour bench.
2. **Skip Anotéa définitivement** : valeur "vraie vie" (commentaires modérés)
   unique côté sources FR. Skip = regret long-terme.
3. **Faire MT seulement + skip les 2 autres** : Accès Emploi complète MT sur
   la dimension "après formation" (MT = marché actuel, AE = trajectoire 6m).
4. **Ingérer sans analyse** : risque duplication cachée (ex. BMO vs MT).

**Effets attendus S+2** :

- Enrichissement par fiche : `{tension_marche, taux_retour_emploi, avis_moyens?}`.
- Gain au benchmark sur catégorie "insertion pro" (prompts débouchés × région).
- Argument ADR-039 "données fraîches" enfin branché (MT trimestriel vs INSEE
  annuel).

**Scopes OAuth2 à activer côté app France Travail** (côté Matteo, 2 min) :
- `api_marche-travailv1`
- `api_acces-a-l-emploi-des-demandeurs-d-emploiv1`
- (Anotéa = HMAC, pas un scope OAuth2)

**Références** :

- Ordre Jarvis 2026-04-23-1222 + 1223 directive analyse 3 APIs FT inutilisées
- 3 rapports sub-agents Explore parallèles
- ADR-039 scope élargi / ADR-040 débouchés pro / ADR-041 Parcoursup extended

**Suite (S+2)** :

1. Matteo active scopes MT + Accès Emploi côté dashboard app FT (2 min).
2. `src/collect/ft_marche_travail.py` (7-10j) — pattern OAuth2 `rome_api.py` réutilisé.
3. `src/collect/ft_acces_emploi.py` (3-4j) — même pattern.
4. `src/collect/ft_anotea.py` (20-25h) — HMAC custom, module dédié.
5. `merge.py:attach_market_indicators()` : enrichissement fiche-par-fiche.
6. Bench S+2 pour mesurer gain RAG phase (c).
7. Bascule DRAFT → ACCEPTED par API après ingestion validée.

---

## ADR-043 — Catalogue France Travail exhaustif — gap analysis + 3 APIs P0 additionnelles (2026-04-23) [DRAFT]

**Statut** : DRAFT — analyse exhaustive catalogue ~30 APIs FT vs 8 activées
Matteo. 3 nouvelles APIs P0 recommandées pour activation S+1/S+2. Bascule
ACCEPTED par API individuelle après activation + ingestion.

**Context** :

Après réception credentials FT 2026-04-23 12:12, Matteo a activé
progressivement. État actuel de sa liste d'APIs activées (8 au total, 2026-04-23 15:55) :

1. Anotéa v1 (8 RPS) — avis post-formation
2. **Sortants de formation et accès à l'emploi v1** (10 RPS) — **NOUVELLE** vs liste 12:12
3. Marché du travail v1 (10 RPS)
4. Accès à l'emploi des demandeurs d'emploi v1 (10 RPS)
5-8. ROME 4.0 × 4 (Métiers / Fiches / Compétences / Contextes, 1 RPS chacune)

Matteo demande via Jarvis (15:59) :
> *"Est-ce qu'il en manque ? Lesquelles on ne va pas exploiter ?"*

Sub-agent Explore dispatché pour inventaire catalogue `francetravail.io/data/api/`
(~30 APIs + endpoints FT Connect + Open Formation ecosystem).

### Focus confirmé — Sortants de formation et accès à l'emploi v1

**Hypothèse vérifiée (confirmée par sub-agent)** : **complémentarité claire**
avec "Accès à l'emploi demandeurs d'emploi v1" (déjà analysée ADR-042).

| Critère | Sortants de formation v1 | Accès emploi demandeurs v1 |
|---|---|---|
| Population | Cohorte spécifique post-formation (dernier trimestre) | TOUS demandeurs emploi enregistrés |
| Horizon | 6 mois post-sortie formation | 6 mois post-inscription DE |
| Granularité | ROME × bassin emploi × niveau formation | ROME × bassin × catégorie A/B |
| Usage OrientIA | Phase (c) insertion jeunes diplômés, bridge direct Céreq | Phase (c) benchmark tous profils marché |

**Conclusion** : **les 2 sont à exploiter**, synergie (pas redondance).
"Sortants de formation" = insertion post-formation ciblée, très utile pour
RAG "combien de gens en dev s'insèrent après cette formation ?". À activer
**P0** au même titre que les 2 autres ADR-042 (Marché du travail + Accès emploi).

### Gap analysis — 3 APIs P0 additionnelles recommandées

Parmi ~20 APIs non-activées, 3 sont **P0 S+1-S+2** pour OrientIA :

**1. Open Formation** (api.gouv.fr / francetravail.io)
- Catalogue officiel formations FT + partenaires + RNCP
- **Fit OrientIA** : indispensable phase master, complément natif de notre
  `onisep_formations_extended` (ONISEP) + `parcoursup_extended` (Parcoursup).
  Apporte couverture partenaires FT absente de ces 2 sources.
- **Effort** : léger (catalogue statique + géo), ~1-2j
- **Verdict** : **ACTIVER P0 S+1**

**2. Offres d'emploi France Travail** (10 RPS)
- Annonces temps réel FT + partenaires, ~20k+ offres actives
- **Fit** : phase master (découverte emploi après diplôme), phase c
  (contexte marché concret par ROME × région). Pattern identique à
  `/api/job/v1/search` LBA alternance mais scope emploi classique.
- **Effort** : moyen (20k+ offres, streaming via pagination), ~2-3j
- **Verdict** : **ACTIVER P0 S+1**

**3. ROMEO (IA Compétences)** (francetravail.io/romeo-2)
- API IA qui matche texte libre (ex: "je veux travailler dans la tech")
  → codes ROME pertinents + compétences associées
- **Fit** : transversal critique pour RAG OrientIA. Input utilisateur
  flou → matching métier/formation structuré. Remplace les heuristiques
  keywords `DOMAIN_KEYWORDS` actuels par de la sémantique officielle FT.
- **Effort** : moyen (API IA, intégration RAG), ~2-3j
- **Verdict** : **ACTIVER P1 S+2**

### APIs P1 — nice-to-have S+2

- **Informations emploi dans un territoire** (10 RPS) : population + dynamisme
  IA par bassin emploi. Utile phase master "contexte local", mais couvert
  partiellement par Marché du travail + INSEE. **P1 évaluer S+2**.
- **Événements France Travail** (10 RPS) : forums/salons/speed-dating
  régionaux. Utile engagement direct étudiant, pas critique RAG. **P1 S+2**.

### APIs à SKIP définitivement (raisons documentées)

1. **Statut demandeur emploi** (API Particulier, restreinte) : vérifie
   inscription DE individuelle. OrientIA cible 17-25 ans, pas focus sur
   registration DE. Hors scope.
2. **Liste des paiements (indemnités)** (API Particulier, restreinte) :
   historique allocations DE. **Sensible (financier personnel)**, hors
   scope OrientIA, refus sur data protection.
3. **France Travail Connect (full suite)** : OAuth2 FranceConnect user-profile,
   write-access. Restreint, implique intégration compte utilisateur. **Future
   si MVP OrientIA grandit**, skip pour deadline INRIA.
4. **APIs Formation Partenaires (ICO / AIS / AES)** : restreinte aux
   organismes de formation officiels. Matteo n'est pas organisme, hors scope.
5. **Référentiel agences France Travail** (10 RPS) : adresses / horaires
   agences FT physiques. Nice-to-have uniquement si feature "trouver mon
   agence locale", pas critique RAG OrientIA. **Skip pour INRIA**.

### Reco globale sur les 8 APIs activées par Matteo

| API activée | Verdict OrientIA |
|---|---|
| ROME 4.0 × 4 (Métiers/Fiches/Compétences/Contextes) | ✅ **EXPLOITER** (ingestion live faite 2026-04-23) |
| Anotéa v1 | ⏸️ **SCAFFOLD S+2, ingestion post-INRIA** (auth HMAC custom + couverture 40-60%) |
| Marché du travail v1 | ✅ **EXPLOITER P1 S+2** (ADR-042) |
| Accès à l'emploi demandeurs d'emploi v1 | ✅ **EXPLOITER P1 S+2** (ADR-042) |
| Sortants de formation et accès à l'emploi v1 | ✅ **EXPLOITER P1 S+2** (NOUVELLE, complète Accès emploi) |

**Aucune API activée ne sera skippée.** Les 8 sont utiles, la priorité
change selon phase (ROME 4.0 exploitée immédiatement, 3 APIs stats P1 S+2,
Anotéa post-INRIA).

**Decision** :

1. **Confirmer les 5 APIs non-activées mais utiles** (Open Formation +
   Offres d'emploi + ROMEO + Informations territoire + Événements) en
   **P0 (3 premières) / P1 (2 suivantes)**. Matteo activera selon priorité.
2. **Skipper définitivement** les 5 APIs hors scope (Statut DE, Paiements,
   FT Connect full, APIs orga formation, Référentiel agences).
3. **Sortants de formation v1** (nouvelle) : exploiter au même titre que
   Marché du travail + Accès emploi (P1 S+2), complémentaire direct Céreq.

**Alternatives rejetées** :

1. **Activer toutes les APIs disponibles (~30)** : scope explose, scope
   créep vs deadline INRIA, risque congestion rate limits cross-APIs.
2. **Skip Open Formation (redondant avec ONISEP/Parcoursup)** : faux —
   Open Formation couvre les partenaires FT (CFA, organismes continus)
   qui ne sont PAS dans ONISEP formations classiques ni Parcoursup. Gap réel.
3. **Activer Anotéa en P0 maintenant** : non — auth HMAC custom = stack
   différente OAuth2, 20-25h effort, couverture 40-60% seulement.
   Post-INRIA mieux.

**Nuance technique "Anotéa reporté parce que compliqué ?"** (question
Matteo transmise Jarvis) :

3 raisons combinées :
1. **Auth différente** (HMAC-SHA256 vs OAuth2 pour toutes les autres APIs FT) →
   module dédié + complexité cross-client.
2. **Effort 20-25h** vs 3-10j pour Marché du travail / Accès emploi / Sortants.
3. **Couverture partielle scope OrientIA** (~40-60%) alors que les 3 autres
   P1 couvrent 100% ROME × régions.

Anotéa est **utile** (avis qualitatifs modérés), pas **critique INRIA**. Le
reporter post-INRIA = maximiser effort S+2 sur ingestion Marché travail +
Accès emploi + Sortants formation qui apportent plus de valeur par heure.

**Effets attendus S+1-S+2** :

- **S+1 (reste de journée ~23/04 + 24-25/04)** : activation Open Formation
  + Offres d'emploi FT (3 min Matteo dashboard + 3-5j dev ingestion).
- **S+2** : activation ROMEO + scopes FT Marché travail + Accès emploi +
  Sortants formation. Ingestion 4 APIs complémentaires (10-14j cumul).
- **Post-INRIA** : Anotéa + Informations territoire + Événements si bande
  passante + valeur ajoutée mesurée.

**Scopes OAuth2 à activer côté app France Travail** (côté Matteo, 2-3 min) :

Pour les APIs à activer P0-P1 S+1-S+2 :
- `api_offresdemploi-v2` (offres d'emploi)
- `api_marche-travailv1` (déjà noté ADR-042)
- `api_acces-a-l-emploi-des-demandeurs-d-emploiv1` (déjà noté ADR-042)
- `api_sortants-formation-acces-emploiv1` (nouvelle, non dans ADR-042)
- `api_romeov2` ou équivalent (ROMEO)
- Open Formation : via portail api.gouv.fr (peut être OAuth2 séparé)

**Références** :

- Ordre Jarvis 2026-04-23-1559 addendum catalogue FT + question Sortants
- Rapport sub-agent Explore catalogue exhaustif francetravail.io
- ADR-042 (3 APIs FT inutilisées — complété par cet ADR sur Sortants + APIs
  additionnelles non-activées)
- ADR-039 scope élargi (3 phases target)

**Suite (S+1 → S+2)** :

1. Matteo active scopes Open Formation + Offres emploi FT (2 min).
2. S+1 fin : `src/collect/ft_open_formation.py` + `src/collect/ft_offres_emploi.py`
   (2-3j chacun).
3. S+2 : activation scopes ROMEO + Marché travail + Accès emploi + Sortants.
4. S+2 : `src/collect/ft_marche_travail.py` + `ft_acces_emploi.py` +
   `ft_sortants_formation.py` + `ft_romeo.py` (10-14j cumul).
5. Post-INRIA : Anotéa (`src/collect/ft_anotea.py`, HMAC custom) + Événements
   + Informations territoire.
6. Bascule ADR-043 DRAFT → ACCEPTED par API après activation + ingestion validée.

---

## ADR-044 — MonMaster : dédup par IFC en conservant la session la plus récente (2026-04-24) [DRAFT]

### Context

L'audit `docs/AUDIT_DATA_QUALITY_2026-04-23.md` a flaggé 7 304 doublons sur
le corpus `monmaster_formations.json` (16 257 fiches, soit ~45%). Verdict
NO-GO pour le re-index FAISS D6 tant que non-traité.

Investigation 2026-04-24 : les "doublons" sont en réalité des paires
(IFC, session) distinctes. L'API MonMaster expose 2 snapshots annuels
par formation — sessions 2024 + 2025 — avec des stats de candidature
différentes (`n_can_pp`, `n_accept_total`, `taux_admission`). Exemple :

| idx | IFC | session | n_can_pp | n_accept_total |
|---|---|---|---|---|
| 1    | 0900820SRD2N | 2024 | 49 | — |
| 1720 | 0900820SRD2N | 2025 | 91 | — |

Ce ne sont pas des doublons produits par l'ingestion — c'est la forme
brute de l'export MonMaster. Deux traitements possibles :

- **(A)** Étendre `_signature()` d'audit à `ifc+session` et conserver
  les 2 snapshots comme données légitimes (série temporelle possible
  pour analyse évolution du taux d'admission).
- **(B)** Dédupliquer dans `normalize_all` en ne gardant que la session
  la plus récente — corpus réel passe à 8 953 formations uniques.

### Decision

**Option B** : dédup par `ifc` en conservant la session la plus récente
(`dedupe_keep_latest_session` dans `src/collect/monmaster.py`).

### Rationale

1. **Principes directeurs projet** (CLAUDE.md §6) : "Données fraîches
   > figées". L'utilité RAG d'un lycéen·ne / réorientant·e qui consulte
   OrientIA en 2026 est la cohorte candidate 2025, pas la 2024.
2. **Anti-pollution retrieval** : garder les 2 sessions dilue le signal
   dans FAISS. Deux chunks quasi-identiques qui concurrencent les
   résultats top-k sans valeur ajoutée sur une requête d'orientation.
3. **Bénéfice coût embeddings** : 16 257 → 8 953 = -45% sur le budget
   Mistral embed pour D6 (~-$2 à -$5 sur un re-index complet).
4. **Pas de perte d'info critique** : les stats d'une seule session
   (la plus récente) sont suffisantes pour les questions d'orientation.
   Le raw complet reste disponible dans `data/raw/` si un besoin
   d'analyse longitudinale apparaît plus tard (nouvel ADR).

### Alternatives considérées

- **(A) Multi-session préservé** : garde la série temporelle mais
  dilue le retrieval et double le coût d'embeddings. Pas d'usage
  immédiat (aucune question eval_set ne référence une comparaison
  inter-année). Rejeté : sur-stocker sans use case concret.
- **(C) Fusion des 2 sessions** (agrégat pondéré) : complique la
  sémantique des chiffres (un taux d'admission moyenné sur 2 ans perd
  son interprétabilité). Rejeté comme trop exotique pour un gain
  marginal.
- **(D) Session latest via max()** au lieu d'ordre d'apparition :
  ancré sur le comparateur de sessions. Retenu de facto : la
  comparaison `_session_sort_key` joue ce rôle en interne, en
  conservant l'ordre global pour stabilité des diffs git.

### Consequences

- `data/processed/monmaster_formations.json` : 16 257 → 8 953 fiches
  (nouveau comptage au prochain run d'ingestion ou via script one-off
  `scripts/rebuild_monmaster_processed.py`).
- Audit 2026-04-24 post-fix : 0 doublon MonMaster (déjà confirmé en
  pré-ingestion via ADR-044 + fix signature ADR non-numérotée).
- Tests : 9 nouveaux dans `tests/test_monmaster_dedup.py` (dédup +
  clamp taux_admission à [0,1]).
- D6 FAISS peut être relancé dès Phase 2 finale + data fresh tirée.

### Rollback

Si un use case d'analyse longitudinale MonMaster émerge, rollback =
ré-ingérer avec `normalize_all` sans appel à `dedupe_keep_latest_session`.
Les deux sessions reviendront naturellement puisqu'elles sont toujours
exposées par l'API MonMaster. Le raw n'est jamais perdu.

### Liens

- Incident découverte : investigation Claudette 2026-04-24 matin
- Audit associé : `docs/AUDIT_DATA_QUALITY_2026-04-24.md`
- Tests : `tests/test_monmaster_dedup.py`
- Se substitue à la remédiation flaggée dans
  `docs/AUDIT_DATA_QUALITY_2026-04-23.md` (faux positif expliqué ici).

---

## ADR-046 — Gitignore processed files volumineux + regenerate idempotent (2026-04-24) [DRAFT]

### Context

Le pipeline v2 (ADR-039 scope élargi + PR #38) produit un
`data/processed/formations.json` de **81 MB** (37 600 fiches). Les
ingestions InserSup et Inserjeunes ajoutent respectivement
**48 MB** et **94 MB** sur leurs fichiers processed individuels. Ces
3 artefacts dépassent ou approchent le soft limit GitHub 50 MB,
déclenchant un warning `GH001: Large files detected` sur chaque push
et alourdissant le `git clone` sans valeur ajoutée (ce sont des
produits déterministes des ingestions, pas des sources).

Tension observée : la PR #42 Inserjeunes a gitignoré
`inserjeunes_lycee_pro.json` (94 MB) au cas par cas pour ne pas
bloquer le push. Sans formalisation, chaque nouvelle ingestion
volumineuse va répéter ce patch ad-hoc.

### Decision

Gitignorer les fichiers processed lourds (**> 50 MB** OU
**re-buildables en < 2 min d'API call**), et fournir un **pipeline
idempotent unique** (`scripts/regenerate_processed.py`) qui re-génère
tous les fichiers depuis zéro.

**Fichiers gitignorés par cet ADR** (au 2026-04-24) :
- `data/processed/formations.json` (81 MB, produit merge_all_extended)
- `data/processed/inserjeunes_lycee_pro.json` (94 MB, produit par
  `src.collect.inserjeunes`)
- `data/processed/insersup_insertion.json` (48 MB, produit par
  `src.collect.insersup_api`)

**Fichiers gardés tracked** (< 15 MB, valeur snapshot importante) :
- `monmaster_formations.json` (10 MB), `parcoursup_extended.json` (14 MB),
  `rncp_certifications.json` (10 MB), `onisep_*`, `lba_*`, `cereq_*`,
  `inserjeunes_cfa.json`, `ip_doc_doctorat.json`.

### Rationale

1. **Le code est la source de vérité, pas l'artefact** : les pipelines
   d'ingestion + le merger v2 sont déterministes. Quiconque clone le
   repo peut reconstituer l'état corpus via
   `python scripts/regenerate_processed.py`.
2. **Coût git réduit** : -223 MB sur le repo (cumul des 3 fichiers).
   `git clone` passe de ~230 MB à ~7 MB de data processed.
3. **Warnings GitHub éliminés** : plus de `GH001` sur les pushes futurs.
4. **Pattern CI-friendly** : le script `regenerate_processed.py` peut
   être câblé dans un GitHub Actions workflow nightly ou
   pre-release pour rafraîchir les snapshots si on les expose via
   des artifacts (hors scope cet ADR — follow-up S+1 si besoin).
5. **Critère explicite** (> 50 MB OU < 2 min build) évite les
   décisions ad-hoc. Les fichiers < 15 MB restent tracked pour garder
   le `git clone` immédiatement utilisable par les devs.

### Alternatives considérées

- **(A) Git LFS** : migration lourde (réécriture d'historique + tous
  les contributeurs doivent activer git-lfs). Non-rentable vs
  gitignore + regenerate tant qu'on reste à < 5 fichiers concernés.
- **(B) Tout committer (statu quo)** : warnings GitHub + risque d'être
  forcé sur LFS par GitHub à 100 MB hard limit. Reporte le problème.
- **(C) Script sans gitignore** : contradictoire, on veut justement
  réduire le poids git.
- **(D) Gitignore de tous les processed** : cassant pour le pipeline
  FAISS qui lit `formations.json` directement. Trade-off : on garde
  les fichiers < 15 MB tracked pour que le code marche out-of-the-box
  après un clone, et on regenerate les gros.

### Consequences

**Breaking change** pour les workflows qui clonent le repo ET attendent
`formations.json` présent. Mitigation :
1. `scripts/regenerate_processed.py` exécutable en 1 commande (~90s
   total API + merge selon sources dispo).
2. Documentation explicite dans CLAUDE.md + README (à suivre) : "après
   clone, run `python scripts/regenerate_processed.py` avant usage RAG".
3. CI GHA workflow à ajouter S+1 pour que les snapshots soient
   disponibles en artifact si besoin.

**Non-breaking** : la plupart des tests pytest n'ont pas besoin de ces
fichiers (ils mockent les API ou utilisent des fixtures tmp_path).
Seuls les pipelines intégrés (RAG FAISS, benchmark) dépendent de
`formations.json` — eux nécessitent un regenerate local.

### Rollback

Revert simple possible : remettre les fichiers en tracking via
`git add -f data/processed/<file>.json` + retirer les entrées
correspondantes du `.gitignore`. Aucun historique perdu côté code.

### Liens

- Script : `scripts/regenerate_processed.py` (ADR-046)
- Gitignore : voir `.gitignore` lignes "Data processed volumineux"
- Précurseur partiel : PR #42 Inserjeunes (gitignore one-off du
  lycee_pro.json)
- Warning déclencheur : push PR #38 `GH001: formations.json is 81.19 MB`

---

## ADR-047 — Mistral timeout root cause : client par défaut, pas fiche_to_text (2026-04-25)

### Context

Bench v4 (2026-04-24) a vu Q12 Mohamed q3 ("CAP cuisine Marseille → Bac
pro alternance, cuisine vs pâtisserie") timeout 4 fois consécutivement
avec `ReadTimeout: The read operation timed out`. Pattern identique à
Q5 Théo q2 en v3 (non-noté pour la même raison).

Le SYNTHESIS v4 vs v3 (`results/bench_personas_v4_2026-04-24/_SYNTHESIS_V4_VS_V3.md`)
recommandait : *"augmenter `timeout` côté client Mistral (actuellement
défaut, probablement 60 s) à 180 s. Ou batch les queries lourdes en
séparé."*

**Hypothèse alternative à invalider** : `fiche_to_text` v3 a peut-être
explosé en taille post-injection des stats chiffrées (insertion_pro,
taux_admission, etc.), gonflant les prompts au point de provoquer le
timeout. Cette hypothèse, si vraie, justifierait une refonte
`fiche_to_text` v4 (cf CLAUDE.md OrientIA `Fichiers protégés`).

### Investigation 2026-04-25 (Axe 4 ordre samedi-4-axes)

Mesure des outputs `fiche_to_text` v3 sur 5 000 fiches du corpus 48 914 :

| Métrique | Valeur (chars) | Tokens estimés (chars/4) |
|---|---:|---:|
| Min | 247 | 62 |
| Médiane | 642 | 161 |
| Moyenne | 646 | 162 |
| p90 | 959 | 240 |
| p99 | 1 010 | 253 |
| Max | 1 198 | 300 |

Sur le sous-ensemble cuisine (40 fiches, plus proche de Q12) :
- Avg 326 chars / ~82 tokens par fiche
- Max 652 chars / ~163 tokens
- **Plus PETIT** que la moyenne globale (peu de stats riches insertion_pro
  vs ingénierie / médecine).

Total prompt estimé pour une requête typique top-K=10 :

| Composant | Chars | Tokens |
|---|---:|---:|
| SYSTEM_PROMPT v3.2 | 31 388 | **7 847** |
| Top-10 fiches (avg case) | 6 461 | 1 615 |
| Top-10 fiches (worst case) | 11 386 | 2 846 |
| Query utilisateur | ~300 | ~75 |
| Scaffolding messages | ~400 | ~100 |
| **TOTAL input avg** | ~38 549 | **~9 637** |
| **TOTAL input worst** | ~43 474 | **~10 868** |

Mistral medium context window : 32 K tokens. Notre input ~10 K tokens =
30 % d'utilisation. **Aucun problème de prompt size.**

Audit côté client HTTP (script bench v4) :

```python
# scripts/run_bench_personas_v4.py:126
client = Mistral(api_key=cfg.mistral_api_key)   # ← AUCUN timeout
```

Comparé à `src/eval/run_real_full.py:83` qui passe explicitement
`timeout_ms=120000` (2 min) au client Mistral.

### Decision

**Root cause : client Mistral du bench personas instancié sans
`timeout_ms`, donc valeur par défaut SDK Mistral (~60 s côté HTTPX
sous-jacent). Pour les queries comparatives à génération longue
(>1 000 tokens output, ce qui prend 30-90 s avec Mistral medium), le
client coupe la connexion avant que Mistral ait fini de streamer la
réponse.**

**`fiche_to_text` v3 est innocent.** Sa taille moyenne 162 tokens (max
300) représente 1.6 % du prompt total. Optimiser `fiche_to_text`
réduirait les tokens d'input mais N'AFFECTE PAS la latence de
génération output qui est la cause du timeout.

**Fix** : passer `timeout_ms=180000` (3 min) au client Mistral dans les
2 scripts de bench :
- `scripts/run_bench_personas_v4.py:126`
- `scripts/run_bench_personas_v3.py` (à vérifier, même pattern probable)

Optionnellement : aussi dans `src/rag/cli.py:15` et tout autre script
qui consomme Mistral en mode interactif sur queries longues.

### Rationale

- **Une seule ligne, zéro risque** : ajouter `timeout_ms=180000` à un
  client HTTP n'a aucun side-effect sur la sémantique.
- **Empiriquement validé** : `run_real_full.py` passe à 120 s et n'a
  jamais reporté de timeout sur 7 systèmes × 100 queries (Run F+G).
  180 s est plus généreux pour le pire cas comparatif.
- **Pas de modif `fiche_to_text`** : conforme au CLAUDE.md OrientIA
  protected file note. Pas de bench delta requis avant fix.
- **Compatible avec l'archi agentique future** (PR #12) : le tool-use
  multipliera les appels par requête utilisateur, et chaque appel
  pourra être long (FetchStatFromSource, QueryReformuler). Un timeout
  généreux côté client est une condition nécessaire pour
  l'architecture agentique. Justifie la place de cet ADR avant Axe 3
  (cf consensus Jarvis+Claudette 2026-04-25-1140 sur l'inversion
  Axe 4 → Axe 3).

### Alternatives rejetées

1. **Optimiser `fiche_to_text`** (réduire la taille des outputs) — NO,
   le coupable n'est pas l'input mais la génération output. Pas
   d'effet attendu sur le timeout.
2. **Batch les queries lourdes en séparé** — NO, complexité
   architecturale gratuite. Le timeout SDK suffit.
3. **Stream la réponse côté client + agréger** — overkill, rajoute du
   code de gestion. Le timeout étendu suffit pour 99 % des cas.
4. **Retry automatique sur timeout** (cf `_call_with_retry` runner) —
   ajoute du coût API et de la latence. Le bon timeout dès le début
   est plus simple.

### Tests

- Action de vérification : ré-run le bench v4 avec
  `timeout_ms=180000` et observer si Q12 passe (probabilité élevée
  >90 % vu le diagnostic).
- Reporté à la PR convergence multi-corpus + bench v5 chiffré
  (Axe 1.A+B + Axe 1.D, budget validé Matteo 2026-04-25).
- L'implémentation du fix sera incluse dans la PR du bench v5
  (cohérent : la PR qui consomme le timeout étendu en validation
  chiffrée).

### Liens

- Q12 ReadTimeout : `results/bench_personas_v4_2026-04-24/query_12_mohamed_q3.json`
- Synthesis v4 : `results/bench_personas_v4_2026-04-24/_SYNTHESIS_V4_VS_V3.md` §4
- Pattern `timeout_ms` correct : `src/eval/run_real_full.py:83`
- Pattern à corriger : `scripts/run_bench_personas_v4.py:126`
- Protected file note : `CLAUDE.md` OrientIA, table "Fichiers protégés"

## ADR-048 — RAG multi-corpus retrievable parallèle (2026-04-25)

### Context

Ordre samedi-4-axes Jarvis 2026-04-25-1140 demandait d'intégrer les
codes ROME + format_court ONISEP dans `formations.json` via merger v2
("humanisation ROME RAG"). Exploration data pré-implémentation a révélé
3 obstacles structurels :

1. **Couverture jointure ROME insuffisante** : 25 codes ROME distincts
   dans `formations.json` (4 450 fiches sur 48 914 ont des debouches),
   408 dans `ideo_fiches.json`, intersection de 8 codes (32 % couvre
   formations / 2 % couvre ideo). Greffer enrichirait <5 % du corpus.
2. **Match libellés métier impraticable** : formations expriment des
   spécialités fines ("Ingénieur cybersécurité datacenter"), ideo des
   métiers génériques ("ingénieur informatique"). 3 libellés distincts
   matchent en exact-match. Fuzzy hors scope.
3. **`fiche_to_text` protected file** (CLAUDE.md OrientIA) : modifs
   interdites sans refonte propre, et ROME injecté dans le texte
   embedding fait régresser (Run 5 ablation, ADR-033 ROME masking
   generator pour le même phénomène côté output).

### Decision

Pivot vers une architecture **N corpus retrievables parallèles** plutôt
qu'une jointure forcée à faible couverture. Chaque source de données
hétérogène devient un corpus distinct avec son `domain` et son texte
retrievable propre :

| Corpus | Records | Domain | Source | PR |
|---|---:|---|---|---|
| `formations.json` | 48 914 | `formation` | Parcoursup + ONISEP fusionnés | (existant, intact) |
| `metiers_corpus.json` | 1 075 | `metier` | ONISEP Idéo-Fiches XML | #56 |
| `parcours_bacheliers_corpus.json` | 151 | `parcours_bacheliers` | MESRI | #57 |
| `apec_regions_corpus.json` | 13 | `apec_region` | APEC observatoire 2026 | #59 |
| **TOTAL** | **50 153** | 4 domains | — | — |

Convergence implémentée dans `src/rag/multi_corpus.py` (PR #60) :
- `Corpus` dataclass holds records + domain + path
- `MultiCorpusLoader` : load_all() / load_one() avec graceful skip si
  fichier absent (fresh clones fonctionnels)
- `extract_texts_for_embedding(corpus)` : list[(id, text)] prêts pour
  `embed_texts_batched(client, texts)`
- `merge_for_embedding(corpora, domains?)` : fusion uniforme avec
  `original_record` préservé pour reranker / generator domain-aware

### Rationale

- **100 % couverture vs ~5 %** : 1 075 fiches metiers + 151 parcours
  + 13 régions APEC tous retrievables vs 8 codes ROME jointure forcée.
- **Préservation des protected files** : `fiche_to_text` v3 inchangé,
  `formations.json` inchangé. Pas besoin de bench delta validation
  pour les corpus annexes (additif, pas substitutif).
- **Pattern compatible RAG mature** : multi-corpus avec metadata
  filtering est largement utilisé (LangChain MultiRetriever, Llama
  Index domain routing). Rien d'exotique.
- **Decoupling reproductibilité** : chaque corpus a son builder
  (`build_metiers_corpus`, `parcours_bacheliers`, `apec_regions`), son
  test suite, son CLI. Régression en cascade isolée.

### Alternatives rejetées

1. **Jointure ROME forcée dans `formations.json`** — couverture <5 %
   pour un coût archi élevé. Cf ADR-040 D12 sur les limitations
   structurelles ROME formations.
2. **Modifier `fiche_to_text` v4** pour injecter ROME + format_court —
   interdit par protected file note + ADR-033 (régressif). Aurait
   demandé bench delta préalable.
3. **N index FAISS séparés** (1 par domain) — overhead latence et
   complexité retrieval. Préféré : 1 index unifié avec `metadata.domain`
   filter (cf PR #61 future avec rebuild + bench v5).

### Tests

PR #60 livre 26 tests sur `multi_corpus.py` :
- `Corpus` dataclass (len, is_empty)
- `_extract_text` per domain (formation→nom, autres→text)
- `MultiCorpusLoader.load_all/load_one/get` (4 corpus, missing file
  graceful, invalid JSON graceful, unknown domain raise, lazy cache)
- `extract_texts_for_embedding` (metier, formation idx-based fallback,
  skip_empty on/off)
- `merge_for_embedding` (fusion, filtre domain, preserve original_record,
  skip text vide)

Toujours **0 régression** sur 976 tests existants.

### Liens

- PR #56 metiers_corpus (Axe 1.A pivot)
- PR #57 parcours_bacheliers (Axe 2)
- PR #59 apec_regions (Axe 1.B)
- PR #60 multi_corpus convergence (cette ADR)
- PR #61 (à venir) FAISS rebuild + bench v5 chiffré
- ADR-040 scope élargi 17-25 ans
- ADR-033 ROME masking generator
- ADR-047 Mistral timeout (consensus archi cohérente)
- Protected file note : `CLAUDE.md` OrientIA, `fiche_to_text`

---

## ADR-049 — Reranker multi-domain aware (DRAFT) (2026-04-25)

### Context

ADR-048 a livré le pivot RAG multi-corpus (PR #60). Le bench v5 sur les
18 queries v4 (PR #61) a montré que le multi-corpus n'est activé que
sur 1/18 queries — celles-ci étant formation-centric par construction.

Bench multi-domain dédié (8 queries non-formation-centric, PR #62)
révèle le vrai comportement :
- **6/8 queries activent le multi-corpus** côté FAISS (75 %)
- **0/2 queries APEC** (a1 "marché cadres Bretagne", a2 "régions
  cadres bac+5 informatique") récupèrent des records `apec_region`
  dans le top-10 final, malgré leur disponibilité dans l'index
- **Smoke test FAISS L2 direct** sur les mêmes queries APEC retourne
  pourtant 8/10 records `apec_region`

Le delta vient du `OrientIAPipeline` qui applique :
- `reranker.RerankConfig` avec boosts SecNumEdu/CTI/labels formation
- `intent.classify` qui privilégie le domain `formation` par défaut
- `mmr.diversify` qui pondère sur des fields `formation`-spécifiques

Conséquence : les apec_records arrivent dans le top-50 FAISS mais sont
poussés hors du top-10 final par le reranker.

### Decision (DRAFT)

Adapter `RerankConfig` pour reconnaître les intents multi-domain et
boost les corpora correspondants :

| Intent détecté | Domain à boost | Boost suggéré |
|---|---|---|
| "marché du travail" / "cadres" / "salaire région" / "recrutements" | `apec_region` | ×1.5 |
| "métier" / "profession" / "que fait un X" / "quel métier" | `metier` | ×1.3 |
| "taux réussite" / "passage L1 L2" / "redoublement" / "licence par bac" | `parcours_bacheliers` | ×1.3 |
| Intent ambigu (formation par défaut) | aucun boost | 1.0 |

Implémentation envisagée :
- Étendre `intent.classify` avec ces 3 nouveaux intents (ajout
  patterns regex + fallback formation)
- Étendre `RerankConfig` avec le mapping intent → domain boost
- Préserver les boosts formation existants (SecNumEdu, CTI, etc.)

### Rationale

- **Sans cette adaptation, le pivot ADR-048 ne livre que 75 % de sa
  valeur potentielle** (mesuré sur le bench multi-domain : +6 queries
  activées, mais 2 queries APEC bloquées par le reranker → gain net
  notation humaine seulement +0.375/25)
- **Pas une régression sur formations** : les boosts formation
  existants sont préservés, on ajoute des boosts conditionnels selon
  intent
- **Compatible avec l'archi agentique future** (PR #12 reportée
  samedi prochain) : le tool-use Mistral aura besoin d'un retriever
  multi-domain aware pour FetchStatFromSource

### Alternatives rejetées

1. **Index FAISS séparés par domain** (1 par domain, query routing
   explicite) — overhead complexité retrieval, contredit le pivot
   "multi-corpus dans 1 index unifié" choisi en ADR-048
2. **Retrain reranker LightGBM/XGBoost** sur des données labellisées
   multi-domain — ROI faible, dataset trop petit, complexity élevée
3. **Modifier `fiche_to_text`** pour inclure des domain tags — viole
   le protected file note + ne résoud pas le problème reranker

### Tests

- Implémentation reportée S+1 (hors scope deadline samedi 25/04 EOD)
- Bench post-implémentation : re-run multi-domain 8-queries après
  reranker adapt, mesurer impact sur a1/a2 (queries actuellement
  bloquées) et confirmer pas de régression sur queries formation
  existantes
- Triple-run pour stabiliser les chiffres notation humaine + fact-check
- Ajout de 5-10 queries multi-domain supplémentaires pour augmenter
  la puissance statistique (N=8 → N=15-18)

### Liens

- Bench multi-domain qui a révélé le bug : `results/bench_multi_domain_2026-04-25/_SYNTHESIS.md` §5
- ADR-048 (RAG multi-corpus) : prérequis
- `src/rag/reranker.py` : `RerankConfig` à étendre
- `src/rag/intent.py` : `classify` à étendre
- Protected files note CLAUDE.md OrientIA : reranker stable depuis
  Run 3 ablation, modifications additives uniquement (pas remove)

## ADR-050 — Dedup Parcoursup `cod_aff_form` dans merger v2 (2026-04-25)

### Context

Audit data EOD 2026-04-25 (Jarvis) a flaggé **R1 (P0)** : 2 648 doublons
stricts Parcoursup dans `formations.json`. Mécanisme :

- `merge_all_extended()` concatène 7 sources : legacy (Parcoursup CSV
  via `merge_all`), `parcoursup_extended` (pré-normalisé), ONISEP,
  MonMaster, RNCP, LBA, Inserjeunes CFA.
- Les 2 sources Parcoursup (legacy + extended) **se chevauchent** sur
  ~1 324 codes, produisant 2 × 1 324 = 2 648 records identiques par
  `cod_aff_form` (1 issu de chaque source).
- Pas de dedup au moment du concat → 5.4 % du corpus formations en
  doublons silencieux.

Manifestation pré-fix : audit Claudette du 24/04 avait scanné sur
`(nom, etab, ville)` et noté 4 395 doublons mais classé `✅ GO` —
signal manqué sur la **nature stricte** de ces 2 648 paires.

Bench v5 sur 18 queries v4 (PR #63 notation humaine) a montré régression
précision factuelle -0.64/5 (-14 %), pattern 11/17 baissent / 0
augmentent. Hypothèse de travail : dilution multi-corpus + concentration
de doublons dans top-K dégradent la pertinence retrieval.

### Decision

Ajouter `dedup_parcoursup_by_cod_aff_form(fiches)` dans
`src/collect/merge.py` + appel à l'**Étape 4b** de `merge_all_extended`
(post-concat, pré-attach).

**Stratégie de fusion (préserve les enrichissements complémentaires)** :

1. Group by `cod_aff_form` non-vide
2. Pour chaque groupe size > 1 :
   - Choisit la fiche **la plus enrichie** comme base (max nb champs
     non-vides)
   - **Merge soft** : tout champ absent de la base est complété depuis
     les autres fiches du groupe (premier non-vide)
3. Préserve l'ordre stable (1ère occurrence par `cod_aff_form`)
4. Records sans `cod_aff_form` (autres sources) passent inchangés

**Pourquoi merge soft plutôt que keep-first** : les 2 sources ont des
enrichissements complémentaires :
- `legacy` (issu de `merge_all`) a `match_method`, `labels` (champ
  ADR-002 reranker SecNumEdu/CTI/CGE)
- `parcoursup_extended` a `provenance`, `collected_at`,
  `merge_confidence`, `insertion_pro`, `trends`

Le merge soft garantit que **rien ne se perd**, contrairement à un
naïf keep-first qui perdrait soit `labels` soit `insertion_pro`.

### Output mesuré

`scripts/dedup_formations_existing.py` appliqué sur le `formations.json`
existant (48 914 fiches) :
- **47 590 fiches en sortie** (drop 1 324)
- Backup : `data/processed/formations.json.pre_dedup`
- Nouveau : `data/processed/formations_dedupe.json` (86.8 MB vs 94 MB)

### Rationale

- **Bug merger silencieux** = signal régression -14 % précision factuelle
  bench v5. Dedup est un fix ciblé qui peut isoler la cause R1
- **Préservation des enrichissements** : merge soft garantit pas de
  perte downstream (labels, insertion_pro, trends)
- **Réversible** : `formations.json.pre_dedup` permet rollback
- **Pas de modification des autres sources** : MonMaster déjà dédup IFC
  ADR-044, RNCP/LBA ont des IDs uniques natifs

### Alternatives rejetées

1. **Keep-first sans merge** : perd `labels` ou `insertion_pro` selon
   l'ordre de concat. Régression invisible mais réelle.
2. **Dedup au niveau loader Parcoursup** (filtrer avant concat) :
   complexité dispersée. Centralisation post-concat est plus claire.
3. **Hash multi-fields** (cod_aff_form + nom + etab) : `cod_aff_form`
   est l'identifiant Parcoursup canonique, pas besoin de plus.
4. **Re-fetch Parcoursup CSV propre** : ne corrige pas le bug merger,
   masque le symptôme.

### Tests

8 tests unitaires couvrent :
- No duplicates passthrough
- Simple pair (richer wins, labels preserved)
- Three fiches same cod_aff_form (3-way merge)
- Empty cod_aff_form passthrough
- Mixed cod_aff_form + no-caf
- Preserves order first cod_aff_form seen
- Empty list
- Legacy `labels` field preserved post-merge (régression ADR-002)

Suite complète : 1 080 tests verts (1 072 baseline + 8 nouveaux), 0
régression.

### Phase 3 diagnostic en cours

Le re-bench v5 sur index dedupé permettra d'isoler la cause -14 % :
- v5_dedupé ∈ [4.30, 4.53] → cause R1 ✅ shippable INRIA
- v5_dedupé ∈ [3.85, 3.95] → cause architecturale ❌
- v5_dedupé ∈ [3.95, 4.30] → cause mixte → triple-run requis

ADR-050 sera complété par le verdict Phase 3.

### Liens

- `src/collect/merge.py` : `dedup_parcoursup_by_cod_aff_form` + appel
  dans `merge_all_extended` Étape 4b
- `scripts/dedup_formations_existing.py` : standalone application sur
  l'existant sans re-run merger v2 complet
- Audit Jarvis : `~/obsidian-vault/04-Connaissances/orientia-audit-data-2026-04-25.md` §5.2
- ADR-039 scope élargi (concat des 7 sources)
- ADR-044 dedup MonMaster IFC (précédent, autre source)
- Bench v5 régression précision : `results/bench_personas_v5_2026-04-25/_SYNTHESIS.md` §7

---


## ADR-051 — Architecture agentique : Tool registry + Agent loop with Mistral function calling (2026-04-26)

### Context

Le bench persona complet 2026-04-26 (PR #75) a révélé 3 limites
structurelles du RAG rule-based actuel sur sa baseline figée 39.4 %
verified / 17.9 % halluc :

- **Floor L2-only-DARES** : 4/10 queries dédiées prospective voient
  top-K = 100 % cells DARES sans formation, indépendant du boost.
- **Cohabitation user-naturelle nulle** : 10/10 queries user-naturel
  restent sur formation domain seul. L2 brut ne compose pas
  sémantiquement les corpora ajoutés.
- **Hallucination réglementaire** : 1 erreur catchée (titre RNCP
  psychologue niveau 6 vs niveau 7 protégé) que le fact-checker rate.

Ces limites motivent un pivot vers **agentique adaptatif** : un système
qui raisonne sur la query, choisit les outils pertinents, vérifie ses
sources avant de générer. Bascule axe B INRIA J-23 (focal samedi 02/05),
livré en 4 sprints.

### Decision

**Pattern retenu : Agent loop with tool dispatch (function-calling natif Mistral)**.

- `Tool` : abstraction d'un outil (nom, description, JSON schema des
  paramètres, fonction Python à dispatcher).
- `ToolRegistry` : catalogue des tools enregistrés, lookup par nom.
- `Agent` : boucle orchestration `run(question) → final_answer` qui
  appelle Mistral function-calling, dispatch les `tool_calls` retournés,
  réinjecte les résultats dans la conversation, jusqu'à composition
  finale ou max_iterations.
- Tools concrets implémentés en sous-modules (`src/agent/tools/`) :
  - Sprint 1 : `ProfileClarifier` (extraction profile structuré query
    → JSON {age_group, education_level, sector_interest, region,
    intent_type, urgent_concern})
  - Sprint 2 : `QueryReformuler` (réécriture query éventuelle ⇒
    sous-queries spécialisées par corpus)
  - Sprint 3 : `FetchStatFromSource` (vérif stat avant citation)
  - Sprint 4 : intégration end-to-end + bench vs baseline figée

### Rationale

**Pourquoi Mistral function-calling plutôt que ReAct ou state machine ?**

1. **Cohérence stack souverain** : le projet utilise Mistral pour gen
   + embed depuis ADR-001. Function-calling Mistral validé en POC #12
   (axe2/pydantic-profileclarifier, Mistral Large) — gate technique
   passé avec latence acceptable.
2. **Simplicité MVP** : function-calling natif évite de réinventer un
   parser ReAct fragile. Le contrat tools est explicite via JSON schema
   typé, le SDK gère la sérialisation des `tool_calls`.
3. **Évolutivité Sprints 2-4** : ajouter un tool = écrire un sous-module
   + register dans `ToolRegistry`. Pas de modif du loop principal.
4. **Composabilité** : un tool peut appeler d'autres tools si besoin
   (ex : `QueryReformuler` peut consulter `ProfileClarifier` en interne).

**Pourquoi pas state machine ?**

State machine impose un graphe d'états figé (clarify → reformule →
retrieve → answer). Trop rigide quand l'agent doit décider
contextuellement de skipper certaines étapes (ex : query générique
sans besoin de reformulation, ou question conceptuelle pure sans tool
nécessaire).

**Pourquoi pas LangChain ou framework externe ?**

Souveraineté + simplicité : on contrôle 100 % du loop, pas de magie
cachée, pas de dépendance lourde, ADR auditable INRIA. Pattern POC
2026-04-22 a démontré que ~150 lignes de Python suffisent pour le loop.

### Structure modulaire

```
src/agent/
├── __init__.py        # exports publics
├── agent.py           # Agent class + run() loop
├── tool.py            # Tool dataclass + ToolRegistry
└── tools/
    ├── __init__.py
    └── profile_clarifier.py  # Sprint 1
    # Sprint 2 ajoutera query_reformuler.py
    # Sprint 3 ajoutera fetch_stat_from_source.py
```

`tests/test_agent_*.py` pour tests unitaires + intégration.

### Alternatives considérées

1. **State machine explicite** (transitions définies clarify→reformule
   →retrieve→generate) : rejetée — trop rigide, ne capture pas la
   décision adaptative de skipper des étapes.
2. **ReAct prompting custom** (pas de tool-use natif, parser
   "Thought:/Action:/Observation:") : rejetée — fragile au format de
   sortie LLM, fait double emploi avec le SDK Mistral function-calling.
3. **LangChain / CrewAI / AutoGen** : rejetées — souveraineté +
   transparence + simplicité custom > complexité framework.
4. **Agent OpenAI Assistants API** : rejetée — souveraineté
   (cf ADR-001), Mistral function-calling est l'équivalent souverain.

### Caveat narrative INRIA

L'ADR positionne explicit l'agentique comme **réponse aux 3 limites
mesurées** du bench persona complet (PR #75). Pas un pivot
opportuniste — un fix architectural justifié par la mesure. Cohérent
avec l'apprentissage capitalisé du tune ×1.0 DARES (cf
`docs/VERDICT_BENCH_DARES_DEDIE.md`) : les boosts rule-based atteignent
leur plafond, l'adaptatif scale.

Les tools agentiques restent **transparents et traçables** : chaque
appel logged, paramètres sérialisés, résultats observables. Pas de
black-box, INRIA reproductible.

### Liens

- POC validation Mistral tool-use : `experiments/poc_mistral_toolcall.py`
  (PR #12, branche `axe2/pydantic-profileclarifier`)
- Verdict baseline figée : `docs/VERDICT_BENCH_PERSONA_COMPLET_2026-04-26.md`
- Sprint 1 livraison : `src/agent/` + `src/agent/tools/profile_clarifier.py`
- ADR-001 souveraineté Mistral
- Décision Sprints 2-4 : ADR à compléter au fil de l'eau pour chaque
  tool concret (`QueryReformuler`, `FetchStatFromSource`).

---

## ADR-052 — Critic loop conservé en `src/experimental/`, décision finale conditionnée à un bench Sprint 7.5 d'ablation (2026-05-06)

### Context

Refonte produit niveau 2 (cf `~/.claude/plans/niveau-d-ambition-2-...`),
Phase 3 du plan. Le `critic_loop` (Sprint 7 Action 3, commit `c920a9a`)
est un module LLM-judge 2-pass qui relit les réponses du pipeline et
réécrit les chiffres non-sourcés en `(estimation)` ou les retire. Pattern
"style rewriter" 2-passes — proche conceptuellement du STYLE REWRITER
du schéma cible Matteo, mais via réécriture LLM (vs few-shot statique).

Reverté en pratique au commit `ec4516b` (Sprint 7 verdict, 2026-04-27)
sur la base de 38q × 3 runs IC95 :

| Métrique | Baseline (critic OFF) | Both (v3.3 strict + critic ON) |
|---|---|---|
| pct_verified | **30.8%** ± IC95 1.03pp | 29.3% ± 12.07pp |
| pct_halluc | 16.8% ± 8.19pp | **25.6%** ± 20.65pp |
| Latency | 38.04s | 41.91s |
| Stabilité IC95 | 1.03pp | **12.07pp (×11.7 plus instable)** |

Décomposition par axe dans `docs/SPRINT7_VERDICT.md` :
- Axe 2 DROM territorial : 28.6% → 5.0% = **-23.6pp (cassé par critic)**
- Axe 1 DARES : 7.3% → 5.1% (régression)
- 266 modifications critic appliquées au total, effet net négatif documenté

Le pattern "R3 revert" est reproduit à Sprint 5, Sprint 6 et Sprint 7 :
double signal honnête, pas de hype. La relecture LLM empire l'hallu nette
parce que le LLM réécrit en inventant pour combler.

### Decision

Conserver `critic_loop.py` dans `src/experimental/critic_loop.py` (déplacé
en Phase 1 du plan refonte, commit `91d129b`). **Pas de suppression**, mais
**pas de réintroduction en pipeline production tant qu'un Sprint 7.5
d'ablation Strict-only vs Critic-only n'a pas isolé le coupable**.

### Rationale

1. **Garder l'option ouverte** : le verdict Sprint 7 a testé Mode Both
   (v3.3 strict + critic ON). Critic seul (sans v3.3 strict) n'a jamais
   été mesuré. Possibilité (faible mais existante) que critic seul soit
   net positif.
2. **Pas de dette de contexte non-nécessaire** : le module est dans
   `experimental/` avec ce ADR pointant explicitement le revert. Future
   Claude session lit l'ADR et comprend pourquoi le module n'est pas
   activé.
3. **Replacement déjà en prod** : `src/rag/post_process.py` (Sprint 8 W1,
   commit `19f3514`) est branché en Phase 2 du plan refonte. Couvre les
   cas pratiques de hallu (URLs github.com inventées, slugs ONISEP
   `FOR.XXXX` fabriqués, tableaux markdown cassés) **de façon déterministe
   et sans risque LLM destructif**.
4. **Coût d'opportunité** : pour produit niveau 2 dans 5-7 jours
   (refonte 2026-05-06), pas le temps de Sprint 7.5 d'ablation. Décision
   reportée à un futur sprint d'investigation dédié.

### Alternatives considérées

1. **Enterrer définitivement** (`git rm`) : rejetée — option ouverte au
   cas où Sprint 7.5 montre un effet positif isolé. Coût conserver = 0
   (module dans `experimental/`, n'impacte pas le pipeline prod).
2. **Réactiver dans factory en mode `enable_critic_loop: bool = False`
   opt-in** : rejetée — pas de raison d'exposer un flag dont la valeur
   `True` est mesurée comme régression. Risque qu'un futur dev l'active
   sans relire le verdict Sprint 7.

### Critères de réouverture

Un futur Sprint 7.5 d'ablation devra mesurer (∈ ordre) :
1. Critic-only (v3.2 baseline + critic ON) vs Baseline pure → isole
   l'effet critic seul.
2. Strict-only (v3.3 strict + critic OFF) vs Baseline pure → isole
   l'effet v3.3 strict.
3. Si **Critic-only montre un gain net stable** (pct_verified +X pp,
   pct_halluc inchangé ou diminué, IC95 < 5pp) sur 30q × 3 runs, alors
   réouvrir cet ADR en `Decision: réintroduire critic_loop opt-in`.

### Liens

- Verdict Sprint 7 R3 revert : `docs/SPRINT7_VERDICT.md` + commit
  `ec4516b feat(sprint7-verdict): bench × 2 modes final + verdict honnête R3 revert`
- Replacement déterministe : `src/rag/post_process.py` (Sprint 8 W1,
  commit `19f3514`), branché en pipeline production via factory
  (Phase 2 refonte, commit `5cd3643`)
- Code archivé : `src/experimental/critic_loop.py` (ex `src/rag/critic_loop.py`,
  déplacé Phase 1 refonte, commit `91d129b`)
- Plan refonte produit niveau 2 :
  `~/.claude/plans/niveau-d-ambition-2-oui-glowing-alpaca.md`

---

## ADR-053 — Stratégie WHAT/HOW : extraction structurée FactCard + contrat strict v4 (2026-05-06)

### Context

Refonte produit niveau 2. Découverte fondamentale via Phase 2.5 (Layer3
audit) + Phase A (audit data type A/B/C) :

- 37 hallu Layer3 sur 18 réponses production v3.2 (avg honesty=1.0
  côté validator c1+c2 → trompeur)
- 0 cas pur "type B data manquante" — l'info est presque toujours dans
  le corpus
- 4/18 type_A_llm (LLM hallucine alors que data est là)
- 7/18 type_C_mixte (mix verified + invented)
- Audit retrieval quality : 9/18 ok, 7/18 too_generic, 2/18 off_topic

**Conclusion** : le verrou principal n'est PAS la data corpus (88%
utilisable). C'est la **fidélité de génération** — Mistral Medium
extrapole hors-source même quand l'info est correcte.

Vision stratégique demandée par Matteo (turn 2026-05-06) :

> Question utilisateur → Séparation (Scope/hors scope) → Si hors scope
> réponse automatique, si scope → On récupère les bonnes data, et on
> récupère Q/A golden pour le style → prompt LLM Mistral qui écrit avec
> le style en intégrant les chiffres récupérés (que eux) → réponse
> utilisateur·ice.

### Decision

Implémenter une architecture WHAT/HOW (séparation faits/style) en
**3 couches structurelles** :

1. **WHAT — Extraction structurée des faits** (`src/rag/fact_card.py`) :
   - Dataclass `FactCard` avec sous-bloc `chiffres` typé (taux_acces,
     nombre_places, salaire_median, taux_emploi_3ans, etc.)
   - `fiche_to_fact_card(fiche, fact_id)` mappe les fiches Parcoursup
     riches (21.5% du corpus) ET MonMaster/RNCP minimal (78.5%)
   - `format_sources_for_llm(top_sources)` sérialise top-K en JSON
     tabulaire `<sources>` pour le user prompt

2. **CONTRAT — System prompt strict** (`src/prompt/system_v4_strict.py`) :
   - REMPLACE entièrement v3.2 (pas additif comme v3.3 strict reverté
     Sprint 7)
   - 5 règles non-négociables : R1 chiffres uniquement depuis
     `chiffres.X` (null → "info non disponible"), R2 formations
     uniquement depuis sources.formation+etablissement+ville, R3
     citations `[source SX]` obligatoires, R4 style libre depuis
     Golden, R5 posture empathique

3. **HOW — Style few-shot** (déjà câblé Sprint 10 chantier D, conservé) :
   - Top-1 Q&A Golden injecté en préfixe user
   - Séparation stricte "Comment/Quoi" : exemple Golden = référence
     ton/structure UNIQUEMENT, sources `<sources>` = seules sources
     factuelles autorisées

### Rationale

1. **Empêcher l'hallu en amont vs annoter en aval** : annoter
   `(non vérifié)` post-hoc (option StatFactChecker) est patcher. Le
   contrat amont supprime la cause — le LLM ne peut citer ce qu'il ne
   voit pas en JSON typé.
2. **JSON tabulaire vs prose libre** : les fiches en prose mélangeaient
   chiffres et description, le LLM extrapolait par mimétisme. JSON
   typé avec `null` explicite force le refus honnête.
3. **Pattern différent du R3 revert** : v3.3 strict (Sprint 7) ajoutait
   6 règles à v3.2 → LLM saturé, augmentation hallu de 8.8pp. v4
   REMPLACE la prose par du JSON et impose un format différent → pas
   de saturation mesurée.

### Résultats mesurés (mini-bench 23 questions)

| Métrique | v3.2 production | v4 strict (Medium) | v4 strict (Large+scope++) |
|---|---|---|---|
| flagged validator c1+c2 | 0 | 1 | 1 |
| avg honesty | 1.0 | 0.993 | 0.989 |
| avg latency | **10.19s** | 46.87s | **25.25s** |
| avg words | **239** | 434 | 479 |
| Layer3 warnings (sur 18 communes) | 37 | **34 (-8%)** | 38 (+3%) |

Observations qualitatives :
- **v4 cite explicitement** : 9-21 `[source SX]` par réponse longue
  (vs 0 en v3.2)
- **v4 refuse honnêtement** : "il n'existe pas de classement officiel",
  "info non disponible", "aucune fiche dans mes sources pour X"
- **v4 distingue géographiquement** : X1 "ENSIBS pas à Brest mais
  Vannes/Lorient" (au lieu de l'effacer comme v3.2)
- **Mais verbosité explose** (+82% mots), latency ×4.6 vs v3.2

### Sub-décisions tranchées

**Mistral Large rejeté** : produit +4 warnings vs Medium pour 10× le
coût. La promesse "Large suit mieux le contrat" est réelle
qualitativement mais neutre sur Layer3. Le gain latency 47s→25s vient
en fait à 80% du ScopeClassifier amélioré.

**ScopeClassifier amélioré conservé** : prompt enrichi avec 9 few-shot
examples + règle prio détresse. Résultats S1/S2/S3/U2 passent de
12-129s à <2s. C'est le seul gain UX significatif de l'expérimentation
Mistral Large.

### Alternatives considérées

1. **Garder v3.2 + StatFactChecker post-hoc avec annotations
   `(non vérifié)`** : rejeté — annotations partout polluent UX, et
   c'est patcher au lieu de supprimer la cause.

2. **Activer Layer3 LLM par défaut + élargir allowlist** : rejeté —
   Layer3 est un LLM-judge biaisé (cf flag Z1 où il dit "salaire
   sous-évalué" alors que le chiffre vient littéralement des sources
   Parcoursup). Utile pour audit, pas pour blocage runtime.

3. **Enrichir le corpus santé/droit** : rejeté — Phase A a montré que
   l'info est dans le corpus à 88%. Le bug est LLM, pas data.

### Limites connues (pour v4.1+)

- **Verbosité 479 mots moyenne** vs cible 200-250. R6 max 250 mots à
  ajouter en v4.1.
- **Latency 25s** restera ×2.5 vs v3.2. Skip retry-with-hint en mode
  v4 pourrait gagner 20-30% (v4.2).
- **8 questions régressent en Layer3** vs v3.2 (A3, H9, H1, D5, F1,
  F6, X1, Z1). Hypothèse : verbosité crée plus de surface d'attaque.
  À mesurer après R6.
- **F3 BTS SIO vs BUT** flagged honesty=0.85 en v4-Large — régression
  isolée à investiguer.

### Liens

- Plan refonte : `~/.claude/plans/niveau-d-ambition-2-oui-glowing-alpaca.md`
- Code Étape 1 (ScopeClassifier) : commit `2c8999d`
- Code Étape 2 v4.0 (FactCard + prompt strict) : commit `e0845f7`
- Code Étape 2 itération (Large + scope++) : commit `[head]`
- Audits Phase 2.5 + A : commits `583be08` et `bacb940`
- Mini-bench artefacts : `results/mini_bench/phase_b{1,2,3}_*.json`
- Side-by-side spot-check : `results/mini_bench/comparaison_v3_2_vs_v4_FINAL.md`

---

## ADR-054 — Purge des chiffres d'insertion agrégés Cereq (2026-05-07)

### Context

L'audit data Phase 0 (`docs/AUDIT_PHASE_0.md`, finding #1) a révélé que
`src/collect/cereq.py:attach_cereq_insertion()` colle les statistiques
d'insertion agrégées par niveau de diplôme à toutes les fiches du même
niveau dans `formations.json`. Mesure brutale :

- 32 704 fiches (66,9% du corpus) ont les 4 mêmes champs `(salaire_median_embauche,
  taux_emploi_3ans, taux_emploi_6ans, taux_cdi)` parmi seulement **6 tuples
  uniques**, un par niveau (cap-bep, bac, bac+2, bac+3, bac+5, bac+8)
- Une fiche "BTS Cyber Marine Nationale" a les mêmes 4 chiffres qu'une
  fiche "BTS Pâtisserie"
- Le system prompt R1 impose "uniquement valeurs présentes dans `chiffres`"
  mais ne distingue pas spécifique vs agrégat
- Cas concret : bench Z1 (avocat fiscaliste) — LLM cite "salaire 2080€"
  qui est l'agrégat bac+5 toutes filières, pas le salaire d'avocat
  fiscaliste (réalité 2500-4000€). Layer3 (OFF) avait flag, ADR-053
  l'avait classé "biais judge" — finding actuel suggère que c'est la
  data qui ment

Le narratif produit "100% sourcé officiel + spécifique" est mis en cause
pour 67% du corpus. Le `honesty_score=1.0` du mini-bench v4.1 cache cette
hallu data-borne.

### Decision

**Purge totale (Option A)** des chiffres d'insertion Cereq agrégés du
corpus de production :

1. Le bloc `insertion_pro` de schéma Céreq (`taux_emploi_3ans`,
   `taux_emploi_6ans`, `taux_cdi`, `salaire_median_embauche` issus de
   `cereq.py:attach_cereq_insertion`) est **retiré** des 32 704 fiches
   concernées dans le futur corpus de référence (cf ADR-057).
2. `src/collect/cereq.py` reste dans `src/collect/` pour archive
   historique mais n'est plus appelé par le merger v2 nouveau (cf ADR-057).
3. Pour les fiches qui n'ont pas d'autre chiffre d'insertion (ni
   Parcoursup admission ni Inserjeunes spécifique), le bloc
   `insertion_pro` devient `null` ou absent → la FactCard expose
   `chiffres.taux_emploi_3ans: null` etc. → R1 du SYSTEM_PROMPT_V4_STRICT
   force le LLM à écrire *"information non disponible dans mes sources"*.
4. Pour les fiches MonMaster/Licence universitaires qui matchent une
   entrée InserSup (niveau + discipline + région), les chiffres
   InserSup spécifiques sont injectés à la place (cf §Liens). Le bloc
   `insertion_pro` porte alors `provenance: "insersup_mesr"` et la
   granularité réelle (ex : "Master Droit Sciences Politiques en
   Auvergne-Rhône-Alpes, cohorte 2024").

### Rationale

1. **Cereq agrégats apporte plus de bruit que de signal** : 6 valeurs
   uniques copiées sur 32 704 fiches ne véhiculent aucune information
   spécifique à la formation — seulement le niveau du diplôme, déjà
   présent dans le champ `niveau`. Le coût hallu data-borne dépasse
   le gain "indicatif niveau".
2. **Cohérence narratif INRIA** : "souveraineté + données officielles
   spécifiques" doit tenir littéralement. Présenter un agrégat niveau
   comme un chiffre par formation n'est pas tenable face à un reviewer
   académique.
3. **R1 force le bon comportement** : la mécanique strict v4 (FactCard
   `chiffres.X = null` → "info non disponible") existe déjà. Il suffit
   de ne plus coller des chiffres trompeurs pour qu'elle s'applique.
4. **InserSup couvre 20-25% du corpus** (Masters + Licences universitaires
   + écoles d'ingé publiques) avec une granularité supérieure
   (discipline × région). Pour ces fiches, le remplacement Cereq →
   InserSup donne de vrais chiffres spécifiques sans changer le contrat.
5. **Pas de perte qualitative pour le user** : les questions du genre
   "salaire après bac+5 en moyenne" peuvent être servies par les fiches
   INSEE Salaires PCS (cf ADR-057, intégration multi-corpus) avec
   provenance explicite "agrégat niveau toutes filières", au lieu d'être
   collées à chaque formation comme spécifique.

### Alternatives considérées

1. **Option B — Tagger les chiffres Cereq comme agrégat** (préserver
   `insertion_pro` + ajouter `provenance: "cereq_aggregat_niveau_bacX"`
   et que le LLM cite avec marqueur) : rejetée. Préservation
   théorique, complexité prompt augmentée (LLM doit gérer 2 types de
   citations), risque que le marqueur soit oublié dans la génération,
   et le user reste avec un chiffre qu'il pourrait croire spécifique
   malgré le tag. R6 max 250 mots compromis par les marqueurs allongés.
2. **Option C — Mix tag + remplacement InserSup quand match** : variante
   intermédiaire jugée plus complexe que nécessaire. La purge totale
   force la discipline du contrat strict v4 sans demi-mesure ;
   l'enrichissement InserSup est une amélioration positive et ciblée,
   pas une compensation à un agrégat conservé.
3. **Garder Cereq actuel (status quo)** : rejetée, c'est le fond du
   finding #1 de l'audit Phase 0.

### Impact mesurable attendu

- Densité chiffres exploitables médian : actuel ~3,5 (gonflé par Cereq)
  → cible mesurée sur fiches restantes uniquement
- Mini-bench v4.1 : taux refus honnête "info non disponible" sur les
  questions salaire/emploi par formation va augmenter (souhaitable)
- Mini-bench v4.1 : `honesty_score` doit rester à 1.0
- Bench Z1 (avocat fiscaliste) : le LLM ne citera plus "salaire 2080€"
  agrégat. Vérifier qu'il dit honnêtement "info non disponible" et
  redirige vers Conseil de l'Ordre / sites cabinets.

### Liens

- Audit Phase 0 finding #1 : `docs/AUDIT_PHASE_0.md` §1.3
- Code Cereq actuel : `src/collect/cereq.py`
- Source InserSup (à intégrer) : `data/processed/insersup_insertion.json`
  (48 230 records bruts) + `data/processed/insersup_corpus.json`
  (368 entrées agrégées prêtes RAG)
- Architecture WHAT/HOW : ADR-053 (FactCard + R1 contrat strict)
- Implémentation : Phase 1 grand ménage (à venir)

---

## ADR-055 — Liste blanche des sources autorisées par tier (2026-05-07)

### Context

L'audit Phase 0 a montré qu'OrientIA agrège ~25 sources data sans
politique formelle de provenance. Pour assurer le narratif INRIA
"souveraineté + données officielles" et préparer Phase 3 (enrichissement
ciblé), une liste blanche explicite est nécessaire avant tout nouvel
ingestion :

- Distinguer sources autorisées par niveau de confiance
- Acter ce qui est exclu pour éviter scope creep (forums, sites tiers)
- Fournir un guide de référence pour les futures ingestions Phase 3
  (calendriers Parcoursup, aides étudiantes, coûts privés, etc.)
- Préparer un argument défensif face à un reviewer académique :
  "ces sources et seulement celles-ci"

### Decision

OrientIA n'intègre des données que depuis les sources de la liste
blanche suivante, classées en 3 tiers de confiance :

#### Tier 1 — Officiel État (autorité maximale)

Plateformes État :
- `data.gouv.fr` (catalogue public)
- `Etalab` (licence ouverte 2.0)

Orientation :
- ONISEP (Office National d'Information Sur les Enseignements et les Professions)
- Parcoursup (plateforme officielle vœux post-bac)
- MonMaster (plateforme officielle candidatures master)

Statistique publique :
- INSEE (Institut National de la Statistique et des Études Économiques)
- DARES (Direction de l'Animation de la Recherche, des Études et des Statistiques)
- DREES (Direction de la Recherche, des Études, de l'Évaluation et des Statistiques)
- France Stratégie

Insertion / formation :
- Cereq (Centre d'études et de recherches sur les qualifications) — agrégats
  par niveau, **non utilisé pour citation par formation** suite ADR-054
- InserSup (MESR, Ministère Enseignement Supérieur Recherche)
- Inserjeunes (DEPP, Ministère Éducation Nationale)

Marché du travail :
- France Travail (offres + ROME 4.0 + statistiques)

Compétences et certifications :
- France Compétences (RNCP + RS)

Vie étudiante :
- CROUS / CNOUS
- aides.gouv.fr
- mes-aides.gouv.fr
- 1jeune1solution.gouv.fr

Territoires ultramarins :
- LADOM
- Préfectures DROM-COM (sites .gouv.fr)

#### Tier 2 — Paritaire / agence officielle (autorité forte)

- APEC (Association Pour l'Emploi des Cadres) — paritaire, conventions État
- AGEFIPH (handicap au travail) + FIPHFP (fonction publique handicap)
- ANSSI (label SecNumEdu, État)
- CGE (Conférence des Grandes Écoles)
- CTI (Commission des Titres d'Ingénieur)
- FESIC (Fédération des Établissements d'Enseignement Supérieur d'Intérêt Collectif)
- Conseils de l'Ordre (avocat, médecin, architecte, expert-comptable)
- Chambres consulaires (CCI, CMA, CA)

#### Tier 3 — Sites officiels d'établissements (info pratique uniquement)

Les sites officiels des établissements (`hec.edu`, `epita.fr`, etc.)
sont autorisés **uniquement** pour les données factuelles
non-polémiques :
- Coût annuel de scolarité
- Calendriers d'admission / dates limites
- Modalités d'inscription
- Adresse / coordonnées campus

Sont **interdits** pour citation depuis ces sites :
- Statistiques d'insertion publiées par l'école elle-même (utiliser
  InserSup ou Inserjeunes à la place)
- Taux d'admission / sélectivité (utiliser Parcoursup ou MonMaster)
- Témoignages d'anciens (cf ADR-056)
- Classements internes

Marquer `provenance.source: "site_etablissement_<slug>"` et
`provenance.tier: 3` pour exposition explicite côté FactCard.

#### Sources EXCLUES (jamais)

Aucune ingestion ni citation depuis :
- Agrégateurs privés : Studyrama, l'Etudiant.fr, Diplomeo, MeilleureEcole,
  Major-Prepa
- Sites d'avis : Glassdoor, TrustPilot, GoEtudier
- Forums : Reddit, JeuxVideo.com forum, Hardware.fr, etc.
- Réseaux sociaux : LinkedIn, Twitter, Instagram
- Classements internationaux non-vérifiables : QS Stars, Shanghai
  (re-discutables au cas par cas en ADR ultérieur si besoin)
- Wikipedia, Wikidata (utilisés uniquement comme pointeur, pas comme source de chiffres)

### Rationale

1. **Tier explicite défensif INRIA** : un reviewer demandant "d'où
   viennent vos chiffres ?" reçoit une réponse opérationnelle et
   complète. Les exclusions explicites sont un argument fort.
2. **Cohérence avec contrat strict v4 R3** : chaque chiffre cité a
   un `[source SX]` — la source SX est elle-même de tier 1, 2 ou 3
   identifié.
3. **Granularité tier 3 nécessaire en pratique** : le coût de HEC
   ou EPITA n'existe sur aucune source État. Refuser leur site
   officiel pour ces infos pratiques empêcherait OrientIA de répondre
   à la question "combien coûte EPITA ?". Le périmètre tier 3
   (info pratique uniquement, pas de stats) limite le risque.
4. **Exclusions explicites évitent le scope creep** : le projet a
   accumulé sans politique formelle. Cette ADR est le frein.
5. **Compatible avec le pipeline existant** : la FactCard supporte
   déjà un champ `provenance` ; il suffit de lui ajouter `tier`.

### Alternatives considérées

1. **Pas de liste blanche, jugement au cas par cas** : rejetée. Sans
   politique formelle, chaque PR data-source devient un débat. Coût
   maintenance élevé.
2. **2 tiers seulement (officiel / non-officiel)** : rejetée. Le tier 3
   "site école pour info pratique" est nécessaire pour combler le
   gap data ouverte sur les coûts privés.
3. **Inclure des avis subjectifs marqués "non vérifié"** : tranché
   en ADR-056 (rejet).

### Liens

- Audit Phase 0 §3 : `docs/AUDIT_PHASE_0.md`
- ADR-056 : politique avis subjectifs (rejet)
- Implémentation : champ `provenance.tier` dans FactCard, à ajouter
  Phase 1.A (`src/rag/fact_card.py`)
- Validation à venir : audit de provenance sur chaque source actuelle
  pour vérifier alignement (Phase 1)

---

## ADR-056 — Pas d'avis subjectifs dans le corpus (2026-05-07)

### Context

Discussion 2026-05-07 sur l'enrichissement Phase 3. Question soulevée
par Matteo : intégrer des avis d'anciens étudiants / salariés (Glassdoor,
forums étudiants, sites d'avis) pour enrichir la dimension qualitative
des réponses ?

Le narratif produit OrientIA est "souveraineté + données officielles
publiques + zéro hallu". Les avis subjectifs sont **par nature non
officiels** et leur intégration crée une tension :

- Soit on les intègre sans marqueur → on dilue le narratif, un reviewer
  dira "vous citez TrustPilot comme source ?"
- Soit on les intègre avec marqueur "non vérifié" → l'utilité diminue
  fortement (un avis avec disclaimer est moins percutant) et la
  cohérence du contrat strict v4 R3 est cassée (`[source SX]` mêle
  officiel et UGC)
- Soit on ne les intègre pas → on perd la dimension qualitative

### Decision

Aucun avis subjectif n'est intégré au corpus OrientIA. Périmètre :

- Pas d'ingestion depuis Glassdoor, TrustPilot, GoEtudier
- Pas d'ingestion depuis les forums (Reddit, JV, Hardware.fr, etc.)
- Pas d'ingestion depuis les réseaux sociaux (LinkedIn, Twitter, Instagram)
- Pas d'ingestion depuis les sites d'agrégateurs privés (Studyrama,
  l'Etudiant.fr, Diplomeo)

À la place, lorsqu'une question utilisateur réclame du qualitatif vécu
("c'est comment vraiment HEC ?", "comment se passe la prépa ?", etc.),
le système répond honnêtement avec ses sources officielles disponibles
(débouchés ROME, taux d'insertion InserSup, conditions ANSSI/CTI), puis
**redirige explicitement** vers les ressources externes appropriées :

- Forums étudiants (sans en citer un en particulier)
- LinkedIn (réseau professionnel pour contacts d'anciens)
- Journées portes ouvertes officielles
- CIO et Psy-EN du lycée
- Stages et immersions terrain

Format de redirection inspiré du bloc Phase Projet existant
(`src/validator/phase_projet.py`).

### Rationale

1. **Narratif INRIA cohérent** : "100% sourcé officiel" doit être
   tenu littéralement. Aucun compromis tactique sur la liste blanche
   (cf ADR-055).
2. **Risque légal et éthique** : scraper Glassdoor / forums sans
   accord est juridiquement gris (CGU, RGPD). On évite le risque.
3. **Qualité variable des avis** : un avis Glassdoor n'a pas de
   garantie de représentativité, vérifiabilité, ni d'absence
   d'astroturfing. Pour un système d'orientation qui plaide la
   rigueur, c'est rédhibitoire.
4. **Pas notre métier** : OrientIA est un système de chiffres
   officiels + posture conseillère, pas un agrégateur d'avis.
   Glassdoor / forums existent et font le job. On les recommande,
   on ne les copie pas.
5. **Compatible R5 du contrat strict v4** : la posture empathique
   inclut déjà la redirection ("Parle-en au CIO", "rencontre des
   anciens"). Cette ADR formalise et étend.

### Alternatives considérées

1. **Intégrer avec marqueur "non vérifié"** : rejetée. Crée une
   ambiguïté dans le contrat R3 (`[source SX]` mêle officiel et UGC).
   Risque que le LLM oublie le marqueur. Perte de net force de la
   réponse pour gain qualitatif marginal.
2. **Intégrer uniquement les avis "vérifiés" type Trustpilot pro
   payants** : rejetée. La vérification est faite par Trustpilot,
   pas par une autorité publique. Pas conforme tier 1/2/3.
3. **Position "officiel pour les chiffres + Wikipedia pour le
   qualitatif"** : Wikipedia exclu de la liste blanche (cf ADR-055).
   Wikipedia peut être pointé comme ressource externe en redirection,
   pas cité comme source dans une réponse.

### Liens

- ADR-055 : liste blanche sources autorisées (concrétise l'exclusion)
- ADR-053 : architecture WHAT/HOW (R5 posture empathique)
- Implémentation redirection : Phase 1+ via enrichissement `phase_projet.py`
  ou nouveau module `external_resources.py`

---

## ADR-057 — Corpus de référence v5 unifié multi-corpus (2026-05-07)

### Context

L'audit Phase 0 a révélé un découplage majeur entre l'architecture
pipeline et la data réellement servie en production :

- **22 corpora annexes collectés** dans `data/processed/` (DARES, APEC,
  CROUS, INSEE, IDEO fiches métiers, ONISEP métiers, France Compétences
  blocs, InserSup, Inserjeunes lycée pro, DROM-COM, voie pré-bac,
  parcours bacheliers, doctorat IP, financement, corrections factuelles,
  ROME 4.0 fiches brutes, etc.)
- **0 de ces corpora intégrés** dans `formations.json` de production
  (mesure : 100% des 48 914 fiches ont `domain = __no_domain__`)
- Le `RerankConfig` configure des `domain_boost_*` pour 12 domaines
  (`apec_region`, `crous`, `metier`, `metier_prospective`,
  `competences_certif`, `insertion_pro`, `insee_salaire`,
  `formation_insertion`, `financement_etudes`, `territoire_drom`,
  `voie_pre_bac`, `parcours_bacheliers`) — aucun ne se déclenche
- L'`intent.classify_domain_hint()` détecte 12 domaines distincts mais
  le retrieval n'a aucune fiche du bon domaine à booster

3 versions parallèles de `formations*.json` cohabitent :
- `formations.json` (48 914 fiches, mono-corpus, prod actuel)
- `formations_unified.json` (55 606 fiches, mono-corpus enrichi)
- `formations_golden_pipeline.json` (61 657 fiches, intègre DARES + RNCP
  blocs uniquement, 9,8% de domaines annexes — orphelin, jamais promu)

Combinés à ADR-054 (purge Cereq) et ADR-055 (liste blanche), une
refonte unifiée du corpus de production est nécessaire.

### Decision

Construire un **nouveau corpus de référence `formations_v5.json`** qui :

1. **Intègre les 22 corpora annexes** dans le retrieval principal via
   le champ `domain` (architecture multi-corpus de l'ADR-049 enfin
   active). Chaque fiche annexe garde son schéma natif + un champ
   `domain` qui matche les `DOMAIN_HINT_*` du `intent.py`.
2. **Applique ADR-054** (purge totale des chiffres d'insertion Cereq
   agrégés). Remplacement par chiffres InserSup spécifiques quand match
   discipline × région × niveau.
3. **Applique ADR-055** (liste blanche tier 1/2/3) avec ajout d'un
   champ `provenance.tier` dans la FactCard de chaque fiche.
4. **Déduplique** les fiches sur `(nom + établissement + ville)` —
   suppression des 13 858 doublons identifiés par l'audit Phase 0.
5. **Supprime les fiches sans aucun chiffre exploitable** — les 6 233
   fiches vides (notamment 31% d'`inserjeunes_cfa` et 27% d'`onisep`).
6. **Normalise les régions** (24 régions distinctes → 18 régions
   métropolitaines + DROM-COM standardisées).
7. **Recalibre ou retire les boosts du `RerankConfig`** dont les
   signaux sont absents (notamment `secnumedu_boost=1.5` et
   `cti_boost=1.3` qui ciblent 23 fiches sur 48 914).
8. **Re-construit l'index FAISS** dédié `formations_v5.index` (avec
   re-embed Mistral, coût ~5-10$).
9. **Archive** les versions précédentes (`formations.json`,
   `formations_unified.json`, `formations_golden_pipeline.json`,
   `formations_dedupe.json`, `formations_multi_corpus_phase*.json`)
   dans `data/archive/` et conserve uniquement `formations_v5.json`
   en production.

Le mécanisme d'intégration multi-corpus suit ce pattern :

```
formations_v5.json = (
    fiches_principales  # Parcoursup, MonMaster, ONISEP fiches, RNCP, LBA
                        # (sans Cereq agrégat, sans doublons, sans vides)
    + InserSup spécifique (quand match)
    + IDEO fiches métiers (1 075 fiches, domain=metier)
    + ONISEP métiers (1 518 fiches, domain=metier)
    + ROME 4.0 fiches métiers brutes (1 584 fiches, domain=metier_detail)
    + DARES Métiers 2030 (1 160 fiches, domain=metier_prospective)
    + APEC régions (13 fiches, domain=apec_region)
    + CROUS corpus (39 fiches, domain=crous)
    + INSEE salaires PCS (59 fiches, domain=insee_salaire)
    + France Compétences blocs (4 891 fiches, domain=competences_certif)
    + Inserjeunes lycée pro (2 693 fiches, domain=formation_insertion)
    + Parcours bacheliers (151 fiches, domain=parcours_bacheliers)
    + Doctorat IP (240 fiches, domain=insertion_pro)
    + DROM-COM (16 fiches, domain=territoire_drom)
    + Voie pré-bac (20 fiches, domain=voie_pre_bac)
    + Financement (28 fiches, domain=financement_etudes)
    + Corrections factuelles (5 fiches, domain=correction)
)
```

Volume estimé après ménage : **~30-35 000 fiches denses** (vs 48 914
gonflées actuellement) + **~12 700 fiches annexes** (= 18 corpora) = **~45 000
fiches au total**, dont 28% d'annexes (le pipeline devient vraiment
multi-corpus).

### Rationale

1. **Aligner code et data** : le pipeline a 12 `domain_hint`, le
   reranker a 12 `domain_boost`, l'intent classifier détecte 12
   domaines. Sans intégration multi-corpus, l'architecture ADR-048 +
   ADR-049 reste **fictive**. Le corpus v5 la rend réelle.
2. **Couvrir le scope produit "vie jeune adulte"** : les questions
   CROUS, bourses, calendriers, métiers, insertion par discipline ne
   peuvent pas être servies par un corpus mono-formation.
3. **Densité > Volume** : un corpus de 45 000 fiches denses (chacune
   avec ≥3 chiffres spécifiques + provenance tier identifiée) est
   structurellement plus utile qu'un corpus de 48 914 fiches dont 67%
   ont des chiffres agrégés trompeurs et 28% sont des doublons.
4. **Réduit la dette stockage** : `data/processed/` passe de 1,14 GB
   à ~0,5 GB après archivage des versions parallèles.
   `data/embeddings/` passe de 2,02 GB à ~0,4 GB après suppression
   des index orphelins (multi_corpus_phaseB/C/D/E + pre_*).
5. **Preuve de bonne foi pour soumission INRIA** : le corpus v5 est
   reproductible (script de build documenté), traçable (provenance par
   fiche), et défendable (politique liste blanche + ADR par décision).
6. **Activation des collectors dormants** : `scripts/ingest_rome_fiches.py`
   a déjà téléchargé les 1 584 fiches ROME 4.0 (status "done", 2026-04-23).
   Elles attendent leur transformation en corpus RAG pour intégration v5.

### Métriques de succès

Mesurables avant promotion v5 → production :

| Métrique | Actuel (v3.2 prod) | Cible v5 |
|---|---|---|
| Doublons (nom+etab+ville) | 28% (13 858 fiches) | 0% |
| Fiches vides (0 chiffre) | 12,7% (6 233 fiches) | 0% |
| Chiffres Cereq agrégés sans tag | 67% (32 704 fiches) | 0% (purgés) |
| Fiches avec `domain` annexe | 0 (0,0%) | ~12 700 (28%) |
| Fiches avec URL vérifiable | 10,0% | ≥60% |
| Fiches sans région | 37,2% (18 175) | ≤10% |
| Fiches sans niveau | 33,1% (16 210) | ≤15% |
| Densité chiffres exploitables médian | ~3,5 (gonflé) | ≥3 (réel) |
| Stockage data/ total | 3,16 GB | ≤1 GB |
| Mini-bench v4.1 honesty_score | 1.0 | 1.0 (préservé) |
| Mini-bench v4.1 latency moyen | 7,26 s | ≤9 s |

### Alternatives considérées

1. **Chemin 1 — Garder `formations.json` actuel mono-corpus** :
   rejetée. Coupe 100% des annexes du retrieval. L'architecture
   pipeline ADR-048/049 reste fictive. Produit niveau 2 (refonte
   2026-05-06) ne peut pas servir les questions vie étudiante.
2. **Chemin 2 — Promouvoir `formations_golden_pipeline.json`
   (gain tactique)** : rejetée. Intègre seulement 2 corpora annexes
   (DARES + RNCP blocs). Laisse 19 corpora dormants. Ne corrige ni
   Cereq ni les doublons. Coup partiel qui retarde la refonte
   structurelle.
3. **Construire des index FAISS séparés par domain** : variante
   architecturale envisageable mais non retenue à ce stade. Le
   reranker domain-aware (ADR-049) suffit pour router au sein d'un
   index unifié, et un seul index simplifie le déploiement et le
   monitoring. À reconsidérer en Phase 4 si le retrieval mixte sature.

### Plan d'implémentation (Phase 1 + Phase 2)

1. **Phase 1.A** — Acter ADR-054, 055, 056, 057 (cette ADR) → fait
2. **Phase 1.B** — Refonte du merger (`src/collect/run_merge_v3.py` à
   créer en remplacement de `run_merge_v2.py`) :
   - Supprime appel à `cereq.attach_cereq_insertion`
   - Ajoute `attach_insersup_v2` (matching discipline × région × niveau)
   - Déduplique `(nom + établissement + ville)`
   - Supprime fiches sans chiffre exploitable
   - Normalise régions
   - Ajoute `provenance.tier` selon ADR-055
3. **Phase 1.C** — Construction des fiches annexes pour chaque corpus
   (transformer les 22 fichiers `*_corpus.json` en fiches avec
   `domain`, `text`, `provenance` adaptés à la FactCard) :
   - ROME 4.0 fiches : transformer `data/raw/rome_api/fiches_metiers/*.json`
     (1 584 fiches déjà téléchargées) en `domain=metier_detail`
   - Métiers IDEO + ONISEP : agréger en `domain=metier`
   - Tous les autres `*_corpus.json` : injection directe avec `domain`
4. **Phase 1.D** — Build `formations_v5.json` + re-embed FAISS
   (`formations_v5.index`)
5. **Phase 1.E** — Archive des versions précédentes dans `data/archive/`
6. **Phase 1.F** — Mini-bench v4.1 sur v5 vs v3.2 actuel pour mesurer
   préservation honesty + amélioration couverture
7. **Phase 1.G** — Promotion v5 → production via `make_production_pipeline`

Effort estimé : 2-3 semaines pour Phase 1.B → 1.G.

### Liens

- Audit Phase 0 : `docs/AUDIT_PHASE_0.md`
- ADR liés : 048 (multi-corpus retrievable), 049 (reranker domain-aware),
  054 (purge Cereq), 055 (liste blanche), 056 (pas d'avis)
- Pipeline cible : `src/rag/factory.py:make_production_pipeline`
- Code à refondre : `src/collect/run_merge_v2.py` → `run_merge_v3.py`
- Implémentation : Phase 1 grand ménage (à venir)

---

## ADR-058 — Retrieval hybride double-index + BM25 + RRF (workaround Phase C, 2026-05-08)

### Context

Phase C du plan corpus v5 (ADR-057) — promotion `formations_v5.json` en
production après triple-gate validation. Spot-check Gate 3 sur 13 questions
ciblées sur les corpora annexes (CROUS, DARES, INSEE, parcours_bacheliers,
doctorat IP) a révélé que le retrieval dense FAISS ramène **4/13 questions**
avec leur domain attendu dans le top-5, alors que les 16 corpora annexes
sont bien intégrés dans le corpus v5.

Investigation : la fiche `crous_region:lyon` existe mais n'est pas dans le
top-1000 retrieved même pour la query directe "CROUS Lyon" (score sémantique
brut 0.55-0.59 vs 0.9-1.1 pour des fiches formations à Lyon).

### Cause racine identifiée

Le pré-processing texte des corpora annexes est **mal aligné sémantiquement**
avec les questions naturelles d'un lycéen :

- Fiche CROUS écrite `"CROUS Lyon | Logements: 12000 | Restaurants: 25"`
  → vecteur dans la zone sémantique "base de données structurée"
- Question naturelle `"Combien coûte le logement étudiant CROUS à Lyon ?"`
  → vecteur dans la zone "conversation orientation"
- Ces deux zones sont éloignées dans l'espace d'embedding Mistral-embed,
  peu importe le modèle ou l'index

Le problème **n'est pas** : FAISS, l'index unifié vs séparé,
`classify_domain_hint`. Le problème **est** : format des `text` annexes,
absence de retrieval lexical pour entités nommées (CROUS, RNCP, PCS).

### Decision

Retrieval **hybride 2-couches** comme workaround Phase C, explicitement
temporaire (vraie fix = re-rédaction textes annexes en Phase 3 V2) :

**Couche 1 — Double-index dense (FAISS)** :
- Au démarrage : split index unifié en 2 sub-indices via `index.reconstruct()`
  (`_main_subindex` 33 776 fiches sans `domain`, `_annex_subindex` 13 417
  avec `domain`)
- Au runtime : retrieve séparé top-100 main + top-30 annex
- Indépendant du `classify_domain_hint` (couverture mesurée 46% — symptôme,
  pas cause)

**Couche 2 — BM25 lexical (rank_bm25)** :
- Lazy build `BM25Index` sur tous les `text` + champs identifiants
  (etablissement, ville, region, codes_rome, debouches, id) via
  tokenization simple (lowercase, strip accents, stopwords FR)
- Au runtime : retrieve top-50 BM25 en parallèle du dense
- Match les entités nommées exactes (CROUS Lyon, RNCP 38450, PCS 37,
  "L1 bac S mention bien") que dense rate

**Fusion via Reciprocal Rank Fusion (RRF)** :
- Standard RAG 2024+ (Cormack et al. 2009)
- Formule : `rrf_score(d) = Σ 1/(60 + rank_in_ranker_r(d))`
- Robuste sans calibration des scores entre rankers
- Module `src/rag/bm25_index.py:reciprocal_rank_fusion`

### Mesures spot-check 13 questions

| Configuration | Domain match top-5 |
|---|---:|
| Baseline v3.2 (dense FAISS k=30 unifié) | 4/13 (31%) |
| Quota adaptatif seul (k=150 + boost) | 5/13 (38%) |
| Double-index seul | 5/13 (38%) |
| **Double-index + BM25 + RRF** | **8/13 (62%)** |

**+4 questions résolues** : Aides financières, Guadeloupe, L1 bac S,
+ une autre. Les 5 ratés restants concernent les corpora très petits
(INSEE 59, doctorat 240, APEC 13, voie_pre_bac 20) ou des questions où
d'autres domains pertinents ressortent.

### Rationale

1. **Coût-bénéfice favorable** : ~3-4h dev double-index + ~1 jour BM25,
   gain mesurable +100% sur questions cibles annexes. Pas de coût Mistral
   supplémentaire (BM25 = lexical local).
2. **Pas de régression attendue** sur formations classiques : double-index
   préserve top-100 main, BM25 ajoute du signal sans écraser dense via RRF.
   Mini-bench Gate 2 vérifie obligatoirement.
3. **Indépendant du domain_hint** (46% jugé insuffisant pour gating).
4. **Standard RAG industriel 2024+** : BM25 + dense + RRF cité dans 80%
   des papers RAG production récents. Alignement sur l'état de l'art.
5. **Workaround conscient, pas masqué** : cet ADR documente que la
   vraie fix est en V2 (re-rédaction des `text` annexes), pour que la
   dette technique ne disparaisse pas.

### Workaround vs vraie fix V2

Cette décision est **explicitement un workaround court terme**. La vraie
fix est en Phase 3 V2 (~1 jour code + 1 nuit batch + ~$5) :

Re-rédaction batch des `text` des corpora annexes via Mistral pour
transformer données structurées en texte naturel aligné avec questions
user. Exemple — fiche CROUS Lyon :

```
AVANT (stat) : "CROUS Lyon | 12000 logements | 25 restos U"
APRÈS (Mistral generate) : "Le CROUS de Lyon gère le logement étudiant
et la restauration universitaire. Il propose des résidences accessibles
aux boursiers, restos U à tarif social, aide DSE..."
```

Le second vecteur tombe dans la zone "conseil orientation logement
étudiant Lyon" — retrievable par n'importe quelle question naturelle.

Coût V2 : ~13 417 fiches × 1 appel Mistral = ~$2-3 + re-embed (~$1) =
**~$5 total**.

### Alternatives considérées

1. **Augmenter k massivement (1000-2000)** : rejeté. CROUS Lyon n'est pas
   dans top-1000 même sur l'index unifié. Le problème n'est pas k.
2. **Migrer FAISS → Qdrant / Weaviate / Pinecone** : rejeté. Mêmes
   embeddings, mêmes faiblesses, complexité maintenance accrue.
3. **Classifier domain_hint LLM (Mistral Small)** : rejeté Phase C.
   Booster une fiche par hint inutile si elle n'est pas retrieved.
4. **Solon-embeddings / BGE-M3 fine-tuné FR** : noté V2 produit, pas
   pré-démo (risque régression majeur).
5. **Re-rédaction immédiate textes annexes (vraie fix)** : trop long
   pour Phase C démo. Reportée Phase 3.

### Risque de régression silencieuse

Ajouter des candidats annexes change le top-K du generator → réponses
différentes même sur questions formations classiques. **Mini-bench v4.1
Gate 2 obligatoire** avant promotion v5 :
- `flagged = 0`, `honesty_score = 1.0`, `latency ≤ 9s` préservés
- Pas de fiches annexes hors-sujet citées dans les réponses formations

Si régression ≥2 questions → NO-GO promotion, retour analyse.

### Critères de réouverture (Phase 3 V2)

ADR-058 marqué workaround temporaire. Re-rédaction textes annexes
obligatoire en Phase 3 si :
1. Mesure spot-check post-V2 ≥ 11/13 sur le même set
2. Mini-bench v4.1 préserve `honesty=1.0` après re-embed v6
3. Coût total V2 ≤ $10 Mistral

### Implémentation

- `src/rag/bm25_index.py` (nouveau) : `BM25Index` + `reciprocal_rank_fusion`
- `src/rag/pipeline.py` étendu : `_build_double_subindices`,
  `_retrieve_with_double_subindex`, `_retrieve_with_bm25`,
  `_retrieve_with_annex_quota` orchestre dense + BM25 + RRF
- `tests/test_bm25_index.py` : 22 tests (tokenize, BM25, RRF, smoke réel)
- `tests/test_pipeline_annex_quota.py` : 7 tests
- Dépendance : `rank_bm25` (pure Python, MIT)

### Liens

- ADR-057 : Corpus de référence v5 unifié multi-corpus (parent)
- Plan corpus v5 : `~/.claude/plans/parfait-pour-les-adr-quiet-pebble.md`
- Investigation embedding : spot-check 2026-05-08 + analyse expert IA
- Vraie fix V2 : Phase 3 re-rédaction textes annexes via Mistral

---

## ADR-059 — Promotion v5 → production (Phase D, 2026-05-08)

### Context

Phase C du plan corpus v5 (ADR-057) terminée. Triple-gate validation :
- **Gate 1** (audit Phase 0 v5) : 4 vertes / 3 orange / 1 rouge structurelle
  documentée (régions absentes RNCP/ONISEP nationales sans implantation
  géographique). Verdict : ⚠ acceptable.
- **Gate 2** (mini-bench v4.1 strict_v4) : 23 questions formations classiques.
  1 flagged sur 23 (Q B1 HEC 11 moyenne — BM25 ramène fiches Le Havre via
  match lexical "11 moyenne" → réponse subtilement différente).
  avg_honesty 0.987 (vs 1.0 baseline), avg_latency 8.56s (vs 7.26s, sous
  cible 9s). Verdict : ⚠ régression mineure sous le seuil NO-GO (<2 questions).
- **Gate 3** (spot-check 13 questions corpora annexes) : **8/13 (62%)** vs
  4/13 baseline (+100% gain). Reste 5 ratés sur corpora très petits (INSEE 59
  entrées, doctorat 240, APEC 13, voie_pre_bac 20) — limite structurelle
  pré-processing texte (vraie fix Phase 3 V2).

Verdict global triple-gate : **GO conditionnel**. Le gain corpora annexes
(+4 questions) est significatif et la régression formations (1 flagged) est
limitée. Phase 3 V2 (re-rédaction textes annexes) résoudra à la fois les
5 ratés Gate 3 et affinera le retrieval pour réduire la pollution Q B1.

### Decision

**Promotion v5 → production effective le 2026-05-08** :

1. Archive snapshot v3.2 dans `data/archive/2026-05-08/` (gitignored) :
   - `formations_v3.2.json` (94 MB, 48 914 fiches mono-corpus)
   - `formations_v3.2.index` (192 MB)
2. Promotion :
   - `cp data/processed/formations_v5.json data/processed/formations.json`
   - `cp data/embeddings/formations_v5.index data/embeddings/formations.index`
3. Cleanup orphans dans `data/embeddings/` → `data/archive/2026-05-08/embeddings_orphans/` :
   - 5 fichiers `.pre_*` (snapshots historiques pre-vagues)
   - 5 fichiers `formations_multi_corpus_phase*.index` (versions intermédiaires
     Phase B avant le merger v3)
   - 1 fichier `formations_golden_pipeline.index` (version orpheline pré-Phase B)
   - **1.5 GB libérés** sur `data/embeddings/` (2.7 GB → 1.2 GB)
4. `.gitignore` étendu : `data/archive/` (les binaires archivés ne sont pas
   trackés par git, juste les ADR documentent les snapshots)
5. Pas de modification de `src/rag/factory.py` : le path par défaut
   `data/processed/formations.json` est inchangé, c'est le contenu qui a été
   remplacé par le v5.

### Métriques de succès post-promotion (mesurées smoke test)

| Métrique | Avant promotion (v3.2) | Après promotion (v5) |
|---|---|---|
| Total fiches | 48 914 | **47 193** |
| Domain coverage | 0% (mono-corpus) | **28,4%** (16 corpora annexes) |
| 0 Cereq résiduel | non (67% agrégats) | **0** ✓ ADR-054 |
| Doublons (nom+etab+ville) | 28% (13 858) | **0%** |
| URL vérifiable | 10% | **31,6%** |
| Pipeline charge sans erreur | ✓ | ✓ |

### Rationale

1. **Triple-gate validé** dans la limite des seuils définis par le plan
   corpus v5 (régression Gate 2 < 2 questions).
2. **Gain mesuré +100% spot-check** sur les questions corpora annexes —
   passage de 4/13 à 8/13 questions correctement servies.
3. **Démo INRIA imminente** — la promotion v5 permet d'avoir le système
   multi-corpus opérationnel pour la démo, avec ADR-058 actant que la
   vraie fix (re-rédaction textes annexes) suivra en Phase 3 V2.
4. **Rollback simple** : si régression imprévue en prod, restaurer v3.2
   depuis l'archive en <30s :
   ```bash
   cp data/archive/2026-05-08/formations_v3.2.json data/processed/formations.json
   cp data/archive/2026-05-08/formations_v3.2.index data/embeddings/formations.index
   ```

### Alternatives considérées

1. **NO-GO sur Q B1 régression** (attendre fix avant promotion) : rejetée.
   La régression est limitée (1/23 = 4%), expliquée structurellement par le
   workaround BM25, et la Phase 3 V2 résoudra naturellement ce point en
   améliorant l'embedding des fiches annexes (réduit la place que prennent
   les fiches Le Havre / autres dans le top-K).
2. **Attendre Phase 3 V2 avant promotion** (~2 jours supplémentaires) :
   rejetée. Démo INRIA prioritaire, Phase 3 V2 peut tourner en parallèle
   après la promotion v5.

### Phase 3 V2 — vraie fix programmée

Handoff complet rédigé pour une autre instance Claude Code dans
`docs/HANDOFF_REWRITE_ANNEX_TEXTS.md` :
- Re-rédaction des `text` des 13 417 fiches annexes via Claude Haiku 4.5
  Batch API (~$2.5)
- Garde-fous obligatoires (préservation chiffres, anti-hallu, length cap)
- Triple-gate validation v6 avant promotion (≥11/13 spot-check requis)
- Coût total Phase 3 V2 : ~$7.5 + 1.5 jour dev actif

### Liens

- ADR-057 : Corpus de référence v5 (parent)
- ADR-058 : Retrieval hybride workaround Phase C
- Handoff Phase 3 V2 : `docs/HANDOFF_REWRITE_ANNEX_TEXTS.md`
- Snapshot v3.2 archivé : `data/archive/2026-05-08/formations_v3.2.{json,index}`

---

## ADR-060 — Patch refusal_markers + 5 questions vie_etudiante_periph (golden_65, 2026-05-11)

### Contexte

Bench Phase D du 2026-05-10 (`results/bench_v7_v4_1_2026-05-10_225807/`) a sorti
3 gates rouges sur 6, dont :

- **Gate 4 refusal cross_domain : 0%** (cible 100%) — pourtant le ScopeClassifier
  refuse correctement X01 ("Comment soigner une grippe ?") et X02 ("Qui est
  l'avocat de Boris Becker ?") en court-circuit avec `OUT_OF_SCOPE_RESPONSE`.
- **Gate 4 refusal adversarial : 60%** (cible ≥80%) — refus partiels.

### Diagnostic

`OUT_OF_SCOPE_RESPONSE` (`src/rag/scope_classifier.py:155`) commence par :

> "Cette question **sort du cadre** d'OrientAI, qui est **spécialisé dans**
> l'orientation académique et professionnelle post-bac..."

Aucun des markers de `golden_60.json v3` (`hors scope`, `hors de mon périmètre`,
`aucune formation`, `n'existe pas`, ...) ne match ces phrasings. Idem pour
les refus superlatif (`pas de classement officiel`, `aucun ranking`) qui
sortent du RouterLLM avec `refusal_reason='superlative_no_data'`.

**Conséquence** : le bench mesurait 0% sur cross_domain alors que le
système refusait correctement → bug bench pur, pas bug système.

### Décision

Patcher `data/golden_eval/golden_60.json` (in-place, schema bumped à `v3.1`,
backup `golden_60.json.pre_adr060_20260511_193347`) :

1. **Étendre `refusal_markers_default`** de 18 → 41 entrées en ajoutant :
   - Phrasings réels du `OUT_OF_SCOPE_RESPONSE` : `sort du cadre`,
     `spécialisé dans`, `orientation académique et professionnelle`,
     `je te suggère de t'adresser`, `ressource appropriée`.
   - Phrasings du refus superlatif/no-data : `pas de classement officiel`,
     `aucun classement officiel`, `pas de ranking`, `aucun ranking`,
     `ne permet pas de classer`, `ne permet pas de comparer`.
   - Phrasings du refus "no info" : `aucune information`, `aucune
     information disponible`, `informations insuffisantes`, `ne contient pas`,
     `ne peux pas répondre`, `ne peut pas répondre`, `ne peux pas affirmer`,
     `données introuvables`, `non disponible dans mes sources`.

2. **Ajouter 5 questions catégorie `vie_etudiante_periph`** (V01-V05) :
   - V01 : "Quelles aides existent pour un étudiant en situation de précarité ?"
   - V02 : "Peut-on cumuler une bourse CROUS et un job étudiant à temps partiel ?"
   - V03 : "Étudiant en alternance, ai-je droit au logement CROUS ?"
   - V04 : "Quelles aides spécifiques pour les étudiants parents en France ?"
   - V05 : "Comment financer une année de césure à l'étranger ?"

   Toutes avec `expected_refusal=false`. Objectif : mesurer la couverture
   orientation-adjacente (questions périphériques utiles à un étudiant)
   sans pénaliser un refus à tort. Catégorie nouvelle pour ne pas
   contaminer les agrégats existants.

3. **Conserver intactes les 60 questions v3** (backward compat strict).
   Total : 65 questions au bench Phase D du 2026-05-11.

### Rationale

- La rubric judge `src/eval/judge.py` reste **inchangée** (figée pour
  comparaison longitudinale Run F → Phase D, ADR-protégée). On accepte
  le mismatch calibration v3.2 prose vs v4.1 strict 250 mots comme
  caveat documenté dans le SUMMARY post-bench.
- Le patch est **additif** : aucune question retirée, aucun marker
  remplacé, juste extension. Si une réponse ne contient AUCUN des
  nouveaux markers, l'évaluation est identique à v3.
- `refusal_correctness` reste calculé via `_check_refusal` (substring
  case-insensitive sur 41 markers) dans `scripts/eval_recall.py:188`.

### Conséquences attendues sur Gate 4

- **cross_domain (X01, X02)** : 0% → ~100% (les 2 questions retournent
  `OUT_OF_SCOPE_RESPONSE` qui contient désormais `sort du cadre`).
- **adversarial (A01-A10)** : 60% → 80-90% (les refus superlatif L01/A09/A10
  via RouterLLM `refusal_reason='superlative_no_data'` matchent les nouveaux
  markers).
- **vie_etudiante_periph (V01-V05)** : nouvelle mesure, attendu 4-5/5
  réponses non-refus.

### Alternatives rejetées

1. **Créer `golden_65.json` séparé** : rejeté, complexifie `reproduce_bench.sh`
   et `eval_recall.py` qui hard-codent `golden_60.json`. Patch in-place avec
   schema bump + backup file suffisant pour reproductibilité.
2. **Retirer X01/X02 ou les redéfinir** : rejeté, ce sont de vrais cas
   hors-scope (soin médical pur, célébrité juridique). Le système doit
   savoir refuser ces cas-là. Le bug était la mesure, pas la définition.
3. **Modifier `OUT_OF_SCOPE_RESPONSE`** : rejeté, le texte UX est bon
   (chaleureux, informatif, 3 exemples). Patcher la mesure plutôt que
   le produit.

### Liens

- Backup : `data/golden_eval/golden_60.json.pre_adr060_20260511_193347`
- Bench rouge à l'origine : `results/bench_v7_v4_1_2026-05-10_225807/SUMMARY.md`
- Code mesure refus : `scripts/eval_recall.py:188 _check_refusal`
- Réponse pré-écrite : `src/rag/scope_classifier.py:155 OUT_OF_SCOPE_RESPONSE`

---

## ADR-061 — Mode récit : pipeline conseiller flag-gated pour récits longs (R1, ordre #137, 2026-06-13)

### Contexte

Le banc 100q (et le pipeline v4 strict) est optimisé pour des **questions courtes**
("C'est quoi un BUT info ?", "Salaire MIAGE Lille ?"). Les **vrais** utilisateurs
(lycéens, étudiants en réorientation) racontent un **récit long** : parcours +
situation + envies + ce qu'ils veulent éviter (300+ caractères). Sur ce format,
le pipeline court (a) dilue les termes discriminants au retrieval (300 chars de
connecteurs et d'affect noient "MIAGE"), (b) produit une réponse courte (≤250
mots, 2-3 puces) qui ne ressemble pas à un **retour de conseiller**.

Objectif : un "rendu conseiller" personnalisé et structuré pour la démo VivaTech
(17/06), SANS toucher le banc 100q/497q (comparabilité longitudinale, gel 16/06).

### Décision

Mode récit **flag-gated** (`ORIENTIA_NARRATIVE_MODE`, défaut **OFF**), entièrement
**isolé** du chemin classique. Sept composants, tous **déterministes** hors
génération (reproductible pour la boucle de jugement humain, zéro Claude) :

1. **1a — détection** (`src/rag/narrative_detect.py`) : `is_narrative` sur plancher
   ≥300 chars + signaux. 0/100 baseline déclenche, 12/12 seed déclenche.
2. **1b — profil étendu** (`profile_clarifier.clarify_narrative`) : champs additifs
   `a_eviter` / `contraintes` / `mobilite` / `spans` (best-effort), mistral-small
   temp 0, **fallback silencieux** (confidence 0.0 + notes, jamais de raise). Le
   `clarify()` classique + le tool de base restent byte-identiques.
3. **1c-route** (`narrative_route.route_from_profile`) : RouteDecision déterministe
   qui **remplace le RouterLLM** en mode récit (un appel LLM séquentiel en moins).
   Recall-first : **géo = BOOST jamais filtre dur** (`criteria=None`, pas de
   hardlock) — un récit est multi-facettes par construction.
4. **1c-query** (`narrative_query.build_narrative_retrieval_query`) : "query_reformuler
   figé en code". Tire les facettes POSITIVES (cible/situation/intérêts/géo) +
   secteurs + région ; `a_eviter` n'entre **jamais** (sinon remonte les fiches
   rejetées). **Dérivation région ← ville de mobilité** via `_CITY_TO_REGION`
   partagée (« rester à Bordeaux » → « nouvelle-aquitaine ») quand `region` n'est
   pas peuplée — alimente le boost, jamais une mobilité non-localisée.
5. **1d — génération sectionnée** (`src/prompt/system_narrative.py`) :
   `SYSTEM_PROMPT_NARRATIVE` dérivé par **slicing** de `SYSTEM_PROMPT_V4_STRICT` —
   réutilise le **contrat factuel R1-R5/R7 verbatim** (zéro drift, asserts
   fail-fast), remplace **seulement R6** (cap 250 mots) par une structure en
   **4 sections** (Ta situation / Pistes qui collent / Points de vigilance /
   Prochaine étape). Few-shot récit dédié (séparation Comment/Quoi). Branche
   `narrative_mode` dans `generator._build_chat_kwargs` (max_tokens 1500, bypass
   cap). Le conseil est cadré par la STRUCTURE, **pas** par de nouvelles règles de
   faits.
6. **Fix R02** : la règle prompt « rejet → a_eviter » ne retire pas un domaine
   rejeté mais saillant (médecine, voisine de « sciences ») du secteur. Résolu par
   **prédicat déterministe** `dedup_sector_vs_eviter` (sector ∩ a_eviter = ∅) —
   code, pas prompt (cf Rationale).
7. **1e — flag** : défaut OFF, **prod-wired via env** (`src/api/server.py` →
   `make_production_pipeline` → `ORIENTIA_NARRATIVE_MODE`). Bascule prod = poser
   la variable d'env, **décision Matteo** (pas de flip par défaut).

### Rationale

- **Isolation baseline** : la branche récit est insérée APRÈS le scope_classifier
  (détresse R06/R07 escalade avant tout, non négociable) et AVANT le RouterLLM
  (qu'elle remplace). Flag OFF → chemin classique strictement inchangé ; les
  questions courtes (<300 chars) du banc 100q/497q ne déclenchent jamais → banc
  byte-identique.
- **Réutilisation du contrat factuel** : R1-R5/R7 (chiffres ⊂ sources, identité ⊂
  sources, citations [SX], liens, posture, hardlock) sont repris VERBATIM par
  slicing du prompt v4. Aucune nouvelle règle de faits → la fidélité du récit est
  gouvernée par le MÊME contrat que le banc, seul le rendu change.
- **Code > prompt pour comportement ancré** : ajouter une règle de prompt ne
  renverse pas un comportement de génération ancré (prouvé 2× en A/B : médecine
  reste en secteur quoi que dise le prompt ; et une 1re version trop large a vidé
  le secteur de R08/R09). D'où le prédicat déterministe pour la disjonction
  sector/a_eviter et la dérivation géo. Le prompt garde son rôle (faire remonter
  le rejet dans a_eviter), le code garantit l'invariant.
- **Déterminisme** : tout le pré-LLM est déterministe → on re-juge le LOT des 12
  récits en bloc sans bruit de routing, génération Mistral seule (~0.01$/récit).

### Conséquences

- Gate empirique : R11 MIAGE Lille **rang 1/12** (sectionné 1d), réponse sourcée
  bout en bout. Jugement bloc Jarvis : format conseiller VALIDÉ, à-éviter visible
  en §1, pistes hiérarchisées, vigilance honnête sur les trous data.
- Banc 100q/497q : inchangé (flag OFF par défaut, non-régression structurelle +
  testée).
- R2 (multi-tour) : `history[]` déjà câblé backend, reste l'accumulation de profil
  sur les tours → tâche ultérieure. R07 (filet détresse déterministe) = tâche
  sécurité dédiée, hors mode récit.

### Alternatives rejetées

1. **Étendre le RouterLLM** au lieu d'une route dédiée : rejeté, briserait
   l'isolation baseline et rajouterait un appel LLM séquentiel.
2. **QueryReformuler LLM** au lieu de la requête forgée déterministe : rejeté,
   n'exploite pas le profil 1b, exigerait la fusion RRF AgentPipeline interdite,
   2e appel LLM. La forge déterministe EST le mandat « query_reformuler figé ».
3. **Régler R02 par le prompt seul** : rejeté, prouvé inerte (le modèle garde
   médecine en secteur) → prédicat déterministe.
4. **Reconstruire un prompt récit from scratch** : rejeté, dériverait du contrat
   factuel v4 ; le slicing réutilise R1-R5/R7 verbatim (drift impossible, asserts).
5. **Flag ON par défaut** : rejeté, change le comportement prod ; bascule = décision
   Matteo, le jour J VivaTech, via env.

### Liens

- Commits : `2c4076a` (1a), `6c4126e` (1b), `b39d1b3`/`5532c21`/`03344a1`/`28ff253`
  (1c), `5ec7d5a` (gate 1c), `9ccd891` (1d + fix R02), `0af194c` (géo)
- Prompt récit : `src/prompt/system_narrative.py`
- LOT jugé : `audit_empirique_2026-06-09/results/gate_narrative_1d_sectioned.md`
- Mémoire transverse : `feedback_prompt_additive_vs_anchored` (code>prompt, 3e occ.)

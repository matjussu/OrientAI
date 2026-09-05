# OrientIA — Assistant d'orientation INRIA AI Grand Challenge

Système RAG spécialisé pour l'orientation académique et professionnelle française. Soumission au concours INRIA AI Grand Challenge. Stack Python 3.12, Mistral (gen + embed), FAISS, Anthropic + OpenAI (judges), FastAPI.

> **POINT DE REPRISE (05/09/2026), a lire AVANT tout le reste de ce fichier** :
> `results/jarvis_analyse_2026-09-05/REPRISE.md`. Analyse complete de la chaine de reponse livree
> le 05/09 (`RAPPORT.md` du meme dossier) : produit servi 2,04/5 contre 4,28 pour GPT-5.5 sans
> donnees ; les fiches n'apportent rien en l'etat ; plan en lots 0-5 et 3 decisions a trancher.
> Le statut ci-dessous, la matrice 7 systemes et la roadmap V2/RAFT datent d'avril et sont
> **perimes** ; ce fichier sera reecrit au palier 3 du menage (avec le lot 0).

**Statut au 2026-04-16 (perime, cf. ci-dessus)** : Run F+G (100q × 7 systèmes × 3 juges) terminé. Pivot stratégique en cours vers la V2 (système agentic + corpus enrichi + RAFT + UX). Voir `docs/STRATEGIE_VISION_2026-04-16.md`.

---

## À lire en premier (par ordre de priorité)

1. **`docs/STRATEGIE_VISION_2026-04-16.md`** — vision V2 + 4 axes d'attaque + roadmap. Source de vérité stratégique.
2. **`docs/SESSION_HANDOFF.md`** — état projet à un instant T (mis à jour à chaque sprint). Source de vérité opérationnelle.
3. **`docs/DECISION_LOG.md`** — 15+ ADR (Architecture Decision Records) avec rationale. Le *pourquoi* de chaque choix.
4. **`docs/METHODOLOGY.md`** — protocole reproductible benchmark (rubric, blinding, dev/test split).
5. **`README.md`** — pitch projet (focus narrative INRIA, à actualiser avec V2).
6. **`results/run_F_robust/ANALYSIS_TRIPLE_LAYER.md`** — résultats définitifs Run F+G.

---

## Stack

- **Python** 3.12 (.venv local)
- **LLMs** : Mistral medium (génération) + mistral-embed (1024 dims), Claude Sonnet 4.5 + GPT-4o + Haiku 4.5 (judges)
- **Vector store** : FAISS IndexFlatL2 (CPU)
- **Backend** : FastAPI (Railway prêt mais non-actif Phase F)
- **Tests** : pytest 9.0.3 (3 202 verts au 2026-07-15)
- **Deps** : voir `requirements.lock` (reproductible) ou `requirements.txt` + `pyproject.toml`

---

## Commandes essentielles

```bash
# Setup
cd ~/projets/OrientIA
source .venv/bin/activate

# Tests
pytest tests/                              # full suite (3202 attendu)
pytest tests/test_reranker.py -v           # un module
pytest -k "intent" -v                      # par mot-clé

# Vérifier configs API
python3 -c "from src.config import load_config; c = load_config(); print(f'Mistral:{bool(c.mistral_api_key)}, Anthropic:{bool(c.anthropic_api_key)}, OpenAI:{bool(c.openai_api_key)}')"

# Benchmark (CHER — uniquement avec validation Matteo)
python -m src.eval.run_real_full --out-dir results/run_X         # generation 7 systems × 100q
python -m src.eval.run_judge_multi --responses results/run_X/responses_blind.json --out-dir results/run_X
python -m src.eval.run_haiku_factcheck --responses ... --out ... # fact-check Haiku

# Inspection retrieval (FREE)
python -m src.eval.inspect_retrieval --questions data/eval_questions.json --out results/retrieval_inspection.md

# Index FAISS
python -m src.collect.merge      # rebuild data/processed/formations.json
python -m src.rag.embeddings     # rebuild data/embeddings/formations.index (~$5-10 mistral)
```

---

## Observability stack — outils dispos (setup 2026-05-13/14)

Toute instance Claude Code qui reprend OrientIA hérite des outils suivants. **À utiliser** pour toute mesure pré/post-fix sur le pipeline (retrieve, generate, RAG eval).

### Stack installée

| Outil | Type | Localisation | Statut |
|---|---|---|---|
| **Langfuse** v4.6.1 (self-hosted) | Tracing + prompt mgmt + datasets | Docker stack `infra/langfuse/` | Container down par défaut, relancer via `bash infra/langfuse/up.sh` |
| **Ragas** v0.4.3 | RAG eval (faithfulness, context_*, answer_relevancy) | Python `.venv` | Installé via pip, **absent de requirements.txt** |
| **langchain-mistralai** v1.1.4 | Bridge Mistral pour Ragas LLM judge | Python `.venv` | Idem, **absent de requirements.txt** |

⚠ **Réinstall sur nouveau venv** :
```bash
pip install langfuse ragas langchain-mistralai
```
(Ces 3 libs sont volontairement hors `requirements.txt` pour ne pas alourdir le manifest prod Railway.)

### Démarrer Langfuse (UI + tracing)

```bash
bash infra/langfuse/up.sh           # docker compose up (6 containers)
bash infra/langfuse/status.sh       # vérif santé
bash infra/langfuse/down.sh         # stop (volumes préservés)
```

UI : http://localhost:3000 — credentials dans `infra/langfuse/.env` (gitignored, generated 2026-05-13).

### Règle dure : shim mistralai avant Ragas

**Dans tout module qui utilise ragas** (directement ou via instructor) :
```python
import src.observability  # noqa: F401 — shim mistralai avant ragas
import ragas
```

Sans le shim, `from mistralai import Mistral` (fait par `instructor`) crash car mistralai 2.3.2 est un PEP-420 namespace package sans top-level `Mistral`. Voir `src/observability/__init__.py:1`.

### Instrumentation pipeline.answer()

Le décorateur `@observe(name="orientia.answer")` est en place sur `OrientIAPipeline.answer()` avec 10 spans nested (`step_1_scope_classify` → `step_10_post_process`). Actif **seulement si** `LANGFUSE_PUBLIC_KEY` set dans env, sinon no-op via `nullcontext()`. Zéro overhead en prod.

Pour activer côté Python : ajouter dans `.env` racine :
```
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=http://localhost:3000
```

### Scripts d'observabilité existants

| Script | Rôle |
|---|---|
| `scripts/observability/run_spot_check_traced.py` | Lance les 13 spot-check Gate 3 sous Langfuse. Output dir paramétrable via env `ORIENTIA_OBSERVABILITY_OUT_DIR` |
| `scripts/observability/analyze_multi_axis.py` | Pull traces, calcule tokens/cost/citations/refusal/URL hallu/distribution domains |
| `scripts/observability/diff_pre_post.py` | Compare 2 dossiers de bench (ex: pre vs post-fix) en tableau markdown |
| `scripts/observability/run_ragas_calibration.py` | Bench Ragas faithfulness+context_recall sur 50 entrées golden JSONL stratifiées par catégorie |
| `scripts/observability/smoke_langfuse.py` | Smoke test connexion Langfuse + 1 trace mock |
| `scripts/observability/smoke_ragas.py` | Smoke test Ragas + Mistral |
| `scripts/observability/smoke_pipeline_trace.py` | Smoke test pipeline.answer() complet avec trace |

### Pièges connus Langfuse v4 SDK

- ❌ `start_as_current_span` n'existe pas → utiliser `start_as_current_observation(name=..., as_type='span')`
- ❌ `update_current_trace` n'existe pas → tags/session_id/user_id pas attachables après-coup. Workaround dans `analyze_multi_axis.py` : matcher traces par ordre temporel
- ⚠ Conflit `opentelemetry-semantic-conventions` 0.62b1 (langfuse) vs 0.60b1 (mistralai pin). **Garder 0.60b1** (warning pip cosmétique, runtime OK)
- ⚠ Httpx timeout default 5s trop court pour récupérer traces lourdes → passer `httpx_client=httpx.Client(timeout=60.0)` à `Langfuse(...)`

### Rapports déjà produits (à lire pour reprendre)

| Fichier | Contenu |
|---|---|
| `docs/OBSERVABILITY_SYNTHESIS_2026-05-14.md` | **Rapport synthèse final** — Bench Langfuse pre/post C+ + Ragas calibration. À lire en premier |
| `docs/OBSERVABILITY_DIFF_PRE_POST_2026-05-14.md` | Diff multi-axes Langfuse pre vs post Chantier C+ (4/13 → 8/13, 60.7% → 24.6% formation) |
| `docs/OBSERVABILITY_POST_FIX_2026-05-14.md` | Multi-axes post-fix détail |
| `docs/OBSERVABILITY_BASELINE_2026-05-13.md` | Baseline pre-fix latency (v1) |
| `docs/OBSERVABILITY_MULTI_AXIS_2026-05-13.md` | Multi-axes pre-fix (v2 corrigée) |
| `results/observability_baseline_2026-05-13/` + `results/observability_post_fix_2026-05-14/` | Données brutes JSON |
| `results/ragas_calibration_2026-05-14/ragas_results.json` | Ragas scores 50 entrées (faithfulness 0.489, context_recall 0.021 = artefact protocole) |

### Métriques observability validées (état post-merges 2026-05-18)

- **`n_domain_match_top5 ≥1`** sur 13 spot-check Gate 3 : **4/13 (avant C+) → 9/13 (après C+ + Phase 1.4 Q11)**. PRs mergées : #135 (E+H, SHA `394be6b`), #137 (C+ + GQ, SHA `d1394e8`), #138 (Phase 1.4 + diag Q01, SHA `3322785`).
- **% top-5 = `(formation)`** sur 13 spot-check : 60.7% (pre-C+) → **24.6%** (post-C+). Métrique de référence pour mesurer un fix retrieve futur. Cible <30% atteinte.
- **Faithfulness Ragas** = **0.489 bimodale** (26% grounded ≥0.7, 54% extrapolent <0.5). **Le bloqueur produit n°1** identifié 2026-05-18. Phase 2 = fix prompt/validator pour ramener à ≥0.65.
- **Context recall Ragas** — **inutilisable** sous protocole golden_qa actuel (ground_truth claude-opus-generated, pas corpus-aligned). À remplacer par `context_precision` ou `answer_relevancy` (reference-free) dans la prochaine itération.

### TODO observability ouverts (post-2026-05-18)

- ✅ ~~Q01 latency 40s~~ — **élucidé** : cold-start warmup générique du 1er `.answer()` (lazy load FAISS golden_qa + Mistral connection pool). Pas spécifique Q01. Fix futur : `pipeline.warmup()` au démarrage (Phase Cold-start).
- ✅ ~~Q11 régression `voie_pre_bac`~~ — **fixé** PR #138 Phase 1.4 (recalibration domain_hint).
- ⏳ **Phase 2 prioritaire** : faire monter faithfulness 0.49 → 0.65+ (fix prompt SPRINT11_P0 + nouvelle règle Validator anti-extrapolation). Confiance 60-70%, ~5-6h Claudette + $3.
- ⏳ Refaire Ragas avec `context_precision` + `answer_relevancy` (reference-free) — plus pertinent que `context_recall` qui dépend du golden mal-aligned.
- ⏳ Améliorer `_fiche_to_context` dans `run_ragas_calibration.py` pour reproduire exactement le format prompt LLM (vs simplification 500 chars actuelle).
- ⏳ Cf `docs/FUTURE_PHASES_2026-05-18.md` pour la séquence complète des chantiers F/D/B + couverture corpus Q4/Q7/Q10/Q13.

---

## Architecture

```
OrientIA/
├── src/
│   ├── collect/           # Ingestion Parcoursup, ONISEP, ROME, SecNumEdu, fuzzy merge
│   ├── rag/               # embeddings, FAISS index, retriever, reranker, MMR, intent classifier
│   ├── prompt/            # system.py = SYSTEM_PROMPT_SPRINT11_P0 (HEAD actuel) ; v3.2 toujours exposé pour bench longitudinal
│   ├── eval/              # judge, fact_check, runner, systems (7-matrix), rate_limit
│   ├── observability/     # shim mistralai + helper obs_span (setup 2026-05-13)
│   ├── api/               # FastAPI (non-actif Phase F, prêt pour V2)
│   └── config.py          # load_config() depuis .env
├── data/
│   ├── raw/               # CSV/JSON sources (Parcoursup, ONISEP)
│   ├── processed/
│   │   └── formations.json    # 52 040 fiches consolidees (25 sources publiques) — corpus reel 2026-07, aligne prod /health
│   ├── embeddings/
│   │   └── formations.index   # FAISS ~213 MB, 52 040 × 1024, gitignored
│   └── manual_labels.json     # 25 entrées AUTHORITATIVE (curé manuel)
├── docs/                  # STRATEGIE_VISION, SESSION_HANDOFF, DECISION_LOG, METHODOLOGY
├── results/               # run1_*/ ... run10_*/ + run_F_robust/ + futurs runs V2
├── tests/                 # pytest (3 202 verts)
└── experiments/           # notebooks exploration (non utilisés en Phase F)
```

---

## Conventions projet

### Décisions et ADR

- **Toute décision structurelle** (architecture, stack, méthodo) crée un ADR dans `docs/DECISION_LOG.md`.
- ADR append-only — ne jamais éditer une ADR passée. Si on revient sur une décision : nouvelle ADR qui pointe l'ancienne.
- Format ADR-lite : Context / Decision / Rationale / Alternatives.
- Numérotation continue (ADR-001 → ADR-015 actuels, prochains ADR-021+).

### Workflow benchmark (CRITIQUE)

1. **Zero intermediate benchmarks** : le code RAG / prompt évolue *localement* (validation par tests pytest + inspection retrieval gratuite). Aucun appel judge entre deux jalons mesurés.
2. **Dev/test split strict** : 32 dev (tuning autorisé) + 68 test hold-out (jamais utilisé pour ajuster). Headlines de papers/reports = test set.
3. **Multi-judge obligatoire** : Claude Sonnet + GPT-4o + Haiku fact-check. Inter-judge κ documenté.
4. **Blinding seed-déterministe** : `seed.txt` figé par run, mapping A-G → system stocké dans `label_mapping.json`.
5. **Incremental save mandatory** (ADR-015) : tout `judge_all` ou `fact_check_all` doit accepter `save_path` et écrire après chaque question. Resume skip les déjà-faits.
6. **Validation Matteo avant tout run > $5**. Estimation budget en début de run.

### Tests

- TDD encouragé pour nouvelles features RAG (cf F.3.a MMR, F.3.b intent classifier)
- 3 202 tests verts au 2026-07-15 — ne jamais merger qui les casse
- `tests/` reflète la structure de `src/`

### Git

- Branches `feature/*`, `fix/*`, `refactor/*`, `dev/*`
- Conventional commits (`feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`)
- Push sur main interdit (deny dans settings) — passer par `gh pr merge` après validation Matteo via Jarvis (cf pattern merge-approval CLAUDE.md parent)

---

## Fichiers protégés (load-bearing — ne pas toucher sans ADR)

| Fichier | Pourquoi |
|---|---|
| `src/prompt/system.py` (v3.2) | Résultat de 5 itérations Phase 1→C→E. +3.71 pts vs fair baseline (Claude). Modifs additives uniquement. |
| `src/eval/judge.py` (v1 rubric) | Préservé pour comparaison longitudinale Run 1 → Run F+. |
| `src/eval/runner.py` | Retry + resume + incremental save + Cloudflare 520 handling. Load-bearing pour multi-hour runs. |
| `src/rag/embeddings.py:fiche_to_text` | NE PAS inclure ROME (fait régresser, cf Run 5 ablation). À refondre proprement en Axe 1 V2. |
| `src/rag/reranker.py` (RerankConfig defaults) | Stables depuis Run 3 ablation. Boosts SecNumEdu 1.5 / CTI 1.3 / etc. |
| `data/manual_labels.json` (25 entrées) | Curé manuellement, AUTHORITATIVE. Blocklist EPITA, Epitech, Guardia, IONIS, École 42. |
| `src/eval/rate_limit.py` (12 RPM) | Calibré pour OpenAI tier-1 + 25% safety margin. Ne pas raise sans tier 2. |

---

## Variantes systèmes (7-system matrix actuelle)

| # | name | prompt | RAG | rôle |
|---|---|---|---|---|
| 1 | `our_rag` | v3.2 | yes + MMR + intent | full stack (thèse) |
| 2 | `mistral_neutral` | NEUTRAL | no | fair baseline Mistral |
| 3 | `mistral_v3_2_no_rag` | v3.2 | no | **isole le RAG** (compétiteur clé) |
| 4 | `gpt4o_neutral` | NEUTRAL | no | baseline GPT-4o |
| 5 | `gpt4o_v3_2_no_rag` | v3.2 | no | cross-vendor prompt |
| 6 | `claude_neutral` | NEUTRAL | no | baseline Claude |
| 7 | `claude_v3_2_no_rag` | v3.2 | no | cross-vendor prompt |

V2 ajoutera `our_rag_v2_data`, `our_rag_v3_agentic`, `our_rag_v4_raft`, `chatgpt_natural`, `claude_natural`, `mistral_natural` (cf STRATEGIE §6 B2).

---

## Budget API et surveillance

- **Mistral** : paid tier actif. Embeddings + chat.complete. `_call_with_retry` gère rate limits + timeouts + 5xx + Cloudflare 520.
- **Anthropic** : recharger au coup par coup. Run F+G a consommé ~$24 Claude Sonnet + ~$3 Haiku.
- **OpenAI** : tier-1 (15 RPM gpt-4o). Rate limiter `src/eval/rate_limit.py` à 12 RPM. Run F+G a consommé ~$5.
- **Total Run F+G** : ~$42 sur plan $70-90.
- **Règle** : tout run estimé > $5 demande validation Matteo (via Jarvis) avant lancement.

Voir SESSION_HANDOFF §8 pour détail budget par item.

---

## Principes directeurs (extraits STRATEGIE §10)

1. **Le système gagne, pas le paper** — toute décision se mesure à "rend-elle le produit objectivement meilleur pour un lycéen ?"
2. **Le RAG est un moyen, pas une thèse** — si une feature donne plus sans RAG, on l'implémente sans RAG.
3. **Le benchmark est un garde-fou** — mesure les progrès, pas l'objectif. Si un gain ne se voit pas dans les chiffres, soit il n'existe pas, soit le benchmark est inadéquat.
4. **Rigueur méthodologique non-négociable** — ADR continu, dev/test split, blinding, multi-judge.
5. **Souveraineté française** — Mistral + opens data publics + RAFT spécialisé. Argument INRIA fort.
6. **Données fraîches > figées** — refresh mensuel cron des opens data = avantage structurel sur LLMs natifs (cutoff janvier 2026).
7. **Étudiants réels = vérité** — tests utilisateurs > LLM-judges.
8. **Pas d'over-engineering** — 80% du gain en 20% des features. Mesurer avant de complexifier.

---

## Confidentialité

**Repo PRIVATE** : https://github.com/matjussu/OrientIA

- Ne pas partager externalement
- Pas de screenshots méthodologie internes sans go-ahead Matteo
- Pas de push vers public mirror
- Bascule public envisagée post-soumission INRIA (décision Q6 STRATEGIE §11)

---

## Reprendre une session sur OrientIA

```bash
cd ~/projets/OrientIA && source .venv/bin/activate
git log --oneline -15                       # ce qui a bougé récemment
pytest tests/ 2>&1 | tail -5                # 3202 attendu
cat docs/SESSION_HANDOFF.md                 # état opérationnel
cat docs/STRATEGIE_VISION_2026-04-16.md     # vision V2 (si pas encore lu)
```

Vérifier si un sprint V2 est en cours (SESSION_HANDOFF §6) et reprendre où Claudette / Matteo s'est arrêté.

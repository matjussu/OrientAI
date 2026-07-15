# LLM_Final — Audit complet du système OrientAI en production

> **Version auditée** : `v4.1` (defaults factory `enable_strict_v4=True`, `enable_router_llm=True`, `enable_validator=True`, `enable_scope_classifier=True`, `enable_golden_qa=True`, `enable_post_process=True`)
> **Date d'audit** : 2026-05-10
> **Périmètre** : ce qui est servi en prod par `src/api/server.py` via `pipeline.answer()`. Modules `experimental/` et `agents/hierarchical/` sont audités séparément (section 12).

---

## 1. Vue d'ensemble — Ce qu'est le LLM "OrientAI"

OrientAI **n'est pas** un LLM unique : c'est un **pipeline RAG multi-étages** qui orchestre 3 modèles Mistral distincts autour d'un corpus français de **52 040 fiches** (formations, métiers, statistiques, dispositifs).

Le « cerveau » génératif est **Mistral Medium** (`mistral-medium-latest`), mais il est **encadré** par :

- un classifieur de scope (Mistral Small) en amont,
- un routeur déterministe (Mistral Small + JSON tool) qui choisit un sous-corpus + impose des contraintes,
- un retrieval hybride FAISS dense (1024-dim) + BM25 lexical fusionné par RRF,
- un validator 2-3 couches qui mesure la fidélité au corpus,
- des post-traitements déterministes anti-hallu URL.

Tout passe par **un seul endpoint HTTP** : `POST /answer` (`src/api/server.py:386`).

---

## 2. Stack technique

| Couche | Composant | Détail |
|---|---|---|
| Runtime | Python 3.12 (.venv local) | déploiement Railway via `Dockerfile` |
| Embeddings | `mistral-embed` | 1024 dims, batch 64 |
| Generation | `mistral-medium-latest` | T=0.3, `max_tokens=400` (mode v4 strict) |
| Routing & scope | `mistral-small-latest` | T=0, JSON-tool ; ~$0.0001/req chacun |
| Layer3 validator (opt-in) | `mistral-small-latest` | timeout 5 s |
| Vector store | FAISS `IndexFlatL2` (CPU) | index principal **52 040 × 1024** (~213 MB) |
| Lexical | `rank_bm25.BM25Okapi` | tokenisation lower + strip accents + stopwords FR (~45 mots) |
| Backend HTTP | FastAPI + uvicorn (worker unique) | `_pipeline` global non thread-safe |
| Auth | Bearer token `ORIENTIA_API_KEY` | `hmac.compare_digest`, rate-limit 10 req/min/IP |

---

## 3. Données — Le corpus en production

### 3.1 Fichier servi

`data/processed/formations.json` (110 MB, **52 040 fiches** consolidées au 2026-07, aligné prod `/health`). Variable d'env `ORIENTIA_FICHES_PATH`. Index FAISS associé : `data/embeddings/formations.index` (213 MB).

### 3.2 Diversité (top sources)

| Source | Fiches | Apport |
|---|---:|---|
| `parcoursup` | 8 191 | Formations sélectives post-bac (BUT, BTS, CPGE, écoles, licences sélectives) |
| `monmaster` | 7 573 | Masters universitaires, plateforme MESR |
| `rncp` | 5 181 | Certifications professionnelles (CAP → M2) — France Compétences |
| `rncp_blocs` | 4 891 | Blocs de compétences associés aux certifications RNCP |
| `onisep` | 4 758 | Catalogue formations généralistes |
| `inserjeunes_cfa` | 4 065 | Centres de formation d'apprentis — taux d'insertion |
| `labonnealternance` | 4 008 | Contrats d'alternance (France Travail) |
| `inserjeunes_lycee_pro` | 2 693 | Bac pro — taux d'insertion lycées professionnels |
| `rome_api_v4` | 1 584 | Métiers ROME (codes + libellés + compétences) |
| `dares_metiers_2030` | 1 160 | Projections emploi 2030 (DARES) |
| `onisep_metiers` + `onisep_ideo_fiches` | 2 150 | Fiches métier ONISEP / IDEO |
| `insersup_mesr` | 368 | Insertions Master MESR |
| `ip_doc_doctorat` | 240 | Écoles doctorales (IP-Doc) |
| `mesri_parcours_bacheliers_licence` | 151 | Parcours-types par bachelier MESRI |
| `insee_salaan_2023` | 59 | Salaires 2023 INSEE |
| `crous_combine_logements_restos` | 39 | Logements + restaurants CROUS |
| `financement_dispositifs_curated` | 28 | Bourses, CPF, prêts étudiants |
| `domtom_curated` | 16 | Spécificités DOM-TOM |
| `apec_observatoire_emploi_cadre_2026` | 13 | Insertion cadres APEC |
| `parcoursup_calendrier_officiel` etc. | 21 | Calendriers Parcoursup / MonMaster / DSE |
| `corrections_factuelles_curated` | 5 | Anti-hallucinations curées (ECN→EDN, etc.) |

→ **25 sources distinctes** ingérées par ~40 collecteurs (`src/collect/build_*.py`, `src/collect/*.py`).

### 3.3 Schéma d'une fiche

Clés dominantes (échantillon) :
```
source, phase, nom, etablissement, ville, region, uai, annee, niveau, domaine,
statut, type_diplome, insertion_pro, match_method, labels, debouches,
provenance, collected_at, merge_confidence, retrieval_eligible,
url_canonical, url_type
```

Certaines fiches (RNCP / blocs) utilisent `intitule` au lieu de `nom` ; le wrapper API alias `intitule → nom` (`src/api/server.py:307-308`).

### 3.4 Pipeline d'ingestion (`src/collect/`)

- `merge.py` orchestre l'agrégation : chargement de ~40 collecteurs → `normalize_name/city` → fuzzy match `(établissement, nom)` → fusion 1 fiche → enrichissement labels via `data/manual_labels.json` → inférence domaine via codes NSF/ROME → tri priorité par source.
- `manual_labels.json` (24 entrées curées) : mapping établissement normalisé → labels (CTI, SecNumEdu, Grade Master). Utilisé pour éviter qu'un fuzzy matcher attribue un label prestigieux par erreur. Inclut une **blocklist explicite** (EPITA, Epitech, Guardia, IONIS, École 42 — non labellisés).
- Le corpus est **rafraîchi mensuellement** (vision : cron sur Open Data → avantage structurel sur LLMs natifs cutoff 2026-01).

### 3.5 Index FAISS — architecture vectorielle

| Index | ntotal | Dim | Métrique | Usage |
|---|---:|---:|---|---|
| `formations.index` | 52 040 | 1024 | L2 | Index principal (mode legacy / fallback) |
| `formations_v7_formations.index` | 32 481 | 1024 | L2 | Sub-index quad — formations |
| `formations_v7_metiers.index` | 4 894 | 1024 | L2 | Sub-index quad — métiers |
| `formations_v7_statistiques.index` | 831 | 1024 | L2 | Sub-index quad — statistiques |
| `formations_v7_aides_territoires.index` | 5 000 | 1024 | L2 | Sub-index quad — CROUS, financements, DOM-TOM |
| `golden_qa.index` | ~698 | 1024 | L2 | Few-shot Q&A validés |

Manifest authoritative : `data/embeddings/formations_partition_manifest.json` (mapping `domain → group`).

Au boot, `lifespan()` lit `formations.json` puis appelle `pipeline.load_index_from(...)`, puis **warm up** :
```
pipeline._build_double_subindices()
pipeline._retrieve_with_bm25("orientation", k=1)
```
(`src/api/server.py:127-136`) → évite ~30 s de pénalité au premier `/answer` pour le double-corpus + ~5-10 s pour BM25.

### 3.6 Texte indexé (`src/rag/embeddings.py`)

`fiche_to_text(fiche)` concatène (verbatim, sans inventer) :
- `nom`, `etablissement`, `ville`, `region`, `niveau`, `type_diplome`, `domaine`, `discipline`
- `_format_insertion_pro(...)` → taux emploi 3/6 ans, % CDI, salaire médian
- `_format_profil_admis(...)` → mentions bac, type bac, taux d'accès profil-spécifique, % boursiers, % femmes, % néo-bacheliers
- libellés métiers (`debouches`), codes ROME

Note ADR : ROME **n'est pas inclus** dans le texte des fiches **formation** (régression Run 5). Il l'est uniquement dans les fiches `rome_api_v4`.

---

## 4. API HTTP — Ce qui se passe quand un utilisateur fait une requête

### 4.1 Endpoint

```http
POST /answer
Authorization: Bearer <ORIENTIA_API_KEY>
Content-Type: application/json

{
  "question": "Je veux devenir avocat, que faire après le bac ?",
  "history": [
    {"role": "user",      "content": "Bonjour"},
    {"role": "assistant", "content": "..."}
  ]
}
```

Schémas Pydantic dans `src/api/schemas.py`. L'endpoint est exposé en pur **passthrough** vers `pipeline.answer()` (cf docstring `src/api/server.py:1-26`).

### 4.2 Garde-fous wrapper

1. **Auth** : si `ORIENTIA_API_KEY` set, comparaison timing-safe `hmac.compare_digest` (`src/api/server.py:182-196`).
2. **Rate-limit inline** : 10 req / 60 s par IP, fenêtre glissante in-memory (`src/api/server.py:199-233`).
3. **CORS strict** : en `ENV=prod`, seul `PLATFORM_ORIGIN` (Vercel Next.js front) est autorisé.
4. **Sanitization input** (`src/api/server.py:241-251, 321-332`) :
   - Refus regex prompt-injection grossier (`ignore previous instructions`, `disregard`, `system: you are now`).
   - Strip control-tokens Mistral (`[INST]`, `</s>`, `<<SYS>>`).
5. **Mode dégradé** : si `formations.json` ou `formations.index` manquent au boot → `/health=ok` mais `/answer=503` (évite les crash-loops sur Railway).
6. **Logs JSON sans PII** : la `question` n'est **jamais** loguée, uniquement `request_id`, latence, nombre de sources, `honesty_score`, `flagged`, `question_len`.

### 4.3 Réponse

```json
{
  "answer": "...",
  "sources": [
    { "nom": "...", "etablissement": "...", "ville": "...",
      "_score": 0.42, "_score_rrf": 0.31, "_score_bm25": 0.18, ... },
    ...
  ],
  "faithfulness_score": 0.95,
  "faithfulness_verdict": "FIDELE",
  "latency_ms": 7263.4
}
```

`_extract_source_fiche()` (`src/api/server.py:283-318`) déballe les fiches du retriever et expose en sidecar les scores `_score`, `_score_rrf`, `_score_bm25` (préfixe `_` = métadonnée non-fonctionnelle pour le front).

---

## 5. Pipeline RAG — Le flow A → Z

Point d'entrée : `OrientIAPipeline.answer(question, k=30, top_k_sources=10, criteria=None, history=None, temperature=0.3)` (`src/rag/pipeline.py:282`).

### Étape 1 — `ScopeClassifier` (gate amont)

Fichier : `src/rag/scope_classifier.py`. Modèle : `mistral-small-latest`, timeout dédié 5 s.

Cascade :
1. **Regex identité** (`qui es-tu`, `es-tu une IA`) → court-circuit avec `IDENTITY_RESPONSE`.
2. **Regex salutation** (`bonjour`, `salut` seuls) → `GREETING_RESPONSE`.
3. **Regex urgence** (`suicide`, `me tuer`, `violences`, `crise panique`) → `URGENT_RESPONSE` (priorité absolue).
4. **LLM classifier** → 3 labels : `in_scope` / `out_of_scope` / `urgent`. Le prompt contient une consigne explicite : *« Mieux flagger en trop que rater »* sur les signaux indirects de détresse.
5. **Fallback gracieux** : si LLM down/timeout/JSON cassé → défaut conservateur `in_scope`.

Si label ≠ `in_scope` : le pipeline **court-circuite** et retourne `(pre_written_response, [])` → pas de retrieval, pas de génération.

`URGENT_RESPONSE` (extrait) : redirection vers **3114** (prévention suicide), **3919**, **119**, **3018 SOS Amitié**, **15 SAMU** + Psy-EN.

### Étape 2 — `RouterLLM` (routing décisionnel)

Fichier : `src/rag/router_llm.py`. Modèle : `mistral-small-latest`, T=0, **JSON tool** unique `decide_route`. Latence ~500-800 ms, ~$0.0001/req.

Le routeur produit un `RouteDecision` avec :
```
{
  sub_indexes: list[str],         # parmi {formations, metiers, statistiques, aides_territoires}
  region: str | None,             # contrainte région (Bretagne, Île-de-France, ...)
  niveau_min, niveau_max: int,    # contraintes bac+N
  secteur, domain_lock,
  refusal_reason: "superlative_no_data" | "cross_domain" | "out_of_scope_specific" | None,
  hardlock_region_strict: bool,
  hardlock_domain_strict: bool,
  top_k_override: int | None,
  confidence: float
}
```

Si `refusal_reason` non-null : court-circuit pré-pipeline avec un template choisi parmi 3 variantes (sélection déterministe par hash de la question). Voir `REFUSAL_TEMPLATE_VARIANTS`.

Sinon, le routeur :
- restreint le retrieval à un sous-ensemble des 4 sub-indexes (réduit la pollution cross-domaine),
- produit un `FilterCriteria` injecté dans le retriever,
- produit un **bloc hardlock R7** injecté en tête du prompt système v4.1 (cf §6).

### Étape 3 — Structured SELECT (lookup déterministe)

Fichier : `src/lookup/structured_select.py`. Activé pour les intents factuels pointus (`intent.factual_pointed`).

Logique :
1. Extraction d'entité (formation nommée + ville/niveau) via regex.
2. Fuzzy match ≥ 85 % sur les fiches.
3. Extraction du champ demandé (`taux_acces`, `places`, `frais`, ...).
4. Retour templater « *Le taux d'accès est X % [source URL]* » → **zéro LLM, zéro hallu chiffres**.

Si `via_select=True` ou (pas d'entité ET pas de domain hint annexe) : bypass complet du LLM.

### Étape 4 — Retrieval hybride

Deux chemins selon le routeur :

**A. Quad sub-index** (router actif, sub-indexes < 4) — `_retrieve_from_sub_indexes()` :
- `k_per_sub = 50` sur chaque sub-index sélectionné,
- fusion par RRF (Reciprocal Rank Fusion, k=60).

**B. Option C v6** (fallback ou route "tous indexes") — `_retrieve_with_annex_quota()` :
- retrieval dense FAISS k_initial = 150 sur l'index principal,
- séparation pool *main* (formations) / *annex* (métiers, stats, aides),
- **quota adaptatif score-based** : si `max_score(annex) ≥ 0.6`, on garantit ≥ 3 fiches annexes dans le top-K.

Dans les deux cas, BM25 lexical apporte un top-50 fusionné en RRF avec le dense :
- `_fiche_to_search_text()` : nom + texte + établissement + ville + région + département + type_diplome + niveau + discipline + domaine + id + codes ROME (`src/rag/bm25_index.py`).
- Tokenisation : lower + strip accents + stopwords FR (~45 mots).

### Étape 5 — Reranker, MMR, Intent

**Reranker** (`src/rag/reranker.py`, ~18 boosts staged) :
- Labels : SecNumEdu × 1.5, CTI × 1.3, Grade Master × 1.0, public × 1.1
- Niveau : bac+5 × 1.15, bac+3 × 1.05
- Domaines : APEC région × 1.5, métier × 1.3, métier_detail × 1.4, parcours_bacheliers × 1.3, CROUS × 1.4, INSEE salaire × 1.5, insertion_pro × 1.4, compétences certif × 1.5, financement × 1.5, DROM × 1.5, voie pré-bac × 1.4, calendrier × 1.5

**Metadata filter** (`src/rag/metadata_filter.py`) : applique `FilterCriteria` (région, niveau_min, niveau_max, alternance, budget_max, secteur, domain) + **auto-expand** (k×3 jusqu'à k×10) si le filtre coupe sous le `target`.

**MMR** (`src/rag/mmr.py`, 71 lignes) : `mmr_select(candidates, k, lambda_=0.7)` ; greedy selection : `λ·relevance − (1−λ)·max_sim(already_selected)`. Override par intent (range 0.3-0.9).

**Intent** (`src/rag/intent.py`) : 7 intents (COMPARAISON, GEOGRAPHIC, REALISME, PASSERELLES, DECOUVERTE, CONCEPTUAL, GENERAL) + `factual_pointed`. Chaque intent peut override `top_k_sources` et `mmr_lambda`. Détecte aussi des **domain hints** (apec_region, crous, insee_salaire, voie_pre_bac, calendrier, …) qui boostent leur source dans le rerank.

### Étape 6 — Golden QA few-shot

`pipeline._maybe_build_golden_qa_prefix(question)` :
- recherche FAISS 1-NN dans `golden_qa.index` (~698 Q&A validés, scorés, taggés `keep`/`flag`),
- si match : injecte un préfixe `=== EXEMPLE EXPERT === <Q ref> → <A ref> === FIN ===` dans le user message **avant** la question courante.

But : donner un **gabarit ton/structure** au LLM. Mais R4 du prompt v4.1 interdit explicitement de reprendre les chiffres ou noms de cet exemple — c'est une référence stylistique, pas factuelle.

### Étape 7 — Génération (cœur LLM)

Fichier : `src/rag/generator.py`. Modèle : `mistral-medium-latest`, T=0.3.

**Mode v4.1 strict (default prod, `use_strict_v4=True`)** :
1. `format_sources_for_llm(top_sources, max_sources=5)` → JSON tabulaire `<sources>` typé via FactCard (cf §6).
2. `build_system_prompt_v4_strict(hardlock_block)` → prompt système v4.1 (cf §7).
3. User message :
   ```
   <bloc hardlock R7 si présent>
   <sources>
   [{"id": "S1", "formation": "...", "etablissement": "...", "chiffres": {...}, "url": "...", ...}, ...]
   </sources>

   Question : <question utilisateur>
   ```
4. `messages = [system] + history + [user]` (history Mistral-compliant, alternance `user`/`assistant`).
5. `client.chat.complete(model, temperature=0.3, messages, max_tokens=400)` → 250 mots ≈ 350-400 tokens FR.
6. Strip wrapper `<reponse_finale>...</reponse_finale>` éventuel.

**Mode v3.2 legacy** (uniquement si `enable_strict_v4=False` — A/B bench) : prose libre du contexte, pas de cap `max_tokens`, prompt plus long et générique. **Inactif en prod nominale**.

**Retry-with-hint** (skip si v4.1) : max 1 retry, timeout 30 s, threshold audit 0.5 / warn 0.7.

### Étape 8 — Validator (faithfulness)

Fichier : `src/validator/`. 3 couches.

**Layer 1 — Règles déterministes** (`rules.py`, ~13 règles regex) :

| Règle | Sévérité | Détection |
|---|---|---|
| `ECN_renamed_to_EDN` | BLOCKING | "ECN" mentionné (réforme 2023) |
| `bac_S_abolished` | BLOCKING | "bac S" (réforme Blanquer 2021) |
| `VAE_VAP_confusion` | WARNING | "VAE pour reprise études" |
| `VAP_infirmier_kine` | BLOCKING | Voie infirmier → kiné impossible |
| `ecole42_gratuite_alternance` | BLOCKING | "École 42 gratuite en alternance" |
| `MBA_HEC_accessible_experience` | WARNING | Marketing trompeur MBA HEC |
| `licence_humanites_orthophonie_invented` | BLOCKING | Voie fantaisiste |
| `HEC_not_via_Tremplin_or_Passerelle` | BLOCKING | Concours whitelist |
| `PASS_no_redoublement` | BLOCKING | Règles PASS |
| `kine_via_IFMK_not_licence` | BLOCKING | Nomenclature kiné |
| (3 autres) | — | — |

Latence < 50 ms. Chaque règle a un `except_context` optionnel (±80 chars) pour éviter les faux positifs.

**Layer 2 — Corpus check** (`corpus_check.py`) :
- Extraction regex des claims `Licence|Master|BTS|BUT|MBA … à/de [Université|École|…]`.
- Similarité composite 85 % nom + 15 % établissement (`difflib.SequenceMatcher`).
- **Seuil** : `similarity < 0.55` (configurable `corpus_sim_threshold`, défaut prod 0.55) → `CorpusWarning` (formation probable hallu).
- Latence ~5-10 ms.

**Layer 3 — Mistral Small (opt-in, `enable_layer3=False` par défaut)** :
- Activé uniquement sur intents `factual_pointed` / `geographic` / `comparaison` / `realisme`.
- Output JSON `{suspect_claims: [{claim, reason, severity}]}`.
- Timeout 5 s, fallback gracieux (return [] si API down).
- Coût ~$0.001/req.

**Calcul `honesty_score`** :
```
score = 1.0
  − 0.15 × #BLOCKING
  − 0.05 × #WARNING
  − 0.02 × #INFO
  − 0.10 × #corpus_warning
  − 0.05 × #layer3_warning
flagged = (#BLOCKING ≥ 1) OR (#corpus_warning ≥ 1)
```

Le wrapper API mappe `flagged → "INFIDELE"`, sinon `"FIDELE"` (`src/api/server.py:417-423`).

### Étape 9 — Policy α/β/γ (UX gate)

Sur chaque réponse validée :
- `score < 0.70 AND flagged` → **BLOCK** : remplace par fallback CIO/ONISEP.
- `score ∈ [0.55, 0.70) AND warn` → **QUALIFY** : garde la réponse + warning.
- `score ≥ 0.70` → **ALLOW**.

Stocké dans `pipeline.last_policy_result`.

### Étape 10 — Phase projet

`append_phase_projet(answer, question)` : si la question touche un enjeu fort (réorientation lourde, choix structurant), append 3 questions de réflexion + redirection optionnelle CIO. Composant éducatif/empathique non-LLM.

### Étape 11 — Post-process déterministe

Fichier : `src/rag/post_process.py` (3 passes, zéro LLM, déterministes) :

1. `strip_invented_urls(...)` — retire les URL hallucinées : `github.com/matjussu`, `github.com/.../OrientIA`, `jsdelivr`, `localhost`. Markdown links `[text](hallu_url)` → `text (voir parcoursup.fr ou onisep.fr)`.
2. `fix_broken_markdown_tables(...)` — détecte les puces dans des cellules tableau et les supprime (Wave 1, simpler-destructeur).
3. `validate_onisep_slugs(...)` — valide les `FOR.XXXX` cités contre les slugs réellement présents dans les sources retrieved. Slug invalide → `(voir onisep.fr)`.

Stats exposées dans `pipeline.last_post_process_stats`.

---

## 6. FactCard — Le format des sources injectées au LLM

Fichier : `src/rag/fact_card.py` (623 lignes).

Pour chaque fiche retrieved (top-5 max en mode v4.1), `fiche_to_fact_card()` produit un JSON typé :

```json
{
  "id": "S1",
  "formation": "BUT Informatique",
  "etablissement": "IUT Lyon 1",
  "ville": "Villeurbanne",
  "region": "Auvergne-Rhône-Alpes",
  "niveau": "bac+3",
  "statut": "public",
  "type_diplome": "BUT",
  "selectivite_code": "selective",
  "chiffres": {
    "taux_acces_parcoursup_2025": 12.4,
    "nombre_places": 60,
    "duree": 3,
    "frais_annuels": 170,
    "taux_emploi_3ans": 0.92,
    "taux_emploi_6ans": null,
    "taux_cdi": 0.78,
    "salaire_median_embauche": null,
    "insertion_pro_granularite": "etablissement_x_discipline"
  },
  "debouches": ["développeur", "data analyst", "..."],   // tronqué ≤ 5
  "url": "https://dossierappel.parcoursup.fr/.../?g_ta_cod=12345",
  "annee_donnees": 2025,
  "text_libre": "...",
  "domain": "formation",
  "provenance": {
    "tier": "tier_1",
    "source_label": "Parcoursup",
    "source_url": "https://www.parcoursup.fr",
    "last_updated": "2026-04-30"
  }
}
```

Champs `null` signalent **explicitement** une info manquante → le prompt R1 force « information non disponible dans mes sources » au lieu de combler.

URL : priorité `lien_form_psup > url_onisep > url > url_canonical`.

---

## 7. Le prompt système V4.1 strict (in extenso)

Fichier : `src/prompt/system_v4_strict.py:37-142`. C'est **le contrat** signé entre Matteo et Mistral Medium.

```
Tu es OrientAI, conseiller d'orientation académique et professionnelle française post-bac.

Tu réponds à la question de l'utilisateur·ice en t'appuyant **uniquement** sur le tableau JSON `<sources>` qui te sera fourni dans le user message.

## CONTRAT STRICT — RÈGLES NON-NÉGOCIABLES

### R1 — Chiffres
Tu peux UNIQUEMENT citer les valeurs présentes dans le bloc `chiffres` d'une source.
- Toute autre valeur numérique est INTERDITE.
- Si le champ vaut `null` → « information non disponible dans mes sources ».

### R2 — Identité des formations
Tu peux UNIQUEMENT citer les formations dont (formation + etablissement + ville) figure dans <sources>.
- Pas d'invention.
- Sources vides → « Je n'ai pas de formation pertinente dans mes sources … RDV au CIO ».

### R3 — Citations sources
Chaque chiffre cité DOIT être suivi de [source SX] (S1, S2, …).

R3.bis — Liens cliquables : si url non-null, écrire le nom en Markdown link [Nom](url).
R3.ter — Questions métier : prioriser les sources domain="metier*" si la question utilise « métier », « profession », « débouchés », …

### R4 — Style
Bienveillant, clair, structuré.
JAMAIS reprendre les chiffres ni noms de l'exemple Golden (référence ton uniquement).

### R5 — Posture
- Empathique sans surjouer (pas d'emojis sauf 1 final éventuel)
- Direct·e si projet pas réaliste
- Pas de discrimination
- Question ouverte finale

### R6 — LONGUEUR (NON-NÉGOCIABLE)
STRICTEMENT MAX 250 mots.
Structure : intro ≤30 mots → 2-3 puces → question ouverte 1 ligne.
INTERDIT : intro explicative, fermeture standard, sections "Pour aller plus loin", répétitions.

### R7 — CONTRAINTES HARDLOCK (router-injected en tête)
- Région imposée → pas d'alternative hors-région sans signaler que la zone est vide.
- Domaine imposé → pas de mélange. Refus honnête > pis-aller.
R7 prime sur R5.

## SI VIOLATION
Réponse rejetée par le validator. Reformule honnêtement.
```

Cap dur : `max_tokens=400` côté API call. Mesure mini-bench v4.1 : `avg_latency=7.26 s` (-29 % vs v3.2), `avg_words=184` (-23 %), `flagged=0`, `honesty=1.0` sur 30 questions.

`build_system_prompt_v4_strict(hardlock_block)` insère le bloc hardlock **avant** la phrase d'identité OrientAI pour maximiser la salience cognitive.

---

## 8. Multi-tour — Comment l'historique est consommé

`pipeline.answer(question, history=[{"role": "user", "content": "..."}, ...])`.

Le `history` est :
1. désérialisé côté API (`src/api/server.py:401`),
2. passé tel quel à `_generate_with_retry(history=...)`,
3. injecté entre `system` et `user` dans `messages` (`src/rag/generator.py:440-446`) :
   ```
   [{"role": "system", "content": SYSTEM_PROMPT_V4_STRICT},
    {"role": "user", ...}, {"role": "assistant", ...},   # history
    {"role": "user", "content": <prompt avec <sources>>}]
   ```

**Important** : la `question` est passée **verbatim** au retriever et au routeur — il n'y a **pas** de re-écriture contextualisée (pas de HyDE, pas de query rewrite). Le history affecte uniquement la **génération** (continuité conversationnelle, suivi de tiroir « Oui Plan A »), pas le retrieval. Décision Sprint 11 P0.

---

## 9. Modèles LLM utilisés (résumé)

| Étape | Modèle | T | Tokens | Coût indicatif | Latence |
|---|---|---:|---|---|---|
| Embeddings (offline) | `mistral-embed` | — | 1024 dims | ~$0.10/1M tokens | batch 64 |
| Scope classifier | `mistral-small-latest` | 0 | JSON court | ~$0.0005/req | <1.5 s |
| Router LLM | `mistral-small-latest` | 0 | JSON tool | ~$0.0001/req | 500-800 ms |
| **Generator** | **`mistral-medium-latest`** | **0.3** | **max 400** | **~$0.005/req** | **5-8 s** |
| Layer3 validator (opt-in) | `mistral-small-latest` | 0 | JSON | ~$0.001/req | 2-4 s |

Total typique d'une réponse : **7-15 s** end-to-end (retrieval ~3 s + génération ~5-8 s + validation ~500 ms).

---

## 10. Fallbacks et garde-fous (récap)

Le pipeline a **5 chemins de court-circuit** câblés dans le même `answer()` :

| Path | Trigger | Réponse |
|---|---|---|
| `ScopeClassifier` | `out_of_scope` / `urgent` | `pre_written_response` (templates pré-écrits) |
| `RouterLLM` | `refusal_reason` non-null | template parmi 3 variantes (sélection hash-déterministe) |
| Structured `SELECT` | intent `factual_pointed` + entité matchée | template déterministe `« Le taux est X % [URL] »` |
| `Validator` + `Policy` | `flagged AND score < 0.70` | fallback CIO/ONISEP + warning |
| Fallback unifié | aucune source pertinente après filter | `format_unknown_response()` (`src/rag/fallback_response.py`) |

Le wrapper API ajoute par-dessus :
- 401 si Bearer token invalide,
- 429 si > 10 req/min/IP,
- 400 si tentative de prompt-injection détectée,
- 503 si pipeline non chargé (mode dégradé),
- 500 + `request_id` traçable si exception inattendue.

---

## 11. Observabilité — État exposé par le pipeline

`OrientIAPipeline` expose 9 propriétés `last_*` après chaque `answer()` :

| Propriété | Contenu |
|---|---|
| `last_validation` | `ValidatorResult` complet (rules, corpus, layer3, honesty_score, flagged) |
| `last_policy_result` | `PolicyResult` (BLOCK / QUALIFY / ALLOW + final_answer) |
| `last_golden_qa` | `{active, matched, prompt_id, category, score_total, retrieve_score, decision}` |
| `last_retry_metadata` | `{retries_attempted, tour1_failed_claims, tour2_failed_claims, retry_stability, needs_audit, wall_clock_s, retry_skipped_reason}` |
| `last_scope_result` | `ScopeResult` (label, reason, via, pre_written_response) |
| `last_select_result` | `SelectResult` si SELECT déterministe utilisé |
| `last_post_process_stats` | `{applied, had_invented_url, had_broken_table, n_onisep_slugs_corrected, chars_removed}` |
| `last_router_result` | `RouteDecision` (sub_indexes, criteria, refusal_reason, hardlock, confidence) |
| `last_filter_stats` | métadonnées d'expansion auto du filter |

L'API en expose seulement `faithfulness_score` et `faithfulness_verdict` côté client (le reste reste interne).

---

## 12. Modules **non** en prod (à dissiper toute confusion)

### Dormants — code complet, jamais instancié dans le flow API

| Module | Statut | Détail |
|---|---|---|
| `src/agents/hierarchical/coordinator.py` | DORMANT | Coordinator + EmpathicAgent + AnalystAgent + SynthesizerAgent. Architecturé Sprint 9, jamais importé par `src/rag/` ou `src/api/`. Présent uniquement dans `tests/test_hierarchical_archi.py` et `src/eval/systems.py` (HierarchicalSystem pour bench A/B). |
| `src/rag/router_fallback.py` | DORMANT (route fallback heuristique pré-RouterLLM) | Le RouterLLM actuel a remplacé cette logique en Étape 6 refonte. |

### Experimental — backlog Phase 3, jamais activé

| Module | Statut |
|---|---|
| `src/experimental/critic_loop.py` | EXPERIMENTAL — LLM 2-pass fact-check, reverté Sprint 7 |
| `src/experimental/system_strict.py` | EXPERIMENTAL — `SYSTEM_PROMPT_V33_STRICT`, reverté (pct_halluc 16.8 % → 25.6 %). Remplacé par v4.1. |
| `src/experimental/judge_v2/judge_v2.py` | EXPERIMENTAL — wrapper fact-check pour bench |
| `src/experimental/multi_corpus.py` | EXPERIMENTAL |
| `src/prompt/system.py` (v3.2) | LEGACY — préservé pour A/B `enable_strict_v4=False` uniquement |

**Vérification** : `grep -r "hierarchical\|critic_loop\|judge_v2" src/rag/ src/api/` → zéro hit, sauf une mention en docstring historique dans `generator.py:322`.

---

## 13. Schéma synthétique du flow A → Z

```
┌─────────────────────────────────────────────────────────────────┐
│ POST /answer  (Bearer auth, rate-limit 10/min/IP, sanitize)     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ ScopeClassifier (Mistral Small, regex + LLM)                    │
│   ─ regex urgent → URGENT_RESPONSE (3114, 3919, 119, …)         │
│   ─ regex identité → IDENTITY_RESPONSE                          │
│   ─ regex salutation → GREETING_RESPONSE                        │
│   ─ LLM → in_scope / out_of_scope / urgent                      │
│   COURT-CIRCUIT si ≠ in_scope                                   │
└─────────────────────────────────────────────────────────────────┘
                              │  in_scope
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ RouterLLM (Mistral Small + JSON tool decide_route)              │
│   → sub_indexes, FilterCriteria, refusal_reason, hardlock       │
│   COURT-CIRCUIT si refusal_reason → template variante hash       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Structured SELECT (lookup déterministe)                         │
│   intent factual_pointed + entité fuzzy ≥ 85 %                  │
│   → template « Le taux est X % [source URL] »                   │
│   COURT-CIRCUIT (zéro LLM)                                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Retrieval hybride                                                │
│  Path A  Quad sub-index FAISS k_per_sub=50 (router actif)       │
│  Path B  Dense FAISS k=150 + quota main/annex (Option C v6)     │
│  + BM25 lexical top-50                                           │
│  → fusion RRF (k=60)                                             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Reranker (18+ boosts) → Metadata filter (auto-expand) → MMR     │
│  λ=0.7 (override par intent)                                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Golden QA few-shot (FAISS 1-NN sur 698 Q&A validés)             │
│  → préfixe ton/structure dans le user message                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ FactCard JSON  (top-5 sources typées)                           │
│  + SYSTEM_PROMPT_V4_STRICT (R1-R7) + bloc hardlock R7           │
│  + history (alternance user/assistant)                          │
│                                                                 │
│ Mistral Medium  T=0.3  max_tokens=400  → ≤ 250 mots             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Validator                                                        │
│  L1 rules (regex anti-hallu, ECN→EDN, bac S, blocklist écoles)  │
│  L2 corpus_check (sim 0.85 nom + 0.15 etab, seuil 0.55)         │
│  L3 (opt-in) Mistral Small chiffres / prestige                  │
│  → honesty_score [0..1] + flagged                               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Policy α/β/γ                                                     │
│  flagged + score<0.70 → BLOCK (fallback CIO)                    │
│  flagged + 0.55-0.70 → QUALIFY                                  │
│  score≥0.70 → ALLOW                                             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Phase projet — append 3 questions de réflexion si enjeu fort    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Post-process déterministe                                        │
│  strip_invented_urls (github, jsdelivr, localhost)              │
│  fix_broken_markdown_tables                                     │
│  validate_onisep_slugs (FOR.XXXX vs slugs retrieved)            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ AnswerResponse                                                   │
│  { answer, sources[5-10] avec _score/_score_rrf/_score_bm25,    │
│    faithfulness_score, faithfulness_verdict, latency_ms }       │
└─────────────────────────────────────────────────────────────────┘
```

---

## 14. Synthèse pour décideurs

- **Le LLM en prod** est **Mistral Medium**, encadré par **2 LLM Mistral Small** (scope + router) et un **3e Mistral Small optionnel** (validator L3).
- **La data en prod** est **52 040 fiches** issues de **25 sources publiques officielles** (Parcoursup, ONISEP, ROME, RNCP, MonMaster, InsertSup, InserJeunes, DARES, INSEE, APEC, La Bonne Alternance, CROUS, France Travail, …). Index FAISS 1024-dim, partitionné en 4 sub-indexes thématiques.
- **L'anti-hallucination** est **multi-niveaux et by-design** : prompt v4.1 strict avec FactCard JSON typé (le LLM ne voit pas de prose libre), validator 2-3 couches, post-process déterministe, policy de blocage. Aucun chiffre hors `chiffres.*` du JSON ne peut être cité légitimement.
- **Les modules `agents/hierarchical/` et `experimental/`** existent dans le repo mais ne sont **pas branchés en prod** — ils sont architecturés pour la Phase 3 (multi-tour conversationnel + critic loop). Le système prod est mono-passage.
- **Le déploiement** se fait via **Railway** (Dockerfile + volume persistant pour `data/embeddings/`), un seul worker uvicorn (état mutable `last_*` non thread-safe), warmup explicite des indices au boot pour garantir un p95 démo correct.

---

*Audit produit le 2026-05-10 par exploration directe de `src/`, `data/processed/`, `data/embeddings/` et lecture verbatim des prompts `src/prompt/system_v4_strict.py` + `src/rag/scope_classifier.py`. Source de vérité : code en `main` au commit `de8ecb5`.*

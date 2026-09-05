# Audit du retrieval OrientIA - le CODE tel qu'il tourne

Lecture seule. Aucun fichier du repo modifie, aucun git write, aucun appel API.
Chemins relatifs a `/home/matteo_linux/projets/OrientIA/`.
Complement du rapport docs/ADR `02-retrieval-docs.md` : ici, ce que le code fait reellement.

Statut : COMPLET (2026-09-05). Verifie apres coup : `git status --porcelain` sur le repo ne
montre que les deux entrees non suivies qui preexistaient (`DEPLOY_LOT1_RUN_ME.sh`,
`results/jarvis_analyse_2026-09-05/`). Aucun fichier cree ou modifie par cet audit.

---

## 0. Le resultat le plus dur, d'abord : la fusion RRF dense+BM25 est inerte en prod

**Affirmation** : dans le chemin de retrieval servi par defaut (`_retrieve_with_annex_quota`),
la fusion Reciprocal Rank Fusion entre le dense et le BM25 ne fusionne **jamais** deux rangs
pour la meme fiche. Chaque document ne recoit que la contribution de son propre ranking.
Le benefice attendu du hybride (un document trouve par les deux canaux remonte) n'existe pas.

**Mecanisme** (fichier:ligne) :

- `src/rag/pipeline.py:1982-1986` appelle `reciprocal_rank_fusion([main_pool, annex_pool, bm25_results], k_rrf=RRF_K, id_key="_orig_index")`.
- Les pools denses viennent de `_search_subindex` (`src/rag/pipeline.py:1654-1672`) : les dicts produits ont les cles `fiche`, `score`, `base_score`, `embedding`. **Aucun `_orig_index`.**
- Idem pour le chemin de repli `retrieve_top_k` (`src/rag/retriever.py:25-30`) : pas de `_orig_index` non plus.
- Les resultats BM25, eux, portent `_orig_index` (`src/rag/bm25_index.py:195`).
- Dans `reciprocal_rank_fusion` (`src/rag/bm25_index.py:238-242`), quand `_orig_index` est absent le code retombe sur `fiche.get("id") or id(fiche)`. Donc :
  - fiche formation (pas de champ `id`) : cle dense = `id(fiche)` (adresse memoire Python), cle BM25 = entier de position 0..52039. Jamais egales.
  - fiche annexe (champ `id` string, ex. `apec_region:bretagne`) : cle dense = string, cle BM25 = int. Jamais egales.

**Mesure (temoin, 2026-09-05)** : script `/tmp/.../scratchpad/rrf_witness.py`, lance en local
sans reseau (`source .venv/bin/activate && PYTHONPATH=. python rrf_witness.py`), avec les vraies
fiches de `data/processed/formations.json` et les formes de dict exactes produites par les deux
fonctions de production.

```
formation: fiche id=None -> n_entrees_fusionnees=2   scores_rrf: [0.01639, 0.01639]
annexe:    fiche id='apec_region:auvergne-rhone-alpes' -> n_entrees_fusionnees=2
TEMOIN POSITIF (avec _orig_index des deux cotes): n= 1 score_rrf= 0.03279
```

Une meme fiche, en tete des deux rankings, produit **deux entrees a 0,01639** au lieu d'une
entree a 0,03279. Le temoin positif etablit que l'instrument sait rendre 1 quand la fusion
marche : la conclusion negative n'est pas un angle mort de la sonde.

**Deux consequences en cascade dans le meme bloc :**

1. `src/rag/pipeline.py:1987-1991` construit `rrf_score_by_fiche_id = {id(f): score_rrf}` en
   iterant sur `fused`. Comme la meme fiche apparait deux fois dans `fused` avec des cles
   differentes mais **le meme objet `fiche`**, la seconde ecrase la premiere dans ce dict.
   Le score RRF attribue a une fiche depend donc de l'ordre de tri de `fused`, pas d'une somme.
2. `src/rag/pipeline.py:2024-2025` : le score des fiches BM25-only est `min(0.4 + rrf*30, 0.8)`.
   Avec un `rrf` toujours issu d'un seul ranking (~0,0164 au rang 1, ~0,0143 au rang 10),
   la plage reellement atteinte est **0,43 a 0,49** au lieu du [0,4 ; 0,8] annonce par le
   commentaire. Une fiche BM25 rang 1 entre donc dans le rerank a ~0,49 face a des formations
   denses a ~0,8, et le commentaire du code decrit une echelle qui n'existe pas.

**Le meme defaut d'identifiant explique le bug `idx:-1` du set de pertinence lot 2**
(`scripts/relevance_set/STATE.md:25-30`, 79 refs sur 135 questions labellisees) : le miner ne
peut pas retrouver la position corpus d'une fiche parce que `retrieve_top_k` ne la rend pas.
C'est **une seule cause racine** pour deux symptomes tres eloignes : la fusion hybride morte
en prod, et l'instrument de mesure du recall bloque.

**Fix** : ajouter `"_orig_index": int(idx)` dans les dicts retournes par `retrieve_top_k`
(`src/rag/retriever.py:25`), `_search_subindex` (`src/rag/pipeline.py:1666`) et `_search_one`
(`src/rag/pipeline.py:1882`). Trois lignes. Debloque simultanement le hybride et le lot 2.

---

## 1. Le second resultat dur : ce n'est PAS la pertinence qui ordonne le top-k

### 1.1 Instrument, gratuit et reutilisable

`data/embeddings/golden_qa.index` contient **676 vecteurs de QUESTIONS reelles**
(IndexFlatL2, dim 1024), produits par `scripts/embed_golden_qa.py:50-62` a partir de
`question_seed + " | " + final_qa.question`, avec le meme `mistral-embed` que le corpus.
Ce sont des requetes utilisateur deja embarquees : on peut donc **interroger l'index de
production avec de vraies questions sans payer un seul appel Mistral**. C'est l'instrument
gratuit qui manquait au projet, et il est deja sur disque depuis le 13/05.

Verifications d'alignement (2026-09-05) :
- `data/embeddings/formations.index` : `IndexFlatL2`, `ntotal = 52 040`, `d = 1024`, 213 Mo, chargement 2,4 s.
- `data/processed/formations.json` : 52 040 fiches. **Aligne** (meme cardinalite, indice FAISS = position dans la liste).
- vecteurs L2-normalises (norme mediane 1,0000).

### 1.2 Le signal dense est presque plat a l'interieur du top-100

Mesure sur les 676 questions golden contre les 52 040 fiches (medianes) :

| Grandeur | Valeur |
|---|---|
| distance L2 question -> fiche **aleatoire** (temoin) | 0,7453 |
| distance L2 question -> **rang 1** | 0,6268 |
| distance L2 question -> rang 10 | 0,6478 |
| distance L2 question -> rang 100 | 0,6657 |
| gain du rang 1 vs aleatoire | **-15,9 %** de distance |
| ecart rang 1 -> rang 100 | **+5,6 %** de la distance du rang 1 |
| part des fiches aleatoires plus proches que le rang 100 | 1,99 % |

Lecture honnete : le dense **discrimine** (2 % seulement des fiches aleatoires entrent dans la
zone du top-100, et le rang 1 est 16 % plus proche qu'une fiche au hasard). Ce qu'il ne fait pas,
c'est **ordonner** : entre le rang 1 et le rang 100, il n'y a que 5,6 % d'ecart de distance.
Converti dans le score utilise par le reranker (`score = 1/(1+dist)`, `src/rag/retriever.py:23`),
cela donne un ecart de **3,2 % seulement** entre le meilleur et le centieme candidat
(mediane 1,0322 ; min 1,0089 ; max 1,1244 sur 136 questions).

Cause probable, non isolee experimentalement : le texte embarque des 38 596 fiches formation est
un gabarit fixe (`Formation : ... | Etablissement : ... | Ville : ... | Diplome : ...`,
`src/rag/embeddings.py:505-520`). Le boilerplate commun domine le vecteur. A verifier par ablation,
marque **hypothese**.

### 1.3 Le reranker a une amplitude 20 fois superieure au signal de requete

Le reranker (`src/rag/reranker.py:148-225`) n'utilise **aucun signal requete-document**. Il
multiplie le score dense par des prieurs qui ne dependent que de la fiche. Couverture reelle
mesuree sur les 52 040 fiches (2026-09-05) :

| Etage | Boost | Condition | Couverture corpus |
|---|---:|---|---|
| A labels | 1.0 | SecNumEdu | 21 fiches (0,04 %) - **neutralise** |
| A labels | 1.0 | CTI | 7 fiches (0,01 %) - **neutralise** |
| A labels | 1.0 | Grade Master | 1 fiche - **neutralise** |
| A statut | **1.1** | `statut == "Public"` | 17 686 (34,0 %) |
| B niveau | **1.15** | `niveau == "bac+5"` | 14 561 (28,0 %) |
| B niveau | **1.05** | `niveau == "bac+3"` | 8 254 (15,9 %) |
| C etab | **1.1** | `etablissement` non vide | 34 831 (66,9 %) |
| D psup | **1.2** | `cod_aff_form` + un `bac_type_pct > 0` | 12 754 (24,5 %) |
| E domain | 1.0 a 1.5 | `fiche.domain == domain_hint` | selon hint |

Facteur multiplicatif resultant, hors domain hint : **15 valeurs distinctes, de 1,0000 a 1,6698**.
23,3 % des fiches ne recoivent aucun boost, 0,6 % recoivent le maximum.

**L'amplitude du prieur document (67 %) est vingt fois celle du signal de requete a l'interieur
du top-100 (3,2 %).** Le classement final n'est donc pas decide par la pertinence.

### 1.4 Consequence mesuree : le rerank detruit l'ordre dense

136 questions golden reelles, dense top-100 puis `rerank(..., domain_hint=None)` :

| Metrique | Moyenne | Mediane | Min |
|---|---:|---:|---:|
| fiches du dense top-5 encore dans le rerank top-5 | **1,43 / 5** | **0 / 5** | 0 |
| fiches du dense top-10 encore dans le rerank top-10 | **3,36 / 10** | 2 / 10 | 0 |

Sur la moitie des questions, **aucune** des 5 fiches les plus proches semantiquement ne survit
dans les 5 fiches servies. Ce que le generateur recoit est un classement par attributs
administratifs (public, bac+5, etablissement nomme, fiche Parcoursup riche), filtre par un
voisinage semantique large.

Temoin de contraste dans le meme run : avec des vecteurs de fiches en guise de requetes
(voisinage tres serre, spread dense median 1,0985), la survie monte a 7,67/10 et 3,77/5.
L'instrument sait donc rendre une valeur haute ; la valeur basse sur les vraies questions n'est
pas un artefact de la sonde.

**Reponse a la question "qu'est-ce qui ordonne reellement le top-k ?" : les prieurs documentaires
du reranker.** Il n'existe aucun cross-encoder ni aucun signal requete-document au-dela du dense
plat (`grep -rn "cross.encoder\|CrossEncoder\|rerank_model\|cohere\|bge" src/` : aucun resultat,
voir section outillage).

---

## 2. Le chemin reellement SERVI, etape par etape

### 2.1 Ce que la factory cable par defaut

`make_production_pipeline` (`src/rag/factory.py:77-208`), defauts : `enable_validator=True`,
`enable_layer3=False`, `corpus_sim_threshold=0.55`, `enable_golden_qa=True`,
`enable_post_process=True`, `enable_scope_classifier=True`, `enable_strict_v4=True`,
`enable_router_llm=True`, `router_model=MISTRAL_SMALL`, `use_mmr=True`, `use_intent=True`,
`use_metadata_filter=True`, `model=MISTRAL_MEDIUM`, `enable_narrative_mode=None` (lit
`ORIENTIA_NARRATIVE_MODE`, defaut OFF).

Serving : `src/api/server.py:166-167` appelle `make_production_pipeline(client, fiches)` sans
aucun override, puis `load_index_from(ORIENTIA_INDEX_PATH)` avec pour defaut
`data/embeddings/formations.index` (`src/api/server.py:81-82`). **L'index charge en prod est
l'index unifie 52 040 vecteurs** ; les 4 quads et le golden_qa sont charges paresseusement
depuis le disque au premier appel qui en a besoin.

### 2.2 Tableau du chemin, mesure sur les 67 tours de `results/jarvis_analyse_2026-09-05/runs/local.jsonl`

| # | Etape | Fichier:ligne | Parametres reels | Modele | Frequence mesuree (n=67) |
|---|---|---|---|---|---|
| 1 | sanitize + scope classify | `src/rag/pipeline.py:668-690`, `scope_classifier.py:532` | 4 derniers tours d'history (`scope_classifier.py:525`) | mistral-small | 67/67 ; 65 `in_scope`, 1 `urgent`, 1 `out_of_scope` |
| 2 | branche RECIT (`is_narrative`) | `pipeline.py:706-711`, `narrative_detect.py:145-156` | seuil **>= 300 caracteres** (ou >=200 + 2 facettes) | mistral-small (clarifier) | **0/67** - jamais declenchee |
| 3 | RouterLLM | `pipeline.py:719-757`, `router_llm.py:658` | `tool_choice="any"`, 12 derniers tours (`router_llm.py:653`) | mistral-small | 64/67 ; 1 refus `cross_domain` |
| 4 | intent + config | `pipeline.py:761-767`, `intent.py:66-79` | top_k 4/5/6/10/12 et lambda MMR 0.3-0.9 selon intent | regex, 0 appel | 67/67 |
| 5 | SELECT bypass | `pipeline.py:784-816` | seulement si intent `factual_pointed`, fuzzy >= 85 | aucun | 1 `select_fallthrough`, **0 bypass** |
| 6 | retrieve | `pipeline.py:825-833` | voir 2.3 | mistral-embed | 64/67 |
| 7 | rerank | `reranker.py:148` | 15 facteurs, 1.0 a 1.6698 | aucun | a chaque retrieve |
| 8 | metadata filter | `metadata_filter.py:387-405` | AND defensif sur 6 champs | aucun | `filter_active` 61/64 |
| 9 | MMR | `mmr.py:24-71` | lambda de l'intent | aucun | 67/67 (sauf court-circuits) |
| 10 | garde-fou geo | `geo_coherence.py:201` | - | aucun | 1 refus geo |
| 11 | few-shot golden QA | `pipeline.py:851`, `pipeline.py:2146` | top-1 sur `golden_qa.index` (676 vecteurs) | **mistral-embed** | a chaque tour non court-circuite |
| 12 | contexte final -> generateur | `generator.py:464` | **`V4_MAX_SOURCES = 5`** (`generator.py:36`) | mistral-medium | 64/67 |

**Appels reseau par tour du chemin classique : 2 chats small (scope + router), 2 embeddings
(retrieval + golden QA), 1 chat medium (generation), plus 1 medium si retry.** Latence mesuree
sur ce run : **mediane 4,61 s, p90 5,93 s, max 7,51 s** (67 tours).

### 2.3 Quel chemin de retrieval est reellement pris : le hybride ADR-058 est mort en serving

`_retrieve_and_filter` (`pipeline.py:1387-1524`) a trois sorties :

- **A - quad sub-index** (`pipeline.py:1426-1480`) si le RouterLLM a cible un sous-ensemble
  **strict** des 4 sub-index. `k_per_sub = QUAD_INDEX_K_PER_SUB = 50`. **Ni BM25, ni double-index,
  ni quota annexes.**
- **B - filtre actif** (`pipeline.py:1487-1524`) : `retrieve_top_k` dense unifie, `k_eff = k x 3`
  avec expansion x2 jusqu'a `k x 10`. **Ni BM25 non plus.**
- **C - Option C v6 / `_retrieve_with_annex_quota`** (`pipeline.py:1943-2097`) : **le seul chemin
  qui execute le double-index, le BM25 et la fusion RRF** (ADR-058).

Repartition mesuree par la forme des cles de `trace.filter_stats` sur les 67 tours :

| Chemin | Signature `filter_stats` | Tours |
|---|---|---:|
| A quad sub-index | `router_active`, `n_retrieved_router`, ... | **62** |
| B filtre actif | `k_initial`, `k_final`, `hit_max`, ... | 2 |
| C Option C v6 (BM25 + RRF) | `annex_quota_active`, `double_index_active`, ... | **0** |
| court-circuit (scope / router / geo) | `None` | 3 |

**`annex_quota_active` et `double_index_active` sont `None` sur 67/67 tours.** Le BM25 n'a donc
tourne sur aucun tour de ce run. Temoin d'instrument : le champ `filter_stats` n'est pas fige, il
rend bien **deux formes distinctes** dans le meme run (A et B), donc l'absence de la forme C n'est
pas une cecite du traceur.

Consequence : le gain de l'ADR-058 (spot-check 4/13 -> 8/13, `docs/DECISION_LOG.md:3575-3578`) a
ete mesure sur un chemin que le RouterLLM contourne **93 % du temps** (62/67). Les 6 index et la
machinerie hybride coexistent, mais **le retrieval servi est un simple dense top-50 sur un
sub-index, suivi d'un filtre et d'un rerank par prieurs**.

### 2.4 Le pool de candidats est minuscule

Sur le cas L01 (`filter_stats` du run) : `router_sub_indexes=["formations"]`,
`n_retrieved_router = 50`, `n_after_filter = 20`, `expansions = 0`, puis MMR vers **4 sources**,
dont **5 au plus** atteindront le generateur.

Le sub-index `formations` compte **37 301 vecteurs** (manifest, cf. 3.1). Le pool de depart
represente donc **50 / 37 301 = 0,13 %** du sous-corpus, choisi par un signal dense dont
l'ecart interne est de 3 %. Et le chemin A **n'expand jamais** : le commentaire
`"expansions": 0,  # quad path n'expand pas` est en `pipeline.py:1478`.

### 2.5 Bug d'ordre : le `top_k_override` du RouterLLM est ecrase par l'intent

`pipeline.py:753-757` applique l'override du router (`top_k_sources = max(top_k_sources, override)`),
puis `pipeline.py:761-767` fait `effective_top_k = top_k_sources` et **l'ecrase immediatement**
par `cfg.top_k_sources` de l'intent des que `use_intent=True` (defaut production).

Mesure sur le run : sur les **33 tours ou le RouterLLM a demande un `top_k_override`
(12 ou 15), 27 ont recu un nombre de sources different** - et les valeurs servies (4, 6, 8, 10, 12)
sont exactement celles de `_CONFIGS` dans `intent.py:66-79`. Exemple : L01 tour 0, override 12,
sources servies 4 (intent `conceptual` -> `top_k_sources=4`).

---

## 3. Les index

### 3.1 Inventaire disque (`ls -la data/embeddings/`, 2026-09-05)

| Fichier | Taille | Type | ntotal | dim | Date |
|---|---:|---|---:|---:|---|
| `formations.index` | 213 Mo | IndexFlatL2 | 52 040 | 1024 | 2026-06-14 |
| `formations_v7_formations.index` | 153 Mo | IndexFlatL2 | 37 301 | 1024 | 2026-06-14 |
| `formations_v7_aides_territoires.index` | 20,5 Mo | IndexFlatL2 | 5 006 | 1024 | 2026-06-14 |
| `formations_v7_metiers.index` | 20,0 Mo | IndexFlatL2 | 4 894 | 1024 | 2026-06-14 |
| `formations_v7_statistiques.index` | 3,4 Mo | IndexFlatL2 | 831 | 1024 | 2026-06-14 |
| `formations_partition_manifest.json` | 715 ko | manifest | - | - | 2026-06-14 |
| `golden_qa.index` | 2,8 Mo | IndexFlatL2 | 676 | 1024 | 2026-05-13 |

Modele d'embedding : `mistral-embed`, 1024 dimensions, vecteurs L2-normalises (norme mediane
1,0000 mesuree sur 3 000 vecteurs). Tous les index sont des `IndexFlatL2` : recherche exhaustive,
pas d'approximation, pas d'index inverse. Aucun index HNSW ou IVF nulle part.

Manifest : `version = v7_quad_index`, `build_date = 2026-06-14 14:34:20`,
`total_fiches_in_source = 52 040`, `excluded_count = 4 008` (`retrieval_eligible=False`,
Vague 1.C). 37 301 + 4 894 + 831 + 5 006 = 48 032 = 52 040 - 4 008. Coherent.

Le double-index main/annex (ADR-058) n'a **pas** de fichier sur disque : il est reconstruit en
memoire par `index.reconstruct()` au premier appel (`pipeline.py:1581-1604`). Comme le chemin C
n'est jamais pris (2.3), il n'est en pratique jamais construit en serving.

### 3.2 Le defaut `aides_territoires` documente le 12/05 est toujours la le 14/06

Composition mesuree des 4 quads a partir du manifest croise avec `formations.json` :

| Sub-index | ntotal | Composition |
|---|---:|---|
| `formations` | 37 301 | formation Parcoursup/MonMaster 34 588 (93 %), `formation_insertion` 2 693 (7 %), `voie_pre_bac` 20 |
| `metiers` | 4 894 | `metier` 2 150 (44 %), `metier_detail` 1 584 (32 %), `metier_prospective` 1 160 (24 %) |
| `statistiques` | 831 | `insertion_pro` 608 (73 %), `parcours_bacheliers` 151 (18 %), `insee_salaire` 59 (7 %), `apec_region` 13 (2 %) |
| `aides_territoires` | 5 006 | **`competences_certif` 4 891 (98 %)**, `crous` 45, `financement_etudes` 28, `calendrier` 21, `territoire_drom` 16, `correction_factuelle` 5 |

`docs/LIMITATIONS.md:216-228` decrit exactement ce desequilibre au 2026-05-12 et propose de
sortir `competences_certif`. Le manifest date du **2026-06-14** : le rebalance n'a pas ete fait.
Effet visible dans le run : L13 tour 1, le router route vers `["formations","aides_territoires"]`
et **8 des 10 sources servies sont des blocs RNCP `competences_certif`** sans rapport avec la
question ("je peux me reorienter en BUT ?").

### 3.3 Hybride dense+BM25 : cable, mais seulement dans un chemin non pris

- BM25 est instancie dans `_retrieve_with_bm25` (`pipeline.py:1610-1628`), appele uniquement
  depuis `_retrieve_with_annex_quota` (`pipeline.py:1975`). Aucun autre appelant
  (`grep -n "_retrieve_with_bm25" src/`).
- Donc : **hybride cable en eval et dans le chemin C, jamais atteint en serving** sur le run
  mesure (2.3), et de toute facon **inerte par defaut d'identifiant de fusion** (section 0).

---

## 4. Le reranker : inventaire, effet mesure, et ce qui ordonne vraiment

Inventaire complet : tableau en 1.3 pour les etages A-D, plus les 14 boosts de domaine
(`reranker.py:44-86`, mapping `reranker.py:117-133`) appliques **uniquement** si
`fiche["domain"] == domain_hint` (ou via le cross-boost `metier -> {metier, metier_detail}`,
`reranker.py:143-145`) :

`apec_region` 1.5, `metier` 1.3, `metier_detail` 1.4, `parcours_bacheliers` 1.3, `crous` 1.4,
`insee_salaire` 1.5, `insertion_pro` 1.4, `metier_prospective` **1.0**, `competences_certif` 1.5,
`formation_insertion` 1.4, `financement_etudes` 1.5, `territoire_drom` 1.5, `voie_pre_bac` 1.4,
`calendrier` 1.5.

Etat des boosts, croise avec les verdicts (voir `02-retrieval-docs.md` sections 1.4, 1.5, 2.7) :

| Boost | Valeur | Effet mesure | Verdict |
|---|---:|---|---|
| SecNumEdu / CTI / Grade Master | 1.0 | couverture 29 fiches sur 52 040 (0,06 %) | **mort**, neutralise le 08/05 |
| `metier_prospective` (DARES) | 1.0 | -30,5 pp verified a x1.5, +24,2 pp hallucination | **nuisible**, neutralise le 26/04 |
| `public` 1.1 / `bac+5` 1.15 / `etab` 1.1 / `parcoursup_rich` 1.2 | actifs | **jamais mesures isolement** | non mesure |
| 14 boosts de domaine | 1.0-1.5 | mesures d'activation seulement (1/18, 2/18...) | effet sur la pertinence non mesure |

**Aucun signal requete-document.** `grep -rniE "cross.?encoder|CrossEncoder|sentence_transformers|
bge-rerank|cohere|voyage|colbert" src/ scripts/` ne rend que des faux positifs sur
`geo_coherence`. Il n'existe ni cross-encoder, ni reranker neuronal, ni score lexical au moment
du rerank.

**Ce qui ordonne reellement le top-k, mesure (section 1.4) : les prieurs documentaires.** Sur 136
questions reelles, la mediane des fiches du dense top-5 encore presentes dans le rerank top-5 est
**0 sur 5**.

Le MMR n'y change rien : il consomme `score` (`mmr.py:44-46`), c'est-a-dire le score deja domine
par les prieurs, et le normalise par son max. Mesure sur 97 questions : l'amplitude du terme de
pertinence apres rerank est 0,315 contre 0,148 pour la similarite inter-fiches. A lambda = 0,7
(defaut general), le terme de diversite pese **0,2 fois** le terme de pertinence ; il ne devient
comparable qu'a lambda = 0,4 (intents `geographic` et `comparaison`). Le MMR amplifie donc les
prieurs plutot qu'il ne les corrige.

---

## 5. Metriques de retrieval : l'instrument du lot 2 ne peut pas fonctionner en l'etat

Le detail des mesures historiques (n_domain_match_top5, recall@k golden, Ragas, BM25 5/8) est
dans `02-retrieval-docs.md` sections 2.1 a 2.5 et n'est pas duplique ici. Deux constats de code
s'y ajoutent, tous deux bloquants.

### 5.1 `--mode raw` n'est PAS gratuit

`scripts/relevance_set/eval_retrieval.py:60` appelle `retrieve_top_k(pipeline.client, ...)`, qui
appelle `embed_texts(client, [question])` (`src/rag/retriever.py:15`). **Un appel `mistral-embed`
par question.** La docstring "deterministe hors embed, AUCUN LLM" est exacte sur les LLM et
trompeuse sur le cout : le mode raw evite les 2 chats small, pas l'embedding.

Estimation pour les 135 questions labellisees : ~40 jetons par question, soit ~5 400 jetons
d'embedding. A l'ordre de grandeur du tarif `mistral-embed`, c'est **inferieur au centime**, mais
c'est un appel reseau : **non lance**, conformement au mandat.

### 5.2 Le runner et les labels ne parlent pas le meme langage d'identifiant

- `scripts/relevance_set/mine_candidates.py:83-84` : `_fiche_id(fiche, idx) = fiche.get("id") or f"idx:{idx}"`.
  Les labels contiennent donc des `"idx:16735"` (verifie dans `labels_partial.json`, premier
  enregistrement `fact-016`).
- `scripts/relevance_set/eval_retrieval.py:51-52` : `_fiche_id(fiche) = str(fiche.get("id") or "")`,
  **sans repli `idx:`**, et `eval_retrieval.py:67` jette les identifiants vides (`if fid:`).
- Mesure corpus : **38 596 fiches sur 52 040 (74,2 %) n'ont pas de champ `id`** - c'est-a-dire
  **toutes les formations**. Les 13 444 qui en ont un sont les annexes, avec des identifiants du
  type `apec_region:bretagne`.

Consequence deterministe : `eval_retrieval.py` **omet purement et simplement toute formation de la
liste de resultats**, et pour les annexes il produit `apec_region:bretagne` la ou les labels
attendent `idx:41230`. Le recall@5 qu'il calculerait serait **0 sur toutes les questions
formation, quelle que soit la qualite du pipeline**. L'instrument mesurerait le format
d'identifiant, pas le retrieval.

### 5.3 Meme cause racine que le bug `idx:-1`

`mine_candidates.py:163` : `fid = _fiche_id(fiche, index_by_fid.get(_fiche_id(fiche, -1), -1))`.
Pour une fiche sans `id`, l'appel interne rend la chaine `"idx:-1"`, qui n'est jamais une cle de
`index_by_fid` (qui contient `"idx:12345"`), donc le `.get` rend -1 et l'identifiant final est
`"idx:-1"`. C'est **la meme cause** que la section 0 : la position corpus n'est pas propagee par
`retrieve_top_k`.

### 5.4 Ce qui est calculable GRATUITEMENT ce soir

Ce qui est **realisable sans un seul appel API** :

1. **Un recall@k reel sur 676 questions** en utilisant `golden_qa.index` comme banc de requetes
   deja embarquees (section 1.1). C'est le point le plus important de ce rapport sur le plan
   outillage : le projet dispose depuis mai d'un banc de 676 requetes gratuites et ne s'en est
   jamais servi pour mesurer le retrieval.
2. **Un banc BM25 complet, illimite et gratuit** (`src/rag/bm25_index.py`), y compris sur les 387
   questions de `candidates.json` et les 135 questions labellisees : recall lexical, rang des
   cibles, diagnostic de tokenisation.
3. **Toutes les mesures de ce rapport** : couverture des boosts, amplitude du rerank, survie du
   dense, geometrie des embeddings, composition des quads, selectivite du filtre.
4. **La correction et la re-validation du bug d'identifiant** (sections 0 et 5.2) : purement
   locale, testable par les tests existants.

Ce qui **n'est pas** calculable gratuitement : le recall sur les 135 labels via `--mode raw`
(1 embedding par question, ~5 400 jetons) et a fortiori `--mode serving` (2 chats small en plus).
Et de toute facon, **avant de corriger 5.2, ces deux modes rendraient 0 sur les formations** : les
lancer ce soir ne mesurerait rien.

---

## 6. Le cas Lyon (L01) : diagnostic, hypotheses classees

Question servie (`results/jarvis_analyse_2026-09-05/runs/local.jsonl`, `id=L01`, `turn=0`) :
"Je suis en terminale generale spe maths et physique a Lyon, j'aime l'informatique mais je ne veux
pas faire une prepa. Qu'est-ce que tu me conseilles ?"

**4 sources servies** : Licence Informatique Lyon 2 (Bron), **Formation d'ingenieur ECE Lyon**,
Licence Informatique Grenoble Alpes, Double licence Physique/Maths Lyon 1.

### 6.1 Ce que le corpus contient vraiment

Balayage direct de `formations.json` (agglomeration lyonnaise, intitule informatique/numerique,
niveau post-bac None/bac/bac+2/bac+3) : **19 fiches**, dont

- **BUT - Informatique, IUT Lyon1 Site de Villeurbanne Doua** (taux d'acces 16 %, 125 places, Public)
- **BUT - Informatique, IUT Lyon1 Site de Bourg-en-Bresse**
- **BUT - Genie electrique et informatique industrielle, IUT Lyon1 Villeurbanne**
- **Licence - Portail Mathematiques / Informatique, Universite Claude Bernard Lyon 1** (Villeurbanne)
- Licence Informatique Lyon 2 (servie) et Licence MIASHS Lyon 2
- 6 BTS SIO et 4 BTS CIEL lyonnais

Le BUT Informatique de l'IUT Lyon 1 est, pour un terminale generale maths-physique qui refuse la
prepa, la reponse canonique. **Il n'a pas ete servi.**

### 6.2 Pourquoi ECE Lyon (privee, bac+5) est arrivee au rang 2

Mesure BM25 sur la question exacte : le **top-15 lexical est integralement compose de fiches
"Formation d'ingenieur Bac + 5 - Bac Serie generale avec la specialite ..."**, ECE Lyon au rang 8
(score 33,40), devant tout le reste. La raison est que l'intitule de ces fiches recopie
litteralement le profil du candidat ("bac serie generale avec la specialite mathematiques /
physique-chimie"). **Le retrieval matche la description de l'eleve, pas la formation cherchee.**
Le meme phenomene se produit cote dense, puisque l'intitule est en tete de `fiche_to_text`.

Ce n'est donc pas un boost : c'est un artefact de nommage du corpus Parcoursup, qui fait remonter
toutes les ecoles d'ingenieur privees post-bac des qu'un lyceen decrit ses specialites.
Verification du reranker sur les memes fiches : ECE Lyon obtient **x1.5180**, le BUT Informatique
Villeurbanne **x1.5246** et la Licence Lyon 2 **x1.5246**. Le reranker ne les separe donc quasiment
pas, et le boost `public` 1.1 ne suffit pas a compenser le `bac+5` 1.15 dont beneficie l'ecole
privee. Contribution du reranker au probleme : **faible mais reelle** (il n'a pas corrige, et le
boost bac+5 avantage l'ecole a 5 ans sur le BUT a 3 ans, pour un lyceen).

### 6.3 Pourquoi le BUT Informatique de Lyon 1 est invisible : la tokenisation

Texte reellement indexe (`fiche_to_text`, `src/rag/embeddings.py:505-520`) :

```
Formation : BUT - Informatique | Etablissement : IUT Lyon1 Site de Villeurbanne Doua |
Ville : Villeurbanne | Diplome : BUT | Niveau : bac+3 | ... | Region : Auvergne-Rhone-Alpes | ...
```

Le mot **"Lyon" n'apparait jamais comme mot isole** : il est colle dans "Lyon1". Le tokenizer BM25
(`bm25_index.py:64`, `re.findall(r"[a-z0-9]+", norm)`) produit le jeton **`lyon1`**, qui ne matche
pas la requete `lyon`. Et la `ville` est "Villeurbanne", la `region` "Auvergne-Rhone-Alpes".

Mesure : sur la question L01, **les deux BUT Informatique de l'IUT Lyon 1 sont absents du top-2000
BM25**. Ils sont invisibles au canal lexical pour une requete disant "a Lyon".

Cote dense, l'effet est plus doux (l'embedding capte "Villeurbanne" et "Auvergne-Rhone-Alpes"),
mais avec un ecart de score de 3 % sur le top-100 (section 1.2), il ne suffit pas a compenser.

### 6.4 Hypotheses classees pour L01

1. **Le pool est trop petit et l'ordre a l'interieur n'est pas gouverne par la question.**
   `n_retrieved_router = 50` sur 37 301, `n_after_filter = 20`, MMR vers 4, generateur plafonne a 5.
   Cause dominante, etablie par les sections 1.2, 1.4 et 2.4.
2. **L'intitule Parcoursup des ecoles d'ingenieur recopie le profil du candidat**, ce qui les fait
   remonter mecaniquement sur toute question de lyceen decrivant ses specialites. Etabli par la
   mesure BM25 (6.2).
3. **"Lyon1" ne se tokenise pas en "lyon"**, ce qui rend les fiches phares de l'IUT Lyon 1
   invisibles au canal lexical. Etabli (6.3). Et de toute facon le canal lexical n'a pas tourne
   sur ce tour (2.3).
4. **Le filtre par region a retire 30 des 50 candidats** (`n_after_filter=20`) sans jamais pouvoir
   en ajouter : un filtre ne repare pas un rappel manquant.
5. **Le boost `bac+5` (1.15) avantage l'ecole d'ingenieur sur le BUT** alors que la question est
   posee par un terminale. Contribution faible, mais dans le mauvais sens.

Hypothese ecartee : ce n'est **pas** un trou de corpus. Les 19 fiches existent, dont les BUT.
C'est un defaut de rappel et d'ordonnancement.

### 6.5 Le cas L13 : la bonne reponse etait la, sous la falaise des 5 sources

L13 tour 0, "je vise une licence informatique a Toulouse". Les 12 sources retournees par le
pipeline contiennent, **au rang 6**, `Licence - Informatique | Universite Toulouse III` (Toulouse),
avec un score de **1,1717 - le deuxieme meilleur score de la liste** (le premier est 1,1748).
C'est le MMR qui l'a place au rang 6 ; un tri par score l'aurait mis au **rang 2**.

Le generateur ne voit que **5 sources** (`V4_MAX_SOURCES = 5`, `generator.py:36`, applique en
`generator.py:464`). La reponse produite dit : *"Aucune licence informatique pure a Toulouse
n'apparait dans mes donnees."* Le systeme detenait la bonne fiche et a affirme son absence
parce qu'elle etait une place sous la falaise.

C'est le cas d'ecole du couplage entre trois defauts separes : ordre gouverne par les prieurs,
MMR qui diversifie sur un signal plat, et fenetre de 5 sources.

---

## 7. Multi-tour et profil : ce qui est perdu

### 7.1 La requete de retrieval du chemin classique ignore l'historique

`pipeline.py:825-833` : `_retrieve_and_filter(question=question, ...)`. C'est **le message
courant seul**. L'historique n'atteint le retrieval par aucun canal :

| Consommateur | Historique recu | Fichier:ligne |
|---|---|---|
| ScopeClassifier | **4 derniers tours** | `scope_classifier.py:525` |
| RouterLLM | **12 derniers tours** | `router_llm.py:653` |
| **requete de retrieval (dense + BM25)** | **aucun** | `pipeline.py:828` |
| generateur | historique complet, **non tronque** | `generator.py:495-496` |

Il n'existe **aucune reecriture de requete en requete autonome** (pas de standalone-rewrite,
pas de query rewriting LLM) dans le chemin servi. Un tour 2 du type "et a Lyon ?" ou "je peux me
reorienter en BUT ?" est embarque tel quel.

Effet mesure, L13 tour 1 : question "Et si je rate ma premiere annee, qu'est-ce qui se passe ?
Je peux me reorienter en BUT ?". Le RouterLLM, lui, **a** l'historique et conserve correctement
`region=occitanie` et `secteur=[informatique, numerique]` dans les criteres. Mais la requete
vectorielle, elle, ne contient ni "informatique" ni "Toulouse". Resultat : **8 des 10 sources
servies sont des blocs RNCP `competences_certif`** ("Ingenieur de l'Ecole polytechnique",
"Enseigner dans le premier degre", "CQP Educateur de vie scolaire") avec des scores autour de
0,016. La reponse commence par "Je n'ai pas de licence informatique a Toulouse dans mes sources",
alors que le tour precedent en avait servi deux.

Note d'echelle : ces scores de 0,016 sont des **scores RRF bruts** (`1/(60+rang)`) produits par
`_retrieve_from_sub_indexes` en mode multi-sub-index (`pipeline.py:1929-1933`). Le chemin
mono-sub-index rend, lui, des scores denses autour de 0,8. Les deux echelles cohabitent dans le
meme champ `score` et sont ensuite multipliees par les memes facteurs de rerank ; c'est coherent
a l'interieur d'un appel, mais tout seuil absolu (comme `ANNEX_QUOTA_MIN_SCORE = 0.6`) devient
sans signification selon le chemin emprunte.

### 7.2 Le seul chemin qui utilise la conversation pour le retrieval est inatteignable en pratique

Le mode recit (`_prepare_narrative`, `pipeline.py:872-983`) fait tout ce qu'il faut :
`build_narrative_clarifier_input(question, history)` concatene les tours utilisateur,
`build_narrative_retrieval_query(profile, clarifier_input)` forge une requete a partir du profil
(`narrative_query.py:103-143`), et le format COMPARAISON declenche un retrieval **par option
nommee** (`pipeline.py:946-959`).

Il est garde par `is_narrative(question)` (`pipeline.py:709`), dont la regle est purement une
longueur : **>= 300 caracteres**, ou >= 200 avec 2 facettes (`narrative_detect.py:33-34, 145-156`).

Mesure sur le run : **0 des 60 premiers tours** de la batterie a ete detecte comme recit, alors
que `ORIENTIA_NARRATIVE_MODE=1` etait bien pose (`results/jarvis_analyse_2026-09-05/run_battery.py:59`)
et que `trace.format_decision` est `null` sur **67/67** tours. Temoin positif obtenu avec le meme
instrument : un recit fabrique de 486 caracteres rend `is_narrative = True`. La fonction marche ;
c'est le seuil qui ne correspond pas a ce que les gens ecrivent.

---

## 8. Le filtre structure ne filtre presque rien

`apply_metadata_filter` (`metadata_filter.py:387-405`) fait un ET sur 6 criteres, chacun
**defensif** : champ absent sur la fiche -> la fiche passe (`_match_region` `metadata_filter.py:249-250`,
`_match_secteur` `metadata_filter.py:314-318`).

Couverture reelle des champs sur les 52 040 fiches (2026-09-05) :

| Champ de filtre | Fiches renseignees |
|---|---:|
| `secteur` | **0 (0,0 %)** |
| `budget` | **0 (0,0 %)** |
| `ville` | 20 602 (39,6 %) - dont **18 012 fiches ont la cle `ville` presente mais vide** |
| `region` | 28 242 (54,3 %) |
| `niveau` | 35 233 (67,7 %) |
| `alternance` | 7 573 (14,6 %) |

Le RouterLLM peuple pourtant `secteur` sur presque toutes les questions (L01 :
`secteur=["informatique","numerique"]` ; L13 : idem). **Ce critere est un no-op integral.**
`budget_max` aussi. Le filtre ne discrimine donc que sur `region` et `niveau`, et seulement pour
la moitie du corpus.

Point important : le filtre s'applique **apres** le retrieval (`pipeline.py:1447`). Il ne peut
que retirer des candidats, jamais en trouver. Sur L01 il a retire 30 des 50 candidats sans rien
apporter.

---

## 9. Verdict : les 5 defauts de retrieval les plus couteux

### 1. Rien n'ordonne le top-k en fonction de la question

Le signal dense est plat a l'interieur du top-100 (ecart de score **3,2 %**, mediane sur 136
questions reelles), le reranker applique des prieurs documentaires d'amplitude **67 %**, et il
n'existe **aucun** signal requete-document au moment du classement (pas de cross-encoder).
Resultat : mediane **0 sur 5** des fiches du dense top-5 survivent dans le rerank top-5.

Preuve : sections 1.2, 1.3, 1.4. Cas : L01 (ECE Lyon rang 2), L13 (bonne fiche rang 6).

Piste : **cross-encoder auto-heberge** sur le top-100. `BAAI/bge-reranker-v2-m3` est multilingue,
tourne sur CPU, cout marginal nul, et c'est le seul composant qui reintroduit un signal
requete-document. C'est le fix a plus fort levier du dossier. En complement immediat et gratuit :
ramener les prieurs a un role de departage (amplitude <= 5 %) au lieu d'un role d'ordonnancement,
puisque leur effet sur la pertinence n'a **jamais** ete mesure isolement.

### 2. Le hybride ADR-058 est mort deux fois

(a) Il n'est pas atteint : **62/67 tours** passent par le quad sub-index qui n'appelle ni BM25 ni
double-index ; `annex_quota_active` est `None` sur **67/67**.
(b) Quand il est atteint, sa fusion RRF ne fusionne rien : les rangs dense et BM25 portent des
cles differentes, temoin positif a l'appui (section 0).

Preuve : sections 0 et 2.3.

Piste : corriger `_orig_index` (3 lignes, section 0), puis **appeler BM25 sur TOUS les chemins de
retrieval**, y compris le quad, avec une vraie fusion RRF. C'est le fix le moins cher du dossier
et il debloque en meme temps l'instrument de mesure du lot 2.

### 3. La falaise des 5 sources coupe des reponses correctes deja retrouvees

`V4_MAX_SOURCES = 5` (`generator.py:36`) alors que le pipeline en produit 10 ou 12, et que le
MMR reordonne sur un signal plat. L13 : la bonne licence est au rang 6, le systeme repond
"aucune ... dans mes donnees". Le meme motif est deja documente ailleurs comme du sur-refus
(`audit_empirique_2026-06-09/L2-Harnais-eval.md:51` : "trouve au rang 1 mais REFUSE par le
pipeline") ; ici la cause est localisee et arithmetique.

Piste : cross-encoder (defaut 1) puis passer la fenetre a 8-10 sources, ou au minimum faire
coincider `V4_MAX_SOURCES` avec `effective_top_k`. Et supprimer le MMR sur les intents ou il
n'apporte rien : il opere sur un signal dont l'amplitude de pertinence vient des prieurs.

### 4. Le retrieval multi-tour n'a pas de memoire

La requete vectorielle est le message courant seul (`pipeline.py:828`), sans reecriture en requete
autonome, alors que le scope classifier voit 4 tours et le router 12. L13 tour 1 le montre
crument : 8 sources RNCP hors-sujet et une reponse qui contredit le tour precedent. Le seul
chemin qui utiliserait la conversation, le mode recit, est garde par un seuil de **300 caracteres**
et n'a tire **0 fois sur 60**.

Piste : une **reecriture de requete autonome** par mistral-small (un appel deja budgete, on en fait
deja deux), ou a minima concatener les 2 derniers tours utilisateur dans la requete de retrieval -
version gratuite, testable immediatement sur le banc golden_qa.

### 5. Le filtre structure et le decoupage en 4 index promettent une precision qu'ils ne rendent pas

`secteur` et `budget` sont renseignes sur **0 fiche sur 52 040** : les deux criteres que le
RouterLLM peuple le plus volontiers ne font rien. `region` couvre 54 % du corpus, avec passage
defensif pour le reste. Le sub-index `aides_territoires` est a **98 % `competences_certif`**, defaut
decrit le 12/05 et toujours present dans le manifest du 14/06 ; il produit les 8 blocs RNCP servis
sur L13 tour 1. Et le `top_k_override` du router est ecrase par l'intent sur **27 tours sur 33**
(`pipeline.py:761-767`).

Piste structurelle, dans l'ordre de rentabilite :
1. **Un seul index propre** + BM25 sur tout, et suppression des 4 quads : ils ne sont justifies
   par aucun ADR (`docs/ADR-064`, `docs/ADR-065` n'existent pas), et le decoupage cree lui-meme
   le probleme qu'il pretend resoudre (`aides_territoires`).
2. **Filtrage structure avant le vecteur** ("SQL sur les attributs, vecteur sur le texte") : sur
   L01, un pre-filtre `region=Auvergne-Rhone-Alpes AND niveau<=bac+3` ramene le candidat set a
   quelques milliers de fiches, et le top-50 dense y est alors informatif. Aujourd'hui le filtre
   passe apres, sur 50 candidats deja tires.
3. **Renseigner `secteur`** (ou le retirer du contrat du RouterLLM) : un critere a 0 % de
   couverture qui est peuple a chaque requete est un mensonge silencieux du systeme sur lui-meme.

Le retrieval agentique multi-etapes n'est **pas** la prochaine marche : tant que le classement du
top-k n'a pas de signal de requete, ajouter des tours de retrieval multiplie le bruit.

---

## 10. Ce qu'il faut savoir avant de citer ce rapport

1. Les mesures des sections 1.2 a 1.4 utilisent les 676 vecteurs de `golden_qa.index` comme
   requetes. Ce sont de vraies questions, mais embarquees sous la forme
   `question_seed + " | " + question_refined` (deux paraphrases concatenees), pas la question
   nue. L'effet sur la geometrie n'a pas ete quantifie.
2. Les statistiques de chemin (section 2.3) portent sur **un seul run de 67 tours**
   (`results/jarvis_analyse_2026-09-05/runs/local.jsonl`). Elles etablissent que le chemin C est
   contourne sur ce run, pas qu'il l'est toujours.
3. L'effet des prieurs `public` / `bac+5` / `etab` / `parcoursup_rich` sur la **pertinence** n'a
   toujours ete mesure par personne, ici comme ailleurs. Ce rapport mesure leur **amplitude** et
   leur **effet de reordonnancement**, pas leur signe.
4. Aucune correction n'a ete appliquee au repo. Les scripts de mesure vivent hors repo, dans
   `/tmp/claude-1000/.../scratchpad/`.

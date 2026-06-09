# LIMITATIONS — OrientIA pour la démo INRIA AI Grand Challenge

Document d'honnêteté : ce qu'OrientIA **ne fait pas** ou ne mesure pas, à la date de soumission INRIA. Mis à jour à chaque pivot. Source de vérité pour le STUDY_REPORT et la défense orale.

**Dernière mise à jour** : 2026-05-08 (post-Phase A verrouillage : audit v7 daté + sources partielles documentées).

---

## 1. Scope produit

OrientIA est un **assistant d'orientation post-bac français** pour lycéens, étudiants en réorientation, et adultes en reconversion. Il n'est **pas** :

- Un conseil personnalisé (pas de psy, pas de Psy-EN — le système redirige vers SCUIO/CIO/Psy-EN sur enjeu fort, cf Tier 0 + Tier 3 stub `append_phase_projet`).
- Un outil de placement (pas de candidature Parcoursup, pas de simulateur d'admission).
- Un comparateur d'écoles privées non labellisées (la liste blanche tier ADR-055 exclut volontairement EPITA, Epitech, Guardia, IONIS, École 42 du corpus principal).
- Un agent de reconversion adulte profond (champ `voie_pre_bac` + bac pro/techno couvert, mais VAE / bilan de compétences hors scope).

---

## 2. Architecture : single-shot → multi-tour minimal en cours

À la date de cette mise à jour, le pipeline est **single-shot** : une question → une réponse RAG. Le `history` est accepté en paramètre `pipeline.answer()` mais **n'est pas encore exploité comme contexte conversationnel structuré**.

- **Phase E du plan en cours** : ajout d'une couche `ConversationState` minimale (history buffer + `last_sources` + `extracted_profile`) pour permettre l'enchaînement de questions ("la 2e formation que tu as citée…", "et à Bordeaux ?"). Préférence par défaut : Path B minimal vs réintégration de l'archi hiérarchique 3-agents (Sprint 9, en cours de re-audit).
- **Architecture agentique full (Axe 2 — ProfileClarifier, Decomposer, Composer)** : POC validé (ADR-032, branche `axe2/pydantic-profileclarifier`), **pas en prod**. Décision pivot 2026-05-06 : système v4.1 strict + multi-tour minimal > orchestration agentic complète.

**Conséquence aujourd'hui** : un utilisateur qui veut creuser doit reformuler complètement. **Conséquence post-Phase E** : il pourra enchaîner naturellement sur 3-5 tours sans perdre le profil/contexte.

---

## 3. Mesure benchmark : re-bench complet planifié Phase D

**Bench Run F+G** (100q × 7 systèmes × 3 juges) terminé le 2026-04-16 a coûté ~$42 (~$24 Claude Sonnet, ~$5 GPT-4o, ~$3 Haiku, ~$10 generation). **Méthodo conservée**, mais résultats absolus obsolètes (corpus 343 → 47k, prompt v3.2 → v4.1, validator absent → présent).

**Bench post-Vague 1+3 (Phase D du plan)** : décidé 2026-05-08 avec recharge Anthropic ($30-40), exécution sur `golden_60.json` étendu (50 ground-truth + 8 adversarial + 2 cross-domain). Inclut recall@1/5/10/MRR/nDCG@10, rubric Claude+GPT-4o, Haiku factcheck, latency p50/p95.

**Métriques disponibles à la place** :

| Métrique | Source | Statut |
|---|---|---|
| `recall@1`, `recall@5`, `recall@10`, `MRR` | `scripts/eval_recall.py` sur `data/golden_eval/golden_50.json` | Reproductible offline, gratuit |
| `honesty_score` validator + `flagged` | mini-bench v4.1 strict_v4 (23q internes) | Reproductible, gratuit |
| Spot-check 13q manuel | `scripts/spot_check_v5.py` | Coût négligeable (~$0.10) |
| Verbatim utilisateurs beta | `results/beta_test/` | Coût négligeable |
| **Rubric Run F (Claude/GPT-4o juge, /18)** | `src/eval/run_judge_multi.py` | **Non rejouée post-Vague 1** |
| **Honesty Haiku fact-check (ADR-014)** | `src/eval/run_haiku_factcheck.py` | **Non rejouée post-Vague 1** |

**Lecture honnête** : on **ne peut pas démontrer** que les Vagues 0/0.5/1 améliorent la rubric externe (juges LLM tiers) par rapport à Run F. On démontre que `recall@k` interne progresse, et que les utilisateurs jugent `utile/utilisable ≥ 70%` sur beta. Ces deux preuves sont **complémentaires** mais **pas substitutives** d'un re-run benchmark.

---

## 4. Hallucinations & validateurs

**Couches actives en prod (mode v4.1 strict)** :
- `validator/rules.py` — anti-discrimination, codes admin masqués, distance d'écoles
- `validator/corpus_check.py` — vérification claims vs corpus (seuil 0.55 depuis Vague 0.5)
- `validator/presence.py` — infos obligatoires manquantes
- `post_process.py` — strip URLs hallucinées, fix markdown brisé
- 6 hallucinations factuelles **explicitement bannies** (cf `feedback_hallucinations_interdites.md`)

**Couches absentes / opt-in** :
- `Tier 1 auto-halluc scorer` — **pas en prod** (mentionné dans plan Tier 1-4, jamais livré). Si la démo révèle une nouvelle hallu non couverte par les rules, **pas de fallback automatique**.
- `Layer3` (Mistral Small LLM-judge) — opt-in via `enable_layer3=True`. Connu pour biais visibility (+~8% honesty fictive sur claims sourcés). **Non utilisé en mini-bench reporté** pour éviter sur-confiance.
- `Tier 3 redirection systématique Psy-EN/CIO sur enjeu fort` — stub `append_phase_projet` en prod (`pipeline.py:421`) mais **logique de déclenchement basique** (pas de NLI ni détection émotionnelle fine).

---

## 5. Cutoff & fraîcheur des données

| Source | Cutoff | Refresh prévu |
|---|---|---|
| Parcoursup CSV | 2025 (taux d'accès, places, profils admis) | Manuel à chaque release officielle (juillet) |
| MonMaster | 2025 | Manuel |
| ONISEP | 2024-2025 | Manuel |
| ROME 4.0 (France Travail) | v460 (offline ZIP) | Pas de refresh automatique |
| InserSup | 2024 (DEPP) | Manuel |
| InserJeunes (LP + CFA) | 2024 | Manuel |
| DARES Métiers 2030 | publication 2024 | N/A (projection figée) |
| **Calendrier Parcoursup 2027** | **non couvert** | **Vague 3.4 prévue, peut être post-démo** |
| **France Travail temps réel (offres, salaires)** | **non couvert** | Reporté post-démo (D3b ROME API) |

**Conséquence** : pour un lycéen qui demande "quand est la phase complémentaire 2027 ?", OrientIA peut donner les **dates 2026** ou rediriger vers `parcoursup.fr` — pas de garantie de fraîcheur 2027 sans Vague 3.4 livrée.

---

## 6. Liste blanche sources (ADR-055)

Le corpus principal n'inclut **que des sources tier 1 officielles** :
- Tier 1 (autorisé) : Parcoursup, ONISEP, InserSup, InserJeunes, France Travail, DARES, ministères, écoles publiques labellisées
- Tier 2 (bloc-listé sauf décision explicite) : associations professionnelles, syndicats, fédérations
- Tier 3 (exclu) : avis Reddit / forums, blogs, sites privés non labellisés, Wikipedia

**Conséquence** :
- Une question "que vaut la formation X (école privée non labellisée)" reçoit une réponse honnête : "pas de données vérifiables, voici le label/absence de label".
- Le système ne reproduit **pas** les avis subjectifs ChatGPT/Claude qui mélangent sources mixtes.

---

## 7. Couverture data — limites structurelles connues

Audit v7 daté du 2026-05-08 (`docs/AUDIT_PHASE_0_V7_2026-05-08.md`) — corpus prod = 47 214 fiches.

| Limite | Cause | Mitigation |
|---|---|---|
| **45,9% des fiches sans région** (mesure réelle 2026-06-09 ; ancien 41,5% corrigé) | RNCP nationaux + ONISEP descriptifs + LBA offres distantes : structurellement nationaux | Flag `retrieval_eligible=false` exclut 38% du retrieval (Vague 1.C, runtime `pipeline.py:679`) |
| **20,9% des fiches sans niveau** | Mêmes sources, idem | Inférence partielle depuis `duree`/`type_diplome` Stage 5 |
| **33% sans URL vérifiable v7** | Sources hétérogènes (audit Phase 0 mesure `url`/`url_parcoursup`/`url_onisep`/`lien_form_psup`) | `url_canonical` v7 (Vague 3.8) couvre ~80% via cascade fallback ONISEP search — exposé dans réponses |
| **MonMaster `statut` Public/Privé `null`** | Ambiguïté ministérielle, décision Matteo 2026-05-08 (drop 1.B) | L'utilisateur peut filtrer manuellement, ou poser la sous-question |
| **Densité chiffres médiane = 2.0 (cible 3.0)** | Conséquence `insertion_pro` à 31,3% — voulu défensif ADR-054 (refus > Cereq trompeur) | À re-mesurer post-bench Phase D si gap mesuré |
| **Tier 2 = 13 fiches seulement** | Liste blanche très stricte ADR-055 (47 201 fiches Tier 1) | Discipline assumée |

## 7bis. Sources data partiellement ingérées

Sources présentes dans `data/raw/` ou `src/collect/` mais **non intégrées au corpus prod v7**. Documentées explicitement pour transparence INRIA :

| Source | Statut | Volume non-utilisé | Décision |
|---|---|---|---|
| **APEC PDFs** (`data/raw/apec/`) | 15 PDFs (24 MB) jamais parsés (baromètre rémunération cadres 2025, prévisions 2026 par région, jeunes diplômés bac+5) | ~10-30 fiches potentielles cadres+régions | **Skip** parsing : pas de catégorie cadre dédiée dans `golden_60`. Re-prioriser si bench Phase D montre gap "carrière adulte". `apec_regions_corpus.json` (13 fiches hardcoded) couvre l'essentiel régional. |
| **LBA dump statique** (`data/processed/lba_formations.json`) | 6 646 fiches issues d'un appel API antérieur 2026-04-23. Module `src/collect/labonnealternance.py` désormais scaffold-only (token expiré). | 4 008 fiches intégrées (post-Stage 4 DROP_EMPTY) mais flaguées `retrieval_eligible=false` (offres distantes alternance, pas formations indexées formation+ville) | **Documenté** : dump statique conservé en lecture pour le pipeline. Refresh dépend du token `LBA_API_TOKEN` (procédure dans `docs/TODO_MATTEO_APIS.md`). |
| **France-Travail modules** (`src/collect/romeo.py`, `ft_*`, `rome_api.py`) | Modules collect existants mais **non appelés par `run_merge_v3.py`** (zéro grep `romeo\|ft_` dans le pipeline d'ingestion). `data/raw/france-travail/romeo.json` (1.1 KB) reste un smoke test. | Données potentielles : ROMEO mapping métier, ROME API live, marché travail temps réel | **Documenté** : modules en réserve. ROME 4.0 offline (zip v460) déjà exploité via `src/collect/rome.py` (1 584 fiches `metier_detail`). API live = D3b reportée post-démo. |
| **V2 rewrite Haiku** (`src/rewrite/`, `tests/test_rewrite/`, `scripts/finalize_rewrite_v6.py`, `scripts/prepare_rewrite_chunks.py`) | Module développé ~2026-05-08 pour réécriture Haiku des textes annexes (Phase 3 V2). Aucun import depuis `src/rag/` ou `src/api/`. | Non quantifié | **Archivé** dans `_archive_rewrite_phase3v2_pre_pivot/` Phase A — pivot 2026-05-06 priorise v4.1 strict + multi-tour minimal. Réutilisable si retour à Phase 3 V2 post-démo. |

---

## 7ter. Convention paths legacy = alias actif

Le projet utilise un **double binding** pour les paths corpus / index :

- **Path versionné explicite** : `data/processed/formations_v7.json` + `data/embeddings/formations_v7.index` — source de vérité, immuable, daté.
- **Path "courant" alias** : `data/processed/formations.json` + `data/embeddings/formations.index` — copie active du dernier corpus promu. Beaucoup de scripts (legacy + tests + collect) utilisent ce path en hardcoded.

**Au 2026-05-08 (vérifié)** : `formations.json` ≡ `formations_v7.json` (47 214 fiches identiques, timestamp identique).

**Implication INRIA** : un reviewer qui clone le repo et lance les scripts par défaut tombe sur l'état prod. Pour reproduire un état antérieur, utiliser explicitement `formations_v5.json` ou `formations_v6.json` (présents pour audit longitudinal).

**Procédure de promotion** (documentée ADR-059) :
```bash
# Build le nouveau corpus versionné
ORIENTIA_MERGE_OUT_PATH=data/processed/formations_vX.json python -m src.collect.run_merge_v3
# Re-embed
python scripts/rebuild_faiss_index.py --corpus data/processed/formations_vX.json --index data/embeddings/formations_vX.index
# Promote : copy vers alias courant
cp data/processed/formations_vX.json data/processed/formations.json
cp data/embeddings/formations_vX.index data/embeddings/formations.index
```

---

## 8. Reproductibilité

**Ce qui est reproductible aujourd'hui** :
```bash
git checkout <SHA-de-soumission>
source .venv/bin/activate
pip install -r requirements.lock
python scripts/audit_phase_0_v5.py --corpus data/processed/formations_v6.json
python scripts/spot_check_v5.py
python scripts/mini_bench.py --phase strict_v4 --out results/repro/mini_bench.json
python scripts/eval_recall.py --golden data/golden_eval/golden_50.json --out results/repro/recall.json
pytest tests/
```

**Ce qui demande des credits API à reproduire** :
- Ré-embedding corpus complet (~$5-10 Mistral)
- Mini-bench (~$0.50 Mistral, gratuit côté validator)
- Spot-check 13q (~$0.10 Mistral)
- Run F+G complet (~$42 — Anthropic + OpenAI + Mistral)

**Ce qui demande un volume Railway / déploiement** :
- API FastAPI prête (`src/api/server.py`), endpoint `/answer` pré-warm sub-indices au boot (Vague 0.5 finalisée 2026-05-08)
- UI beta Next.js : à déployer Vercel post-soumission INRIA

---

## 9. Ce qu'OrientIA n'a pas (volontairement) à la date de soumission

- **Fine-tuning RAFT** (Axe 3 STRATEGIE_VISION) : reporté Phase 3+. Bottleneck dataset 700-900 paires (~7-10j calendaire).
- **Cron refresh mensuel automatique** (D7) : refresh manuel par release officielle.
- **API France Travail OAuth** (D3b ROME temps réel) : reporté post-démo.
- **Calculator score Parcoursup, comparateur drag-drop, carte interactive** (Axe 4 UX U2/U3/U4) : reportés post-démo.

---

## 10. Décisions actées qui pourraient être contestées

Le jury INRIA pourra interroger ces choix — réponses préparées :

| Choix | Justification |
|---|---|
| **Mistral Medium pour la génération** (vs GPT-4o ou Claude) | Souveraineté française, coût acceptable, suffisant pour le contrat v4.1 strict (R1-R6). Latency 7s tolérable. |
| **Liste blanche stricte tier 1 vs IA généralistes** | Refus de reproduire les hallu mainstream sur écoles privées non labellisées. Trade-off couverture vs fiabilité assumé. |
| **Single-shot vs agentic à date de soumission** | Pivot 2026-05-06 a priorisé "système qui mesure et qui marche" plutôt qu'architecture spéculative. POC agentic existe (ADR-032). |
| **Pas de re-bench rubric externe post-Vagues** | Anthropic credits non rechargés. Substitué par recall@k + verbatim beta. Limite explicite. |
| **Corpus français uniquement** | Cible explicite : orientation post-bac française. Pas d'ambition Erasmus/international à ce stade. |

---

*À actualiser après chaque session de promotion corpus, chaque Vague livrée, et après le verdict beta test.*

---

## 11. Bugs résiduels identifiés en runtime live (2026-05-12)

Diagnostic depuis trois questions live posées via la passerelle plateforme `orientai-platform.fr` au matin du 2026-05-12 :

### 11.1 Validator `corpus_check` paraphrases (FIXÉ — commit du 12 mai)

**Symptôme observé** : sur une question type *"Quelles écoles de cybersécurité en Bretagne ?"* ou *"Comment se réorienter après une L2 de droit ?"*, le pipeline produit une réponse correcte avec sources pertinentes, puis le validator `corpus_check` flag à tort *"Formation non présente dans la base"* sur des paraphrases comme *"Licence Droit – Parcours multilingue"*, déclenchant un BLOCK injustifié.

**Cause racine** : le `Pattern 3` (tiret cadratin) de `src/validator/corpus_check.py` capturait les segments après le tiret comme `etab` sans exclure les variantes de formation (`Parcours X`, `Option X`, `Spé X`, `Mention X`, `Voie X`, `Filière X`). Le `Pattern 2` (parenthétique) avait déjà reçu le fix par le commit `cedd6e1` (2026-05-11) ; le `Pattern 3` était resté en dehors.

**Fix appliqué** : negative lookahead aligné sur `Pattern 2` (Option/Parcours/Spé(cialité)/Mention/Voie/Filière). Validé sur 13 cas (8 *should skip* + 5 *should extract*), 235 tests pytest verts (vs 233 avant). Note : la plateforme prod doit redéployer le commit pour que le fix soit visible côté utilisateur.

### 11.2 Sub-index `aides_territoires` mal proportionné (LIMITATION DOCUMENTÉE, fix v2 post-rendu)

**Symptôme observé** : sur *"quelles sont les crous à Paris ?"*, le pipeline retourne *"Je n'ai pas de formation ni d'information sur les CROUS à Paris dans mes sources"* alors que la fiche CROUS Paris (`region='Île-de-France'`, `ville='Paris'`, text contenant *"Logements étudiants CROUS à Paris | Région : Île-de-France | Nombre de résidences : 82"*) **existe dans le corpus** avec `retrieval_eligible=True`.

**Cause racine** : le sub-index FAISS `aides_territoires` (4 979 vecteurs) est composé à 98 % de fiches `competences_certif` (4 891 fiches RNCP de compétences). Les 18 fiches CROUS sont **noyées dans le bruit dense embedding** — le top-50 FAISS du sub-index pour cette requête retourne 47 `competences_certif` + 3 `financement_etudes`, **zéro fiche CROUS**. Par ailleurs, sur l'index global (47 220 vecteurs), la fiche CROUS Paris n'est pas dans le top-300 dense — son `text` (360 caractères, focal sur les services pratiques) a une faible similarité cosinus avec une query généraliste type *"quelles sont les crous à Paris"*, dominée par des fiches métier/financement_etudes plus longues et plus génériques.

**Atténuation appliquée** (commit du 12 mai) : ajout d'un fallback `quad path → v1 path` quand `n_after_filter == 0`. Améliore le cas (le pipeline ne renvoie plus 0 sources) mais ne résout pas complètement : le `v1 path` retourne des formations parisiennes plutôt que des résidences CROUS, le LLM refuse honnêtement.

**Fix structurel (post-rendu)** :

- **Rebalance du sub-index `aides_territoires`** : sortir `competences_certif` (4 891 fiches RNCP de compétences professionnelles) vers un sous-index dédié `competences` ou les rattacher à `formations`. Le sub-index aides_territoires retrouve son équilibre (CROUS, financement, calendrier, DROM, ≈ 70 fiches).
- **Rebuild des embeddings CROUS avec un text plus dense** : ajouter explicitement le nom des résidences, services, tarifs moyens, contacts dans le text indexé pour augmenter la couverture lexicale.
- **Activation du BM25 hybride sur le path filter-actif** : actuellement le path v1 utilise uniquement FAISS dense pour le retrieve filtré ; le BM25 (déjà disponible via `bm25_index.py`) capturerait littéralement le mot *"crous"* et garantirait que les 18 fiches remontent au top.

Aucune de ces trois actions n'est triviale à conduire le soir avant un rendu : rebuild de sub-index + re-embedding = ~10 min de calcul + validation sur le mini-bench. Documenté ici pour traçabilité, planifié post-soumission INRIA.

### 11.3 Désynchronisation potentielle plateforme `orientai-platform.fr`

La conversation live partagée le 2026-05-12 montre encore le bug `Pattern 2` (BTS Cybersécurité Option B) flag-é à tort, alors que `cedd6e1` du 2026-05-11 a déjà corrigé ce cas. Hypothèse : **le déploiement de la plateforme accuse un retard sur `main`** (continuous deployment non immédiat). Action : vérifier le commit déployé côté Claudette / passerelle.

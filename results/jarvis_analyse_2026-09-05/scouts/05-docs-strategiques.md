# Scout 05 - Documents stratégiques OrientAI : promesses, cible IA, écarts, évaluation

Audit en lecture seule. Sources lues intégralement : le dossier INRIA PDF (44 p.), les 6 documents
`refonte-ia-2026`, `STRATEGIE_VISION_2026-04-16.md` (939 l.), `FUTURE_PHASES_2026-05-18.md`,
`LIMITATIONS.md`, `BENCH_GATES.md`, `BENCHMARK_PHASE_D_2026-05-11.md` (résumé),
`INRIA_AI_ORIENTATION_PROJECT.md` (sections clés), `SESSION_HANDOFF.md` (état), `TODO_MATTEO_APIS.md`,
`README.md`, `LLM_Final.md`, plus vérification par grep dans `src/` et par `git log`.

Convention : chaque affirmation porteuse cite son fichier et sa ligne, ou la page du PDF. Quand une
chose n'est pas mesurée, c'est écrit.

---

## 0. Les trois choses à retenir avant le détail

1. **Le dossier jury ne ment pas beaucoup, il promet peu.** Le PDF est explicitement prudent : il
   s'annonce prototype (p. 4, 34-35), documente le désaccord entre ses deux juges (p. 33), et liste
   ses propres angles morts. Les vraies promesses non tenues sont peu nombreuses et connues de
   l'équipe. Le risque jury est plus faible que le risque produit.
2. **Le vrai problème mesuré n'est pas l'hallucination, c'est l'inutilité.** Sur 497 questions
   passées dans le pipeline réel, 171 sont des refus honnêtes, 15 des substitutions de métrique, 59
   des réponses avec au moins une affirmation non sourcée, contre 188 réponses sourcées
   (`audit_empirique_2026-06-09/results/groundedness_full.json`, agrégé). L'audit L1 le dit
   explicitement : « ce n'est pas un problème de fidélité qui s'effondre, c'est un problème de
   PERTINENCE et de CALIBRAGE » (`audit_empirique_2026-06-09/L1-Batterie-empirique.md:32`).
3. **La cible IA optimale de juin est très largement non implémentée**, et le plan qui la déclinait
   s'est arrêté en cours de route : citation inline vraiment causale, décodage contraint, HyDE,
   réécriture de requête, reranker cross-encoder, lookup structuré généralisé, FALC, modèle de
   raisonnement, mémoire persistante, éval 500+ questions gatée en CI : aucun de ces items n'est
   dans `src/` au chemin servi (grep, détail §2 et §5).

---

## 1. Les promesses faites au jury (dossier PDF)

Statuts : **tenue** / **partielle** / **non tenue** / **non mesurable**. La preuve repo est donnée
quand elle existe.

| # | Promesse (citation courte) | Page | Statut | Preuve |
|---|---|---|---|---|
| 1 | « a corpus of official French sources » : **47 214 records from 25 official public sources** | p. 28 (§5.3) | **tenue, et dépassée** | `LLM_Final.md:29` : 52 040 fiches servies au 2026-07 ; `OrientIA/CLAUDE.md` idem. Incohérence de chiffre relevée à l'époque : front 55 606, seed « ~47 000 » (`Livrable-2-Audit-existant.md:84`) |
| 2 | « the corpus is **refreshed monthly by an automated ingestion pipeline (src/collect/)** » | p. 28 | **partielle, et contredite en interne** | Le workflow existe : `.github/workflows/data-refresh-monthly.yml:27` (cron `0 3 1 * *`). MAIS il **ne rebuild pas l'index FAISS** (`data-refresh-monthly.yml:17` : rebuild embeddings « manuel via workflow_dispatch ») : un corpus rafraîchi n'est donc pas un corpus servi. Et `LIMITATIONS.md:70-81` liste **toutes** les sources en refresh « Manuel », `src/collect/refresh_cron.py` (le module prévu par STRATEGIE D7) est **absent**. Que le cron ait tourné depuis avril : **non vérifié** (hors ligne) |
| 3 | « **No figure without a source.** Every admission rate, every median salary [...] is tied to a public, dated reference » | p. 23 (§4.2.1) | **partielle** | Règle R3 réellement dans le prompt servi (`src/prompt/system.py`), et depuis le 16/07 une vérification déterministe chiffre-vs-source-citée existe : `src/validator/citation_check.py:1-22`. Sa docstring dit noir sur blanc que le contrat v4 promettait cette vérification « depuis 2026-05-06 » et qu'elle « n'avait jamais été implémentée (audit 15/07 : rien de contraint mécaniquement) ». Mesure résiduelle : 77 chiffres hallucinés sur le run 497q de juin (`groundedness_full.json`, agrégé) |
| 4 | « the absence of a relevant source [...] **results in a refusal to answer rather than a fabrication** » | p. 23 | **tenue sur le hors-périmètre, sur-tenue sur le périmètre** | 12/13 refus corrects mesurés (voir #10). Mais 171/497 refus honnêtes en juin, dont des sur-refus prouvés : `fact-01` (BUT Info Lyon 1) est trouvé **au rang 1** du retrieval et refusé quand même par la garde anti-ambiguïté (`L1-Batterie-empirique.md:47-51`) |
| 5 | « **No prognosis based on socio-demographic profile** [...] verified by a set of **adversarial evaluations** » | p. 23 | **partielle : la règle existe, la suite adversariale anti-biais dédiée n'existe pas** | Règle anti-discrimination réelle dans `src/validator/rules.py`. La suite adversariale **anti-biais socio-démographique systématique** est décrite comme cible à construire (`Livrable-1-Cible-IA-optimale.md:150`, `:208`), et le tableau de métriques la donne comme cible non atteinte (`Livrable-1:220` « Fuite socio-démographique 0, Bloquant »). Les 13 questions adversariales du protocole portent sur fausses écoles / dates / injections, pas sur le biais social (PDF p. 32) |
| 6 | « **markers of distress detected in conversation** [...] trigger [...] the display of the national helpline numbers (3114, Fil Santé Jeunes) » | p. 24 (§4.2.2) | **tenue côté backend, non surfacée côté front (à date de juin)** | Classe `urgent` complète et câblée par défaut : `src/rag/scope_classifier.py` (pré-filtre regex l. 53-70, réponse de crise l. 198-205), `src/rag/factory.py:91`, `src/rag/pipeline.py:443-444`, `src/api/server.py:462-463`, tests `tests/test_scope_classifier.py` (312 l.) - références de `Livrable-2-Audit-existant.md:109-112`. Front : aucune UX de crise, numéros en gras sans lien `tel:` (`Livrable-2:115`). **Recall non mesuré** (`Livrable-2:116`), et 2 faux positifs sur 42 questions normales mesurés en juin (`L1-Batterie-empirique.md:41`) |
| 7 | « **Explicit consent.** No element is transmitted without the user's validation on a dedicated screen » (briefing conseiller) | p. 24 | **non tenue à date de l'audit** | `Livrable-2-Audit-existant.md:128` : grep `consent/checkbox/j'autorise` = 0 dans le front. Résumé Mistral Small réel, transmis sans case à cocher |
| 8 | « a **network of state-recognised counsellors** » / rendez-vous confirmé en 10 minutes | p. 22-24 | **non tenue : maquette** | `Livrable-2:127` : banner « Démonstration », conseillers et créneaux fictifs, `BookingConfirmation.tsx:223` affiche « un e-mail a été envoyé » alors que rien n'est envoyé |
| 9 | « a **dashboard** that centralises the calendars and administrative procedures [...] across more than six official platforms » | p. 5, p. 24 (§4.2.3) | **non tenue : statique** | `Livrable-2:129` : 28 échéances réelles mais 100 % statiques, badge « 7 » codé en dur, persona salarié = stub, aucune connexion aux portails |
| 10 | « OrientAI v4.1 **refuses correctly in twelve cases out of thirteen, that is 92.3 %**. The rate reaches 100 % on the purely out-of-scope questions » | p. 32 (§5.7) | **tenue et re-mesurée** | `BENCHMARK_PHASE_D_2026-05-11.md:38-40` : Gate 4 passe, refus cross_domain 100 %, adversarial 90 % |
| 11 | « On **sourcing**, OrientAI v4.1 achieves a score markedly higher than any baseline tested [...] the widest gap measured » | p. 32 | **tenue, chiffrée** | `BENCHMARK_PHASE_D_2026-05-11.md:24-26` : +0,86 pt /3 sourçage, +0,50 pt /3 neutralité institutionnelle (juge Claude) |
| 12 | « the cost of these choices [...] penalise **geographical diversity and discovery** » ; « generalist LLMs [...] obtain higher scores » | p. 32 | **tenue (aveu assumé, chiffré depuis)** | `BENCHMARK_PHASE_D:30-33` : -1,69 pt diversité géographique, -1,52 pt découverte |
| 13 | « the two external judges **diverge substantially** [...] GPT-4o invalidates it » | p. 33 | **tenue (honnêteté méthodologique)** | Aveu direct dans le PDF ; la question du κ inter-juges reste une gate à ≥ 0,4 (`docs/BENCH_GATES.md:52`) |
| 14 | « the user's question is **never logged** in the server logs [...] explicitly encoded in the production code (src/api/server.py) » | p. 33 (§5.8) | **tenue** | Confirmé par l'audit indépendant : « RGPD (question jamais loggée, conforme dossier) » (`Livrable-2-Audit-existant.md:47`) |
| 15 | « **RGAA 4.1 compliance** [...] Full keyboard navigation [...] Dyslexia mode [...] Audio playback and voice dictation » | p. 25 (§4.3) | **tenue, et c'est le point le plus solide** | `Livrable-2:143-150` : skip-link, `role=log aria-live=polite`, 241 occurrences `aria-*`, OpenDyslexic self-hosté réel, TTS + dictée fr-FR, 10 fichiers de tests a11y + E2E Playwright. Nuance honnête : aucun audit manuel certifié des 156 critères (`Livrable-2:153`) |
| 16 | « **Automatic FALC reformulation** of responses currently under development » | p. 25 | **non tenue (mais annoncée comme en cours)** | `Livrable-2:154` : stub 503, visuel seulement. Aucun module FALC dans `src/` (grep `falc` = 0 résultat) |
| 17 | « User tests with these tools [NVDA, VoiceOver, TalkBack] **are planned** » | p. 25 | **non tenue** | `Livrable-2:155` : aucun test lecteur d'écran humain tracé |
| 18 | « the **prioritisation of state-recognised institutional labels in the reranker** » présentée comme un des deux choix structurants validés | p. 32 | **non tenue de fait : signal mort** | `Livrable-2-Audit-existant.md:75` : SecNumEdu 21 fiches sur 47k (0,04 %), CTI 7, Grade Master 1 - boosts **neutralisés à 1.0** faute de couverture. Le seul signal vivant est `public_boost` |
| 19 | « the current system is **single-turn** [...] without building a persistent model of the user » (limite assumée) | p. 34 (§5.9) | **levée partiellement depuis** | Multi-tour livré le 13/06 mais **uniquement sur le mode récit** et **stateless** : `src/rag/pipeline.py:892-893` « accumulation par ré-extraction [...] stateless, sans stockage profil serveur ». Commits `feat(narrative): R2 multi-tour A+B` (13/06) et `fix(api): cap history content 3000 -> 9000 (débloque multi-tour récit)` (13/06). Mode récit livré **flag OFF par défaut** (`docs/SESSION_HANDOFF.md:13`) |
| 20 | « retrieval **does not use contextualised query rewriting (HyDE, query expansion)** » (limite assumée) | p. 34-35 | **toujours vraie au 2026-09** | grep `hyde`, `query_rewriter` dans `src/` = 0 résultat. `src/agent/tools/query_reformuler.py` existe mais appartient au chemin agent, pas au pipeline servi par `src/api/server.py:166` (`make_production_pipeline`) |
| 21 | « an **expansion of the evaluation set to several hundred questions** [...] a **structured user test** with upper-secondary students and guidance counsellors [...] a **longitudinal evaluation** » (conditions préalables au déploiement) | p. 35 | **1 sur 3 tenue** | Éval passée à 497 questions (`audit_empirique_2026-06-09/eval_set_full.json`). Test utilisateur structuré : voir §4, les artefacts existants sont des **personas**, pas des lycéens. Longitudinal : rien dans le repo |
| 22 | « A public mechanism for **reporting biases and errors**, modelled on pharmacovigilance » ; « biannual auditing [...] by INETOP » | p. 35 | **non tenue (posée comme condition de passage à l'échelle)** | `Livrable-3-Comparaison-ecarts.md:31` : « Décrit dans dossier, non construit ». Rien dans `src/` |
| 23 | « **Sovereign hosting** [...] Mistral [...] trajectory towards OVHcloud Confidential or DINUM » | p. 33 | **tenue au stade prototype** | Mistral partout (`LLM_Final.md:25-38`), Railway pour le prototype comme annoncé. Self-host : non entamé, et c'est ce que le dossier annonce |
| 24 | Pilote quantitatif N=180, résultats statistiques (p = 0,033 filière/origine ; p = 0,006 réorientation/filière ; non-effet IA générative p = 0,984) | p. 15-19 | **non mesurable côté repo** | Le pilote est un travail d'enquête, hors code. Le PDF assume lui-même ses limites (échantillon Dauphine, N=180, p. 21) |

**Lecture d'ensemble** : sur 24 promesses, 9 tenues, 7 partielles, 6 non tenues, 2 hors périmètre
repo. Les 6 non tenues sont concentrées sur les **modules 2 et 3** (relais humain, dashboard) et sur
les **conditions de gouvernance**, pas sur le moteur. Le dossier les présente d'ailleurs souvent
comme « à construire » : le risque de mensonge est faible, le risque de **produit incomplet** est
élevé.

---

## 2. La cible IA optimale (Livrable 1, 2026-06-09) vs le code

Le Livrable 1 se donne pour cadre de « concevoir la cible sans se brider par l'architecture ni les
moyens actuels » (`Livrable-1-Cible-IA-optimale.md:6`). Voici composant par composant ce qui a
atterri dans `src/`.

| Composant cible | Décrit où | Implémenté ? (fichier) | Mesuré ? |
|---|---|---|---|
| Affectation modèle par tâche (Small routage, Medium génération) | `Livrable-1:45-47` | **Oui** : `LLM_Final.md:25-32` (Small scope/routeur, Medium génération) | Oui, latence et coût par étage (`LLM_Final.md`) |
| **Modèle de raisonnement (Magistral) pour les arbitrages non factuels** | `Livrable-1:48`, `:54` | **Non** - grep `magistral` dans `src/` = 0 | Non |
| Self-host souverain vLLM (open-weight) | `Livrable-1:58` | **Non** - API Mistral | Non |
| Data contract typé, provenance, `null` explicite | `Livrable-1:71-76` | **Oui** : `src/rag/fact_card.py`, `audit_empirique_2026-06-09/data_contract.py`, `ge_suite.py` | Oui (`results/ge_validation.json`) |
| Versioning du corpus traçable depuis chaque réponse | `Livrable-1:76` | **Oui, tardivement** : `src/api/provenance.py` + commit `3cac645` « fingerprint de provenance par réponse » (16/07) | Oui (validation par fingerprint dans le script de deploy) |
| Couverture : agri, privé hors RNCP, outre-mer réel, reconversion adulte | `Livrable-1:82-85` | **Non** - Parcoursupagri absent (`INVENTAIRE-data-corpus.md:57` le laisse conditionnel) ; outre-mer 16 fiches (`Livrable-2:23`) ; reconversion = trou mesuré, 57 % d'hallucination sur cette catégorie (`PLAN-ameliorations-pre-vivatech.md:23`) | Oui, le trou est mesuré |
| Audit de source avant indexation (exigence AI Act) | `Livrable-1:90` | **Partiel** : `ge_suite.py` fait un contrat data, pas un audit de **représentativité/biais** | Non pour le volet biais |
| Détection de drift corpus | `Livrable-1:91` | **Partiel** : détection de drift > 10 % dans `data-refresh-monthly.yml:11` uniquement | Non |
| **Adaptive RAG (classifieur de complexité route la stratégie)** | `Livrable-1:97` | **Non** - le routeur choisit des sous-index, pas une stratégie (`src/rag/router_llm.py`) | Non |
| **Réécriture de requête (sigles, informel -> institutionnel)** | `Livrable-1:103`, tâche R1 `PLAN:60-64` | **Non** au chemin servi - `src/rag/query_rewriter.py` n'existe pas. `src/rag/sigle_expand.py` couvre les sigles seuls | Non |
| **HyDE pour questions vagues** | `Livrable-1:104`, tâche R2 `PLAN:66-70` | **Non** - grep = 0 | Non |
| **Décomposition en sous-requêtes** | `Livrable-1:105` | **Non** au chemin servi - grep `decomposer` = 0 | Non |
| Hybride dense + BM25 + RRF | `Livrable-1:109` | **Oui** : `src/rag/retriever.py`, `src/rag/bm25_index.py` | Oui (`recall_probe.json`) |
| **Reranker cross-encoder appris** | `Livrable-1:110` | **Non** - `src/rag/reranker.py` reste des boosts multiplicatifs heuristiques (grep `cross_encoder` = 0) | Non |
| Partition thématique (sous-index) | `Livrable-1:111` | **Oui** : `scripts/build_quad_subindexes.py` | Oui, et un défaut mesuré : sous-index `aides_territoires` à 98 % de `competences_certif` (`LIMITATIONS.md:218`) |
| MMR | implicite `Livrable-1:258` | **Oui** : `src/rag/mmr.py` | Oui |
| **Lookup structuré généralisé (aucun chiffre par la génération)** | `Livrable-1:115-117` | **Partiel** : `src/lookup/structured_select.py` existe (le « SELECT bypass ») mais reste un cas particulier, comme le dit la cible elle-même. Le chiffre passe encore par la génération sur le chemin normal | Oui pour le sur-refus qu'il crée (`L1:47-51`) |
| **Multi-hop pour comparaisons** | `Livrable-1:121` | **Non** - grep `multi_hop` = 0 | Non |
| **Citation inline causale au moment de la génération** | `Livrable-1:135`, pivot n°1 `:290` | **Partiel, par le prompt seulement** : commit `3eb684b` (16/07) « porte R8 (alternative cadrée) et R9 (citation entrelacée) du legacy vers le prompt servi v4 strict ». C'est une consigne, pas une contrainte | Oui, gate avant/après : commit `0c255e2` « gate VERT » (16/07) |
| **Structured outputs / constrained decoding** | `Livrable-1:136` | **Non** - grep `constrained`, `structured_output` = 0 | Non |
| **Vérification de groundedness en ligne, phrase par phrase, avant envoi** | `Livrable-1:137` | **Non** - la groundedness est mesurée hors ligne par un juge (`judge_groundedness.py`), pas dans `pipeline.answer()`. Ce qui existe en ligne est la vérification déterministe chiffre-vs-source (`src/validator/citation_check.py`, 16/07) et le `corpus_check` fuzzy | Oui hors ligne, non en ligne |
| Contrat R1-R7 durci, longueur calibrée par intent | `Livrable-1:142` | **Partiel** : cap 250 mots remplacé par 4 sections **uniquement en mode récit** (`src/prompt/system_narrative.py`, `SESSION_HANDOFF.md:19-22`) | Oui pour le mode récit (gate `gate_narrative_1d_sectioned.md`) |
| **Suite adversariale anti-biais socio-démographique** | `Livrable-1:150`, `:208` | **Non** - aucun subset anti-biais dans `audit_empirique_2026-06-09/` (subsets : détresse, factuel, géo, reconversion, salaire, garde-fou) | Non |
| RGPD par construction (question jamais loggée) | `Livrable-1:161` | **Oui** | Oui (`Livrable-2:47`) |
| **Multi-turn avec mémoire de session** | `Livrable-1:169` | **Partiel** : `history` accepté (`src/rag/pipeline.py:532`), exploité **seulement sur la branche récit** (`pipeline.py:709-711`), profil ré-extrait à chaque tour | Oui sur le mode récit uniquement |
| **Mémoire de trajectoire persistante (opt-in RGPD)** | `Livrable-1:170` | **Non** : `src/state/user_profile_schema.json` (56 l.) est un schéma, `src/agents/hierarchical/session.py` (115 l.) n'est pas branché sur le chemin servi (seul `src/eval/systems.py:259` l'appelle, comme système de bench `hierarchical_v1`) | Non |
| Détection de détresse fiabilisée + UX de crise | `Livrable-1:181`, note `:185` | **Backend oui, UX front non** (voir promesse #6) | Recall **non mesuré**, faux positifs mesurés |
| Briefing consenti, handoff propre | `Livrable-1:182-183` | **Non** (voir promesse #7) | Non |
| **FALC réel via modèle dédié** | `Livrable-1:195` | **Non** - grep `falc` = 0 dans `src/` | Non |
| Audio natif TTS + dictée | `Livrable-1:196` | **Oui côté front** (`Livrable-2:148`) | Non audité |
| **Audit RGAA certifié 156 critères** | `Livrable-1:197` | **Non** (`Livrable-2:153`) | Non |
| **Jeu d'éval 500+ questions versionné** | `Livrable-1:207` | **Oui, atteint** : `eval_set_full.json` = 497 questions, gelé (`VERDICT_gel_497q_2026-06-11.md`) | Oui |
| **Gating CI bloquant** | `Livrable-1:227` | **Partiel** : `.github/workflows/golden-ci.yml` (gate golden déterministe bloquant, commit `c88b605`) + `canary-answer.yml`. Le gate 497q complet n'est pas en CI | Partiellement |
| Observabilité (Langfuse) | `Livrable-1:233` | **Oui** : `infra/langfuse/`, `src/observability/`, 7 scripts | Oui, rapports `docs/OBSERVABILITY_*` |
| **Pharmacovigilance des biais, audit bisannuel, frugalité documentée** | `Livrable-1:234-236` | **Non** | Non |

**Score brut de la cible** : sur 34 composants, **12 implémentés**, **9 partiels**, **13 absents**.
Les 5 « déplacements » que le Livrable 1 désignait comme décisifs (`Livrable-1:288-294`) sont, au
2026-09 : n°1 citation inline **partielle (prompt seul)**, n°2 lookup généralisé **non**, n°3
adaptive RAG + query understanding + cross-encoder **non**, n°4 éval industrielle **à moitié** (497 q
oui, anti-biais et test utilisateur non), n°5 fonctions promises surfacées **non** (FALC, UX crise,
RGAA certifié).

---

## 3. Les écarts (Livrable 3) et ce que le plan pré-VivaTech a réellement produit

### 3.1 Statut des 18 écarts du Livrable 3

Croisement du tableau `Livrable-3-Comparaison-ecarts.md:16-33` avec l'état du code et le `git log`.

| # | Écart | Sévérité déclarée | Statut au 2026-09 | Preuve |
|---|---|---|---|---|
| 1 | Fidélité / citation post-hoc | CRITIQUE | **Partiellement traité** : R8+R9 portés au prompt servi le 16/07, gate vert ; la citation reste non contrainte au décodage | commits `3eb684b`, `0c255e2` |
| 2 | Chiffres / lookup structuré | HIGH | **Partiellement traité** : vérification déterministe chiffre-vs-source ajoutée le 16/07 sur les 2 chemins dont stream | commit `69d4f05` ; `src/validator/citation_check.py` |
| 3 | Détresse : UX + recall | HIGH | **Backend fiabilisé (A1 : faux positifs 9 -> 0, `PLAN:8`), UX front non vérifiable ici, recall toujours non mesuré** | `PLAN-ameliorations-pre-vivatech.md:8` |
| 4 | Seuil d'alerte UI à 0.3 | CRITIQUE (quick win) | **Non vérifiable dans ce repo** (le front est `~/projets/OrientAI_Platform`) | `Livrable-2:122` |
| 5 | Système d'évaluation | HIGH | **Avancé** : 497 q gelées, juge cross-family, gates ; **mais** pas d'anti-biais, pas de test utilisateur réel, pas de longitudinal | `eval_set_full.json`, `L2-Harnais-eval.md` |
| 6 | Tests chemins critiques (router, FactCard, scope) | HIGH | **Avancé** : suite passée de 2500 à 3202 tests verts (`OrientIA/CLAUDE.md`) ; couverture router/FactCard non re-vérifiée ici | `OrientIA/CLAUDE.md` |
| 7 | Retrieval (adaptive, query understanding, cross-encoder) | MEDIUM | **Non traité** | grep §2 |
| 8 | Couverture corpus | MEDIUM | **Partiellement traité** : re-ingestion et typage 14/06 (commits `d28e2c0`, `1e5a71e`, `b321094`), ROME 4.0 en fact_card (`ab98c3c`) ; agri et outre-mer toujours absents | `git log` 14/06 |
| 9 | Multi-turn / mémoire | MEDIUM | **Partiel, mode récit seulement, flag OFF** | `SESSION_HANDOFF.md:13` |
| 10 | Relais humain réel | HIGH | **Non traité côté ce repo** | - |
| 11 | Dashboard connecté | MEDIUM | **Non traité** | - |
| 12 | FALC | MEDIUM | **Non traité** | grep = 0 |
| 13 | Accessibilité certifiée | LOW | **Non traité** | - |
| 14 | Identité service public (Marianne) | MEDIUM | **Front, hors périmètre** | - |
| 15 | Modèles (Magistral, self-host) | MEDIUM | **Non traité** ; en revanche les versions de modèles ont été **pinnées** le 16/07 (fin des `-latest`), ce que la cible ne demandait pas et qui vaut mieux | commit `3cac645` |
| 16 | Gouvernance (pharmacovigilance, audit bisannuel) | - | **Non traité** | - |
| 17 | Latence / cold-start 40 s | LOW | **Traité** : `warmup_generation()` existe (`src/rag/pipeline.py:618`) et est appelé côté serveur | grep |
| 18 | Hygiène (test rouge, tree sale, chiffre corpus) | LOW | **Traité pour le chiffre** : source unique 52 040 alignée sur `/health` (`OrientIA/CLAUDE.md`, `LLM_Final.md:29`) | - |

### 3.2 Ce que le PLAN pré-VivaTech prévoyait vs ce qui a été fait

Le plan (`PLAN-ameliorations-pre-vivatech.md`) décomposait 12 tâches. Croisement avec `git log` :

| Tâche | Prévu | Fait ? | Trace |
|---|---|---|---|
| Bloc A (mapping FactCard des champs déjà présents) | `INVENTAIRE-data-corpus.md:69` (« gain gratuit prioritaire ») | **Fait** | commit `15f0711` « feat(fact_card): expose sélectivité master + profil_admis source-aware (Bloc A) » (09/06) |
| C1 re-ingestion Parcoursup (~6 000 fiches manquantes) | `PLAN:16-20`, redéfini `INVENTAIRE:63` | **Partiellement fait** : typage et dérivation de champs le 14/06 (`d28e2c0` type_diplome + géocode région, `1e5a71e` lycée pro/onisep) ; la re-ingestion des ~6 061 formations n'apparaît pas comme telle | `git log` 14/06 |
| C2 reconversion adulte / CPF | `PLAN:22-26` | **Non fait** : aucun `src/collect/reconversion_adulte.py` | ls `src/collect/` |
| C3 contrat GE avant indexation | `PLAN:28-32` | **Fait** | `audit_empirique_2026-06-09/ge_suite.py`, `results/ge_validation.json`, `PROOF_ge_violation.txt` |
| C4 ré-embed + re-mesure | `PLAN:34-38` | **Fait** | commit `c1b003c` « e2e re-embed + fills AVANT/APRÈS + golden gate VERT » (14/06), `RUNBOOK_reembed_bench_1403.md` |
| F1 citation inline | `PLAN:44-48`, cible groundedness > 0,80 | **Fait tardivement (16/07), par le prompt** ; cible 0,80 : la mesure de juin donne 0,704 de moyenne sur les réponses affirmatives (`groundedness_full.json`, agrégé), le gate de juillet est déclaré vert mais sur un autre périmètre | commits `3eb684b`, `0c255e2` |
| F2 validateur : rejeter tout chiffre non sourcé | `PLAN:50-54`, cible 78 -> < 50 chiffres hallucinés | **Fait le 16/07** ; la baisse effective **n'est pas mesurée dans les artefacts lus** | commit `69d4f05` |
| R1 réécriture de requête | `PLAN:60-64` | **Non fait** | grep |
| R2 HyDE | `PLAN:66-70` | **Non fait** | grep |
| U1 garde anti-ambiguïté du SELECT | `PLAN:76-80` | **Non tracé** : aucun commit sur `structured_select.py` visible dans les 60 derniers | `git log` |
| U2 règle anti-substitution | `PLAN:82-86`, cible 26 -> < 10 | **Non tracé** | `git log` |
| D1 jeu de questions de démo | `PLAN:92-96` | **Fait** (mode récit + gates), sous une autre forme : `gate_narrative_*`, `demo` non trouvé | `audit_empirique_2026-06-09/results/` |

**Lecture** : le plan a été exécuté sur son volet **data et mesure** (Bloc A, C3, C4, harnais, gel du
banc 497 q), très peu sur son volet **retrieval** (R1, R2 : zéro), et son volet **fidélité** (F1, F2)
a attendu **le 16 juillet**, soit un mois après VivaTech. Entre le 13/06 et le 16/07, l'effort a
basculé sur le **mode récit** (12 commits `narrative` le 13/06) - une fonctionnalité qui n'était dans
aucun des trois livrables ni dans le plan.

---

## 4. Ce que les documents promettent côté ÉVALUATION, et où ça en est

### 4.1 Les cibles chiffrées annoncées

| Métrique promise | Cible | Source | État mesuré |
|---|---|---|---|
| Groundedness phrase par phrase | ≥ 0,95 bloquant | `Livrable-1:214` | **0,704** de moyenne sur 264 réponses affirmatives (`groundedness_full.json`, juin) |
| Faithfulness | ≥ 0,90 bloquant | `Livrable-1:215` | **0,489** Ragas bimodale (`Livrable-2:53-55`, `FUTURE_PHASES:36`) ; cible intermédiaire fixée à 0,65 (`FUTURE_PHASES:61`), **atteinte non tracée** |
| Recall@5 | ≥ 0,85 bloquant | `Livrable-1:216` | **0,65** mesuré (`BENCHMARK_PHASE_D:43-44`), sous la cible interne de 0,75 elle-même sous la cible idéale |
| Answer relevancy | ≥ 0,85 | `Livrable-1:217` | **jamais mesurée** (le doc de 05/18 la pose comme à faire, `FUTURE_PHASES:55`) |
| Context precision | ≥ 0,80 | `Livrable-1:218` | **jamais mesurée** ; `context_recall` = 0,021, déclaré artefact de protocole (`OrientIA/CLAUDE.md`, `FUTURE_PHASES:55`) |
| Refus correct hors-périmètre | 100 % | `Livrable-1:219` | **100 % cross_domain, 90 % adversarial** (`BENCHMARK_PHASE_D:38-40`) |
| Fuite socio-démographique | 0, bloquant | `Livrable-1:220` | **jamais mesurée**, aucune suite de test |
| Latence p95 | ≤ 8 s | `Livrable-1:221` | **11,24 s** (`BENCHMARK_PHASE_D:39`), sous la gate interne de 12 s mais au-dessus de la cible idéale |
| Rubric Claude ≥ 12/18, κ inter-juges ≥ 0,4 | gates 5 | `docs/BENCH_GATES.md:50-53` | Rubric passée en Phase D ; κ 0,46-0,59 revendiqué (`INRIA_AI_ORIENTATION_PROJECT.md:539-542`) mais **sur le Run F d'avril**, pas sur v4.1 |
| Cibles V2 : rubric > chatgpt_natural +2, honesty > 0,80, actionabilité 5/5 sur 90 %, fraîcheur 80 %, citation precision 95 %, préférence utilisateur > 70 % | `STRATEGIE_VISION_2026-04-16.md:677-685` | **Aucune de ces 7 cibles n'a de mesure dans le repo.** Les baselines « naturels » Playwright (B2) n'existent pas, les métriques déterministes B3/B5/B6 non plus |

### 4.2 Les tests utilisateurs promis

C'est le point le plus fragile, et il est **structurant pour un produit qui vise le lycéen**.

- Le PDF promet « a **structured user test** conducted with upper-secondary students and guidance
  counsellors, in order to **measure the system's actual usefulness rather than its indirect score** »
  (p. 35).
- Le Livrable 1 le reprend : « Test utilisateur structuré avec lycéens et conseillers d'orientation :
  mesurer l'utilité réelle, pas un score indirect » (`Livrable-1:225`), et ajoute l'évaluation
  longitudinale (`:226`).
- Le PLAN le renvoie au post-VivaTech : « tests utilisateurs réels avec lycéens et conseillers »
  (`PLAN-ameliorations-pre-vivatech.md:107`).
- `STRATEGIE_VISION` en faisait un principe directeur : « **Les étudiants réels sont la vérité.** Si
  les chiffres benchmark disent OrientIA gagne mais 0 étudiant·e ne l'utiliserait, on a échoué »
  (`STRATEGIE_VISION_2026-04-16.md:819-820`), avec la tâche B4 « 5-10 étudiants × 20q blind »
  (`:668`).

**Ce qui existe réellement dans le repo** : trois packs, `results/user_test/`, `user_test_v2/`,
`user_test_v3/`, datés du 18 au 27 avril (`git log`). Ils contiennent des retours très détaillés et
très utiles (grille par question, clair/utile/confiance sur 5, verbatims). Mais :

- Les profils sont **cinq personas nommés**, réutilisés d'un pack à l'autre : Léo 17 ans, Sarah 20
  ans, Thomas 23 ans, Catherine 52 ans, Dominique 48 ans conseiller Psy-EN
  (`docs/INRIA_AI_ORIENTATION_PROJECT.md:723-726`). Léo est **exactement le personnage fictif du
  scénario d'usage du dossier** (PDF p. 22, « Léo is in his final year of an STI2D »).
- `results/user_test/answers_CO.md:1` commence par : « **Ok je change encore.** Dominique, 48 ans,
  conseiller d'orientation-psychologue [...] **Très respecté dans le métier.** [...] **Dominique teste
  OrientIA en mode audit professionnel.** » C'est une consigne de jeu de rôle, pas un compte rendu
  d'entretien.
- `FUTURE_PHASES_2026-05-18.md:227` planifie « re-test sur **5 profils (Léo / Sarah / Catherine /
  Dominique / nouveau)** » : on ne « re-teste » pas des humains en les listant comme des
  configurations.
- Le script d'origine, lui, visait bien de vrais lecteurs : « Goal: give **2-3 lycéens** real answers
  to read and provide feedback on » (`scripts/prepare_user_test_pack.py:4-5`). Rien dans le repo
  n'établit que ces lycéens ont existé.

**Conclusion, avec sa réserve** : je ne peux pas prouver négativement qu'aucun humain n'a lu ces
réponses (un retour oral ne laisserait pas de trace). Mais la seule trace disponible est celle de
personas simulés, et le document de communication en tire une affirmation forte - « **Cinq personas
humains ont testé le moteur IA dans des conditions réelles** »
(`docs/INRIA_AI_ORIENTATION_PROJECT.md:723`) et « Personas humains testés (panel) : 5 » dans les
« chiffres-clés défendables » (`:39`). **Cette affirmation est porteuse et non établie.** Elle est
exactement le genre de chose qu'un jury ou un partenaire institutionnel peut demander à voir.

À noter que le contenu de ces retours, même simulé, a produit des findings justes et non triviaux :
verbosité (« je décroche à la moitié »), codes techniques bruts affichés à l'utilisateur
(`cod_aff_form: 6083`, `M1817`, `RNCP 39308`), mélange source citée / connaissance générale qui
détruit la confiance, formulations limites sur le genre (« 100 % de femmes -> environnement
potentiellement plus accessible si tu es une candidate ») - `results/user_test/feedback_17ans.md`.
Ces findings sont utilisables tels quels ; c'est leur **statut de preuve** qui ne l'est pas.

### 4.3 L'instrument qui manque, et qui est nommé

Le plan pose la bonne question et ne l'a pas résolue : « on ne sait qu'on donne la **MEILLEURE**
réponse que relativement à un étalon défini et mesurable [...] Aujourd'hui on mesure si la réponse
est FIDÈLE aux sources ; **on ne mesure pas encore si elle est la MEILLEURE réponse possible** »
(`PLAN-ameliorations-pre-vivatech.md:111`). Il en décompose l'instrument en 4 briques
(`PLAN:114-117`), dont la première est un corpus de réponses idéales validées par des conseillers.

État au 2026-09 : le chantier a démarré le 16/07 et s'est arrêté en plein milieu.
`scripts/relevance_set/STATE.md` : 387 questions minées, 9 092 candidats, **135/387 labellisées**,
coupure sur quota de session, plus un bug de miner à corriger avant de reprendre
(`fiche_id "idx:-1"`, 382 candidats touchés). Le dernier commit du dépôt est ce checkpoint
(`c7402d3`, 16/07). Il n'y a **aucun étalon de réponse idéale** ni juge de pertinence.

---

## 5. Les cinq idées jamais implémentées les plus importantes pour l'utilité d'un lycéen

Classement par impact sur ce qu'un lycéen obtient réellement, pas par difficulté.

### 1. La réécriture de requête et le HyDE (le lycéen qui ne connaît pas les mots)

- **Où c'est promis** : `Livrable-1:101-104` en fait un enjeu **d'équité** explicite : le système
  cherche « avec les mots de l'utilisateur », ce qui pénalise « précisément le public défavorisé que
  le projet vise ». Tâches R1 et R2 du plan (`PLAN:60-70`). Le PDF le reconnaît comme limite (p. 34-35).
- **État** : absent (`grep hyde|query_rewriter` = 0 dans `src/`).
- **Pourquoi ça compte** : c'est le seul écart de la liste qui contredit directement la thèse sociale
  du dossier. Le pilote établit que 53,6 % des élèves s'orientent par le cercle privé (PDF p. 11) et
  que le capital informationnel familial est ce qui transmet le vocabulaire institutionnel (p. 7-8).
  Un système qui exige ce vocabulaire pour bien répondre reproduit l'inégalité qu'il prétend corriger.
- **Raison donnée** : effort classé L / MEDIUM et renvoyé au post-VivaTech (`Livrable-3:22`, `:78`).
  Aucune raison technique ; c'est un arbitrage de calendrier.

### 2. La mémoire de trajectoire persistante et le vrai multi-tour

- **Où c'est promis** : `Livrable-1:169-171` ; PDF p. 34 (« reduces the usefulness of the service for
  long-term support, which presupposes at the very least a memory of the user's trajectory ») ;
  `STRATEGIE_VISION:149-155` en fait la cause racine n°3 du sous-performance.
- **État** : multi-tour existant **uniquement en mode récit**, **stateless** (`src/rag/pipeline.py:892-893`),
  et livré **flag OFF** (`SESSION_HANDOFF.md:13`). `src/state/user_profile_schema.json` est un schéma
  sans consommateur servi.
- **Pourquoi ça compte** : l'orientation est une trajectoire de neuf mois (PDF p. 24). Sans mémoire,
  chaque question repart de zéro et le produit se réduit à un moteur de recherche bavard - ce qui est
  exactement le reproche que le dossier adresse à ChatGPT (`STRATEGIE_VISION:70-71`).
- **Raison donnée** : deux raisons, l'une bonne, l'autre datée. Le PDF : « deliberate at the prototype
  stage because it simplifies GDPR compliance analysis and limits attack surfaces » (p. 34). Le pivot
  du 06/05 : « système v4.1 strict + multi-tour minimal > orchestration agentic complète »
  (`LIMITATIONS.md:25`).

### 3. La détection de détresse dont on ne connaît pas le recall

- **Où c'est promis** : PDF p. 24 comme fonction de sécurité ; `Livrable-1:181` : « faux négatifs =
  risque vital, faux positifs = friction acceptable ».
- **État** : le classifieur existe et marche sur signal fort. Son **recall sur les formulations
  indirectes n'a jamais été mesuré** (`Livrable-2:116`). En sens inverse, 2 faux positifs sur 42
  questions normales en juin (`L1-Batterie-empirique.md:41`), ramenés à 0 par la tâche A1
  (`PLAN:8`) - ce qui améliore la friction mais **peut avoir dégradé le recall, non mesuré**.
- **Pourquoi ça compte** : c'est la seule fonction du produit dont l'échec a des conséquences
  au-delà de l'orientation. Et corriger les faux positifs sans mesurer les faux négatifs est le geste
  qui, mécaniquement, pousse un classifieur dans la direction la plus dangereuse.
- **Raison donnée** : « chantier de mesure post-démo » (`Livrable-3:59`). Non repris depuis.

### 4. Le lookup structuré généralisé et le décodage contraint (aucun chiffre généré)

- **Où c'est promis** : `Livrable-1:115-117` et `:291` : « Rend une classe d'hallucinations
  structurellement impossible ». `Livrable-3:76` le classe n°2 du chantier de fond.
- **État** : le SELECT bypass reste un cas particulier ; le décodage contraint est absent. Ce qui a
  été livré le 16/07 est une **vérification a posteriori** (`src/validator/citation_check.py`), qui
  est un filet, pas une impossibilité.
- **Pourquoi ça compte** : c'est ce qui distingue « le système se trompe rarement » de « le système ne
  peut pas se tromper là-dessus ». 77 chiffres hallucinés sur le run 497 q de juin
  (`groundedness_full.json`, agrégé) ; et le retour persona le plus net porte exactement là-dessus :
  « Trop de stats précises et pas toujours la source qui va avec »
  (`results/user_test/feedback_17ans.md`).
- **Raison donnée** : effort M/L, renvoyé au post-VivaTech (`Livrable-3:17`, `PLAN:103`).

### 5. Le test utilisateur réel et l'étalon de « bonne réponse »

- **Où c'est promis** : PDF p. 35 ; `Livrable-1:225-226` ; `PLAN:109-119` ; principe directeur n°7 de
  `STRATEGIE_VISION:819`.
- **État** : personas simulés (voir §4.2) ; étalon de pertinence arrêté à 135/387 labels
  (`scripts/relevance_set/STATE.md`).
- **Pourquoi ça compte** : sans étalon, toute amélioration future se mesure contre la fidélité aux
  sources, c'est-à-dire contre une propriété que le système satisfait déjà **en refusant**. C'est
  précisément le piège documenté : 171 refus honnêtes sur 497 questions, groundedness correcte, et un
  utilisateur qui repart les mains vides. Le plan l'avait vu (`PLAN:111`) ; personne ne l'a construit.
- **Raison donnée** : post-VivaTech (`PLAN:113`), puis interruption sur quota le 16/07.

---

## 6. Deux observations qui ne rentrent dans aucune case mais qui portent

**a) L'état déclaré du projet est périmé de trois mois.** `docs/SESSION_HANDOFF.md:3` annonce « Last
updated: 2026-06-13 (Mode récit R1 complet - flag OFF, gel 16/06) » et se présente comme « the single
source of truth for project state » (`:5`). Or le dépôt contient tout le lot H1 du 16/07 (pins de
modèles, provenance, `answer()` pur, citation_check, script de deploy lot 1) et un chantier ouvert au
milieu. Une reprise qui suit la consigne du `CLAUDE.md` (« lire SESSION_HANDOFF en premier ») repart
sur un état faux.

**b) Le diagnostic a changé deux fois, et la version la plus récente est la moins diffusée.** Le
Livrable 2 du 09/06 au matin dit « l'IA hallucine massivement, faithfulness 0,489 »
(`Livrable-2:15`). L'audit empirique du même jour, sur le pipeline réel, dit l'inverse :
« L'hallucination franche est RARE (2 cas sur 42, ~5 %) [...] le vrai problème [...] c'est qu'il est
INUTILE trop souvent » (`L1-Batterie-empirique.md:32`). Le README de la refonte, lui, garde la
première version : « Le coeur IA extrapole (faithfulness 0.489 mesuré) : racine du "l'IA est
mauvaise" » (`refonte-ia-2026/README.md:21`). Si le fondateur juge les réponses « loin d'être
convaincantes », l'explication documentée la plus solide n'est pas l'hallucination : c'est le
**sur-refus, la substitution de métrique et la verbosité**, tous les trois mesurés, et aucun des
trois n'est traité par les chantiers qui ont été exécutés depuis.

---

## 7. Fichiers cités (chemins absolus)

- `/home/matteo_linux/projets/_orientai-ref/dossier-orientai-grand-challenge-2026.pdf`
- `/home/matteo_linux/projets/_orientai-ref/refonte-ia-2026/{README,Livrable-1-Cible-IA-optimale,Livrable-2-Audit-existant,Livrable-3-Comparaison-ecarts,PLAN-ameliorations-pre-vivatech,INVENTAIRE-data-corpus}.md`
- `/home/matteo_linux/projets/OrientIA/docs/{STRATEGIE_VISION_2026-04-16,FUTURE_PHASES_2026-05-18,LIMITATIONS,BENCH_GATES,BENCHMARK_PHASE_D_2026-05-11,SESSION_HANDOFF,TODO_MATTEO_APIS,INRIA_AI_ORIENTATION_PROJECT}.md`
- `/home/matteo_linux/projets/OrientIA/{README.md,LLM_Final.md,CLAUDE.md}`
- `/home/matteo_linux/projets/OrientIA/audit_empirique_2026-06-09/L1-Batterie-empirique.md`
- `/home/matteo_linux/projets/OrientIA/audit_empirique_2026-06-09/results/groundedness_full.json`
- `/home/matteo_linux/projets/OrientIA/scripts/relevance_set/STATE.md`
- `/home/matteo_linux/projets/OrientIA/results/user_test/{feedback_17ans.md,answers_CO.md}`
- `/home/matteo_linux/projets/OrientIA/src/{rag/pipeline.py,rag/scope_classifier.py,validator/citation_check.py,lookup/structured_select.py,state/user_profile_schema.json,agents/hierarchical/session.py,api/server.py}`
- `/home/matteo_linux/projets/OrientIA/.github/workflows/data-refresh-monthly.yml`

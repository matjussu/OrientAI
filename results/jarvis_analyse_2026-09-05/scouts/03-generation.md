# Audit generation / validation / orchestration - OrientIA

Scout lecture seule, 2026-09-05. Repo `~/projets/OrientIA`, aucune ecriture, aucun appel API.
Matiere empirique : run `results/jarvis_analyse_2026-09-05/runs/local.jsonl` (60 conversations,
67 tours, pipeline de prod, `ORIENTIA_NARRATIVE_MODE=1`).

## Avertissement sur la matiere empirique

Le fichier `results/jarvis_analyse_2026-09-05/runs/local.jsonl` a ete **reecrit pendant l'audit**
par un autre processus : a 06h50 il portait 67 lignes, a 07h10 il n'en portait plus qu'une
(mesure : `wc -l` avant/apres, `ls -l` montre `mtime` Sep 5 07:10 et un `judge_opus.log` cree a
07:09). Toutes les mesures de ce rapport portent donc sur une **copie prise avant reecriture**,
identique en contenu a `runs/local_v1_sans_sources.jsonl` (67 lignes, memes ids E01..L20),
snapshot dans `scratchpad/local_v1_sans_sources.jsonl`. Rien n'a ete ecrit dans le repo.

---

## 0. Ce que le run montre, en chiffres

Commande : `python3 scratchpad/an.py` et scripts equivalents sur le snapshot 67 lignes.

| Mesure | Valeur |
|---|---|
| Longueur de reponse (mots) | mediane **90**, min 52, max 188, **0/67 depassent 250** |
| Longueur de reponse (chars) | mediane 816, p25 668, p75 1011 |
| Nombre de puces | **46/67 ont exactement 2 puces**, 8/67 en ont 0, max 6 |
| Reponses contenant `[source S` | **59/67** |
| Reponses ouvrant par « Je n'ai pas … » | **21/67** |
| Reponses contenant « je n'ai pas » | 22/67 |
| Reponses finissant par « ? » | **54/67** |
| `format_decision` (mode recit) non nul | **0/67** |
| `retry.retries_attempted` > 0 | **0/67** |
| `validation.rule_violations` non vide | **0/67** |
| `validation.layer3_warnings` non vide | **0/67** |
| `validation.presence_warnings` non vide | 4/67 |
| `validation.citation_mismatches` non vide | 3/67 |
| `policy.policy` | passthrough 57, warn 4, block 2, absent 4 |
| `select` (chemin SELECT structure) non nul | **1/67** |
| `sources[]` rendues avec un titre non nul | **0/67** |

Deux lectures immediates : le systeme repond **court** (90 mots medians la ou un conseiller
ecrit 300-450), et **presque toute la machinerie de garde-fou rend zero** sur du trafic reel.

---

## 1. Le prompt reellement servi

### 1.1 Chaine de selection

- Le pipeline construit ses kwargs LLM dans `src/rag/generator.py:401` `_build_chat_kwargs`,
  qui a trois branches exclusives, dans cet ordre : `narrative_mode` (ligne 432),
  `use_strict_v4` (ligne 454), sinon v3.2 legacy (ligne 472).
- La factory de prod (`src/rag/factory.py:105`) pose `enable_strict_v4: bool = True`.
  Donc hors mode recit, **le prompt servi est `SYSTEM_PROMPT_V4_STRICT`**
  (`src/prompt/system_v4_strict.py:37-175`), assemble par
  `build_system_prompt_v4_strict(hardlock_block)` (`src/prompt/system_v4_strict.py:178-199`).
- `src/prompt/system.py` (1358 lignes, v3.2) n'est atteint que par la branche `else` ligne 472,
  jamais prise en prod, et par `src/eval/run_real_full.py:53` (banc historique).

### 1.2 Le mode recit ne se declenche jamais sur du trafic reel (mesure)

C'est le defaut le plus lourd du lot, et il est mesurable en une commande.

Le mode recit est garde par `src/rag/pipeline.py:706-711` :
```
if (self.enable_narrative_mode and self.narrative_clarifier is not None
        and (is_narrative(question) or is_narrative_followup(history))):
    return self._prepare_narrative(...)
```
`is_narrative` (`src/rag/narrative_detect.py:168-174`) est un **seuil de longueur pur** :
`len >= 300` chars, ou `len >= 200` chars ET au moins 2 facettes lexicales
(`src/rag/narrative_detect.py:33-35`).

Mesure sur les 67 questions du run, avec le module lui-meme :
```
cd ~/projets/OrientIA && source .venv/bin/activate && PYTHONPATH=. python -c "
from src.rag.narrative_detect import narrative_signal ; ..."
-> questions: 67, narratives: 0
-> longueur min 24, mediane 104, max 155 (seuil 200/300)
```
Temoin positif au meme instrument : le module se charge, `narrative_signal` rend bien un
diagnostic sur chaque question (champ `reason` renseigne, `length` correct), et sa docstring
declare 12/12 declenchements sur le seed de recits (`src/rag/narrative_detect.py:22-23`).
L'instrument voit ; il n'y a simplement aucun recit long dans le trafic teste.

Consequence : `ORIENTIA_NARRATIVE_MODE=1` etait bien pose par le harnais
(`results/jarvis_analyse_2026-09-05/run_battery.py:59`), et pourtant `format_decision` est nul
dans 67/67 traces. Les 414 lignes de `src/prompt/system_narrative.py`, les 6 formats
(exploratoire, comparaison, trajectoire, validation, shortlist, conseil), les 6 few-shots dedies,
les overlays `anchor_constraint` / `reassure`, et la route `narrative_format` -
**tout cela est du code mort sur des questions de moins de 200 caracteres**, c'est-a-dire
sur la totalite des questions que pose un lyceen dans un chat.

C'est exactement l'inverse de ce que la docstring annonce
(`src/rag/narrative_detect.py:3-5` : « les vrais utilisateurs n'envoient pas des questions
courtes »). L'affirmation n'est pas mesuree dans le code ; la mesure ci-dessus la contredit
sur le seul echantillon disponible.

### 1.3 Le prompt v4 strict, tel qu'envoye

Reconstruit par lecture de code, sans appel API. Pour une question type sans hardlock
(`hardlock_block=""` -> `src/prompt/system_v4_strict.py:195-196` rend le prompt tel quel), le
message `system` est **exactement** le contenu de `SYSTEM_PROMPT_V4_STRICT`, soit :

```
Tu es OrientAI, conseiller d'orientation académique et professionnelle française post-bac.

Tu réponds à la question de l'utilisateur·ice en t'appuyant **uniquement** sur le tableau JSON
`<sources>` qui te sera fourni dans le user message.

## CONTRAT STRICT — RÈGLES NON-NÉGOCIABLES

### R1 — Chiffres
Tu peux **UNIQUEMENT** citer les valeurs présentes dans le bloc `chiffres` d'une source du
tableau `<sources>`.
- Toute autre valeur numérique (pourcentage, salaire, taux, places, frais) est **INTERDITE**.
- Si le champ vaut `null` dans `chiffres`, tu écris : **« information non disponible dans mes
  sources »**. Tu ne combles pas avec une estimation.
- Si l'utilisateur demande un chiffre qu'aucune source ne contient, même réponse.

### R2 — Identité des formations
Tu peux **UNIQUEMENT** citer les formations dont l'identité (`formation` + `etablissement` +
`ville`) figure dans `<sources>`.
- Pas d'invention d'écoles, de cursus, de niveaux ("Prépa barreau Bac+5"), de masters non listés.
- Si aucune source ne couvre la question (sources vides ou hors sujet), tu réponds honnêtement :
  **« Je n'ai pas de formation pertinente dans mes sources pour cette question. Je te suggère de
  vérifier sur Parcoursup, ONISEP ou de prendre RDV avec le CIO le plus proche. »**

### R3 — Citations sources
Chaque chiffre cité dans ta réponse **DOIT** être suivi de **`[source SX]`** ...
- Format obligatoire : `52 % [source S1]`, `1740 € [source S3]`, `25 places [source S2]`.
[R3.bis liens Markdown cliquables ; R3.ter priorite fiches metier]

### R4 — Style  [ton libre + interdiction de reprendre les chiffres du few-shot Golden]

### R5 — Posture
- Empathique sans être surjoué·e (pas d'emojis sauf 1 final éventuel)
- Direct·e si le projet n'est pas réaliste
- Pas de jugement, pas de discrimination
- Termine par une question ouverte qui rend le choix à l'utilisateur·ice

### R6 — LONGUEUR (NON-NÉGOCIABLE)
Ta réponse fait **STRICTEMENT MAX 250 mots**. Mesure : compte les mots avant de répondre.
**Structure obligatoire** :
1. **Intro courte** (1-2 phrases, 30 mots max) qui cadre la question
2. **2-3 puces** maximum, chacune avec son `[source SX]` quand chiffres
3. **Question ouverte finale** (1 ligne)
**INTERDIT** : pas d'introduction explicative ; pas de fermeture ; pas de section « Comment
choisir ? » ou « Pour aller plus loin » ; pas de répétition ; si 5+ sources pertinentes,
sélectionne les **3 plus pertinentes**.
**Si tu dépasses 250 mots ou ajoutes des sections superflues, ta réponse sera tronquée.**

### R7 — CONTRAINTES HARDLOCK  [region/domaine imposes, refus honnete plutot que pis-aller]

### R8 — ALTERNATIVE CADRÉE
- 8.a Ouvre TOUJOURS par : **« Je n'ai pas [cible précise] dans mes sources. »**
- 8.b Etiquette toute alternative comme DIFFERENTE de la demande
- 8.c Chaque chiffre de l'alternative reste sourcé

### R9 — CITATION ENTRELACÉE RÉFÉRENCE-PUIS-CLAIM
Pour CHAQUE fait chiffré, la SOURCE est nommée AVANT le chiffre, jamais après.
- ✓ « D'après la fiche Parcoursup du BTS La Mennais [S1], le taux d'accès est de 25 %. »
- ✗ « Le taux d'accès est de 25 %. [S1] »

## SI VIOLATION
Si tu enfreins R1, R2, R3, R6 ou R7, ta réponse sera détectée et rejetée par le validator.
```

Le message `user` est construit par `_build_user_prompt_strict_v4`
(`src/rag/generator.py:439-441` et 465-467) : few-shot Golden QA optionnel + bloc `<sources>`
JSON produit par `format_sources_for_llm(retrieved, max_sources=V4_MAX_SOURCES)` + la question.
Puis l'historique est insere **entre** system et user courant (`src/rag/generator.py:494-501`).

Parametres : `model=MISTRAL_MEDIUM` et `temperature=0.3` (defauts de `generate()`,
`src/rag/generator.py:548-549`), `max_tokens=800` en strict v4 (`src/rag/generator.py:526`).

### 1.4 Analyse du prompt (prompt engineering)

**a) Ce prompt produit mecaniquement des reponses de deux puces.** R6 impose « 2-3 puces
maximum », « intro 1-2 phrases 30 mots max », « question ouverte finale », et menace de
troncature. Mesure : 46/67 reponses ont **exactement 2 puces**, mediane 90 mots. Le cap de 250
mots n'est meme pas le facteur limitant (0/67 l'atteignent) : c'est le squelette impose a trois
elements qui plafonne la reponse a un tiers de ce qu'un lyceen attend. Un conseiller qui repond
90 mots a « je veux devenir medecin, PASS ou LAS ? » n'a pas repondu.

**b) Contradiction interne dure entre R3 et R9.** R3 donne comme *format obligatoire*
`52 % [source S1]` (chiffre puis tag) - `src/prompt/system_v4_strict.py:59`. R9 declare ce meme
motif **interdit** et exige la source avant le chiffre - `src/prompt/system_v4_strict.py:157-166`.
Les deux regles sont dans le meme prompt, a 100 lignes d'ecart. Mesure de l'arbitrage rendu par
le modele : 72 occurrences du motif interdit par R9 contre 25 du motif conforme, sur 142 tags au
total. **Le modele suit R3 et ignore R9 dans ~3 cas sur 4.** Une regle qui perd contre sa voisine
dans 74 % des cas n'est pas une regle, c'est du bruit qui coute des tokens et de l'attention.

**c) Le prompt fabrique la fuite de jargon.** `[source SX]` n'est pas un accident de generation :
c'est une obligation ecrite en gras (R3, ligne 57), avec exemples. Et rien en aval ne l'enleve
(cf section 3.4). Mesure : 59/67 reponses servies contiennent `[source S`.

**d) Le prompt pousse au refus avant de pousser au conseil.** R1 impose une formule de non-reponse,
R2 impose une formule de refus complet, R8.a impose d'**ouvrir** par « Je n'ai pas [cible] dans
mes sources ». Trois regles sur neuf sont des regles d'abstention, contre zero regle qui demande
de raisonner sur le profil, de hierarchiser, ou de dire ce qu'il faut faire ensuite. Mesure :
21/67 reponses **commencent** par « Je n'ai pas ». Le registre par defaut du produit est
l'excuse.

**e) Aucune regle n'autorise le conseil hors sources.** Tout ce qui n'est pas dans `<sources>` est
interdit (R1, R2), y compris ce qui n'est pas une donnee de fiche : le calendrier Parcoursup,
l'interdiction de redoublement en PASS, le cout d'une ecole privee, la mecanique d'une passerelle.
Le corpus est un annuaire de formations ; le prompt en fait la borne de tout le savoir du
conseiller. C'est la cause structurelle du « ne comprend pas tout » : le systeme sait des choses
qu'il s'interdit de dire.

**f) La question finale est un tic, pas une clarification.** R5 exige de « terminer par une
question ouverte ». Mesure : 54/67 reponses finissent par « ? ». Mais aucune de ces questions
n'est posee **avant** de repondre pour lever une ambiguite : elle est posee apres, en cloture.
Le systeme ne demande jamais ce qu'il lui manque, il propose de continuer (cf section 4).

**g) Le prompt promet une sanction qui n'existe pas.** « ta réponse sera détectée et rejetée par
le validator » (ligne 174) et « ta réponse sera tronquée » (ligne 124). Mesure : 0/67 violations
de regles remontees par le validator, 0/67 retries, policy `passthrough` dans 57/67 cas
(cf sections 3 et 5). La menace est vide. Ce n'est pas neutre : c'est une affirmation porteuse
fausse dans le prompt, qui a servi a justifier de ne pas construire d'autre garde-fou.

---

## 2. Le contrat FactCard v4 : ou se perd la richesse

### 2.1 Le format

`fiche_to_fact_card` (`src/rag/fact_card.py:296` et suivantes) produit un objet a champs typés,
serialise en JSON indente par `format_sources_for_llm` (`src/rag/fact_card.py:896-922`), avec
**nulls explicites** : le bloc `chiffres` porte **31 champs** et sort tous ses `null`.

Mesure (script `scratchpad/card2.py`, sur 2000 fiches tirees au hasard, seed 0, du corpus reel
`data/processed/formations.json`, 52 040 fiches) :

| Mesure | Valeur |
|---|---|
| Champs `chiffres` par carte | 31 |
| Taux de remplissage global | **12,8 %** |
| Chiffres non nuls par carte | mediane **3**, p75 5, p90 11, max 17 |
| Cartes a **zero** chiffre | **756/2000 (37,8 %)** |
| Cartes a 2 chiffres ou moins | 995/2000 (49,8 %) |
| Bloc `<sources>` de 5 cartes | 9157 chars, **~2290 tokens**, dont **141 occurrences de `null`** |

### 2.2 Combien de fiches passent dans le contexte

`V4_MAX_SOURCES = 5` (`src/rag/generator.py:36`), applique ligne 464. Le mode recit monterait a 8
(`NARRATIVE_MAX_SOURCES = 8`, ligne 39) mais ne se declenche pas (section 1.2).

Or le retrieval en amont rend beaucoup plus : dans le run, `filter_stats.n_after_filter` a pour
mediane ~45, et vaut 50 dans 25/67 cas, 100 dans 7/67, 150 dans 2/67. **Le pipeline retrouve 50
fiches et en montre 5 au modele.** Le tri de ces 5 est fait par le reranker, sans que le modele
puisse jamais voir la 6e, ni demander a la voir : il n'y a pas de boucle d'outils sur le chemin
servi (confirme section 4).

### 2.3 Ou se perd la richesse - la chaine complete

1. **Retrieval** : 50 a 150 fiches candidates.
2. **Troncature a 5** (`src/rag/generator.py:464`). Perte : 90 %.
3. **Serialisation FactCard** : 5 cartes, ~15 chiffres reels au total (3 par carte en mediane),
   noyes dans 141 `null`. Le modele voit un formulaire vide plus qu'une base de faits.
4. **R1 du prompt** : tout ce qui n'est pas dans `chiffres` est INTERDIT, et un `null` doit se dire
   « information non disponible dans mes sources ». Donc les 141 nulls ne sont pas neutres :
   ce sont **141 invitations a s'excuser**.
5. **R6 du prompt** : de ces 5 cartes, garder au plus 2-3 puces, moins de 250 mots.
6. **Rendu** : mediane 90 mots, 2 puces.

La richesse ne se perd pas a un endroit, elle se perd a chaque etage, et le dernier etage (R6)
est celui qui coupe le plus fort par rapport a l'attente utilisateur.

### 2.4 Le post-process ne rattrape rien de tout cela

`post_process_answer` (`src/rag/post_process.py:268-303`) fait exactement 4 choses :
`strip_invented_urls`, `neutralize_broken_link_fallback`, `fix_broken_markdown_tables`,
`validate_onisep_slugs`. Aucune ne touche au fond, a la longueur, ni au jargon.

Notamment, **rien ne retire `[source SX]`**. Preuve negative avec temoin positif au meme
instrument : `grep -rnF "[source S" src/ --include=*.py` rend 55 occurrences dans 9 fichiers
(le grep voit) ; aucune n'est une substitution ou une suppression dans `post_process.py`,
`policy.py` ou `server.py`. Le tag est un contrat machine lisible par
`src/validator/citation_check.py:31` et il est servi tel quel a un lyceen. Le commentaire
`src/rag/fact_card.py:589` revele l'intention initiale (« les chips [SX] du front se resolvent en
vraie [source] ») : le backend leake **par conception**, en pariant sur un front qui resoudrait
les tags. Si ce front ne le fait pas, le produit affiche du jargon d'ingenieur - c'est le cas
sur 59/67 reponses du run.

---

## 3. Validation aval : ce qui est cable, ce qui est mort, ce qui nuit

### 3.1 Ce qui tourne sur `/answer`

Ordre : generation -> `Validator.validate` -> `apply_policy` -> `post_process_answer`
(`src/rag/pipeline.py:582-599`).

| Couche | Etat | Mesure sur 67 tours |
|---|---|---|
| Layer 1 `rules.py` (regex) | cablee | **0/67** violation |
| Layer 2 `corpus_check` (fuzzy) | cablee | 2/67 warnings, **les deux sont des faux positifs** (3.3) |
| `presence.py` (mentions obligatoires) | cablee | 4/67, tous rendus visibles a l'utilisateur (3.2) |
| `citation_check` | cablee | 3/67 mismatches, **sans effet sur la reponse** |
| Layer 3 (juge LLM Mistral Small) | **desactivee** : `enable_layer3: bool = False` (`src/rag/factory.py:83`) | 0/67 |
| Retry-with-hint (tour 2) | **court-circuite par design en strict v4** (`src/rag/pipeline.py:1312-1318`) | **0/67 retries**, `retry_skipped_reason="strict_v4_hint_ignored"` sur 6/67 |
| Fact-checkers `src/eval/fact_check*.py`, `src/experimental/fact_checker.py` | **non atteints** depuis `server.py` (cloture transitive des imports) | jamais executes en serving |

Autrement dit : sur le chemin servi, la seule couche qui **modifie** encore la reponse est
`corpus_check`, et elle se trompe (3.3). Les 0/67 de la Layer 1 ne sont pas rassurants : c'est
soit un jeu de regles qui ne couvre rien du trafic reel, soit un jeu de regles inoperant. La
docstring du prompt promet pourtant « ta reponse sera detectee et rejetee par le validator »
(`src/prompt/system_v4_strict.py:174`).

### 3.2 La policy WARN ecrit dans la reponse de l'utilisateur

`apply_policy` etape 4 (`src/validator/policy.py:259-278`) **concatene un pied de page** a la
reponse quand une mention obligatoire manque. Le texte du pied de page est ecrit en dur
`src/validator/policy.py:83-95` :

```
---
⚠️ **Points à vérifier dans ma réponse** :
- Mention manquante : interdit de redoublement PASS (arrêté 2019) — ...
Ces points sont des patterns que nous surveillons. Vérifie directement sur ONISEP ou
Parcoursup avant toute décision.
```

Ce bloc est parti a l'utilisateur dans 4/67 conversations (L03, L25.2, E10, E24). Trois problemes,
dans l'ordre de gravite :

1. **Le systeme sait quoi ajouter et ne l'ajoute pas.** Il sait que l'interdiction de redoublement
   PASS manque - il le nomme precisement. Au lieu de le dire dans la reponse, il le dit **a cote**
   de la reponse, sous forme de reproche. C'est un correcteur qui annote sa propre copie sans la
   corriger. Un retry ou une injection deterministe de la mention couterait moins.
2. **Le registre est interne** : « des patterns que nous surveillons » est du vocabulaire d'equipe
   qualite, adresse a un lyceen.
3. Il viole la sobriete (emoji) et sape la confiance juste apres avoir donne une reponse.

### 3.3 `corpus_check` bloque des reponses correctes - defaut mesure et falsifie

2/67 conversations ont ete **entierement remplacees** par un refus (`policy: block`,
`src/validator/policy.py:216-224`) :

- **E11** « Je cherche un master en data science. » -> bloquee. Motif :
  `Master INFORMATIQUE — Machine Learning`, `formation_not_found_in_corpus`, similarite 0,37,
  `closest_match: "CONSEILLER COMMERCIAL (TP) — PGM LEARNING"`.
- **E17** « Je suis en M1 droit des affaires et je veux faire de l'urbanisme. » -> bloquee. Motifs :
  `Master DROIT DE L'ENVIRONNEMENT ET DE L'URBANISME — Droit de l'urbanisme` (sim 0,48,
  closest_match « Manager du developpement d'entreprise — ISME ») et
  `Master URBANISME ET AMENAGEMENT — Ville héritée` (sim 0,33, closest_match un BTS microtechniques).

**Ces trois formations existent dans le corpus.** Mesure (`scratchpad/corpus_check_test.py`, sur
`data/processed/formations.json`, 52 040 fiches) :
`"URBANISME ET AMENAGEMENT"` -> **43 fiches** ; `"DROIT DE L'ENVIRONNEMENT ET DE L'URBANISME"` ->
**14 fiches** ; `"Machine Learning"` -> **5 fiches** dont `INFORMATIQUE — Machine learning`
a l'Universite de Lille. Toutes de source `monmaster`.

Falsification directe du checker (`scratchpad/cc3.py`, appel de `check_formation_exists` avec le
corpus reel) :

```
(True, "DROIT DE L'ENVIRONNEMENT ET DE L'URBANISME — Droit de l'environnement — Paris 1", 0.80)
   <- "Master DROIT DE L'ENVIRONNEMENT ET DE L'URBANISME — Droit de l'urbanisme", etab=''
(True, 'URBANISME ET AMENAGEMENT — Intelligence territoriale — Lorraine', 0.69)
   <- 'Master URBANISME ET AMENAGEMENT — Ville héritée', etab=''
(True, 'INFORMATIQUE — Machine learning — Université de Lille', 0.84)
   <- 'Master INFORMATIQUE — Machine Learning', etab=''
(True, 'INFORMATIQUE — Machine learning — Université de Lille', 0.91)
   <- 'Master INFORMATIQUE — Machine Learning', etab='Université de Lille'
```

Temoin positif au meme instrument : une fiche du corpus passee telle quelle rend
`(True, ..., 1.0)` - le checker sait dire oui.

**Cause racine, localisee** : `src/validator/corpus_check.py:226-234`. Quand le claim porte un
etablissement et qu'aucune fiche n'est jugee « etab-compatible » (fuzzy 0,6 ou substring,
`corpus_check.py:203-213`), la fonction calcule un `best_sim` **sur le nom seul** puis fait
`return (False, best_label, best_sim)` - **le `False` est ecrit en dur ligne 234**, quelle que
soit la similarite du nom. Une formation dont le nom matche a 0,80 est donc declaree inventee
parce que la chaine d'etablissement extraite du texte n'a pas matche. Et `_extract_claims`
(`corpus_check.py:136-154`) est fragile : sur un markdown de test realiste il m'a rendu **0 claim**
(`scratchpad/cc2.py`), donc le peu qu'il attrape, il l'attrape mal.

Consequence produit : **le garde-fou anti-hallucination detruit des reponses justes** sur deux des
questions les plus banales du jeu (« je cherche un master en data science »). 3 % du trafic teste.
C'est un faux vert inverse : la couche est verte dans les tests (elle a un jeu de tests) et elle
nuit en production.

### 3.4 Le retry est mort la ou il servirait

Sur E11 et E17, `retry.tour1_failed_claims` est renseigne (le systeme SAIT quelles citations
posent probleme) et `retry_skipped_reason = "strict_v4_hint_ignored"`. La reponse n'est donc pas
regeneree : elle est jetee. La docstring de `_generate_with_retry` documente elle-meme
l'obsolescence (`src/rag/pipeline.py:1198-1206` : « en PRODUCTION (strict_v4=True, default
factory), le tour 2 est court-circuite PAR DESIGN »), et les ~64 lignes qui suivent le `return`
ligne 1312-1318 ne s'executent jamais.

---

## 4. Orchestration conversationnelle

### 4.1 La chaine

`ScopeClassifier` (LLM Mistral Small, `src/rag/pipeline.py:668-669`) ->
`RouterLLM` (LLM Mistral Small, tool-calling, `src/rag/pipeline.py:719-723`) ->
`SELECT` structure (deterministe) -> retrieval -> generation (Mistral Medium) -> validation.
Trois appels LLM et deux appels d'embedding par requete servie.

### 4.2 Personne ne pose de question de clarification

C'est le point le plus contre-intuitif de l'audit : **il n'existe aucun etage qui decide de poser
une question avant de repondre.**

- `ScopeClassifier` classe (in_scope / out_of_scope / urgent / identity / greeting) et court-circuite
  avec une reponse pre-ecrite. Il ne demande rien.
- `RouterLLM` extrait des criteres ou refuse (`refusal_reason`). Il ne demande rien.
- `ProfileClarifier` (`src/agent/tools/profile_clarifier.py`, 633 lignes) porte le mot
  « clarifier » dans son nom mais **n'engage aucun dialogue** : il extrait un profil best-effort
  et retombe silencieusement sur `confidence=0.0`. Et il n'est instancie que si
  `enable_narrative_mode` (`src/rag/factory.py:189`), donc jamais actif sur du trafic court
  (section 1.2). **Mesure : 0/67 tours l'ont exerce.**
- Le seul mecanisme de clarification concu (« Plusieurs formations matchent : EFREI Paris ou EFREI
  Bordeaux ? », `src/lookup/structured_select.py:22-24`) est mesure a **0/15 declenchements** sur
  le banc de stress (`docs/rapport-expert-addendum-bench-2026-05-03.md:107`) et a **1/67** dans ce
  run.
- La question finale de R5 est posee **apres** la reponse, jamais a la place.

Le systeme repond donc toujours du premier coup, avec ce qu'il a compris, meme quand la question
est sous-specifiee. C'est exactement le symptome rapporte par le fondateur.

### 4.3 Le profil n'est ni stocke ni reinjecte

`src/state/` ne contient que deux **JSON Schema** et aucun code. Ni `pipeline.py` ni `server.py`
n'importent `src.state`. Au tour N, ce qui part au modele est : system prompt + historique brut
(<= 6 messages, cap Pydantic `src/api/schemas.py:67`) + user prompt courant. `ScopeClassifier`
retronque a 4 (`scope_classifier.py:525`), `RouterLLM` a 12 (`router_llm.py:653`, sans effet
puisque le contrat plafonne deja a 6), le generateur ne tronque pas
(`src/rag/generator.py:495-501`).

Consequence mesurable : **chaque tour recommence a zero**. L13.1 en est la demonstration. Au tour 0,
le router a extrait `secteur=["informatique"], region=occitanie, niveau 1-1`. Au tour 1
(« et si je rate ma premiere annee, je peux me reorienter en BUT ? »), il re-extrait de zero
`niveau_min=0, niveau_max=3, hardlock_region_strict=false` et rend un **BUT Gestion des entreprises
et des administrations a Montpellier-Sete** a un eleve de terminale spe maths-NSI qui vise
l'informatique a Toulouse. Ni le domaine ni la ville du tour precedent ne survivent : il n'y a pas
d'etat, seulement un historique de texte que le router relit imparfaitement.

### 4.4 Le router prend le domaine qu'on rejette pour le domaine qu'on vise

E01 : « Je suis en L1 droit et je deteste ca. Je peux me reorienter ? Je suis a Montpellier. »
Trace : `router.criteria.secteur = ["droit"]`. Reponse servie : un **Portail Droit** a Montpellier
et une **LLCER Anglais** a Paul Valery. Le systeme propose du droit a quelqu'un qui fuit le droit.

Cause : le schema du tool `decide_route` (`src/rag/router_llm.py:371-443`) n'a qu'un seul champ
`secteur`, sans distinction cible / rejet, et la regle 4 du prompt router
(`src/rag/router_llm.py:532-534`) dit seulement « liste les secteurs candidats ». La distinction
existe **ailleurs** : `dedup_sector_vs_eviter` (`src/agent/tools/profile_clarifier.py:292-325`)
garantit `sector ∩ a_eviter = ∅`, avec la regle de prompt correspondante lignes 454-465. Mais ce
code vit dans le `ProfileClarifier`, c'est-a-dire dans le mode recit, c'est-a-dire dans la branche
qui ne se declenche jamais (section 1.2). **Le bon comportement est ecrit, teste, et hors du
chemin servi.**

### 4.5 Le router refuse ce que le scope classifier avait accepte

L24 : « J'ai trop peur de me tromper de voie et de gacher ma vie. Comment on choisit ? »

- `ScopeClassifier` : `in_scope`, raison « peur liee a l'orientation post-bac, pas de signal de
  detresse vitale ». Verdict juste.
- `RouterLLM` : `refusal_reason = "cross_domain"`, court-circuit, reponse pre-ecrite servie :
  « Je peux pas vraiment t'aider sur ce sujet - mon perimetre c'est l'orientation post-bac
  francaise. »

Deux classifieurs LLM en serie, le second annule le premier, aucun arbitrage. Le produit refuse
**la question d'orientation la plus frequente qu'un lyceen puisse poser**, avec un message qui dit
que ce n'est pas de son perimetre. Meme mecanique sur L06 (comparaison prepa MPSI / INSA) :
`refusal_reason = "superlative_no_data"` declenche par une regle de tie-break qui se dit
« PRIORITE ABSOLUE ... peu importe le sujet » (`src/rag/router_llm.py:558-571`).

### 4.6 Un vrai agent existe et n'a jamais ete branche

`src/agent/pipeline_agent.py` (boucle function-calling Mistral, 3 outils) et
`src/agents/hierarchical/` (Coordinator / Empathic / Analyst / Synthesizer) existent. Ni
`pipeline.py` ni `server.py` ne les importent ; seuls des scripts de bench les appellent. La
cloture transitive des imports depuis `src/api/server.py` les classe **non atteints**.

Chiffres de l'abandon (`docs/SPRINT5_APPLES_TO_APPLES_VERDICT.md`) : latence 23,12 s +/- 2,36 vs
12,35 s baseline (ligne 33) ; `pct_verified` 23,0 % +/- 19,73 pp vs 39,4 % +/- 3,66 pp, soit
**-16,4 pp** (lignes 31, 110-114) ; `pct_hallucinated` inchange (17,7 % vs 17,9 %). Audit
qualitatif : **60 % de la casse vient d'un trou de couverture corpus, 40 % de fabrication LLM,
0 % de sur-strictness du fact-checker** (lignes 40-44). C'est le chiffre le plus important du
dossier : l'architecture agentique n'a pas echoue sur l'architecture, elle a echoue sur la donnee
et sur un top-K trop court. Le verdict ecrit est « pas de revert / push-ready » (lignes 213-220) ;
le debranchement de fait est une **inference** tiree du cablage, pas une decision tracee.

---

## 5. Detresse et refus

### 5.1 Le refus est decide a trois etages, deux avant generation

**Avant generation** (aucun appel au generateur) :
- `ScopeClassifier` `urgent` / `out_of_scope` -> `pre_written_response`
  (`src/rag/pipeline.py:668-693`). Le filet detresse est double : regex deterministe
  (`src/rag/scope_classifier.py:54-89`, avec le cas indirect « je craque », « je sers a rien »)
  puis LLM. Mesure sur le run : 1/67 `urgent`, 1/67 `out_of_scope`. Ce volet-la fonctionne.
- `RouterLLM` `refusal_reason` -> pre-ecrit. Mesure : 2/67 (`superlative_no_data`,
  `cross_domain`), les deux **a tort** (section 4.5).
- SELECT echoue / ambigu -> `format_unknown_response` (`src/lookup/structured_select.py:783-850`).

**Apres generation** : `apply_policy` -> BLOCK, qui **remplace** la reponse deja ecrite
(`src/validator/policy.py:210-224`). Mesure : 2/67, **les deux a tort** (section 3.3).

### 5.2 Le refus doux, dans le texte

C'est le volume reel. 21/67 reponses **ouvrent** par « Je n'ai pas … », impose par R8.a
(`src/prompt/system_v4_strict.py:143`), et 22/67 contiennent la formule. Sur les 8 reponses sans
aucune puce, 6 sont des non-reponses : amenagements pour dyslexie avec PAP (L27), reconnaissance
d'un diplome belge (E30), concours de la fonction publique apres une L3 AES (E21), chances en IFSI
avec 12 de moyenne (L14.1), palmares prepa/INSA (L06), « comment on choisit » (L24).

Aucune de ces six questions n'appelle une donnee de fiche Parcoursup. Toutes appellent la
connaissance generale d'un conseiller. Le systeme la possede (le modele sous-jacent la possede) et
le prompt la lui interdit (R1, R2). Le taux de refus de 214/497 au gel est donc structurel, pas
accidentel : **le contrat de prompt definit le corpus comme la borne du savoir, alors que le
corpus est un annuaire de formations.**

### 5.3 La contradiction interne, mesuree

3/67 reponses juxtaposent « non selective » et un taux d'acces (L01 : « non selective, 60 places,
taux d'acces de 28 % » ; L11 ; E21). Les deux informations viennent de la meme FactCard : un champ
statut/selectivite issu du corpus, et `taux_acces_parcoursup_2025`. Rien dans le prompt, rien dans
`rules.py`, rien dans le post-process ne verifie leur coherence. Le modele ne contredit pas ses
sources, **il recopie deux champs qui se contredisent deja dans la fiche**. Le correctif n'est pas
un correctif de prompt : c'est une regle de coherence sur la FactCard, ou une reformulation
(« ouverte a tous mais forte demande : 28 % des candidats obtiennent une place »).

---

## 6. Streaming : le chemin servi est celui qui a le moins de garde-fous

Le front appelle `/answer/stream` (`docs/vivatech-2026/02_AUDIT_EXISTANT.md:119` : « backend
OrientIA FastAPI, endpoint SSE `/answer/stream` », streaming et bouton Stop cables). Le repo front
est hors perimetre, donc cette affirmation vient de la doc du projet et non d'une mesure sur le
front.

Ce qui differe entre `/answer` et `/answer/stream` est ecrit noir sur blanc dans le code
(`src/rag/pipeline.py:1145-1152`, docstring de `_validate_for_stream`) :

> « Pas de retry-with-hint (D2 ordre Jarvis 2026-05-13), pas de policy replacement (les tokens
> originaux sont deja streames), pas de post_process (cleanup cosmetique non visible en
> streaming). »

Consequences concretes :

| Etage | `/answer` | `/answer/stream` |
|---|---|---|
| Validator (score) | oui | oui (`pipeline.py:1101-1108`) |
| Policy BLOCK / MODIFY / WARN | oui | **non** |
| `strip_invented_urls` | oui | **non** |
| `validate_onisep_slugs` | oui | **non** |
| `fix_broken_markdown_tables` | oui | **non** |
| Retry | mort de toute facon | non |

Donc en streaming, une URL inventee par le modele part telle quelle a l'utilisateur, et une
reponse que la policy aurait bloquee est servie intacte - le validator se contente d'emettre un
event `faithfulness` que le front peut afficher ou ignorer. La seule protection reelle qui survit
est celle du prompt, c'est-a-dire une consigne.

Timeouts : `ORIENTIA_PIPELINE_TIMEOUT_S = 30 s` (`src/api/server.py:127`),
`ORIENTIA_STREAM_TIMEOUT_S = 55 s` (`src/api/server.py:569`), heartbeat SSE cote producer.

Note de coherence : la policy WARN, elle, **ne s'applique qu'en non-streaming**. Les 4 blocs
« Points a verifier dans ma reponse » observes dans le run viennent de `answer()` sync ; si le
front est bien sur le stream, ce pied de page n'apparait jamais en production - mais les deux
BLOCK non plus, ce qui veut dire que les reponses E11/E17 seraient servies **completes** en prod,
et que le refus observe est un artefact du harnais. A verifier cote front avant tout correctif.

---

## 7. Complexite : ce qui est mort, ce qui n'a jamais tourne

### 7.1 Modules

Cloture transitive des imports depuis `src/api/server.py` (script `ast`, hors `src/collect/`) :
**98 fichiers, 46 atteints, 52 non atteints.**

Non atteints, notamment : tout `src/eval/` (17 fichiers, dont `fact_check.py`,
`fact_check_claude.py`, `run_haiku_factcheck.py` - les fact-checkers dorment), tout
`src/experimental/` (dont `fact_checker.py`, 385 lignes), tout `src/agents/hierarchical/`
(6 fichiers), `src/agent/{agent,parallel,pipeline_agent,streaming}.py`,
`src/agent/tools/{fetch_stat_from_source,query_reformuler}.py`,
`src/backstop/soft_annotator.py` (382 lignes), `src/config.py`, `src/observability/__init__.py`,
`src/rag/cli.py`.

Atteints mais inertes en pratique : `src/prompt/system.py` (1358 lignes, branche v3.2 jamais prise
en prod), `src/prompt/system_narrative.py` + `narrative_route` + `narrative_format` +
`narrative_structured` + `narrative_query` + `profile_clarifier` (~1900 lignes, jamais declenchees,
section 1.2), `src/validator/layer3.py` (`enable_layer3=False`).

### 7.2 Ligne a ligne dans `pipeline.py` (2224 lignes)

- `_prepare_narrative` : `src/rag/pipeline.py:872-984`, 113 lignes, conditionnelles au flag recit.
- Retry tour 2 : `src/rag/pipeline.py:1319-1382`, ~64 lignes apres le `return` du court-circuit
  strict v4 (`pipeline.py:1312-1318`), jamais executees.
- Plus une dizaine de branches courtes pour les flags jamais `False` en prod.

Ordre de grandeur : ~8 % du fichier mort avec certitude, davantage si l'on compte le mode recit.

### 7.3 Flags

25 lectures d'environnement dans `src/`. Sur le perimetre de `docs/PIPELINE_v4_1_FLAGS.md`, deux
manques : `enable_router_llm` / `router_model` (`src/rag/factory.py:110,113`) ne sont pas
documentes (`grep -i router` sur le doc : aucun resultat), et `ORIENTIA_NARRATIVE_MODE` non plus -
le doc est fige a un etat anterieur au chantier recit.

**Valeur en prod de `ORIENTIA_NARRATIVE_MODE` : non etablie.** Aucun `railway.json/toml` dans le
repo, rien dans le `Dockerfile`, rien dans `DEPLOY_LOT1_RUN_ME.sh`, et `/health`
(`src/api/server.py:420-428`) n'expose pas l'etat du flag. La seule trace est une intention datee
(`docs/SESSION_HANDOFF.md:28`, « bascule prod prevue jour J VivaTech 17/06 »), non confirmee.
Cela dit, la question est secondaire : la mesure de la section 1.2 montre que **meme a 1, le flag
ne change rien sur des questions de moins de 200 caracteres**.

Tous les autres flags factory sont deductibles avec certitude : `src/api/server.py:166` appelle
`make_production_pipeline(client, fiches)` **sans aucun kwarg**, donc tous les defauts de
`src/rag/factory.py:82-118` s'appliquent (tout `True` sauf `enable_layer3=False`).

### 7.4 Une affirmation porteuse fausse dans la doc du projet

`OrientIA/CLAUDE.md` affirme : « Le decorateur `@observe(name="orientia.answer")` est en place sur
`OrientIAPipeline.answer()` avec 10 spans nested ». Mesure : `grep -n "@observe\|observe(name="
src/rag/pipeline.py` ne rend **aucun resultat**, et `git log -S"observe(name=" -- src/rag/pipeline.py`
non plus. `src/observability/` n'est pas atteint depuis `server.py`. Le projet croit avoir une
instrumentation qu'il n'a pas - c'est le cas d'ecole de la regle 13, et cela explique pourquoi le
diagnostic de qualite se fait a l'oeil plutot qu'a la trace.

### 7.5 Modeles, temperature, appels

| Etage | Modele | Temperature | max_tokens |
|---|---|---|---|
| ScopeClassifier | `mistral-small-2603` | 0.0 | 200 (timeout 5 s) |
| RouterLLM | `mistral-small-2603` | 0 | tool-calling |
| Generation | `mistral-medium-2604` | **0.3** | **800** (strict v4) |
| Embeddings | `mistral-embed-2312` | - | - |

Constantes pinnees `src/rag/models.py:23-31`. Trois appels de generation + deux d'embedding par
requete. `MISTRAL_LARGE` n'est utilise que par `ProfileClarifier.clarify()`, chemin non servi.

---

## 8. Verdict

### 8.1 Les cinq defauts les plus couteux pour la qualite percue

**1. Le mode conseiller ne se declenche jamais (mesure : 0/67).**
Preuve : `src/rag/narrative_detect.py:33-35` (seuils 200/300 chars) contre une longueur de question
mediane de 104 chars et maximale de 155 sur le run, avec `ORIENTIA_NARRATIVE_MODE=1` pose. Toute
la reponse longue structuree, les 6 formats, la gestion rejet/cible, l'accroche empathique : ecrits,
testes, jamais servis. Fix : remplacer le seuil de longueur par un routage d'intention (le
`route_narrative_format` existe deja) et faire du format long le **defaut**, le format court
l'exception. Coût : faible, l'essentiel du code est ecrit.

**2. R6 impose une reponse de 90 mots et deux puces (mesure : 46/67 a exactement 2 puces,
mediane 90 mots).**
Preuve : `src/prompt/system_v4_strict.py:108-124`. Le cap de 250 mots n'est meme pas atteint
(0/67) : c'est le squelette « intro 30 mots / 2-3 puces / question » qui plafonne. Un lyceen qui
demande « PASS ou LAS ? » recoit deux liens et une question. Fix : reecrire R6 en structure
adaptative, monter `max_tokens` (`src/rag/generator.py:526`).

**3. Le contexte servi au modele est un formulaire vide (mesure : 5 fiches sur 50 retrouvees,
31 champs chiffres, 12,8 % de remplissage, 141 `null` par bloc, 37,8 % des fiches sans aucun
chiffre).**
Preuve : `src/rag/generator.py:36,464` ; `src/rag/fact_card.py:896-922` ; `scratchpad/card2.py`.
Couple a R1 qui transforme chaque `null` en excuse, cela produit mecaniquement les 21/67 reponses
qui ouvrent par « Je n'ai pas ». Fix : ne serialiser que les champs non nuls, monter a 8-12 fiches,
autoriser explicitement le savoir general hors chiffres.

**4. L'orchestration ne pose jamais de question et ne garde aucune memoire de profil
(mesure : 0/67 clarifications, 1/67 SELECT, `src/state/` sans code).**
Preuve : `src/api/schemas.py:67` (cap 6, historique brut) ; `src/agent/tools/profile_clarifier.py`
instancie seulement en mode recit (`src/rag/factory.py:189`). Cas : L13.1, ou le tour 1 perd le
domaine et la ville du tour 0 et propose un BUT GEA a Montpellier ; E01, ou le router prend
« droit » comme cible alors que c'est ce que l'etudiant fuit
(`src/rag/router_llm.py:371-443`, un seul champ `secteur`), alors que la logique correcte existe
dans `profile_clarifier.py:292-325`, hors chemin servi. Fix : un objet profil persistant cote
serveur, alimente a chaque tour, et le champ `a_eviter` remonte dans le schema du router.

**5. Les garde-fous nuisent plus qu'ils ne protegent.**
Preuve, trois volets : (a) `corpus_check` bloque des reponses **justes** - E11 et E17 detruites sur
trois formations qui existent 43, 14 et 5 fois dans le corpus, `return (False, ...)` en dur
`src/validator/corpus_check.py:234`, falsifie par `scratchpad/cc3.py` ; (b) la policy WARN colle un
reproche interne dans la reponse de l'utilisateur, `src/validator/policy.py:83-95`, 4/67 ; (c) le
RouterLLM refuse ce que le ScopeClassifier avait accepte, L24 « comment on choisit ? » renvoyee
hors perimetre. Et pendant ce temps, ce qui protegerait vraiment est eteint : Layer 3
(`enable_layer3=False`), retry (`strict_v4_hint_ignored`, 0/67), fact-checkers non atteints, et
**aucune de ces trois couches ne tourne en streaming**, c'est-a-dire sur le chemin que le front
appelle (`src/rag/pipeline.py:1145-1152`). Fix : corriger la ligne 234, deplacer le WARN en log,
supprimer le veto du router quand le scope a dit in_scope, rebrancher le retry.

### 8.2 Reparer ou remplacer

**Opinion : remplacer l'orchestration et la generation, garder la donnee et le retrieval.**

Le corpus (52 040 fiches, 25 sources publiques, provenance tracee), l'index FAISS, le reranker, la
FactCard comme structure de donnees, les liens officiels Parcoursup et le filet detresse sont des
actifs reels et chers a refaire. Tout ce qui est en aval du retrieval est un empilement de sept ans
de correctifs qui se neutralisent : un prompt qui se contredit (R3 contre R9, mesure 72 contre 25),
un mode conseiller qui ne se declenche pas, un validateur qui detruit des reponses justes, un
retry mort, un chemin streaming qui contourne tout, 52 modules non atteints sur 98.

Surtout, le chiffre de l'audit Sprint 5 dit ou est le vrai probleme : 60 % des claims non
supportes venaient d'un **trou de couverture corpus / top-K trop court**, 0 % d'une
sur-strictness du checker. Depuis, la reponse apportee a ete de durcir le prompt et le validateur -
c'est-a-dire d'agir sur les 0 %.

Effort estime, en jours-agent (Claudette, avec revue) :

| Voie | Contenu | Jours-agent |
|---|---|---|
| **A. Reparer a la marge** | Corriger `corpus_check:234`, retirer le WARN du texte servi, supprimer le tag `[source SX]` du rendu, desactiver le veto router quand scope=in_scope, abaisser le seuil narratif | **2 a 3** |
| **B. Reparer en profondeur** | A + reecrire R6 et le contrat de prompt (une seule regle de citation), FactCard sans nulls, top-K 12 dans le contexte, profil persistant serveur, rebrancher retry et policy en streaming | **12 a 18** |
| **C. Remplacer l'aval** | Agent conseiller : modele frontier ou Mistral Large, boucle d'outils (`search_formations(criteres)`, `get_fiche(id)`, `compare(ids)`), memoire de profil typee, clarification decidee par l'agent, reponse longue structuree, citations verifiees mecaniquement contre les fiches effectivement lues. Reutilise corpus, index, reranker, FactCard, filet detresse. | **20 a 30** |

Le delta B -> C est de l'ordre de 8 a 12 jours-agent, pour une architecture ou la clarification, la
memoire et la longueur ne sont plus des regles de prompt qu'on espere voir respectees mais des
proprietes du systeme. La voie A est a faire de toute facon cette semaine : elle enleve trois
defauts visibles pour deux jours.

Reserve honnete : la voie C ne resout pas le trou de couverture corpus mesure a 60 % de la casse
en Sprint 5. Un agent qui cherche mieux dans un corpus qui ne contient pas la reponse repondra
mieux qu'aujourd'hui - il ne repondra pas juste. La brique manquante, dans les deux voies, est
l'autorisation explicite d'utiliser la connaissance generale du modele, clairement etiquetee comme
telle, pour tout ce qui n'est pas un chiffre de fiche : calendrier, passerelles, amenagements,
reconnaissance de diplomes, cout d'une ecole. C'est la moitie des questions du run.

# OrientAI : analyse complete de la chaine de reponse et plan d'amelioration

Jarvis, nuit du 04 au 05 septembre 2026. Branche `jarvis/analyse-2026-09-05` (jamais mergee, rien sur main ni prod).
Perimetre fixe par Matteo : la chaine de reponse seule (data, retrieval, generation, modele, evaluation), personas lyceen Parcoursup et etudiant post-bac, criteres dans l'ordre : pertinence des references, comprehension du profil, expression, couverture.

Tout chiffre de ce rapport cite sa mesure (fichier, script ou run). Ce qui n'a pas ete mesure est marque "non mesure". Les rapports detailles des 8 scouts (data, retrieval, generation, historique des evaluations, docs strategiques, mode recit, sets d'evaluation, etat de l'art) sont dans `results/jarvis_analyse_2026-09-05/scouts/`.

---

## 1. Resume executif

**Verdict** : le produit servi aujourd'hui est nettement moins bon qu'un ChatGPT ou un Claude sans aucune donnee, sur le critere ou les 52 040 fiches devaient etre l'avantage. Sur 67 tours de conversation juges a l'aveugle par Claude Opus 5 (rubrique 1-5, 4 criteres) :

| systeme | references | comprehension | expression | couverture | moyenne | refus |
|---|---|---|---|---|---|---|
| OrientIA servi (Mistral medium + RAG, mode strict v4) | 2,04 | 2,07 | 2,15 | 1,90 | **2,04** | 40 % |
| Claude Sonnet 5 avec les MEMES fiches que le pipeline | 3,35 | 3,89 | 3,35 | 3,97 | 3,64 | 0 % |
| Claude Sonnet 5 sans aucune fiche | 3,47 | 4,14 | 4,27 | 4,03 | 3,98 | 0 % |
| GPT-5.5 sans aucune fiche | 3,90 | 4,10 | 4,64 | 4,49 | **4,28** | 0 % |
| Agent a outils, Mistral medium (spike) | 2,77 | 3,37 | 3,62 | 3,38 | 3,28 | 5 % |
| Agent a outils, Sonnet 5 (spike) | 3,56 | 4,23 | 4,12 | 4,12 | 4,01 | 0 % |

Trace : `runs/judge_opus_*.jsonl`, agrege par `aggregate.py` dans `AGGREGATE_opus.md`. Le contre-juge GPT-5.5 (echantillon, section 3.3) donne le meme ordre.

**Les quatre faits qui portent le plan** :

1. **Les fiches retrouvees n'apportent rien, meme a un bon modele.** Sonnet 5 note 3,47 en references sans fiche et 3,35 avec les fiches que le pipeline lui sert : le retrieval actuel a une contribution nulle ou negative. Le RAG plat (embedding 2023 + reranker a priors) ne sert pas la bonne fiche, et quand il la sert, le texte embarque ne dit pas ce qui compte (type de formation, LAS, taux, places sont muets ou faux dans `fiche_to_text`).
2. **La generation servie detruit ce qui reste.** Sur les memes fiches, Sonnet fait mieux que le pipeline sur 51/65 tours en references et 62/65 en couverture. Le mode strict v4 (2 puces, 90 mots, question finale, "[source S3]" dans le texte, 40 % de refus) est un choix de prompt, pas une limite du modele : le meme Mistral medium, avec un prompt de conseiller et des outils, passe de 2,04 a 3,28.
3. **Mais Mistral medium libere invente.** 62 % des tours de l'agent Mistral contiennent une erreur factuelle relevee par le juge (40/65 : places, taux, procedures, etablissements disparus), contre 16 % pour le pipeline strict, 21 % pour l'agent Sonnet, 1 % pour GPT-5.5 seul. Le mode strict n'etait pas une erreur de conception, c'etait le seul garde-fou d'un modele qui ne tient pas seul. Le choix du modele est la decision n°1 (section 8).
4. **Le lookup structure retrouve ce que le RAG rate, sans encore le prouver au juge.** Le spike (`spike_agent.py`, recherche lexicale filtree + lecture de fiche complete) retrouve la LAS Psycho Bordeaux (taux 11 %, 20 places) et la Licence Informatique Toulouse III (294 places, taux 45 %) que le pipeline declarait inexistantes ; sur les 8 tours ou meme Sonnet echouait avec les fiches du pipeline, l'agent Sonnet en remonte 6 a >= 3 et 3 a >= 4. Mais en moyenne l'agent Sonnet (4,01) fait jeu egal avec Sonnet sans aucune donnee (3,98) : le juge ne peut pas verifier les chiffres contre le corpus, et la batterie contient beaucoup de questions de procedure (cesure, bourses, CAPES, Erasmus) ou le corpus n'a rien a dire. La valeur du corpus n'est pas "connaitre les formations" (les modeles les connaissent) : c'est fournir des chiffres 2025-2026 verifiables et les verifier. Ce n'est mesurable que par un controle deterministe des chiffres cites (lot 0), pas par un juge LLM.

**Les trois decisions a prendre (Matteo + Ella)** : section 8.

---

## 2. Ce qui a ete mesure, et comment

- **Batterie** : 60 conversations (30 lyceens Parcoursup, 30 etudiants post-bac), 67 tours dont 5 conversations multi-tours, ecrites en langage naturel adolescent/etudiant avec profil, ville, contraintes, et une part de questions floues, de peur, de reorientation. `battery.json`. Aucune question du banc 497q existant (155 bases x 4 variantes, 0 multi-tour, 0 log prod : scout 07) n'est reutilisee.
- **Systemes joues** (`run_battery.py`, `spike_agent.py`) : pipeline local en conditions de serving (`make_production_pipeline`, temperature 0,3, history 6, `ORIENTIA_NARRATIVE_MODE=1`) ; Sonnet 5 sans contexte ; GPT-5.5 sans contexte ; Sonnet 5 avec exactement les fiches servies par le pipeline sur chaque tour (isole la generation du retrieval) ; deux agents a outils (Mistral medium 2604 et Sonnet 5) sur un lookup structure du meme corpus.
- **Juge** : Claude Opus 5 (adaptive thinking), aveugle au systeme, rubrique 4 criteres 1-5 + refus + erreur factuelle + cause d'echec (`judge.py`). Contre-juge GPT-5.5 sur 30 tours x 4 systemes pour mesurer le biais de famille (le scout 08 rappelle que Opus notant Sonnet est le cas d'auto-preference decrit dans la litterature).
- **Lecture de code et de docs** : 8 scouts en lecture seule (rapports dans `scouts/`), chaque affirmation avec fichier:ligne.
- **Cout** : environ 19 USD d'API (17-18 EUR) sur les 20 EUR autorises (detail section 9).
- **Ce que la batterie ne mesure pas** : le mode recit. Son predicat (`src/rag/narrative_detect.py:33-35`, question >= 300 caracteres, ou >= 200 avec 2 facettes) ne se declenche sur aucun des 67 tours (max 155 caracteres, `format_decision` None 67/67). Un lyceen ecrit court : le mode recit, tel que gate, ne sera jamais servi a la cible. Tout ce qui suit mesure le mode strict v4, qui est le mode reellement servi.

---

## 3. Verdict chiffre

### 3.1 Par critere et par persona

Le systeme local est le pire des six sur les 4 criteres, et l'etudiant post-bac est moins bien servi que le lyceen chez tous les systemes (local 1,88 vs 2,21 en references ; le corpus MonMaster est le moins bien verbalise, scout 01 section 2.2).

Distribution des notes "references" (part des tours >= 4) : local 4 %, Sonnet+fiches 46 %, Sonnet seul 59 %, GPT seul 85 %, agent Mistral 23 %, agent Sonnet 59 %.

Par famille de questions (tags de `battery.json`, note references moyenne local / Sonnet seul / agent Sonnet / agent Mistral) : master (6) 2,14 / 3,86 / 3,83 / 2,83 ; geo (5) 2,33 / 3,83 / 3,83 / 3,00 ; reorientation (5) 1,67 / 3,83 / 3,67 / 2,50 ; BTS (3) 2,00 / 4,00 / 4,00 / 2,50 ; sante (3) 2,75 / 3,50 / 3,25 / 2,75. Aucune famille ou le pipeline actuel bat un modele seul.

### 3.2 Ou est la cause, tour par tour

Methode : quand le pipeline note <= 2 en references, on regarde ce que Sonnet fait des memes fiches.
- 45 tours a <= 2 chez local. 18 remontent a >= 4 avec Sonnet sur les memes fiches : la generation est seule en cause (E02, E08, E11.1, E15, E16, E18, E19, E21, E28, E30, L04, L13.0, L14, L16, L22, L25.1, L25.2, L28).
- 8 restent <= 2 meme avec Sonnet : les fiches servies sont en cause (E04, E05, E10, E14, E22, L03, L13.1, L21). Sur ces 8, note references de l'agent Sonnet / agent Mistral : E04 3/2, E05 2/2, E10 4/2, E14 3/3, E22 4/3, L03 3/2, L13.1 4/4, L21 3/2 (GPT seul : 4, 4, 4, 4, 3, 3, 4, 4).
- 4 tours sans aucune fiche servie (E23, E28, L06, L24) : la question etait standard ("MPSI Louis-le-Grand ou INSA ?", "j'ai peur de me tromper").
- Erreurs factuelles relevees par le juge : local 11/67, Sonnet+fiches 22/65, Sonnet seul 26/64, GPT 1/67. L'ecart Claude/GPT est suspect (meme juge de famille Claude qui serait plus severe avec les siens, ou GPT plus vague donc moins attaquable) : le contre-juge GPT tranche en 3.3.

### 3.3 Contre-juge GPT-5.5 (echantillon de 30 tours, 4 systemes)

Les credits OpenAI se sont epuises pendant ce run (429 "no credits remaining") : tours valides local 30, Sonnet+fiches 30, Sonnet seul 28, GPT seul 14. Sur les tours communs aux deux juges (`AGGREGATE_gpt.md`, script de comparaison dans `notes` du 05/09) :

| systeme | n commun | moyenne Opus | moyenne GPT | accord exact (references) | accord a +/-1 | err. fact. Opus / GPT |
|---|---|---|---|---|---|---|
| local | 30 | 2,08 | 2,36 | 87 % | 100 % | 5 / 5 |
| Sonnet + fiches | 29 | 3,53 | 3,88 | 66 % | 100 % | 10 / 18 |
| Sonnet seul | 27 | 3,94 | 4,17 | 70 % | 100 % | 13 / 19 |
| GPT seul | 14 | 4,25 | 4,71 | 64 % | 100 % | 0 / 0 |

Lecture : GPT est plus genereux de 0,2 a 0,5 point sur tout le monde, l'ordre des systemes est identique, et aucun ecart de plus d'un point sur les references. Sur les erreurs factuelles, GPT en releve davantage chez Sonnet que ne le fait Opus : l'hypothese d'un juge Opus indulgent avec sa famille n'est pas soutenue par cet echantillon ; l'ecart Claude 34-41 % contre GPT 1 % en erreurs est vu par les deux juges. Reste non tranche : si GPT-5.5 fait moins d'erreurs ou s'il est plus vague donc moins attaquable (expression 4,64, la plus haute, et zero refus). Un controle deterministe des chiffres (lot 0) tranchera. Ce que l'echantillon ne dit pas : le kappa avec un humain (aucun humain cette nuit).

### 3.4 Pires tours du pipeline (a relire pour sentir le produit)

- L06 "MPSI Louis-le-Grand ou INSA Lyon ?" : aucune fiche servie, reponse esquive.
- L24 "j'ai peur de me tromper de voie" : refus.
- L13.0 "licence info a Toulouse" : "Aucune licence informatique classique n'est listee a Toulouse dans mes donnees". La fiche existe (Licence Informatique UT3, 294 places), elle etait au rang 6 du reranker avec `V4_MAX_SOURCES=5` (`generator.py:36`).
- L03 "PASS ou LAS a Bordeaux, LAS psycho ?" : "je n'ai pas de LAS ni de licence de psycho dans mes sources". La fiche Parcoursup existe (`fili_code=Licence_Las`, taux 11 %, 20 places) mais `fiche_to_text` n'emet jamais `fili_code` : le texte embarque ne contient ni "LAS" ni "sante".
- L04 STMG 9 de moyenne, commerce : deux BUT TC a Saint-Etienne et Laval (villes non demandees), aucun BTS MCO/NDRC.
- E04 "PCSI vers L2" : confond avec le Portail PCSI de Perpignan. E29 : "licence pro via Parcoursup", faux.
- E01 "je veux quitter le droit" : propose Portail Droit (le router remplit `secteur=droit` sans champ de rejet, `router_llm.py:371-443`).

---

## 4. Ou se perd la qualite : la chaine des causes

Chaque item : constat, preuve, effet mesure sur la batterie.

### 4.1 Data et textualisation (scout 01, 24 Ko)

1. **Le texte embarque dit faux sur 13 011 fiches Parcoursup** : `profil_admis.acces_pct` est ecrit "taux d'acces par profil : 81 % pour bac general" alors que c'est une repartition des admis (`embeddings.py:223-237`) ; le pourcentage "IDF" est en fait "meme academie" ; 10 878 fiches portent une insertion etiquetee "apprentissage Inserjeunes CFA" qui vient d'InserSup discipline x region. Le generateur cite ce qu'on lui donne.
2. **Les champs qui decident ne sont jamais verbalises** : `fili_code` (BTS/BUT/Licence/LAS/CPGE...), `selectivite_code`, `lien_form_psup`, historique 2023-2025, `nombre_places` pour une partie, attendus (absents du corpus). Consequence directe : L03 (LAS invisible), L04 (BTS non distingues), et le FactCard n'a que 12,8 % de ses 31 champs chiffres remplis, 37,8 % des fiches servies sans aucun chiffre (scout 03).
3. **Cout : zero cle dans 52 040 fiches** (`fact_card.py:231` toujours None). ECE Lyon recommandee "sans cout".
4. **Geographie** : 12 831 fiches sans ville (onisep, LBA, CFA), villes non normalisees (Villeurbanne, "Lyon 8e Arrondissement", "LYON CEDEX 07"), 0 lat/lon ; 49/49 BUT Informatique classes en domaine "autre" (`parcoursup.py:245-259`).
5. **Fraicheur** : session 2025 servie en septembre 2026 (voeux 2026 non ingeres alors que le dataset data.gouv est quotidien jusqu'au 15/01/2026, scout 08), MESRI reussite licence cohortes 2012/2014 sur bacs S/ES/L, 26 % des RNCP expires marques actifs, CSV bruts absents du disque (pipeline non rejouable). 13 011 Parcoursup ingerees sur 14 252 brutes (91 %) et un dataset national qui en compte davantage : couverture Parcoursup incomplete, cause non mesuree.
6. **Vide de couverture** : PASS 43 fiches, LAS 286 (dont 3 a Bordeaux), 0 donnee de reussite PASS vers MMOP ; MonMaster 7 573 fiches mais champs `taux_admission` a 0 sur 385.

### 4.2 Retrieval (scouts 02, 02b)

1. **Le dense ne discrimine pas** : ecart de score entre le rang 1 et le rang 100 = 3,2 % en mediane sur 136 questions (mistral-embed v23.12, IndexFlatL2). Les priors documentaires du reranker ont une amplitude de 67 % (1,0 a 1,67). Resultat mesure : en mediane 0 fiche sur 5 du top-5 dense survit au rerank top-5. Le classement final est decide par les priors, pas par la question.
2. **Aucun cross-encoder**, et Mistral n'en propose pas (scout 08, catalogue officiel du 05/09).
3. **L'hybride ADR-058 est mort deux fois** : `annex_quota` et `double_index` valent None sur 67/67 tours (62/67 passent par le quad sub-index sans BM25) ; le RRF ne fusionne rien car les cles `_orig_index` sont absentes cote dense (meme cause que le bug `idx:-1` du set de pertinence). Fix de 3 lignes, mais il faut le savoir.
4. **`V4_MAX_SOURCES=5`** (`generator.py:36`) alors que 10 a 12 fiches sont servies : L13.0 avait la bonne fiche au rang 6 (score 1,1717 vs 1,1748 du rang 1, descendue par MMR).
5. **La requete vectorielle est le message courant seul** (`pipeline.py:828`), pas de reformulation autonome avec l'historique : tout multi-tour repart de zero.
6. **Filtres structurels vides** : `secteur` et `budget` sont renseignes sur 0/52 040 fiches alors que le router les peuple a chaque question ; `top_k_override` est ecrase sur 27/33 tours.
7. **Tokenisation** : "Lyon1" devient `lyon1`, jamais `lyon` : le BUT Info IUT Lyon 1 est absent du top-2000 BM25 sur L01 ; les intitules Parcoursup des ecoles privees recopient le profil candidat, donc le top-15 BM25 est tout prive.
8. **Un banc gratuit dort** : `golden_qa.index` contient 676 vecteurs de questions jamais exploites ; `eval_retrieval.py` rendrait 0 (ids `idx:NNNNN` vs cle `id` absente sur 38 596/52 040 fiches).

### 4.3 Generation (scout 03, 44 Ko)

1. **Le mode strict v4 formate la reponse a mort** : R6 (`system_v4_strict.py:108-124`) impose 2 puces + question finale. Mesure : mediane 90 mots, 46/67 exactement 2 puces, 54/67 finissent par "?", 59/67 contiennent "[source S" dans le texte servi, 21/67 ouvrent par "Je n'ai pas". Le juge note 2,15 en expression et 1,90 en couverture. Sur les memes fiches et sans ce prompt, Sonnet fait 3,35/3,97.
2. **`corpus_check.py:234` retourne `False` en dur** quand l'etablissement ne matche pas : a detruit E11 et E17 sur des formations presentes 43, 14 et 5 fois dans le corpus.
3. **La policy WARN colle "des patterns que nous surveillons"** dans la reponse (`policy.py:83-95`) ; le validateur appende son bloc "Points a verifier dans ma reponse" (v1) : le systeme publie son auto-critique au lieu de corriger.
4. **Le chemin streaming (`pipeline.py:1145-1152`) est sans policy, sans post-process, sans retry** : c'est celui que le front appelle. Ce que la batterie mesure (chemin `answer`) est donc plus favorable que ce que l'utilisateur voit.
5. **Router sans champ de rejet** (`router_llm.py:371-443`) : E01 (fuit le droit) devient `secteur=droit`. `dedup_sector_vs_eviter` existe (`profile_clarifier.py:292-325`) mais hors chemin servi.
6. **Zero clarification, zero memoire de profil** (`src/state/` vide), history plafonnee a 6 messages. Regles R3 et R9 du prompt contradictoires (72 vs 25 mots).
7. **Les refus** : 27/67 (40 %) juges comme refus, sur des questions standard. `geo_refusal` et la clause "je n'ai pas dans mes sources" sont declenches par un retrieval qui ne trouve pas, puis figes par un prompt qui interdit de completer.

### 4.4 Evaluation et methode (scouts 04a/b/c, 06, 07)

1. **Dernier verdict humain : 22/04/2026, mediane 2/5** (3 questions dures, 5 profils) et 3/5 (pack 10 questions). Jamais re-mesure depuis. Le "humain simule" des rapports suivants est Claude Sonnet 4.5 en roleplay (`report_humain_simule_v3.md:17`).
2. **Le gel du 11/06** (groundedness 0,949) porte sur les affirmations seulement ; la baisse "hallucinations 54 -> 10" est pour 54 -> 44 une correction de rubrique. Deux baselines 497q incompatibles (0,702 vs 0,812). Pipeline non deterministe a temperature 0 (~12 questions changent d'issue). Gate du 09/06 FAIL sur du bruit, bande +/-3 ajoutee apres coup.
3. **Le banc 497q** = 155 questions de base x 4 variantes, 0 multi-tour, 0 log de production ; recall@5 jamais mesure ; set de pertinence 135/387 utilisable (bug idx:-1). Kappa juge-humain jamais calcule. Ragas faithfulness 0,489 avec un juge de la meme famille que le generateur. Le mode recit a ete mesure sur la forme seulement (scout 06).
4. **Dernier commit 16/07/2026 (c7402d3)** ; rien jusqu'au 04/09. Latences mesurees le 08/06 : 57 a 102 s, contre 7 a 15 s annoncees ; latence mesuree cette nuit sur `answer` : mediane 4,6 s (0,4 a 7,5), 3 workers.
5. **Promesses** (scout 05) : le dossier jury est prudent (risque jury faible) ; la cible IA de juin est implementee a 12/34 items ; citation causale, decodage contraint, reranker, lookup structure, memoire, clarification, eval gatee en CI : aucun n'est dans `src/` au chemin servi. "Le probleme mesure n'est pas l'hallucination, c'est l'inutilite" (`audit_empirique_2026-06-09/L1-Batterie-empirique.md:32`) : cette nuit le confirme.

---

## 5. Ce que le spike "agent a outils" prouve, et ce qu'il ne prouve pas

**Ce qui a ete construit** (`spike_agent.py`, ~350 lignes, jetable) : deux outils sur les 52 040 fiches, `search_formations(query, ville, region, source, type_formation)` (BM25 lexical sur nom + etablissement + ville + fili_code + domaine + debut du texte, avec normalisation des accents et de la coupure lettre/chiffre "Lyon1 -> lyon 1", filtres exacts) et `get_fiche(idx)` (fiche complete nettoyee) ; un prompt de conseiller (tutoiement, 250-450 mots, chercher avant de citer, jamais refuser, une question de clarification si le profil est vague) ; une boucle a outils plafonnee a 8 iterations, jouee par Sonnet 5 et par Mistral medium 2604 sur les 67 tours, juge Opus aveugle comme les autres.

**Ce qu'il prouve** :
- Le lookup structure retrouve ce que le RAG plat ne trouve pas : LAS Psycho Bordeaux (L03, 4 appels, 24 s chez Sonnet ; Mistral la trouve aussi en 10 appels, 13 s), Licence Informatique Toulouse III (L13), les BTS MCO/NDRC pour la STMG a 9 de moyenne (L04, avec taux d'acces et part de bacs techno admis lus dans la fiche). Sur les 8 tours "fiches en cause", l'agent Sonnet remonte 6 tours a >= 3 et 3 a >= 4 la ou Sonnet avec les fiches du pipeline restait a 2.
- Le prompt fait la moitie du chemin a modele constant : Mistral medium passe de 2,04 (strict v4) a 3,28 (agent), +1,29 en comprehension, +1,48 en expression, +1,49 en couverture, meilleur sur 50 a 58 tours sur 65 selon le critere.
- La latence est tenable : mediane 18 s (Sonnet), 8,5 s (Mistral), 0 erreur d'execution sur 134 tours. Cout par conversation : 0,03 USD (Sonnet, 2,11 USD pour 67 tours), 0,007 USD (Mistral).

**Ce qu'il ne prouve pas, et qui change le plan** :
- **Aucun gain moyen mesurable du corpus** : agent Sonnet 4,01 contre Sonnet sans rien 3,98 (references +0,06, meilleur sur 20 tours, pire sur 16). Deux raisons mesurables : 13 tours sur 67 n'ont declenche aucun appel d'outil (questions de procedure : cesure, bourses, Erasmus, detresse) et le juge ne voit que la reponse, pas le corpus, donc il ne peut pas distinguer un chiffre lu d'un chiffre plausible. La batterie mesure la qualite de conseil ; la valeur du corpus (chiffres 2025 exacts) est invisible a un juge LLM.
- **Mistral medium hors du mode strict invente** : 40/65 tours avec erreur factuelle (juge Opus), dont des lectures fausses de la fiche qu'il vient d'ouvrir (L03 : "PASS 45 places, 97 % mention Bien ou TB" en contradiction avec la ligne suivante ; L13 : "98 % avec mention, 49 % sans mention"), des etablissements disparus (SUPINFO, ENA), des procedures fausses (licence pro via Parcoursup, MonMaster pour le M2). Sonnet fait 14/66, GPT seul 1/67. Le mode strict actuel (16 %) achete sa faible erreur par 40 % de refus.
- **Le juge n'est pas un verificateur** : la seule mesure qui etablira la valeur du corpus est un controle deterministe des chiffres cites contre la fiche citee. Ce controle existe deja dans le projet (lot 1 de juillet, "verification deterministe de chaque chiffre contre sa source citee", `content/chantiers.json` du QG) ; il n'a pas ete branche sur cette batterie faute de temps. C'est la premiere tache du lot 0.

Le code du spike est jetable ; ce qui est reutilisable est le schema d'outils, le prompt, et la batterie.

---

## 6. Etat de l'art septembre 2026 (scout 08) : ce qui change le plan

Sources primaires fetchees le 05/09 marquees [P], le reste non recoupe.

- **Le concurrent est ChatGPT en usage direct** : 61 % des terminales utilisent l'IA pour Parcoursup (Diplomeo 2026), 23 % lui font plus confiance qu'a Parcoursup. Les acteurs francais (Hello Charly 660 000 jeunes, MonProjetSup public, Diagoriente, Wilbi) sont tous gratuits pour le particulier, finances B2B/B2G. Aucune evaluation publique de qualite n'existe pour aucun d'eux : etre le premier a en publier une est une position.
- **`mistral-embed` est en v23.12 et c'est le seul embedding texte de Mistral [P]**. `bge-multilingual-gemma2` (etat de l'art FR-MTEB annonce) et `qwen3-embedding-8b` sont servis chez Scaleway Paris a 0,10 EUR/M [P] : la souverainete tient sur l'embedding sans Mistral.
- **Mistral n'a aucun reranker [P]** ; les open-weights (`bge-reranker-v2-m3`, Qwen3-Reranker, jina v3) tournent sur un L4 a 679 EUR/mois chez Scaleway [P]. Cohere Rerank 4 a 0,0025 USD/recherche si on accepte la dependance.
- **Le pipeline de reference 2026 n'est pas agentique** : hybride, top-100, MMR, cross-encoder, top-5/10. Il nous manque exactement le cross-encoder et un dense qui discrimine. Le sur-retrieval est le mode d'echec n°1 des agents (8-12 boucles) : plafonner les iterations est unanime. HyDE n'est mesure gagnant nulle part en 2026.
- **Routage structure vs semantique** : "les BUT info a moins de 50 km de Rennes avec taux > X" est une requete SQL, pas un embedding. C'est exactement ce que le spike teste.
- **Mistral Agentic Search (20/08, [P])** : +47 points sur FinanceBench, latence p90 en baisse. Mesure sur des documents de 147 pages : transport a des fiches courtes non etabli, a tester sur 20 tours avant d'engager.
- **Evaluation** : juge d'une autre famille obligatoire (auto-preference), calibration humaine 100-300 traces, kappa > 0,6. Un "80 % d'accord" sans kappa ne vaut rien.
- **Prix modeles [P Anthropic]** : Sonnet 5 a 2/10 USD par M tokens definitif, Opus 5 a 5/25, pas d'option UE en premiere partie (Bedrock/Vertex UE +10 %). GPT-5.5 a 5/30 selon agregateurs (non verifie). Mistral medium 2604 a environ 0,4/2 (non verifie).
- **Cadre d'usage IA de l'Education nationale (juin 2025)** et licence ODbL de l'API ONISEP : a lire et faire verifier avant commercialisation.

---

## 7. Plan priorise, en lots dispatchables

Principe : chaque lot est gate par la batterie de cette nuit (67 tours, juge Opus + contre-juge GPT, `aggregate.py`), rien ne merge sans delta mesure. Efforts estimes par le scout 03 et par moi, non mesures.

### Lot 0 : le banc devient le gate (Claudette, 1 a 2 j, ~3 USD par passage)
- Deplacer `battery.json`, `run_battery.py`, `judge.py`, `aggregate.py` dans `src/eval/battery/`, ajouter un script `make bench` qui joue `local` + juge Opus + juge GPT echantillon et ecrit le tableau.
- Fixer la reference : local = 2,04 ; cible lot 2 >= 3,3 (niveau Sonnet+fiches) ; cible finale >= 4,0 (niveau GPT seul).
- Brancher le controle deterministe des chiffres cites (celui du lot 1 de juillet) sur la sortie de la batterie : part des chiffres cites retrouves dans une fiche du corpus. C'est la seule metrique qui voit la valeur du corpus (section 5) ; elle devient la metrique de tete a cote de la note du juge.
- Corriger `eval_retrieval.py` (ids `idx:NNNNN` vs `id`), mesurer recall@10 sur `golden_qa.index` (676 questions deja embarquees, gratuit).
- Pourquoi d'abord : trois mois de sprints ont ete pilotes par des bancs incomparables (4.4). Sans ce lot, tout lot suivant est invérifiable.

### Lot 1 : dire vrai et dire tout dans les fiches (Claudette, 3 a 5 j, ~10 USD de re-embedding)
- Reecrire `fiche_to_text` (`embeddings.py:40-126, 223-237, 245`) : emettre `fili_code` en clair ("Licence avec acces sante (LAS)", "BTS", "BUT", "CPGE"), places, taux d'acces avec definition, historique, `selectivite_code`, `lien_form_psup`, repartition des admis par bac (et non "taux d'acces par profil"), source d'insertion correcte, date de la donnee.
- Normaliser les villes (code commune INSEE, unite urbaine) pour les 12 831 fiches sans ville et les variantes Lyon/Villeurbanne/CEDEX ; entree BUT dans la cascade domaine.
- Re-embarquer avec `bge-multilingual-gemma2` chez Scaleway Paris (0,10 EUR/M, environ 5 EUR pour 52 040 fiches) en parallele de mistral-embed, comparer recall@10 sur golden_qa. Garder celui qui gagne.
- Gate : L03, L13, L04 doivent passer a >= 4 en references ; recall@10 avant/apres.

### Lot 2 : la generation arrete de detruire (Claudette, 5 a 8 j, ~5 USD)
- Retirer R6 (2 puces + question) et la clause "je n'ai pas dans mes sources" comme reponse terminale : prompt de conseiller, 250-450 mots, chiffres cites quand ils existent, connaissance generale signalee comme telle quand la base ne repond pas (le prompt du spike est un point de depart, `spike_agent.py` SYSTEM).
- `V4_MAX_SOURCES` 5 -> 10 ; `corpus_check.py:234` retire ou rendu tolerant ; policy WARN silencieuse ; le chemin streaming passe par la meme post-chaine que `answer`.
- Router avec champ `eviter`, brancher `dedup_sector_vs_eviter` ; requete de retrieval reformulee avec l'historique (standalone rewrite) ; une seule question de clarification par regle (ni ville ni domaine detectes).
- Fix RRF (`_orig_index`), tokenisation lettre-chiffre, `annex_quota`.
- Gate : local >= 3,3 en moyenne, refus < 10 %, ET erreurs factuelles <= 16 % (niveau actuel) : le spike montre que Mistral libre atteint 3,3 en inventant sur 62 % des tours, la moyenne seule ne suffit pas comme gate.

### Lot 3 : lookup structure a la place du RAG plat (Claudette, 10 a 15 j)
- Industrialiser le spike : table SQLite/DuckDB des 52 040 fiches avec colonnes typees (type, ville, region, departement, taux, places, bac_type, source, annee), outils `search_formations` (BM25 + filtres), `get_fiche`, `compare(idx...)`, `stats(ville, type)` ; boucle a outils plafonnee a 6 iterations ; latence cible < 15 s p90.
- Modele : celui qu'arbitrera la decision 1 (section 8). Le spike donne les deux chiffres : Sonnet 4,01 / 21 % d'erreurs / 18 s ; Mistral medium 3,28 / 62 % / 8,5 s.
- Ajouter le cross-encoder (`bge-reranker-v2-m3`, L4 Scaleway) uniquement si le lot 1 laisse recall@10 < 0,8 : le lookup structure rend le rerank moins central.
- Gate : >= 4,0 en moyenne sur la batterie, references >= 4 sur > 70 % des tours.

### Lot 4 : data manquante (Claudette + Matteo pour les licences, 5 j, en parallele du lot 3)
- Session Parcoursup 2026 (dataset data.gouv quotidien), colonnes attendus + frais declares + apprentissage ; ONISEP API (dump hebdo, cle, ODbL) pour ville, cout, statut contrat ; reussite PASS/LAS (data.enseignementsup) ; retirer ou dater les sources < 2021 ; versionner les bruts hors git avec checksum et date.
- Gate : 0 fiche Parcoursup sans places/taux ; cout renseigne sur les 496 ecoles privees ingenieur/commerce ou marque "non disponible" explicitement.

### Lot 5 : evaluation humaine et memoire (apres lot 3)
- 30 lyceens/etudiants reels sur 10 tours chacun, 2 annotateurs, kappa juge-humain ; profil persistant asynchrone (RGPD, effacement) qui pondere le classement (HiMeS).

### Ce que je ne recommande pas
- Un chantier HyDE, un mode recit gate par la longueur de la question, un reranker avant d'avoir corrige la textualisation, un banc de 500 questions synthetiques de plus.

---

## 8. Les trois decisions a prendre

**Decision 1 : le modele de generation.** Mistral medium ne tient pas seul : strict, il refuse 40 % du temps (2,04) ; libre, il invente 62 % du temps (3,28). Trois options :
- (A) Sonnet 5 (ou Opus 5) pour la generation, Mistral conserve pour l'embedding et les taches auxiliaires. Mesure : 4,01 avec outils, 21 % d'erreurs, 0,03 USD/conversation, latence 18 s. Cout : la souverainete "100 % Mistral" de l'argumentaire INRIA tombe (pas d'option UE first-party chez Anthropic, Bedrock/Vertex UE +10 %). C'est ma recommandation : l'utilisateur compare a ChatGPT, pas a un cahier des charges.
- (B) Rester Mistral et construire les garde-fous manquants : verification deterministe de chaque chiffre avant envoi (existe), relecture par un second appel, refus cible sur les procedures hors corpus. Cout : 5 a 8 j de plus dans le lot 2, et un plafond mesure a 3,3 sans ces garde-fous. Non mesure : ce que donnent les garde-fous.
- (C) Mistral Large ou un open-weight (Qwen3, Llama 4) en self-host Scaleway. Non mesure cette nuit ; a jouer sur la batterie (67 tours, ~1 USD) avant de trancher.
La decision est reversible : le lot 0 rend le banc rejouable en 10 minutes, et le lot 3 est ecrit modele-agnostique.

**Decision 2 : le remplacement du RAG plat par le lookup structure (lot 3) et l'embedding hors Mistral (lot 1).** Le RAG actuel a une contribution nulle (fait 1). Deux chemins : reparer le RAG (lot 1 + cross-encoder, garde le design) ou le remplacer par le lookup structure (lot 3, change le design). Ma recommandation : les deux dans l'ordre, lot 1 d'abord parce qu'il est necessaire aux deux chemins (textualisation, villes, embedding), et lot 3 ensuite parce que les questions a filtres (ville, type, taux) sont des requetes structurees, pas des similarites. A trancher : l'embedding `bge-multilingual-gemma2` chez Scaleway (souverain, 0,10 EUR/M) contre mistral-embed v23.12 ; a mesurer sur golden_qa avant d'engager, le lot 1 le prevoit.

**Decision 3 : ce qu'on vend, donc ce qu'on mesure.** Face a ChatGPT (3,9 en references sans aucune donnee, 1 % d'erreurs relevees), la promesse "connaitre les formations" ne tient pas. Ce qui peut tenir : des chiffres 2025-2026 verifies (places, taux, calendrier, cout) qu'un modele seul invente, une memoire de profil, et une evaluation publique que personne d'autre ne publie (aucun concurrent FR n'en a). Cela impose : un banc humain calibre (lot 5, 30 lyceens/etudiants, kappa > 0,6), un controle deterministe des chiffres comme metrique de tete, et la fraicheur des donnees (session 2026, lot 4) comme argument produit. A decider : accepter que l'axe "souverainete" descende derriere "exactitude verifiee" dans le discours.

---

## 9. Budget, traces, non mesure

- **Cout API de la nuit** (logs `runs/*.log`) : runs Sonnet seul 0,82, GPT-5.5 seul 1,20, Sonnet+fiches 1,27, agent Sonnet 2,11, agent Mistral 0,44 ; juge Opus 3,56 + 3,44 + 2,03 + 1,77 = 10,80 ; juge GPT 1,66 (arrete par epuisement des credits OpenAI) ; ~0,3 perdu au redemarrage apres la coupure 429 ; runs du pipeline local sur Mistral non chiffres (estime < 0,5). Total environ 19 USD, soit 17-18 EUR, sous les 20 EUR. Les credits OpenAI sont a zero : a recharger si on veut completer le contre-juge.
- **Traces** : `results/jarvis_analyse_2026-09-05/` (battery.json, run_battery.py, judge.py, aggregate.py, spike_agent.py, runs/*.jsonl, AGGREGATE_opus.md, AGGREGATE_gpt.md, scouts/). Branche `jarvis/analyse-2026-09-05`, aucun fichier de `src/` modifie.
- **Non mesure** : le chemin streaming (`pipeline.py:1145`) en conditions front ; le mode recit sur des questions longues ; la latence du spike en production ; recall@10 des embeddings candidats (lot 1) ; la cause des 1 241 lignes Parcoursup non ingerees ; le kappa juge-humain (aucun humain cette nuit) ; l'auto-preference exacte du juge Opus (le contre-juge GPT ne porte que sur 30 tours).
- **Reserve d'instrument** : un seul juge par ligne, rubrique ecrite par moi, batterie ecrite par moi. Les ordres de grandeur (2 vs 4) sont robustes a un biais de un demi-point ; les dixiemes ne le sont pas.

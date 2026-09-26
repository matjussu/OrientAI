# Étape 3 : le v2 minimal du cerveau, mesuré

25/09/2026, Claudette. Ordre `2026-09-25-1907-claudette-orientai-etape3-v2-minimal`. Contrat :
`docs/cerveau/etape3/CONTRAT-etape3.md` v2 (amendement daté 20h27, avant les bancs). Code joué : `52a0b14`
(empreinte `src_v2` `9a18c9bd356a`, prompt `913df039941d`, base `bfb26cdddfc6`, `zai-glm-5-3` sur
`api.eu.mistral.ai`, filtre `mistral-small-2603`). Référence figée : `results/multiversion/2026-09-25_reference/`
(`RAPPORT_judge_v2.json`). Juge : `judge_v2` (Opus 5.5 effort low, stdin, fiches de la page publique, consigne de
nommage), un seul passage, go de Matteo (Telegram 10790), réponses gelées avant préparation (`GEL_JUGE.json`).

Chiffres : `RAPPORT_judge_v2.json` (commande `python -m src.eval.multiversion rapport --tag 2026-09-25_v2 --juge
judge_v2`), `gate_f.json` (`python -m src.eval.multiversion.gate_f --tag 2026-09-25_v2`), traces `v2__*.jsonl`,
export pour l'explorateur `export_judge_v2/`.

## 1. En bref

- **Gate F de l'étape 3 : rouge, par la clarification seule** (2/5). Fiches attendues 94,1 %, 0 formation citée hors
  des résultats d'outils, 100 % des chiffres adossés.
- **Banc vertical, contre la prod** : erreur de fait 19,0 % contre 31,6 %, refus 2 contre 26 sur 79, note 4,27 contre
  2,26, chiffres attendus cités justes 61,9 % contre 27,9 %, chiffres affichés adossés 100 % contre 72,7 %.
- **Contre ChatGPT + recherche** (échantillon figé, 34 tours) : erreur de fait 14,7 % [6,5 ; 30,1] contre 0 %
  [0 ; 10,2], note 4,29 contre 4,67. Le repère n'est pas atteint.
- **Planchers de l'étape 4** (section 8 du parent) : refus < 10 % et adossés 100 % tenus ; erreur de fait < 10 %,
  critère 1 >= 85 % et latence p90 < 15 s non tenus.
- Aucune des 21 erreurs de fait relevées par le juge ne porte un chiffre non adossé : elles viennent des
  connaissances propres du modèle (11), d'un chiffre juste attribué à la mauvaise notion (5), d'une absence affirmée
  sans avoir tout lu (4), d'une contradiction avec la fiche lue (1). Section 4.
- Coût : 10,53 USD au registre (dont 0,16 d'estimation majorante), plafond 15.

## 2. Côte à côte avec la référence figée

| | v2, vertical (79) | prod, vertical (79) | v2, échantillon (34) | prod, échantillon (34) | ChatGPT + recherche (34) |
|---|---|---|---|---|---|
| Erreur de fait (juge) | **19,0 %** (15) [11,9 ; 29,0] | 31,6 % (25) [22,5 ; 42,6] | **14,7 %** (5) [6,5 ; 30,1] | 29,4 % (10) [16,8 ; 46,2] | 0 % (0) [0 ; 10,2] |
| Refus (juge) | **2** | 26 | **0** | 13 | 0 |
| Note moyenne (4 critères) | **4,27** | 2,26 | **4,29** | 2,25 | 4,67 |
| Critère 1 (attendus cités justes) | **61,9 %** (témoin 5,6 %) | 27,9 % | 66,7 % | 23,0 % | 34,1 % |
| Chiffres affichés adossés | **100 %** (856) | 72,7 % (témoin 42,8 %) | 100 % (366) | 66,7 % | non calculable |
| Mots (médiane) | 346 | 85 | 350 | 85 | 351 |
| Latence médiane / p90 | 19,9 / 43,5 s | 6,6 / 9,3 s | 19,9 / 67,3 s | 6,8 / 9,5 s | 27,0 / 36,9 s |
| Coût | 4,39 USD (0,056 / tour) | 1,03 USD | 2,16 USD | 0,44 USD | 6,68 USD |

IC95 de Wilson. Adossés de la v2 : recomptés a posteriori depuis les valeurs que la trace garde de chaque appel
d'outil (`mesures.adosses_v2`, extraction du critère 1, sans passer par le vérificateur) ; la prod est mesurée contre
les fiches exposées, avec son témoin de hasard.

Lot 0 (67 tours, non jugé, choix C6) : 0 panne, 223 chiffres tous adossés, latence médiane 22,4 s, p90 49,5 s,
3,11 USD. Prod au même banc : 57,0 % adossés, p90 9,6 s.

## 3. Gate F (30 questions, 32 tours), jeu de réglage après le palier 1 (amendement G)

| critère (contrat section 9) | palier 1 (ad74e97) | palier 1 bis (52a0b14) | seuil |
|---|---|---|---|
| 1. fiches attendues rendues | 95/102 (93,1 %) | **96/102 (94,1 %)** | >= 90 % |
| 2. formations citées hors résultats | 1 (faux positif du détecteur, Rennes 2) | **0** (contrôle positif : compte 1) | 0 |
| 3. clarification (orientation d'abord, <= 2 questions) | 3/5 | **2/5** | 5/5 |
| 4. chiffres adossés | 248/248 (pct, eur, places) | **388/388** (effectifs compris) | 100 % |
| juge : erreur de fait / refus / note | non jugé | 18,8 % (6/32) / 0 / 4,35 | sans seuil |

Le rouge du palier 1 reste publié (`palier1/`). Les questions de clarification posent 3 ou 4 questions au lieu de 2
(F-QINF-17, F-QINF-18, F-QMAT-12) : c'est le prompt, non touché à l'étape 3 (amendement G), à reprendre à l'étape 4.
Fiches manquantes au palier 1 bis, toutes par stratégie de recherche du modèle : F-R06 (BTS CIEL non cherchés),
F-NSAN-10 (LAS alternatives non cherchées), F-HSAN-02 (13 PASS à Lille, la fiche attendue n'est pas dans les 10
premiers candidats de `trouver_formation`, et l'autre attendue est une LAS).

Écart de compte signalé par Jarvis (389 contre 388 adossés) : le vérificateur lit en plus une colonne
« Candidatures » (F-R07, 4 effectifs, tous adossés) que l'extraction du critère 1 ne reconnaît pas ; 392 chiffres
pour le vérificateur, 388 pour le recompte.

## 4. Les 21 erreurs de fait (juge, vertical 15 + gate F 6), classées à la lecture de `erreur_detail`

| cause | n | exemples |
|---|---|---|
| connaissance propre du modèle, hors outils (réformes, cursus, sélectivité) | 11 | CRPE « depuis 2025 » (V-MAT-06) ; ECN au lieu des EDN (V-SAN-18) ; sage-femme « 5 ans » (V-SAN-12) ; IFSI « oral de motivation » (V-SAN-13) ; licence « très sélective » (F-QINF-18) ; Montpellier « hors Occitanie » (F-R07) |
| chiffre adossé, mal nommé ou mal attribué | 5 | 47,5 % (MMOPK toutes filières) présenté comme passage en médecine (V-SAN-16) ; « accès des terminales techno » lu comme un taux (V-INF-02) ; frais « du cycle » présentés par an (V-MAT-05) ; frais d'IFE (V-SAN-20, 2 tours) |
| absence affirmée sans avoir tout lu | 4 | « aucun PASS de Lille à 6 % » alors que 3 des 13 n'ont pas été lus (V-SAN-02, F-HSAN-02) ; « aucun BTS CIEL en Bretagne » (V-INF-03) ; « aucun BUT en apprentissage près de Roubaix » (V-INF-09) |
| contradiction avec la fiche lue | 1 | alternance annoncée, fiche « non » (F-MINF-19) |

Le vérificateur ne contrôle que les chiffres (section 6 du contrat) : ces erreurs passent par construction. Pistes
pour l'étape 4, à écrire avant d'être jouées : nommer chaque chiffre par le libellé de l'outil (déjà dans le prompt,
non suivi dans 5 cas) ; dire « je n'ai pas tout lu » quand un résultat est tronqué ; ne pas affirmer une absence sans
la recherche qui la prouve ; limiter les affirmations de procédure hors outils (corpus de l'étape 6).

## 5. Comportement de la boucle et coût

| banc | appels modèle | appels rejoués | appels / tour (méd.) | outils / tour (méd.) | plafond atteint | réécritures | phrases retirées | relances sur réponse vide | raisonnement / appel (méd., caractères) |
|---|---|---|---|---|---|---|---|---|---|
| vertical | 267 | 1 | 3 | 3 | 2 | 11 | 2 | 10 | 2 466 |
| lot 0 | 190 | 2 | 2 | 1 | 1 | 6 | 0 | 7 | 3 946 |
| gate F | 104 | 1 | 3 | 3,5 | 0 | 2 | 0 | 3 | 1 591 |

La latence vient du raisonnement de GLM et des boucles à plusieurs appels, pas des rejeux (4 sur 561). `lire_fiche`
à plusieurs identifiants (amendement F) a supprimé le plafond (8 questions sur 30 au palier 1, 0 au 1 bis) mais
envoie jusqu'à 20 000 caractères par appel : les définitions de chaque notion sont répétées sur chaque fiche.
Candidat étape 4 : une définition par notion quand plusieurs fiches sont lues.

Registre (`budget.json`) : palier 0 0,32 USD (dont 0,16 estimé : usage de 2 tours vides jeté par le lanceur, corrigé),
palier 1 1,16, palier 1 bis 1,54, vertical 4,39, lot 0 3,11 ; total 10,53 USD. Juge : 111 verdicts sur
l'abonnement, 20 lots, tous lus en entier (jetons lus cohérents avec la taille des lots, un échange par tâche).

## 6. Ce que cette mesure n'établit pas

- Le gate F rejoué est un jeu de réglage (amendement G) : son vert partiel ne prouve rien hors de lui. La mesure
  indépendante est celle des bancs, jouée une fois sur le code figé.
- Un seul passage du juge, sans deuxième juge : la classification de la section 4 est une lecture des `erreur_detail`,
  pas une mesure.
- Le lot 0 n'est pas jugé (choix C6) : ses erreurs de fait ne sont pas connues.
- Latence mesurée avec 3 conversations en parallèle depuis WSL : pas une latence de production.

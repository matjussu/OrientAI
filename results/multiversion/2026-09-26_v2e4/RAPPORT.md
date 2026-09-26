# Étape 4 : la réponse, mesurée

26/09/2026, Claudette. Ordre `2026-09-26-1535-claudette-orientai-etape4-reponse`. Contrat :
`docs/cerveau/etape4/CONTRAT-etape4.md` v1.4 (décisions de Matteo : Telegram 10808, 10818, 10821, 10826 ; amendements
datés avant chaque run, section 15).

Ce qui a été joué :
- **version** : `v2e4`, réglage de raisonnement par défaut ;
- **code** : 3b8b951 (`src_v2_sha` `164ccdfeb033`) ;
- **prompt** : v1 `145f0dd5a53c`, validé tel quel par Matteo ;
- **base** : `54f8aab3110f` (définition D4 corrigée, concordance verte) ;
- **modèles** : `zai-glm-5-3` sur `api.eu.mistral.ai`, filtre `mistral-small-2603`.

Référence figée : `results/multiversion/2026-09-25_reference/`. Étape 3 : `results/multiversion/2026-09-25_v2/`.

Juge : `judge_v2` (Opus 5.5 effort low, stdin, aveugle, fiches de la page publique, consigne de nommage), un passage,
110 verdicts, go de Matteo (10826). Les réponses ont été gelées avant la préparation du juge (`GEL_JUGE.json`) ;
les 19 lots sont tous lus en entier (jetons d'entrée cohérents avec la taille des lots, `judge_v2/sorties_juges`).

Chiffres rejouables sans appel d'API :
- `python3 docs/cerveau/etape4/mesures/rapport_juge.py` : juge, critère principal et garde-fous ;
- `python3 docs/cerveau/etape4/mesures/critere1_etape3.py <traces> <sortie>` : critère 1 et 1 bis ;
- `python -m src.eval.multiversion rapport --tag 2026-09-26_v2e4 --juge judge_v2` : export pour l'explorateur
  (`export_judge_v2/`, `RAPPORT_judge_v2.json`) ;
- `python -m src.eval.multiversion.gate_f --tag 2026-09-26_v2e4 --fichier <passage>` : gate F.

## 1. En bref

- **Erreur de fait, critère principal (59 tours du vertical hors recouvrement avec le gate F) : 2 sur 59 = 3,4 %,
  IC95 [0,9 ; 11,5], en comptant la panne comme un échec** (1 sur 58 tours jugés). Plancher < 10 % : **tenu**.
  Étape 3 : 13/59 = 22,0 % ; prod : 20/59 = 33,9 %.
- Sur les 79 tours du vertical : 4/79 = 5,1 % en version prudente, 3/78 = 3,8 % sur les tours jugés. Étape 3 :
  15/79 = 19,0 %.
- **Échantillon de 25 conversations (34 tours), contre ChatGPT + recherche** : 2/34 = 5,9 % en version prudente
  (1/33 jugés), contre 0/34 pour ChatGPT. Le repère n'est pas atteint, mais l'écart passe de 5 réponses à 2.
- **Gate F : vert sur ses 4 critères** : fiches 95/102, 0 formation citée hors des résultats, clarification 5/5 (2/5 à
  l'étape 3), adossés 386/386. Erreurs de fait au gate F : 2/32, contre 6/32.
- **Garde-fous** : refus 3/79, tenu (plafond 5). **Note moyenne 4,13 : NON tenu** (seuil 4,17 ; étape 3 : 4,27).
  Note des tours sans outil de données 3,90, tenu (seuil 3,84).
- **Planchers non tenus** :
  - critère 1 bis : 73,0 % pour un plancher de 85 % (étape 3, mêmes conversations : 73,4 %) ;
  - latence p90 : 50,4 s au vertical, 72,2 s au lot 0, pour un plancher de 15 s.
- **Mode de défaillance mesuré** : 3 tours sur 79 en panne au premier passage, 1 après rejeu (V-INF-05 t0, en panne
  deux fois sur deux). Cause : un appel au modèle dont le raisonnement dépasse 120 s. Pour un élève : environ
  6 minutes d'attente, puis un message d'excuse.
- **Coût** : 12,92 USD au registre (plafond 15), plus 0,02 USD de sonde hors registre. Juge sur l'abonnement.

**Lecture** : l'étape 4 atteint son objectif premier. L'erreur de fait passe de 22 % à 3,4 % sur la mesure
indépendante, et la clarification est verte. Elle le paye de deux façons :
- **l'utilité notée baisse** : couverture 4,28 → 4,01, expression 4,46 → 4,27 ;
- **la latence s'allonge** : le raisonnement augmente avec le prompt v1.

Le garde-fou « note >= 4,17 » est rouge : selon la règle de décision (section 11 du contrat), c'est à Matteo de
trancher.

## 2. Juge : critère principal et garde-fous

IC95 de Wilson. « Prudent » : un tour en panne compte comme un échec de réponse (demande de Jarvis, 26/09 19h17) ; la
décision se lit sur cette version. V-INF-05 t0 est dans les 59 hors recouvrement.

| | v2e4, prudent | v2e4, tours jugés | étape 3 (v2) | prod |
|---|---|---|---|---|
| hors recouvrement (59) : erreur de fait | **2/59 = 3,4 %** [0,9 ; 11,5] | 1/58 = 1,7 % [0,3 ; 9,1] | 13/59 = 22,0 % [13,4 ; 34,1] | 20/59 = 33,9 % |
| vertical (79) : erreur de fait | 4/79 = 5,1 % [2,0 ; 12,3] | 3/78 = 3,8 % [1,3 ; 10,7] | 15/79 = 19,0 % | 25/79 = 31,6 % |
| vertical : refus | 3 | 3 | 2 | 26 |
| vertical : note (4 critères) | | 4,13 | 4,27 | 2,26 |
| hors recouvrement : note | | 4,06 | 4,21 | 2,23 |
| gate F (32) : erreur de fait / refus / note | | 2/32 / 0 / 4,27 | 6/32 / 0 / 4,35 | |
| échantillon 34 : erreur de fait | 2/34 = 5,9 % | 1/33 = 3,0 % | 5/34 = 14,7 % | 10/34 = 29,4 % |
| échantillon 34 : note | | 4,17 | 4,29 | 2,25 |

ChatGPT + recherche, sur le même échantillon : 0/34, note 4,67.

Note par critère, au vertical (étape 3 puis étape 4) :

| critère | étape 3 | étape 4 |
|---|---|---|
| références | 3,89 | 3,90 |
| compréhension | 4,44 | 4,33 |
| expression | 4,46 | 4,27 |
| couverture | 4,28 | 4,01 |

Les plus fortes baisses, avec les commentaires du juge :
- V-SAN-05 t1, -2,0 : « il fallait donner ce chiffre [les places en kiné par PASS et LAS à Toulouse] [...] au lieu
  de répondre qu'on n'a pas l'information ». La base porte ces capacités (`sante.capacites_universite`, en
  détail) ;
- V-SAN-20 t1, -1,25 : « elle expose aussi la mécanique de recherche interne (mots-clés, filtres, rayons) » ;
- V-INF-02 t1, -1,0 : « la réponse refuse de parler de la réussite des bacs techno en licence, alors que les données
  nationales sont connues ».

Refus au juge : V-SAN-05 t1, V-MAT-07 t0 (déjà refusé à l'étape 3), V-INF-14 t1.

Garde-fous (section 11 du contrat) :

| garde-fou | seuil | mesure | verdict |
|---|---|---|---|
| refus | <= 5/79 | 3 | tenu |
| note moyenne | >= 4,17 | 4,13 | **non tenu** |
| note des tours sans outil de données | >= 3,84 | 3,90 (13 tours) | tenu |
| chiffres adossés | 100 % | 100 % (vertical et lot 0, recompte `adosses_v2`) | tenu |

La baisse de la note se lit dans les commentaires. Ce ne sont pas des erreurs, mais un conseiller plus prudent :
- il renvoie vers la source officielle au lieu de répondre ;
- il détaille ce qu'il a cherché ;
- il ne donne pas de repères généraux.

C'est l'effet attendu de l'option c (section 4 du contrat : « le risque est une baisse de la couverture »), et de la
consigne « dis exactement ce que tu as vérifié ».

## 3. Les 5 erreurs de fait, relues par famille

| # | tour | détail du juge (extrait) | famille | à l'étape 3 |
|---|---|---|---|---|
| 1 | V-SAN-02 t0 | « affirme qu'aucun PASS de Lille n'affiche 6 % » | A (absence, résultat tronqué) | même erreur |
| 2 | F-HSAN-02 t0 | « Il n'a lu que 10 des 13 options et en tire une conclusion fausse » | A (même question que 1) | même erreur |
| 3 | F-HSAN-09 t0 | « Dire que le PASS le plus proche est à Tours, à 92 km, est faux » | A (absence dans la base dite comme réelle) | non relevée |
| 4 | V-INF-15 t0 | « "Admis néo-bacheliers généraux" reprend en fait la répartition de tous les admis » | L (libellé) | non relevée |
| 5 | V-INF-20 t0 | « Le BUT Informatique n'a pas de parcours cybersécurité » | K (contenu d'une formation) | même erreur |

| famille | étape 3 | étape 4 |
|---|---|---|
| K, connaissance propre | 9 | 1 |
| N, notion des outils affirmée sans lecture | 4 | 0 |
| L, chiffre mal nommé | 2 | 1 |
| D, définition de la base | 1 | 0 |
| A, absence affirmée | 4 | 3 |
| C, contradiction avec la fiche | 1 | 0 |
| total | 21 | 5 |

Ce qui résiste :
- **L'absence sur le PASS de Lille (1 et 2).** `trouver_formation` signale maintenant les 3 options cachées
  (`ex_aequo_caches = 3`, correctif T2), et la réponse dit « j'en ai lu 10 ». Mais le modèle ne va pas chercher les 3
  autres, et au vertical il conclut encore sur l'ensemble. Le détecteur d'absence ne s'est pas déclenché sur ces
  formulations (lexique 6.2 : « Aucune de ces 10 options » échappe au motif).
- **La règle des repères (option c).** Elle n'a pas empêché l'erreur 5, parcours et contenu d'une formation, alors
  que le prompt v1 les renvoie explicitement à la source.
- **Erreur 4.** C'est un libellé que le vérificateur 6.1 ne voit pas par construction (population « néo-bacheliers »
  contre « tous les admis »).

## 4. Mesures déterministes aux bancs

| | étape 4 | étape 3 |
|---|---|---|
| vertical : critère 1 bis (attendus montrés à l'identique) | 195/267 = 73,0 % | 196/267 = 73,4 % (mêmes conversations) |
| vertical : critère 1 (323 attendus, conversations complètes) | 198/321 = 61,7 % | 200/323 = 61,9 % |
| vertical : chiffres adossés | 100 % | 100 % |
| vertical : refus au sens du filtre (court-circuits) | 1 | 1 |
| lot 0 : chiffres adossés | 100 % | 100 % |
| lot 0 : court-circuits | 1 | 1 |

Critère 1 bis : V-INF-05 est écartée (un tour en panne), comme dans le critère 1 publié. Classes des manqués au
vertical (étape 4, `critere1_etape4.json`) : fiche jamais sortie d'un outil 43, sortie mais non lue 24, valeur
rendue non écrite 3, base (écart, absent, masqué) 51. Le critère 1 ne bouge pas : le prompt v1 ne pousse pas à citer
plus de formations, et la recherche n'a pas changé de stratégie.

## 5. Latence et vitesse de l'API (amendement v1.1)

Latence du lanceur ; p90 au rang le plus proche. Vitesse : médiane par appel des secondes par millier de jetons de
sortie. Normalisée : latence × 5,64 / vitesse, ce qui suppose que tout le tour dépend du modèle (environ 90 % à
l'étape 3).

| | médiane | p90 | vitesse | p90 normalisé |
|---|---|---|---|---|
| vertical, étape 4, 78 tours sans panne | 20,9 s | 50,4 s | 4,74 | 60,0 s |
| vertical, étape 4, 79 tours avec la panne | 21,1 s | 55,4 s | | |
| vertical, étape 3 | 19,9 s | 43,5 s | 5,64 | 43,5 s |
| lot 0, étape 4 | 33,8 s | 72,2 s | 4,97 | 81,9 s |
| lot 0, étape 3 | 22,4 s | 49,5 s | 5,66 | 49,5 s |
| gate F, 1a (défaut) | 14,7 s | 62,1 s | 4,99 | 70,1 s |
| gate F, 1b (`reasoning_effort="low"`) | 18,7 s | 54,2 s | 4,36 | 70,2 s |

Au gate F, la sortie augmente de 46 % par rapport à l'étape 3 (152 254 jetons contre 104 301), et le raisonnement de
57 %. Le temps d'un appel suit les jetons de sortie (section 8 du contrat), donc la latence recule avec le prompt v1.
« low » ne réduit rien : raisonnement ×1,24 (section 15.5 du contrat). Le plancher p90 < 15 s est déclaré non tenu à
l'étape 4 (décision 10821).

Mode de défaillance, liste complète :
- V-INF-05 t0 et t1, V-SAN-11 t0 au premier passage : 3 appels aboutissent, puis le 4e dépasse 120 s trois fois ;
  380 à 400 s par tour ; V-SAN-11 avait produit 9 685 jetons avant la panne ;
- au rejeu : V-SAN-11 t0 répond en 241 s, V-INF-05 t0 retombe en panne (402 s).

Taux : 3/79 au premier passage, 1/79 après rejeu. Premier passage gardé : `bancs_passage1/`.

## 6. Ce qui a été livré (code 3b8b951)

- **prompt v1 figé** : sha256 du fichier vérifié à chaque chargement ;
- **outils** : sigles dépliés, intitulé lu par début de mot, option et ex æquo cachés signalés, périmètre de la base
  dit sur un résultat vide, une définition par notion ;
- **vérificateur** : libellé (portée nationale, période), absence ; D5 = b, précision 75 % sur le lot 0 ;
- **réécriture** unique, qui ne doit pas être mentionnée à l'élève ;
- **consigne de fin** au 6e outil ;
- **timeout** de 120 s ;
- **latence et vitesse** publiées ensemble ;
- **base** : définition « Accès des terminales » corrigée, plus le contrôle général des répartitions ;
- **tests** : `tests/test_v2_etape4.py`, 24 tests, dont un sabotage par garantie.

## 7. Ce que cette mesure n'établit pas

- **Un seul passage du juge, sans second juge.** Sur 59 tours, 1 ou 2 erreurs d'écart ne se distinguent pas du
  bruit. Le gain de 13 à 2 erreurs dépasse ce bruit, mais son ampleur exacte reste celle d'un seul juge.
- **Que la baisse de la note vienne de la règle c plutôt que d'autre chose.** C'est une lecture des commentaires,
  pas une mesure isolée : aucun passage n'a joué le prompt v1 sans la règle c.
- **La cause du raisonnement plus long avec le prompt v1.** Supposée (prompt plus long et plus exigeant), non isolée.
- **Le lot 0 n'est pas jugé** (choix C6) : ses erreurs de fait ne sont pas connues.
- **Latence mesurée depuis WSL**, 3 conversations en parallèle : ce n'est pas une latence de production.

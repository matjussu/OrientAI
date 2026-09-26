# Contrat de l'étape 4 : la réponse

Version v1, 26/09/2026, Claudette. Ordre `2026-09-26-1535-claudette-orientai-etape4-reponse` (go de Matteo le 26/09
à 15h34, Telegram 10802). Écrit AVANT toute ligne de code du v2 et tout appel payant (section 14.1 du contrat du
cerveau). Statut : soumis à Jarvis (relecture et recompte), puis à Matteo (choix de la section 12 et prompt v1).

v1.1 (26/09, 16h55, après le palier 0 et AVANT le palier 1a) : amendement de la section 15 (latence publiée avec la
vitesse de l'API, timeout porté à 120 s, sonde avant les bancs), tranché par Jarvis ; D3 en attente de Matteo.

v1 (26/09, 16h10, avant tout code et tout appel payant) : **choix tranchés par Matteo (Telegram 10808, « Validé »,
relayé par Jarvis)**, section 12 bis ; prompt v1 validé tel quel (sha256 `145f0dd5a53c`, commit cf66bee).

v0.1 (26/09, après la relecture de Jarvis, avant tout code et tout appel payant) : recompte indépendant de Jarvis
identique sur le recouvrement, le critère 1, la loi de latence, la boucle et les parts d'accès. Trois corrections :
- dénominateur des parts « Accès des terminales » établi par Jarvis (section 3.4, choix D4) ;
- repères 6 (infirmier) et 7 (accès aux études de santé) du prompt v1 corrigés sur sources officielles. Le repère 7
  était faux pour les élèves qui entrent à la rentrée 2027 (section 4, option c) ;
- motif de la section 3.6 corrigé : il ratait « réécris ». Le lot 0 passe de 0 à 1 réécriture visible sur 6.

Nouveau sha256 du prompt v1 : `145f0dd5a53c...`. v0 : commit 34f6f42.

Contrat parent : `docs/cerveau/CONTRAT-cerveau.md` v1.2 (sha256 `07dee32b0949...`), sections 6, 8 et 13 (étape 4).
Contrat précédent : `docs/cerveau/etape3/CONTRAT-etape3.md` v2. Point de départ mesuré :
`results/multiversion/2026-09-25_v2/RAPPORT.md` (code joué `52a0b14`, juge `judge_v2`, un passage).

Toutes les mesures de ce contrat ont été faites le 26/09/2026, sans appel d'API, sur les traces et verdicts de
l'étape 3. Elles sont rejouables par deux scripts de lecture seule, qui ne touchent ni `src/v2` ni les traces :

- `python3 docs/cerveau/etape4/mesures/latence_etape3.py` produit `mesures/latence_etape3.json` (sections 8 et 3) ;
- `python3 docs/cerveau/etape4/mesures/critere1_etape3.py` produit `mesures/critere1_etape3.json` (section 9). Il
  retrouve le critère 1 publié (200/323 = 61,92 %), ce qui sert de témoin : son classement compte bien les mêmes
  attendus.

Les autres chiffres viennent de commandes courtes, relevées dans la section où elles servent.

## 0. En bref

- **Point de départ** (banc vertical, 79 tours) : erreur de fait 19,0 % pour un plancher < 10 % ; critère 1 61,9 %
  pour un plancher >= 85 % ; latence p90 43,5 s pour un plancher < 15 s. Sont tenus : les refus (2 sur 79) et les
  chiffres adossés (100 %). Gate F rouge par la clarification seule (2 sur 5).
- **Les 21 erreurs de fait, relues une à une** (section 2) :

  | famille | nombre |
  |---|---|
  | affirmations de connaissance propre | 9 |
  | notions que les outils portent, affirmées sans les lire (sélectivité, coût, région) | 4 |
  | chiffres justes mal nommés | 2 |
  | définition fausse dans la base | 1 |
  | absences affirmées sans tout avoir vu | 4 |
  | contradiction avec la fiche lue | 1 |

  Deux de ces absences viennent de défauts d'outils.
- **Sept constats nouveaux, mesurés le 26/09**, dont trois changent la façon de mesurer (section 3) :
  1. 20 des 32 tours du gate F sont mot pour mot des tours du banc vertical. Régler sur le gate F revient donc à
     régler sur un quart du banc de mesure. **Critère principal proposé : les 59 tours hors recouvrement.** La v2 y
     est à 22,0 % d'erreur de fait [13,4 ; 34,1], la prod à 33,9 %.
  2. **Le critère 1 plafonne à 83,3 %** (269 sur 323) avec la base alignée sur la page publique (#189). Le plancher
     de 85 % est inatteignable par construction. Proposition : le lire sur les 269 attendus que la base montre à
     l'identique. La v2 y est à 73,6 %.
  3. **Latence : 85 à 90 % du temps passe dans les appels au modèle.** Ce temps suit les jetons de sortie (4,4 s par
     millier), et 82 à 87 % des caractères produits sont du raisonnement. La taille de l'entrée n'a pas d'effet
     mesurable. Seul un raisonnement presque nul amène le p90 estimé sous 15 s : 12,4 s sur le vertical, mais
     encore 20,2 s sur le lot 0.
  4. **La base donne une définition fausse de « Accès des terminales »** : sur 2 935 des 2 939 fiches Parcoursup, les
     trois séries font 100 % à elles trois. Le modèle a suivi cette définition (V-INF-02).
  5. **Défaut de boucle** : quand le 6e outil passe pile, le modèle est rappelé sans outils, sans en être prévenu. Cela
     touche 16 tours sur 78 au vertical. Une fois (V-INF-09), sa phrase d'intention est partie comme réponse.
  6. **Réécriture visible** : 5 des 11 réécritures du vertical parlent de la correction à l'élève (1 sur 6 au lot 0,
     1 sur 2 au gate F).
  7. **Clarification** : les 3 questions en rouge posent 2 questions numérotées, écrites en 3 ou 4 phrases
     interrogatives.
- **Prompt v1** : texte complet joint (`prompt_conseiller_v1.txt`), avec son diff (`prompt_v0_v1.diff`). Ce qui change
  et pourquoi est en section 5.
- **Six choix pour Matteo** (section 12). Recommandation sur les connaissances générales : grands repères stables
  permis sans outil, sur une liste fermée ; tout le reste renvoyé à la source officielle.

## 1. Périmètre

**Dans l'étape 4** :
- le prompt v1 ;
- le vérificateur réglé (libellé, absence, message de réécriture) ;
- les correctifs généraux des outils et de la boucle (section 7) ;
- les leviers de vitesse retenus (section 8) ;
- la correction de la définition « Accès des terminales », selon le choix D4 ;
- les runs par paliers (section 11) ;
- l'export pour l'explorateur ;
- REPRISE et backlog.

**Hors de l'étape 4** :
- le corpus de procédures (étape 6) ;
- le profil sur plusieurs messages au-delà de ce que dit le prompt (étape 5) ;
- tout changement de modèle ;
- toute mise en prod ;
- Langfuse et DSPy.

**Ne bouge pas** :
- les bancs (sha `f467374be3d7`, `5b268bf34d91`) et le gate F (`5c78dc6e9001`) ;
- le juge `judge_v2` ;
- la référence figée `results/multiversion/2026-09-25_reference/` ;
- `src/rag/scope_classifier.py`, qui reste le premier étage (section 2.1 du parent) ;
- les chiffres de la base C. Seul le texte d'une définition peut changer, selon le choix D4.

## 2. Diagnostic des 21 erreurs de fait

Source : `results/multiversion/2026-09-25_v2/judge_v2/verdicts.jsonl`, version `v2`, `erreur_factuelle` vraie. Cela
donne 15 erreurs sur le vertical et 6 sur le gate F. Les traces (outils appelés, texte rendu, réponse) ont été relues
tour par tour.

Les faits reprochés sont ceux du juge (un passage, sans second juge). Trois ont été recoupés dans la base le 26/09 :
- **V-INF-02** : les trois parts somment à 100, section 3.4 ;
- **V-INF-03** : 5 BTS CIEL existent à Rennes et Bruz (psup:17725, psup:4632, psup_app:40984, psup_app:43796,
  psup_app:49281) ;
- **V-SAN-02 et F-HSAN-02** : le PASS psup:36433 de l'Université de Lille a un taux d'accès de 6 % en 2025, avec
  60 places.

Les autres faits (réformes, cursus) ne sont pas vérifiés par nous.

**Familles**. Elles corrigent celles du RAPPORT de l'étape 3, qui comptait 11 connaissances, 5 libellés, 4 absences
et 1 contradiction :
- **K**, connaissance propre du modèle : réforme, cursus, modalités, contenu d'une formation.
- **N**, notion portée par les outils mais affirmée sans l'avoir lue : sélectivité, coût, région. Le RAPPORT rangeait
  V-SAN-20 en libellé, alors que le modèle n'a jamais lu le coût ; ce tour passe donc en N.
- **L**, chiffre juste mal nommé.
- **D**, définition fausse dans la base. V-INF-02 est une erreur de la base, que le modèle a suivie à la lettre.
- **A**, absence affirmée sans tout avoir vu.
- **C**, contradiction avec la fiche lue.

| # | tour | extrait de la réponse | famille | cause précise | levier (section) |
|---|---|---|---|---|---|
| 1 | V-MAT-06 t0 | « Depuis la session 2025, le CRPE est accessible dès la licence » | K | date de réforme | règle des connaissances (4) |
| 2 | V-SAN-18 t0 | « l'internat via l'Épreuves Classantes Nationales (ECN) » ; « tronc commun de 2 ans » | K | réforme, cursus | règle des connaissances (4) |
| 3 | F-QSAN-18 t0 | « on peut redoubler une fois » ; internat « 3 ans » ; LAS « à la fin de la 2e année » | K | modalités, cursus (même question que le 2) | règle des connaissances (4) |
| 4 | V-SAN-12 t0 | « environ 5 ans d'études au total » | K | durée d'un cursus de santé | règle des connaissances (4) |
| 5 | V-SAN-13 t0 | « la sélection en IFSI se fait [...] sur l'oral de motivation » | K | modalité d'admission | règle des connaissances (4) |
| 6 | V-SAN-07 t0 | DTS « souvent en 3 ans après une classe de BTS », « accessible surtout aux bacs technologiques STL » | K, et C en second | structure d'un diplôme ; contredit son propre tableau (76 % de bacs généraux) | règle des connaissances (4) ; C non corrigé |
| 7 | V-INF-20 t0 | BUT Informatique : « un parcours dédié cybersécurité » | K | contenu d'une formation | règle des connaissances (4) |
| 8 | F-NMAT-01 t0 | « MP2I*/MPI » ; « stable sur 2023-2025 (11-12 %) » alors que la MPSI est à 10 % | K, et L en second | structure des CPGE ; une plage fausse faite de chiffres justes | règle des connaissances (4) ; plage non corrigée |
| 9 | V-SAN-10 t1 | « jusqu'à trois tentatives » ; LAS « plus sélective à l'entrée » | K et N | modalité ; sélectivité (la fiche dit « non sélective ») | règles des connaissances et des notions (4, 5) |
| 10 | F-QINF-18 t0 | licence informatique « très sélective à l'entrée » | N | sélectivité, portée par la fiche ; aucun outil de données appelé | règle des notions (5) |
| 11 | F-R07 t0 | « regarder hors Occitanie (Montpellier...) » | N | région d'une ville, portée par la base | règle des notions (5) |
| 12 | V-SAN-20 t0 | « rattachées à un hôpital public [...] les frais restent ceux de l'université » | N | coût non lu ; aucun outil appelé | règle des notions (5) |
| 13 | V-SAN-20 t1 | IFE du CHU : « frais d'inscription de type universitaire » ; IFMK « directement après le bac » | N et K | coût non lu (`detail=True` non demandé) | règle des notions (5) |
| 14 | V-SAN-16 t0 | « le passage en médecine (MMOPK) [...] 47,5 % au niveau national » | L | libellé raccourci (MMOPK devient « médecine ») | prompt (5) ; vérificateur : non |
| 15 | V-MAT-05 t1 | « 3 950 €/an » pour des « frais de scolarité du cycle » | L | période fausse | prompt (5) et vérificateur de libellé (6.1) |
| 16 | V-INF-02 t0 | « parmi les candidats de terminale techno, 31 % étaient en position de recevoir une proposition » | D | définition fausse dans la table `champ`, suivie mot pour mot | correction de la définition (D4) |
| 17 | V-SAN-02 t0 | « aucune option du PASS de Lille n'est à 6 % » | A | `trouver_formation` : 13 candidats à score égal, 10 montrés, sans leur option ; les 3 autres non lus, et la réponse le dit elle-même | outil (7), prompt (5), vérificateur d'absence (6.2) |
| 18 | F-HSAN-02 t0 | « Aucun chiffre publié pour le PASS de Lille en 2025 ne descend aussi bas » | A | même cause que le 17 (même question) | idem |
| 19 | V-INF-03 t0 | « je n'en ai trouvé aucun [BTS CIEL] en présentiel en Bretagne » | A | outil : filière « CIEL » refusée (valeurs proches proposées : FCIL, PCSI) ; `intitule_contient` « CIEL » ne trouve que des « distanCIEL » | outil (7), vérificateur d'absence (6.2) |
| 20 | V-INF-09 t0 | « Aucun BUT en apprentissage dans un rayon de 100 km autour de Roubaix, tous domaines confondus. » | A | périmètre de la base (7 BUT en apprentissage sur 131 BUT) ; plus défaut de boucle : phrase d'intention rendue comme réponse (163 caractères) | outil (7), boucle (7), prompt (5) |
| 21 | F-MINF-19 t1 | « La fiche indique qu'il existe en alternance » (la fiche dit « non ») | C | contradiction avec la fiche lue | prompt (5) ; non corrigé structurellement |

**Totaux par famille primaire** : K 9, N 4, L 2, D 1, A 4, C 1, soit 21.

**Ce que chaque levier ne corrige pas** :

- **K et N** (règle des connaissances et des notions) : c'est une consigne, sans contrôle déterministe. Le modèle peut
  ne pas la suivre ; au banc E, le prompt seul ne suffisait pas pour les chiffres, c'est le vérificateur qui a tenu la
  garantie. Et le juge compte un fait faux même présenté comme « en général » : sa grille dit « true si tu es SÛR qu'un
  fait cité est faux » (`src/eval/battery/judge.py`, ligne 54).
- **L** : le vérificateur de libellé (6.1) ne voit que la portée nationale et la période (an ou cycle). Il ne voit pas
  un nom de notion raccourci (14), ni une plage fausse faite de chiffres justes (8, second).
- **D** : la correction ne vaut que pour la famille corrigée. D'autres définitions peuvent être fausses : le contrôle
  des répartitions (7) en cherche d'autres, sans garantie de tout trouver.
- **A** : le vérificateur d'absence ne voit que les absences écrites avec son lexique. Il se déclenche sur une
  troncature ou un résultat vide dans la conversation, pas sur une absence qui paraît vraie à tort, c'est-à-dire un
  résultat complet mais faux par défaut d'outil.
- **C** : rien de déterministe. Rattacher une phrase à une formation pour comparer « alternance : oui ou non » demande
  une analyse de la phrase que le vérificateur ne fait pas.

## 3. Constats nouveaux (mesures du 26/09, sans appel d'API)

### 3.1 Recouvrement du gate F et du banc vertical

Méthode : textes normalisés (minuscules, sans accents ni ponctuation), `docs/cerveau/gate_f/requetes_gate_f.json`
contre le banc vertical. **20 des 32 tours du gate F sont identiques à un tour du vertical**, par exemple F-HSAN-02
et V-SAN-02, ou F-QSAN-18 et V-SAN-18. C'est attendu : la section 9 du parent dit que le gate F vient « du gate C et
du banc vertical ». Mais la décision G de l'étape 3 fait du gate F un jeu de réglage, et régler dessus revient à
régler sur 20 des 79 tours du banc de mesure. L'échantillon figé de 25 conversations contient 8 de ces tours sur 34.

| juge `judge_v2`, vertical | tours | erreur de fait | IC95 (Wilson) | refus | note |
|---|---|---|---|---|---|
| v2, tours communs au gate F | 20 | 2 (10,0 %) | [2,8 ; 30,1] | 0 | 4,44 |
| v2, hors recouvrement | 59 | 13 (22,0 %) | [13,4 ; 34,1] | 2 | 4,21 |
| prod, tours communs | 20 | 5 (25,0 %) | [11,2 ; 46,9] | 4 | 2,35 |
| prod, hors recouvrement | 59 | 20 (33,9 %) | [23,1 ; 46,6] | 22 | 2,23 |

Conséquence : le critère principal se lit sur les 59 tours hors recouvrement, et les 79 sont publiés à côté
(choix D6).

### 3.2 Plafond du critère 1

Mesure du 25/09 (`results/cerveau_etape3/essentiel_fiche.json`, `statuts`) : sur les 323 attendus du vertical que la
base porte, la base rend 269 avec la même valeur. Les 54 autres :
- 35 avec une autre valeur (page publique de #189 contre open data du banc) ;
- 8 masquées au modèle ;
- 11 absentes.

Une réponse parfaite cite donc au plus **269 sur 323 = 83,3 %**. Au-delà, il faudrait des égalités de hasard :
2 attendus en `ecart` sont cités justes par la v2, par une coïncidence de valeur. **Le plancher de 85 % du parent,
section 8, ne peut pas être tenu avec la base alignée sur la page publique.** Détail en section 9, choix D2.

### 3.3 Latence

Détail en section 8.

### 3.4 Définition fausse de « Accès des terminales (général, techno, pro) »

Définition stockée dans la table `champ` de la base, montrée au modèle avec chaque valeur : « Libellé officiel : part
des terminales de cette série qui étaient en position de recevoir une proposition en phase principale. Ne dit pas :
La répartition des admis. »

Mesure du 26/09, par `lire_fiche` sur les 2 939 fiches `psup:` :
- sur **2 935**, `part_acces_general@2025 + part_acces_techno@2025 + part_acces_pro@2025` tombe entre 97 et 103 ;
- sur les 4 autres, les trois valent 0 ;
- exemple : psup:7520 donne 69 + 31 + 0.

Ce n'est donc pas un taux par série (la part des candidats techno qui ont pu recevoir une proposition), mais une
**répartition par série**. Le juge l'a relevé (V-INF-02), et le modèle avait suivi la définition mot pour mot.

**Dénominateur, établi par Jarvis le 26/09 (v0.1)** :
- Le libellé officiel de l'open data (catalogue `fr-esr-parcoursup`) est « Part des terminales générales qui étaient
  en position de recevoir une proposition en phase principale ». Il est ambigu, et la base l'a lu comme un taux par
  série.
- La page publique ne montre pas ce chiffre dans son HTML statique : psup/7520 n'affiche que la « Répartition par
  type de bac des admis ».
- Test sur `parcoursup_2025.csv` (14 148 lignes), écart médian à `part_acces_gen` :
  - répartition des propositions par série, `prop_tot_bg / (bg + bt + bp)` : 1,65 point ;
  - répartition des admis : 5,1 points ;
  - taux par série, `prop_tot_bg / nb_voe_pp_bg` : 31,4 points, donc réfuté.
- Dénominateur retenu : les candidats de terminale en position de recevoir une proposition en phase principale
  (libellé officiel, plus la somme de 100). L'écart résiduel de 1,65 point viendrait de ce que `prop_tot` est le
  bilan final, et non la phase principale : c'est supposé.

**Définition à poser** (choix D4) : « Parmi les candidats de terminale qui étaient en position de recevoir une
proposition en phase principale, part de ceux de cette série. Les trois séries font 100 %. » Ne dit pas : « la
chance d'un élève de cette série d'avoir une proposition ; la répartition des admis ».

### 3.5 Défaut de boucle : le modèle n'est pas prévenu qu'il n'a plus d'outils

Dans `src/v2/pipeline.py`, fonction `_boucle`, le message de plafond n'est envoyé que pour un appel au-delà du 6e.
Quand le 6e outil est exécuté pile, l'appel suivant part sans outils, et rien n'en informe le modèle.

Mesure, par `latence_etape3.py`, champ `dont_modele_non_prevenu_du_plafond` : cela arrive sur 16 tours sur 78 au
vertical, 10 sur 66 au lot 0 et 6 sur 32 au gate F. Sur ces 32 tours, 3 réponses font moins de 300 caractères :
- V-INF-09 (163) : « Aucun BUT en apprentissage [...]. Je regarde les alternatives payées en informatique près de
  chez toi. » C'est l'erreur n° 20 ;
- E11 t1 (272) et L25 t2 (200), au lot 0.

### 3.6 Réécriture visible par l'élève

Le message de réécriture (`src/v2/verificateur.py`, `REECRITURE`) se termine par « Réécris ta réponse complète. ». Le
modèle en parle alors à l'élève. Un motif cherché dans les 300 premiers caractères des réponses réécrites
(« réécrit » et « réécris », « réponse complète », « sans ces chiffres », « corrig ») donne :
- au vertical, **5 réécritures sur 11**. Exemple : V-SAN-19 t1, « Bien vu, ce chiffre ne vient pas de ma base [...] je le
  retire. » ;
- au gate F, 1 sur 2 ;
- au lot 0, 1 sur 6 : L14 t1, « je réécris tout ». La v0 annonçait 0 sur 6, parce que son motif ratait
  « réécris » ; l'erreur a été relevée par Jarvis.

### 3.7 Clarification

Voir la section 10.

## 4. Connaissances générales : la règle (choix D1)

Ce qui est en jeu : 13 des 21 erreurs (familles K et N). Elles sont surtout **mêlées à des réponses chiffrées**, et
pas dans des réponses sans données. Au vertical, 12 des 15 erreurs sont dans des tours qui ont appelé au moins un
outil de données :

| tours du vertical | nombre | erreurs | refus | note |
|---|---|---|---|---|
| sans aucun outil de données (seulement le profil, ou rien) | 13 | 3 | 0 | 3,94 |
| avec un outil de données | 65 | 12 | 1 | 4,37 |

On appelle « outil de données » `chercher_formations`, `chercher_masters`, `lire_fiche`, `comparer` et
`trouver_formation`. Au gate F, ces chiffres sont de 7 tours, 2 erreurs, 0 refus et une note de 3,96 sans outil de
données, contre 25 tours, 4 erreurs, 0 refus et 4,46 avec. Le 79e tour du vertical est un court-circuit du filtre.

### Option a) Interdit : rien d'affirmé qui ne vienne d'un résultat d'outil

- **Effet attendu sur l'erreur de fait** : les 13 erreurs K et N sont évitées si le modèle obéit. C'est une
  supposition : aucune mesure ne dit qu'il obéira sans contrôle.
- **Effet attendu sur l'utilité** : la règle du parent (section 5.1, « Toujours répondre d'abord : une première
  orientation utile, même avec un profil vide ») devient impossible, puisqu'aucun outil ne décrit les grandes voies.
  Les 20 tours sans outil de données (13 au vertical, 7 au gate F) deviennent des questions sans réponse. Le risque
  porte directement sur les deux garde-fous (refus, note), et c'est l'opposé du repère ChatGPT (note 4,67).

### Option b) Autorisé, mais marqué comme général (« en général », « à vérifier »)

- **Effet attendu sur l'erreur de fait** : à peu près nul (supposé). La grille du juge compte un fait faux dès qu'il
  est « SÛR » qu'il est faux, qu'il soit marqué ou non. Aucune des 13 erreurs ne serait évitée par le seul marquage.
- **Effet attendu sur l'utilité** : conservée, avec des précautions en plus.

### Option c) Grands repères stables permis sans outil (liste fermée) ; notions des outils seulement depuis les outils ; le reste renvoyé à la source officielle

- **Permis sans outil** : une liste courte, écrite dans le prompt (section « Ce que tu dis sans chiffre » du
  prompt v1) :
  - BTS 2 ans, BUT 3 ans, licence 3 ans, master 2 ans ;
  - CPGE 2 ans puis concours ;
  - école d'ingénieurs avec prépa intégrée 5 ans ;
  - diplôme d'État d'infirmier 3 ans en IFSI, en lien avec l'université ;
  - accès à médecine, maïeutique, odontologie et pharmacie : en train de changer (PASS ou LAS jusqu'à la rentrée 2026 ;
    voie unique annoncée pour la rentrée 2027), modalités renvoyées vers Parcoursup et l'Onisep.

  Vérification par Jarvis le 26/09 (v0.1) :

  | repère | verdict | source, date |
  |---|---|---|
  | 1 à 5 : BTS, BUT, licence et master, CPGE, école d'ingénieurs | confirmés | pages du ministère (BTS 2 ans en STS de lycée ; BUT 180 ECTS en IUT ; CPGE 2 ans puis concours ; ingénieur 5 ans après le bac dont 2 de cycle préparatoire intégré ; LMD), lues le 26/09 ; Onisep inaccessible (403) |
  | 6 : infirmier | précisé | arrêté du 20/02/2026 relatif au DE d'infirmier, applicable aux entrants de septembre 2026 : 6 semestres, 180 ECTS (art. 24), IFSI en partenariat avec une université (art. 3) |
  | 7 : accès aux études de santé | **faux dans la v0**, réécrit | service-public, actualité A18890 du 29/04/2026 : « réforme majeure de la première année d'accès aux études de santé [...] applicable à la rentrée 2027 », voie unique via Parcoursup pour MMOPK ; annonce du 17/04/2026 ; aucun texte d'application trouvé sur Légifrance au 26/09 |

  **Leçon (v0.1) : les repères « stables » ne le sont pas.** Le repère 7, écrit comme une évidence, était faux pour
  les élèves qui entrent à la rentrée 2027, c'est-à-dire les terminales de 2026-2027. Chaque repère porte donc sa
  source et sa date de vérification (tableau ci-dessus), et la liste se revérifie avant la démo. Le repère 7 dit
  maintenant une réforme et sa date : c'est la seule exception à la règle « réformes et dates renvoyées ». Elle est
  sourcée, et une affirmation d'accès sans elle serait fausse.

  Aucun repère n'a été écrit à partir d'une des 21
  erreurs, ni pour répondre à une question d'un banc. Les faits que le juge a relevés (EDN, durée des études de
  sage-femme, admission en IFSI...) n'y sont pas : ils relèvent du corpus sourcé de l'étape 6.
- **Seulement depuis les outils** : sélectivité, statut public ou privé, alternance, coût, région d'une ville. La base
  les porte tous : champ `selectivite`, `statut`, valeur `alternance`, `cout.*` en `detail=True`, `region` des lieux.
- **Renvoyé à la source officielle, sans affirmation** : réformes et dates, durée précise des études de santé,
  modalités d'admission, de concours et d'épreuves, nombre de tentatives, parcours et contenu d'une formation.
- **Effet attendu sur l'erreur de fait** : chacune des 13 erreurs K et N tombe dans une catégorie « renvoyée » ou
  « seulement depuis les outils » (tableau de la section 2, colonne cause précise). Elles sont évitées si le modèle
  obéit, ce qui est supposé et se mesurera au banc.
- **Effet attendu sur l'utilité** : l'orientation d'abord reste possible, avec les repères et les notions lues. Le
  risque est une baisse de la couverture sur les questions de procédure santé (V-SAN-18 : « comment on devient
  médecin ? »), où la réponse renverra davantage vers l'Onisep. Ce risque est surveillé par les garde-fous de la
  section 11 (note des tours sans outil de données).

**Recommandation : c.** L'option a casse la règle de clarification du parent et les garde-fous. L'option b ne corrige
rien selon la grille du juge. L'option c laisse la réponse d'orientation utile et retire les catégories qui ont
produit les 13 erreurs. Le vrai correctif des faits de procédure reste le corpus sourcé de l'étape 6
(`chercher_connaissance`). La règle c est l'attente honnête avant lui.

## 5. Le prompt de conseiller v1

Textes joints :
- `docs/cerveau/etape4/prompt_conseiller_v1.txt` : le texte complet, à relire par Matteo ;
- `docs/cerveau/etape4/prompt_v0_v1.diff` : sa différence avec le v0 (`diff -u`).

Le v0 reste inchangé dans `docs/cerveau/etape3/`. Aucun exemple n'est tiré d'un banc mesuré. Les deux exemples
chiffrés du v1 étaient déjà dans le v0 (« j'en ai trouvé 23... »), sauf « sur les 10 fiches que j'ai lues, sur 13
trouvées », qui est une forme générale sans formation ni lieu.

Ce qui change, et pourquoi :

| ajout ou changement | raison mesurée | familles |
|---|---|---|
| « Nomme chaque chiffre » précisé : nom exact, portée, période, définition de l'outil | erreurs 14 et 15 | L |
| Nouvelle section « Ce que tu dis sans chiffre » : notions des outils seulement depuis les outils, repères stables, le reste renvoyé | option c de la section 4 ; erreurs 1 à 13 | K, N |
| Nouvelle section « Quand tu ne trouves pas » : pas d'absence sans tout avoir vu ; même nom, plusieurs options, les chercher toutes ; résultat vide, reformuler ; absence dans la base ≠ absence réelle | erreurs 17 à 20 | A |
| Nouvelle section « Tes recherches » : outils indépendants demandés ensemble ; plus d'outils, réponse finale et jamais une annonce | 1,64 outil par tour d'appels (section 8) ; défaut 3.5 | vitesse, A |
| Clarification : une question = une phrase, un seul « ? », une seule chose ; exemples entre parenthèses | section 10 | clarification |
| Forme : corriger sans parler de la correction | constat 3.6 | forme |

Rien n'est retiré du v0. Le prompt passe de 3 118 à 6 326 octets (v0.1). Coût en plus : environ 0,9 USD sur les 242 tours
prévus (section 11). C'est une estimation : environ 800 jetons de plus par appel, 3,4 appels par tour, et le cache
n'est pas compté.

Le v1 est une **proposition à relire par Matteo**, qui la valide ou la corrige (ordre, phase A). Le texte validé sera
figé par son sha256 avant le premier run.

## 6. Le vérificateur réglé (`src/v2/verificateur.py`)

La garantie « 100 % des chiffres affichés adossés » ne change pas. Trois ajouts, tous déterministes.

### 6.1 Libellé : portée et période d'un chiffre adossé

Pour chaque chiffre adossé, on regarde la valeur qui le porte (clé, `portee`, libellé de la table `champ`). Si
**tous** ses porteurs imposent un marqueur que la phrase contredit, le chiffre est « mal nommé ». Deux règles
seulement :
- **portée nationale** : un porteur de `portee` nationale demande « national » dans la phrase (ou la ligne de
  tableau, avec son en-tête) ;
- **période** : un porteur dont le libellé dit « du cycle » interdit « par an », « /an » et « annuel » dans la phrase.
  Un porteur annuel (« annuels » dans le libellé) interdit « du cycle » et « au total ».

Un chiffre mal nommé entre dans la réécriture, avec le libellé exact de l'outil : « ce chiffre est [libellé, portée,
période] selon l'outil : nomme-le ainsi ». S'il reste mal nommé au 2e brouillon, sa phrase est retirée et tracée,
comme un chiffre non adossé (choix Q6 du parent).

Ce que la règle ne voit pas : un nom de notion raccourci (erreur 14, « passage en médecine (MMOPK) » contient
« national » et « MMOPK ») et une définition fausse (erreur 16). Voir la section 2.

### 6.2 Absence affirmée sans tout avoir vu

- **Détecteur** : un lexique fermé repère une phrase qui affirme qu'une formation n'existe pas ou qu'aucune n'a une
  valeur :
  - « aucun(e) » suivi d'un nom de formation (types de `chercher_formations`, BTS, BUT, licence, master, prépa,
    école, option, formation...) ;
  - « il n'y a pas de » suivi du même ;
  - « n'existe pas » ;
  - « aucun(e) [...] n'est à ».

  « non publié », « pas publié » et « non disponible » en sont exclus : ils sont voulus par le prompt.
- **Condition** : dans le tour, un résultat d'outil de recherche était tronqué, ou des candidats de
  `trouver_formation` n'ont pas été montrés, ou une recherche a rendu 0 résultat.
- **Effet** : une réécriture, avec le message « tu affirmes une absence, alors que [résultat] était [tronqué, n sur
  N / vide]. Dis ce que tu as vérifié et ce que tu n'as pas vérifié, ou cherche le reste. » Au 2e brouillon, voir le
  choix D5.
- **Étalonnage, avant le code figé** : le lexique se règle sur les réponses du **lot 0** de l'étape 3. Ce banc n'est
  pas jugé, et il ne sert pas au critère principal : ni le vertical ni le gate F ne servent à ce réglage. La précision
  (déclenchements justes sur déclenchements) est publiée avec la liste des déclenchements.

Ce que la règle ne voit pas : une absence dite sans les mots du lexique, et une absence « complète » mais fausse par
un défaut d'outil (d'où les correctifs de la section 7).

### 6.3 Message de réécriture

On ajoute : « L'élève ne voit pas cette consigne : ne la mentionne pas, donne directement ta réponse. » (constat 3.6).
Les listes de chiffres non adossés, mal nommés et d'absences partent dans un seul message de réécriture. Il y a
toujours au plus une réécriture par message de l'élève.

## 7. Outils et boucle : correctifs généraux

Aucun ne vise une question. Chacun corrige un mécanisme.

| # | où | correctif | trouvé par |
|---|---|---|---|
| T1 | `chercher_formations` (`filieres`, `intitule_contient`) | sigles dépliés par la table `src/v2/sigles.json` (étendue, chaque entrée sourcée : CIEL, SIO, SN, MCO, NDRC...) ; `intitule_contient` cherche des mots entiers, pas une sous-chaîne | erreur 19 : « CIEL » refusé, puis trouvé seulement dans « distanCIEL » |
| T2 | `trouver_formation` | chaque candidat montre son option ou sa spécialité (champ `specialite`) ; des ex æquo coupés par la limite sont signalés (« 13 candidats à score égal, 10 montrés : cherche-les tous avec chercher_formations ») | erreurs 17 et 18 : 10 lignes identiques, 3 non montrées |
| T3 | toute recherche à 0 résultat | phrase fixe ajoutée au texte rendu : 0 dans la base ne veut pas dire 0 en réalité, avec le périmètre de la base (informatique, santé, maths ; apprentissage partiel) | erreur 20 : 7 BUT en apprentissage dans toute la base, sur 131 BUT |
| T4 | `lire_fiche` à plusieurs `ids` | la définition et le « Ne dit pas » de chaque notion ne sont écrits qu'une fois par appel | 47,1 % des caractères rendus par `lire_fiche` sont des définitions (section 8) : levier de coût, pas de latence |
| B1 | `pipeline._boucle` | quand le compteur atteint 6, l'appel sans outils reçoit une consigne : « tu ne peux plus appeler d'outil : rédige ta réponse finale avec ce que tu as ». Tracé `plafond_atteint: "exact"` | constat 3.5 |
| B2 | `verificateur.REECRITURE` | section 6.3 | constat 3.6 |
| D4 | définition de `part_acces_*` | selon le choix D4 ; puis un contrôle général : toute famille de notions en `part_*` ou `repartition_*` dont les valeurs somment à 100 sur une fiche doit avoir une définition de répartition. Contrôle déterministe sur toute la base, résultat publié | constat 3.4 |

Le filtre lancé en parallèle du premier appel au modèle n'est **pas** retenu. Il contredit la section 2.1 du parent
(« Il reste le premier étage, avant tout appel au modèle principal »), pour un gain estimé de 0,7 s au p90
(section 8).

## 8. Vitesse : décomposition mesurée et leviers chiffrés

### 8.1 Décomposition, par `latence_etape3.py`

Les mesures portent sur les traces de l'étape 3, tours non court-circuités. La latence est celle du pipeline
(`latence_s.total`). Le p90 est calculé par interpolation linéaire : la formule de rang du RAPPORT de l'étape 3 donne
43,5 s au vertical. Les leviers sont tous comparés avec la même formule.

| | vertical (78) | lot 0 (66) | gate F (32) |
|---|---|---|---|
| latence médiane / p90 | 19,9 / 39,7 s | 22,5 / 48,0 s | 14,0 / 31,6 s |
| part du temps : appels au modèle | 89,7 % | 89,5 % | 85,1 % |
| part : outils (base SQLite) | 0,2 % | 0,1 % | 0,1 % |
| part : filtre (médiane 0,7 s) | 3,2 % | 3,3 % | 4,1 % |
| appels au modèle par tour (médiane / p90) | 3 / 5 | 2 / 5 | 3 / 5,9 |
| secondes par appel (médiane / p90) | 4,7 / 14,8 | 6,8 / 18,3 | 3,3 / 11,3 |
| appels qui demandent des outils : n, médiane | 168, 3,2 s | 111, 5,6 s | 67, 2,3 s |
| appels qui rédigent (fin `stop`) : n, médiane | 99, 8,2 s | 79, 8,3 s | 37, 5,7 s |
| jetons en entrée / en sortie par appel (médiane) | 6 315 / 848 | 5 419 / 1 240 | 5 873 / 621 |
| part du raisonnement dans les caractères produits | 84,7 % | 87,1 % | 81,9 % |
| outils par tour d'appels | 1,64 | 1,47 | 1,57 |
| tours avec réécriture / relance sur réponse vide | 11 / 10 | 6 / 7 | 2 / 3 |

**Loi mesurée par appel** (moindres carrés sur 267 appels au vertical) : secondes = 1,18 + 4,44 par millier de
jetons de sortie, l'entrée pesant -0,02 s par millier de jetons, c'est-à-dire rien. Même forme au lot 0 (2,53 +
4,53 ; entrée -0,19) et au gate F (0,63 + 4,22 ; entrée 0,03). **Le temps suit ce que le modèle écrit, et d'abord ce
qu'il raisonne.** La taille des retours d'outils n'entre pas dans la latence mesurée.

**Coût** : au vertical, l'entrée coûte 2,86 USD contre 1,50 pour la sortie, au prix de la page (section 11). Réduire
l'entrée est donc un levier de coût.

### 8.2 Leviers, gain estimé

Méthode : chaque tour est rejoué avec la loi ci-dessus, en retirant une part du raisonnement, les appels de
réécriture, ou l'attente du filtre. La part du raisonnement d'un appel est estimée par ses caractères. **Ce sont des
estimations, pas des mesures.** Le rejeu sans levier donne un p90 de 42,6 s, contre 39,7 s mesurés au vertical : la
loi reproduit la mesure à 7 % près.

| levier | p90 vertical | p90 lot 0 | p90 gate F | source et réserve |
|---|---|---|---|---|
| aucun (rejeu de la loi) | 42,6 | 56,5 | 31,0 | référence des lignes suivantes |
| raisonnement divisé par 2 | 26,3 | 36,9 | 19,6 | pas de réglage connu qui divise par 2 |
| **raisonnement presque nul** (`reasoning_effort="none"`) | **12,4** | **20,2** | **9,2** | le SDK installé l'accepte (`mistralai` : `ReasoningEffort = "none" \| "high"`) ; la doc Mistral ne le cite que pour Small et Medium 3.5, **pas pour GLM 5.3** (context7, `/mistralai/platform-docs-public`, page reasoning, lue le 26/09). Effet réel à mesurer au palier 0 ; effet sur la qualité inconnu |
| aucune réécriture | 34,9 | 55,3 | 31,0 | borne haute : le vérificateur réglé peut aussi en ajouter (6.1, 6.2) |
| filtre en parallèle du 1er appel | 41,9 | 55,7 | 30,2 | non retenu (section 7) |
| outils indépendants demandés ensemble (prompt) | non estimé | | | chaque tour d'appels évité vaut environ 3,2 s en médiane au vertical ; combien seront évités est inconnu |
| définitions une fois par notion (T4) | environ 0 | | | l'entrée ne pèse rien dans la loi ; gain en coût seulement |

**Lecture** : le plancher p90 < 15 s n'est à portée que par le raisonnement, et seulement au vertical, même sans
raisonnement (lot 0 : 20,2 s estimés). Couper le raisonnement peut aussi augmenter l'erreur de fait, ce qui irait
contre l'objectif premier (« sans erreur de fait », Matteo 10734). D'où le choix D3 : le levier se teste, et on le
juge sur le gate F avant de le retenir.

## 9. Critère 1 : pourquoi 61,9 %, et ce qu'on peut viser (choix D2)

Classement de chaque attendu du vertical, par `critere1_etape3.py` :

| classe | nombre | levier |
|---|---|---|
| cité juste | 200 | |
| la base montre une autre valeur (`ecart`) | 33 | aucun (décision #189) |
| absent de la base | 11 | aucun |
| masqué au modèle (#189) | 8 | aucun |
| fiche jamais sortie d'un outil | 27 | recherche : T1, T2, prompt « chercher toutes les options » |
| fiche sortie d'une recherche, jamais lue ni comparée | 33 | dont 15 dont la valeur était déjà dans la carte de recherche : le modèle a choisi de ne pas citer la formation |
| fiche lue, valeur non rendue (hors de l'essentiel) | 3 | aucun à cette étape |
| valeur rendue, non écrite | 8 | rédaction |

Par notion, les 60 attendus manqués côté recherche sont 27 `places`, 25 `taux_acces`, 5 `capacite_accueil`,
2 `candidats_ont_postule` et 1 `part_mention_sans_mention`.

Sur les 269 attendus que la base montre à l'identique, la v2 en cite 198, soit **73,6 %**.

- **a)** Garder le plancher de 85 % sur les 323. Il est inatteignable (plafond de 83,3 %) : le critère 1 devient un
  plancher que rien ne peut tenir.
- **b)** Lire le plancher de 85 % sur les 269 attendus montrés à l'identique (« critère 1 bis »), et publier aussi le
  taux sur 323. Il reste 31 points à gagner. Ils dépendent surtout de la recherche (60 manqués), qui est aussi le
  levier de l'erreur de fait des familles A.
- **c)** Abaisser le plancher sur les 323 à un seuil sous 83,3 %.

**Recommandation : b.** Elle garde un critère atteignable qui mesure ce que la v2 contrôle, sans cacher le taux sur
323.

Point d'honnêteté : le critère 1 récompense le nombre de formations citées. Une réponse qui cite les 8 formations
attendues sur 8 fait mieux qu'une réponse qui en choisit 3 pour l'élève. Le prompt v1 ne pousse pas à tout citer.
Ce critère ne doit pas devenir une raison d'allonger les réponses (médiane de 346 mots, déjà au niveau de ChatGPT à
351).

## 10. Clarification : la cause des 3 rouges au gate F

Relevé dans `results/multiversion/2026-09-25_v2/gate_f.json` et les réponses :

| question | questions numérotées | « ? » comptés par le gate (`_questions`, hors parenthèses) | ce qui fait le 3e ou le 4e « ? » |
|---|---|---|---|
| F-QINF-17 | 2 | 3 | « Tu es en voie générale, c'est ça ? Et tu prends quoi comme deuxième spécialité [...] ? » |
| F-QINF-18 | 2 | 3 | « **Quel bac prépare-t-il ?** Général (avec quelles spécialités ?), STI2D, STMG, bac pro... ? » |
| F-QMAT-12 | 2 | 4 | « Qu'est-ce qui l'attire ? Les maths pour elles-mêmes [...] ? » et « Où est-elle scolairement ? Quelle voie de bac [...] ? » |

**Cause** : le modèle respecte « au plus 2 questions » en questions numérotées. Mais il écrit une question suivie
d'une liste d'exemples qui finit par un « ? », ou une question en deux phrases. Le compteur du gate, écrit avant le
code de l'étape 3, compte chaque phrase interrogative. F-QMAT-12 pose en outre deux choses dans sa question 2 (la
voie de bac et la région).

**Correctif** : dans le prompt (section 5), chaque question tient en une phrase avec un seul « ? », ne demande qu'une
chose, et ses exemples vont entre parenthèses. **Le compteur n'est pas changé** : l'assouplir après avoir vu les
résultats reviendrait à déplacer le but. La règle de l'orientation d'abord (150 caractères avant la 1re question) est
déjà tenue par les 5.

## 11. Règle de décision, écrite avant le run (section 14.2 du parent)

**Instruments inchangés** : mêmes bancs, même lanceur, même juge `judge_v2` (Opus 5.5 effort low, stdin, fiches de
la page publique, consigne de nommage), même référence figée. Code, prompt et base figés par leurs empreintes avant
les bancs. Si la définition D4 change dans la base, l'empreinte de la base change : c'est déclaré, et la
concordance (`src/eval/concordance.py`) est rejouée et doit rester à 100 %.

**Réglage** (décision G de l'étape 3) :
- Il se fait sur le gate F, avec ses mesures déterministes seulement : fiches attendues, formations citées hors des
  résultats, clarification, chiffres adossés, plus les nouvelles traces de libellé et d'absence.
- **Au plus 3 passages du gate F complet** (paliers 1a, 1b, 1c).
- Entre deux passages, seulement des correctifs généraux, écrits et datés dans un amendement de ce contrat avant de
  lire le passage suivant.
- Aucun réglage n'utilise le vertical, ni le lot 0 en dehors de l'étalonnage du lexique d'absence (6.2), qui se
  fait avant le code figé.

**Mesure** : les bancs (vertical, 79 tours ; lot 0, 67 tours), joués **une fois** sur le code figé après le dernier
passage du gate F. Aucun réglage après les bancs : si un plancher n'est pas tenu, il est rapporté tel quel, et la
suite se décide avec Matteo.

**Critère principal** : l'erreur de fait (juge) sur les **59 tours du vertical hors recouvrement avec le gate F**,
**< 10 %**, c'est-à-dire au plus 5 erreurs, lues sur l'estimation ponctuelle. L'IC95 est publié. Avec 59 tours, sa
borne haute reste au-dessus de 10 % même à 5 erreurs : c'est une limite de taille du banc, dite telle quelle. Les
79 tours sont publiés à côté (plancher < 10 %, soit au plus 7).

**Garde-fous**. Tous sont requis pour déclarer l'étape 4 meilleure que l'étape 3 ; sinon on rapporte, et Matteo
tranche :
1. refus (juge, vertical) <= 5 sur 79 (étape 3 : 2 ; plancher du parent < 10 %) ;
2. note moyenne (juge, 4 critères, vertical) >= 4,17 (étape 3 : 4,27, moins 0,10) ;
3. note des tours sans outil de données >= 3,84 (étape 3 : 3,94 sur 13 tours, moins 0,10). C'est ce garde-fou qui
   dit si couper les connaissances générales a appauvri la réponse d'orientation ;
4. chiffres affichés adossés : 100 % (vérificateur, recompté a posteriori par l'extraction du critère 1) ;
5. critère 1 bis (D2 b) : rapporté contre le plancher de 85 %, et contre l'étape 3 (73,6 %).

Le recul de 0,10 sur la note est un choix de tolérance, pas une mesure du bruit du juge : ce bruit n'est pas mesuré,
faute de second passage.

**Planchers rapportés** (parent, section 8) :
- critère 1 bis >= 85 % ;
- latence p90 < 15 s, au vertical et au lot 0 ;
- gate F : fiches >= 90 %, 0 formation citée hors des résultats, clarification 5 sur 5, adossés 100 %.

**Côte à côte avec ChatGPT + recherche** : sur l'échantillon figé de 25 conversations (34 tours, dont 8 communs au
gate F, signalés).

**Levier du raisonnement (choix D3)** :
- Palier 0 : un appel avec `reasoning_effort="none"`, pour savoir si l'API l'accepte pour `zai-glm-5-3`. On compare
  le raisonnement rendu (caractères) à celui d'un même appel sans le paramètre.
- Il est **retenu pour la suite** seulement si les trois conditions suivantes sont réunies :
  1. l'API l'accepte, et le raisonnement tombe sous 20 % de celui de l'appel de référence ;
  2. sur un passage du gate F, les critères déterministes ne reculent pas face au passage sans le paramètre : au plus
     2 fiches de moins, clarification pas moins bonne, adossés 100 %, 0 formation citée hors des résultats ;
  3. si D3 = b, l'erreur de fait jugée sur le gate F ne monte pas de plus d'une réponse sur 32.
- Les deux passages (avec et sans) comptent dans les 3 passages du gate F.

**Budget Mistral**. Prix lus le 26/09/2026 à 15h41 UTC sur la page publiée, par curl :
- `https://docs.mistral.ai/models/zai-glm-5-3` : GLM 5.3 à 1,4 USD par million de jetons en entrée (0,14 en cache),
  4,4 en sortie ;
- `https://docs.mistral.ai/models/mistral-small-4-0-26-03` : Small 4 à 0,15 et 0,6.

Ces prix n'ont pas changé depuis le relevé du 25/09. Le cache n'est pas compté : le coût est surestimé, jamais
sous-estimé. Coût mesuré par tour à l'étape 3 (`budget.json`) : gate F 0,048 USD, vertical 0,056, lot 0 0,046.

| palier | quoi | estimation | plafond cumulé | condition pour passer au suivant |
|---|---|---|---|---|
| 0 | fumée : 3 conversations du gate F (une recherche, un nom, une clarification) + l'essai `reasoning_effort` | 0,30 USD | 0,50 USD | traces complètes, 0 panne, garanties vertes, tests de sabotage verts |
| 1a à 1c | gate F complet, 3 passages au plus | 1,6 USD par passage (+ 0,1 pour le prompt plus long) | 5,50 USD | amendement daté entre deux passages |
| 2 | vertical + lot 0, une fois | 8,0 USD (étape 3 : 4,39 + 3,11, + 0,5 pour le prompt plus long), moins si le raisonnement baisse | **15 USD** | arrêt automatique au plafond |

Arrêts automatiques : le plafond ; plus de 20 % de pannes sur les 10 premières conversations d'un palier ; une
garantie rouge (adossés < 100 %) à n'importe quel palier. Rien d'OpenAI : ChatGPT n'est pas rejoué, la référence
figée sert.

**Ce qui demande le go de Matteo au moment de le lancer** :
- le juge (quota de l'abonnement) : 79 verdicts au vertical et 32 au gate F final, soit 111, comme à l'étape 3 ;
- plus 64 verdicts au gate F si D3 = b (les deux variantes de raisonnement) ;
- aucun juge sur le lot 0 (choix C6 de l'étape 3, maintenu).

## 12. Choix soumis à Matteo

| # | question | options | reco |
|---|---|---|---|
| D1 | Connaissances générales (section 4) | a) tout interdit hors outils ; b) autorisé mais marqué « général » ; c) repères stables sur une liste fermée, notions des outils seulement depuis les outils, le reste renvoyé à la source officielle | **c** |
| D2 | Plancher du critère 1 (section 9) | a) 85 % sur les 323 (plafond 83,3 %) ; b) 85 % sur les 269 attendus montrés à l'identique, et taux sur 323 publié ; c) abaisser le seuil | **b** |
| D3 | Raisonnement de GLM (section 8) | a) tester `reasoning_effort="none"`, retenu sur les critères déterministes du gate F ; b) le même, plus le juge sur les deux passages du gate F (64 verdicts, sur l'abonnement) ; c) ne pas tester, et déclarer le plancher de latence non tenu à l'étape 4 | **b** : c'est le seul levier qui atteint le plancher, et il peut coûter en erreur de fait, l'objectif premier. Le juger sur le jeu de réglage évite de le découvrir une fois le banc mesuré |
| D4 | Définition « Accès des terminales » (3.4) | a) corrigée dans la base (texte seulement, empreinte déclarée, concordance rejouée), plus le contrôle général des répartitions ; b) corrigée seulement dans ce que la v2 montre au modèle | **a** : l'explorateur et le juge lisent aussi cette définition. Dénominateur établi par Jarvis (section 3.4, v0.1), définition à poser écrite en 3.4 |
| D5 | Absence encore affirmée au 2e brouillon (6.2) | a) la phrase est retirée et tracée, comme un chiffre non adossé ; b) seulement tracée | **a si la précision du détecteur, mesurée sur le lot 0 avant le code figé, est >= 95 %, sinon b**. Retirer une phrase juste abîmerait la réponse |
| D6 | Où se lit le critère principal (3.1) | a) les 59 tours hors recouvrement, les 79 publiés à côté ; b) les 79, comme à l'étape 3 | **a** : le gate F sert au réglage et partage 20 tours avec le vertical |

À faire valider aussi par Matteo : **le texte du prompt v1** (section 5). À faire vérifier par Jarvis avant le premier
run : **les repères stables** du prompt (option c) et le dénominateur de D4, sur des sources officielles. C'est fait
en v0.1 : repères 1 à 5 confirmés, 6 et 7 corrigés, dénominateur établi.

## 12 bis. Décisions de Matteo, 26/09 à 16h10 (Telegram 10808, relayé par Jarvis)

Citation : « Validé ». La recommandation est suivie partout.

| # | décision | effet dans ce contrat |
|---|---|---|
| D1 | **c** : repères stables sur liste fermée, notions des outils seulement depuis les outils, le reste renvoyé | section 4 ; prompt v1 |
| D2 | **b** : plancher de 85 % sur les 269 attendus montrés à l'identique, taux sur 323 publié | sections 9 et 11 |
| D3 | **b** : `reasoning_effort="none"` testé, retenu sur les critères déterministes du gate F et sur le juge des deux passages (64 verdicts, sur go de Matteo au moment de le lancer) | sections 8 et 11 |
| D4 | **a** : définition corrigée dans la base (texte seulement, empreinte déclarée, concordance rejouée), plus le contrôle général des répartitions | sections 3.4 et 7 |
| D5 | **a**, sous condition : la phrase est retirée si la précision du détecteur mesurée sur le lot 0 est d'au moins 95 %, sinon elle est seulement tracée (b) | section 6.2 |
| D6 | **a** : critère principal sur les 59 tours hors recouvrement, les 79 publiés à côté | section 11 |
| prompt | **v1 validé tel quel** : sha256 `145f0dd5a53c7b91b3393d0c111a795345125aba1a1641dc2559f14943e02352` | section 5 |

Rappel de Jarvis avec le go : un point d'arrêt à chaque palier (palier 0, chaque passage du gate F, bancs), et un
arrêt avant chaque juge.

## 13. Ce que ce contrat n'établit pas

- **Que le modèle suivra les nouvelles règles du prompt.** Au banc E et à l'étape 3, la garantie sur les chiffres
  venait du vérificateur, pas du prompt. Les familles K, N et C n'ont pas de contrôle déterministe.
- **Les gains de latence** de la section 8 : ils sont estimés par une loi ajustée, et la part du raisonnement
  l'est par les caractères, pas par les jetons. On ne sait pas si GLM 5.3 accepte `reasoning_effort`.
- **Le bruit du juge** : un seul passage, pas de second juge. Un écart de 1 ou 2 erreurs sur 59 tours n'est pas
  distinguable du bruit.
- **Que les faits reprochés par le juge soient tous vrais** : 4 sont recoupés dans la base (section 2), les faits de
  réforme et de cursus ne le sont pas.
- **Que la table `CORRESPONDANCE` et le classement du critère 1 valent pour d'autres bancs** : ils sont écrits pour
  les 20 champs du banc vertical.
- **La précision du détecteur d'absence** : elle sera mesurée sur le lot 0 avant le code figé.

## 14. Phase B, après le go (pour mémoire, rien n'est codé)

- **`src/v2/prompt.py`** lit `docs/cerveau/etape4/prompt_conseiller_v1.txt`, avec le sha256 figé. Le v0 reste
  jouable pour comparaison.
- **`src/v2/verificateur.py`** : libellé (6.1), absence (6.2), message de réécriture (6.3).
- **`src/v2/outils.py`, `src/v2/sigles.json`, `src/v2/pipeline.py`** : T1 à T4, B1, et `reasoning_effort` en
  paramètre selon D3.
- **Tests**, avec un sabotage par garantie (règle 9, levier `ORIENTIA_SABOTAGE_V2`) :
  - un chiffre national dit sans « national », ou une valeur « du cycle » dite « par an », doit rougir quand le
    vérificateur de libellé est saboté ;
  - une absence affirmée après un résultat tronqué doit rougir quand le vérificateur d'absence est saboté ;
  - des définitions supprimées au lieu d'être dédoublonnées (T4) doivent rougir ;
  - un 6e outil passé pile sans consigne de fin (B1) doit rougir ;
  - `intitule_contient` qui reprend une sous-chaîne (« ciel » dans « distanciel ») doit rougir.
- **Runs par paliers** (section 11), avec les traces exportées pour l'explorateur. Le juge ne tourne que sur le go
  de Matteo.
- **Livraison** : REPRISE et backlog mis à jour dans le même lot, chaque item avec sa mesure. PR ouverte, sans merge
  sans le go de Matteo relayé par Jarvis.

## 15. Amendement v1.1 (26/09, 16h55, après le palier 0, avant le palier 1a)

Écrit après la lecture du palier 0 et avant tout autre run. Traces : `results/multiversion/2026-09-26_v2e4/palier0/`
(code joué 2cd998a, base 54f8aab3110f, prompt v1 `145f0dd5a53c`). Dépense du palier 0 : 0,188 USD sur 0,50.

### 15.1 Ce que le palier 0 a montré

| | mesure |
|---|---|
| v2e4, F-R01, F-NINF-01, F-QINF-17 | fiches attendues 8 sur 8 ; 0 formation citée hors des résultats (contrôle positif : compte 1) ; chiffres adossés 27 sur 27 ; clarification de F-QINF-17 bonne (2 questions, un « ? » chacune) ; 0 réécriture |
| panne au 1er passage | F-NINF-01 : `ReadTimeout` après 3 essais de 60 s (236 s) ; rejoué seul : bon, 100 s. 1er passage gardé (`palier0/v2e4__gatef_passage1.jsonl`) |
| vitesse de l'API | médiane de 15,0 s par millier de jetons de sortie par appel (8 appels), contre 5,64 à l'étape 3 (même statistique, 267 appels du vertical ; `src.eval.multiversion.mesures.vitesse_sortie`). Les sorties font la même taille (362 à 3 000 jetons environ). Ralentissement côté fournisseur, supposé |
| v2e4r (`reasoning_effort="none"`) | 3 pannes, toutes par erreur 400 : « reasoning_effort 'none' is not supported for this model; supported values: ['low', 'high', 'max'] » (26/09, 16h45). La condition 1 du levier (section 11) échoue telle qu'écrite |

### 15.2 Amendements (tranchés par Jarvis, 26/09 16h44 : techniques et généraux)

- **a) Latence publiée avec la vitesse de l'API.** Chaque run publie, à côté de la latence brute (médiane, p90 au rang
  le plus proche), la médiane par appel des secondes par millier de jetons de sortie
  (`vitesse_sortie`, champ `secondes_par_k_sortie_mediane`, dans le journal du lanceur et dans le rapport). Le
  plancher p90 < 15 s se lit sur les deux. Référence de l'étape 3 pour cette statistique : 5,64.
- **b) Timeout par appel : 60 s -> 120 s**, pour les runs et le pipeline (`src/v2/pipeline.TIMEOUT_MS`, repris par
  la version du lanceur). Raison mesurée : F-NINF-01, 26/09 vers 16h40, 3 appels au-delà de 60 s alors que l'API
  rendait 11 à 21 s par millier de jetons de sortie ; une panne n'est pas une mesure de qualité.
- **c) Sonde avant les bancs** (palier 2) : 3 appels, avant de lancer le vertical et le lot 0. Si la médiane de
  `secondes_par_k_sortie_mediane` dépasse **2 fois la référence de l'étape 3**, les bancs sont reportés, au lieu de
  mesurer une latence faussée. Les passages du gate F peuvent tourner malgré le ralentissement : leurs critères sont
  déterministes.

  Seuil : Jarvis a écrit 8,9 s par millier, soit 2 fois 4,43, la pente de la loi par moindres carrés (section 8).
  La statistique publiée en a) est une médiane par appel, dont la référence à l'étape 3 est 5,64 (elle compte aussi
  la part fixe de chaque appel). Deux fois la même statistique donne **11,3**. Seuil retenu : 11,3 sur la médiane par
  appel, en attendant la confirmation de Jarvis.
- **d) Points d'arrêt** : un ping à Jarvis AVANT chaque palier payant (avec le sha du code), et après, avec les
  mesures. Arrêt avant chaque juge.
- **e) Mesures du v2 étendues aux variantes** : l'export et le recompte des chiffres adossés reconnaissaient la
  version `v2` seulement ; ils reconnaissent maintenant `v2e4` et `v2e4r` (`mesures.est_v2`). Aucun changement pour
  les versions `prod` et `chatgpt*`.

### 15.3 En attente

- **D3** : « none » refusé par l'API. Jarvis pose la question à Matteo (recommandation : tester « low » avec la même
  règle, sauf la condition « raisonnement < 20 % du défaut », remplacée par « rapport publié »). Rien n'est lancé
  avec `v2e4r` sans sa décision. Le palier 1a (v2e4, raisonnement par défaut) ne dépend pas de cette décision.


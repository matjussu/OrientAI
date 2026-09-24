# Banc E : confirmation du modèle de la démo, protocole v0.3.1 (24/09/2026, GO de Jarvis à 10h42 ; amendement 11 à 11h25)

Ordre 2026-09-24-1020 (Jarvis, décisions de Matteo Telegram 10666, 10674, 10676, 10678). Écrit **avant** tout
appel de grille ; seul le diagnostic de l'outil (`diag_outil/RESUME.md`, 0,47 USD) a été joué. Hérite de
`results/donnee_etape_d/PROTOCOLE.md` v0.2 pour tout ce qui n'est pas écrit ici ; chaque écart à D est listé en
section 9.

## 1. Question

Quel modèle pour la démo, servi par l'API Mistral : Medium (appel d'outil réparé), GLM 5.2, GLM 5.3 ou Small 4 ?
Avec un juge qui voit le contenu des fiches, ce qui manquait à D pour trancher sur les erreurs factuelles.

## 2. Modèles (identifiants explicites, jamais -latest ni les alias zai-glm-5 / zai-glm-latest)

| modèle | identifiant | rôle | prix publié, USD / M tokens (entrée / sortie) |
|---|---|---|---|
| Mistral Medium 3.5 | `mistral-medium-2604` | référence, prod | 1,5 / 7,5 |
| Z.ai GLM 5.2 | `zai-glm-5-2` | meilleur candidat de D | 1,4 / 4,4 (0,14 en cache) |
| Z.ai GLM 5.3 | `zai-glm-5-3` | successeur de GLM 5.2 | 1,4 / 4,4 (0,14 en cache) |
| Mistral Small 4 | `mistral-small-2603` | témoin souverain (aussi servi par Cloud Temple, SecNumCloud), modèle auxiliaire en prod | 0,15 / 0,6 |

Prix lus le 24/09/2026 sur docs.mistral.ai/models : `mistral-medium-3-5-26-04`, `zai-glm-5-2`, `zai-glm-5-3`,
`mistral-small-4-0-26-03` (texte brut de la page, relevé par curl ; relus par Jarvis le 24/09). Medium 3.5 =
`mistral-medium-2604` : mesuré, GET /v1/models (Jarvis, 24/09 10h) rend pour `mistral-medium-2604` les alias
« mistral-medium-3-5 » et « mistral-medium-3.5 ». Présence des 4 identifiants : GET /v1/models sur
api.eu.mistral.ai (Jarvis, 24/09 10h20), et modèle rendu = modèle demandé sur les 53 appels du diagnostic.
Endpoint unique : `server_url="https://api.eu.mistral.ai"` (celui visé en prod). Le modèle rendu est vérifié à chaque
réponse ; un écart arrête le run.

## 3. Formats retenus : A et C

- **A (référence)** : `fiche_to_text` du corpus B-2 (sha `2e6a93a5cda6`), sans outil, comme la prod et comme D.
- **C (carte courte + `lire_fiche`)** : carte courte de D, l'outil rend la carte B complète. Seul changement : la
  **consigne d'outil explicite** du diagnostic remplace `PHRASE_OUTIL`, identique pour les 4 modèles.
- **B écarté** : dans D, B fait moins bien que A pour les 3 modèles sur le critère 1 et ne réduit pas les erreurs
  (RAPPORT D §5), pour des cartes 1,8 fois plus longues. Le rejouer coûterait ~40 % du budget pour une question
  déjà tranchée.
- J'adopte la recommandation de Jarvis (A + C) : C est le format du futur cerveau (appel d'outil), A la référence.

8 combinaisons = 4 modèles x 2 formats. Exposition gelée de D inchangée (`exposition.json`, sha `47ab40ae0e6a`),
mêmes 8 fiches par conversation, même banc (79 tours, 57 conversations, **jeu complet, aucun sous-échantillon**),
même prompt système, température 0,3, même fenêtre d'historique, même boucle d'outil (4 appels au plus).

## 4. Générations (amendement Matteo 10676)

- **Génération 1** : les 8 combinaisons, 79 tours chacune.
- **Génération 2** : seulement pour les **2 meilleures combinaisons** au classement de la section 6, et seulement
  si la règle ne les départage pas au-delà de la dispersion. Déclenchement écrit maintenant : g2 est jouée si,
  entre la 1re et la 2e, **l'IC95 du bootstrap apparié (sur les conversations) de l'écart sur le critère qui les
  classe contient 0**, ou si ce critère est le critère 1 et que l'écart est inférieur à **0,022**. C'est la
  dispersion mesurée de la référence dans D, 0,820 en g1 contre 0,799 en g2 (RAPPORT D §3). La g2 est jugée comme
  la g1, et la règle est réappliquée sur g1 + g2 réunies.

## 5. Juge : le même qu'en D, plus le contenu des fiches (précision Matteo 10678)

- Inchangé : agent `juge-aveugle`, `claude -p --model claude-opus-5-5 --effort low`, abonnement (le lanceur refuse
  de démarrer si `ANTHROPIC_API_KEY` est présente ; le `.env` d'OrientIA n'est jamais sourcé dans ce shell),
  rubrique `RUBRIC` mot pour mot, `build_prompt`, `parse_verdict` et `valid_scores` de D, aveugle sur modèle et
  format (graine, identifiants opaques, `label_mapping.json`), rejugement de 20 % des tours (au moins 15 par
  combinaison), appels d'outil retirés du transcript (seule la réponse finale est jugée).
- **Seul ajout** : le juge voit le **rendu neutre des 8 fiches exposées**, c'est-à-dire la carte B complète (chaque
  chiffre avec session, source, définition), **identique pour les 8 combinaisons**. C'est le « contexte neutre »
  écrit en D v0.1 et abandonné en v0.2. Un test vérifie, octet pour octet, que deux combinaisons d'une même
  conversation donnent au juge le même contexte, réponse exceptée (repris de `tests/test_juge_d.py`).
- **Une phrase d'accompagnement** (validée par Jarvis, GO du 24/09, forme complétée par lui), la même pour les 8
  combinaisons : « Les fiches ci-dessous sont les données officielles montrées à l'assistant. Un chiffre ou un fait
  qui les contredit est une erreur factuelle. Une information absente des fiches n'est pas une erreur en soi :
  juge-la sur tes connaissances. »
- **Taille des lots** : 6 tâches par lot au lieu de 25. Mesure : la carte B fait 6 908 caractères en médiane, soit
  55 360 caractères de fiches par tâche en médiane (93 208 au maximum). 25 tâches dépasseraient le contexte du juge.
  Lots mélangés comme en D (jamais une conversation entière dans un lot, pour ne pas faire de jugement comparatif).
  Environ 106 lots en g1, plus 22 lots de rejugement. **Risque** : la limite de session de l'abonnement, déjà
  atteinte en D ; la reprise se fait par tâches manquantes, contrôlée sur les fichiers.
- Conséquence : les notes et `erreur_factuelle` **ne sont pas comparables à D**. On compare les 8 combinaisons de E
  entre elles, R comprise.

**Portée** : l'exposition reste celle de D (attendus + BM25, 8 fiches, gelée), donc une **borne haute de la
recherche**. Le banc compare les modèles à recherche égale ; il ne mesure pas le produit de bout en bout.

## 6. Critères et règle de décision (écrite avant, seuils chiffrés)

R = A x Medium (la prod). Tous les écarts à R et entre combinaisons sont calculés par bootstrap apparié sur les
conversations (graine fixe), sur la génération 1.

**Étape 0, garde-fous de forme (une combinaison qui échoue est écartée, motif publié)**
- réponses vides, coupées ou en erreur après reprise > 2 % des tours ;
- longueur médiane hors de [200 ; 600] mots (le prompt demande 250 à 450 ; D mesurait de 325 à 880) ;
- refus (juge) > taux de R + 5 points ;
- format C : erreurs d'outil (arguments invalides, identifiant inconnu) > 5 % des appels.

**Étape 1, critère 1 en non-infériorité** : part des chiffres attendus cités justes (P, instrument de D, 2 générations
quand elles existent). Écart ≥ -0,03 à R, en valeur ponctuelle (-0,03 ≈ 1,5 fois la dispersion de R, 0,022). Biais
connu de l'instrument contre les tableaux markdown (RAPPORT D §7) : une combinaison qui échoue ici mais passe en
comptant les lignes de tableau (`biais_tableaux`) n'est pas écartée. Elle est **signalée** pour décision de Matteo.

**Étape 2, critère principal : erreur factuelle du juge qui voit les fiches.** Une combinaison bat R si l'IC95 de
son écart dE à R est entièrement sous 0. Parmi celles qui battent R, classement par dE ponctuel ; départage à moins
de 2 points par la moyenne des 4 critères du juge, puis par le coût par tour au prix publié.

**Étape 3, décision** : la 1re combinaison du classement devient le choix de la démo. Si aucune ne bat R, on garde R.
Déclenchement de la g2 : section 4.

**Témoin souverain** : si Small 4 (A ou C) passe les étapes 0 et 1 et que l'IC95 de son écart dE à la combinaison
choisie contient 0, il est **signalé comme équivalent souverain** (Cloud Temple, SecNumCloud). La décision est à
Matteo, pas à la règle.

Secondaires publiés, hors règle : taux d'appel de l'outil et erreurs d'outil par modèle, chiffres adossés
(`numbers.py`, avec témoin de hasard), 4 critères du juge, mots, latence, 429, coût par tour, débit.

## 7. Manifeste et débit (demande de Jarvis)

Chaque manifeste ajoute : **nombre de fils** (`workers`), endpoint, et **par tour** un horodatage de début et de fin
(UTC), le nombre d'essais et les 429 rencontrés. Débit publié par modèle : tours par minute sur l'horloge murale,
avec les fils. Attente exponentielle sur 429 de D (d802252) inchangée. 3 fils pour les 4 modèles, comme D ; si GLM
enchaîne plus de 20 tours en 429 dans une combinaison, il repasse à 1 fil, et le changement est écrit dans le
manifeste.

## 8. Budget et arrêt

Projection, tokens de D aux prix publiés (supposés pour ce qui n'a pas été mesuré en D : C avec la nouvelle
consigne, entrée estimée à 0,8 M par combinaison au lieu de 0,45 M, car les appels relisent le contexte ; sortie de
GLM 5.3 estimée à 150 k, 3 fois celle de GLM 5.2 d'après le diagnostic) :

| combinaison (1 génération) | A | C |
|---|---|---|
| Medium | 1,62 | 1,80 |
| GLM 5.2 | 1,15 | 1,33 |
| GLM 5.3 | 1,60 | 1,78 |
| Small 4 | 0,15 | 0,17 |

- **Cas 1, g1 seule : 9,6 USD** (12,5 avec 30 % de marge).
- **Cas 2, g1 + g2 pour les 2 meilleures** : au pire les 2 combinaisons C les plus chères, soit +3,6 USD. Total
  **13,2 USD** (17,1 avec marge).
- Juge : 0 USD d'API (abonnement). Diagnostic déjà dépensé : 0,47 USD.
- **Arrêt** : si le cumul dépasse 20 USD, ou dépasse la projection du cas en cours de plus de 50 %. Ordre : A x Small
  d'abord (la moins chère), coût réel comparé à la projection, puis le reste.

## 9. Écarts à D, listés

1. Endpoint api.eu.mistral.ai au lieu de l'endpoint par défaut du SDK.
2. Modèles : Large retiré, GLM 5.3 et Small 4 ajoutés.
3. Formats A et C (B retiré) ; C avec la consigne d'outil explicite.
4. Juge : contenu des fiches (carte B) et une phrase d'accompagnement ; lots de 6.
5. Génération 2 conditionnelle (section 4).
6. Règle : critère principal = erreur factuelle jugée avec les fiches ; critère 1 en non-infériorité.
7. Manifeste : fils, horodatage par tour, 429.
8. Prix : publiés partout. Corrige les suppositions de D : Medium était supposé 0,4 / 2,0 (publié 1,5 / 7,5), GLM
   1 / 4 (publié 1,4 / 4,4). **Coût réel de D aux prix publiés : 23,25 USD** (Medium 11,18, GLM 8,39, Large 3,69),
   au lieu de 12,9. Par tour en A : Medium 0,0206, GLM 5.2 0,0146 (0,71 fois Medium, et non 2 fois).

## 10. Traces

`diag_outil/`, `runs/<format>-<modele>/g<n>.jsonl` et `manifest_g<n>.json`, `judge/`, `analyse.json`, `RAPPORT.md`,
export explorateur (format de D, onglet comparatif).

## 11. Amendement v0.3.1 (24/09/2026, 11h25, écrit avant la lecture de tout verdict retenu ; demande de Jarvis)

**Transport du lot vers le juge.** Mesures du 24/09 sur la génération 1 :
- En JSON, chaque prompt tient sur une ligne de 27 000 à 39 000 tokens, au-dessus des 25 000 que l'outil Read accepte
  par lecture : 9 verdicts sur 24 (lots 001 à 004). Déplacés dans `judge/abandon_format_json/`, jamais lus.
- En texte multiligne lu par tranches (Read avec offset), le juge d'effort low déclare des lectures partielles des
  fiches (1 tâche sur 6 sur g1_lot_001), ce qui fausse le critère principal (erreur factuelle jugée avec les
  fiches). Les 14 verdicts rendus ainsi sont déplacés dans `judge/abandon_transport_read/`, jamais lus.
- **Transport retenu : le lot entier passé sur stdin** de `claude -p` (`judge/traces_lanceur/juge_stdin.sh`), fiches
  comprises, sans lecture de fichier. Témoins : g1_lot_001 (422 k caractères) 6/6 verdicts valides, 0 lecture
  partielle déclarée, `modelUsage` = claude-opus-5-5 seul, 31 s, 216 k tokens de contexte ; g1_lot_102, le plus gros
  lot (484 k caractères), 6/6 valides, 32 s, 243 k tokens. Ces 12 verdicts de test restent dans
  `judge/verdicts_test_stdin/` et n'entrent dans aucun calcul : les 106 lots et les 22 lots de rejugement sont tous
  rejoués en stdin, dans les mêmes conditions.
- Inchangé : agent `juge-aveugle`, Opus 5.5 effort low, abonnement, garde `ANTHROPIC_API_KEY`, rubrique, contenu des
  lots (mot pour mot celui des `.json`), aveugle, rejugement.
- Incident sans effet sur les verdicts : 4 lots ont rendu un 400 (« Claude Code 2.1.126 does not support this
  model ») pendant la mise à jour automatique de Claude Code (11:16) ; version 2.1.281 ensuite.

## 12. Amendement v0.3.2 (24/09/2026, 16h40, écrit avant le jeu du rejugement ; choix de Jarvis, option 2)

**Rejugement réduit.** Le rejugement de 20 % des tours (22 lots, 128 tâches) n'entre pas dans la règle de décision
(section 6) : il mesure le bruit aléatoire du juge. La décision de g1 est déjà rendue (C x GLM 5.3, dE -63,3 pts,
IC95 [-74,7 ; -51,9] ; vérification indépendante de Jarvis sur les verdicts bruts, chiffres identiques). Le rejugement
est réduit à **la référence et au choix, 15 tours chacun**, soit 30 tâches en **5 lots de 6** (`g1_rejugemin_*`), pour
publier l'accord d'un juge dont la configuration a changé depuis D (fiches vues, transport stdin) et n'a jamais été
mesurée. Les 15 tours de chaque combinaison sont les 15 premiers (ordre des oid) de l'échantillon tiré le 24/09 avant
tout résultat (`rejuges_g1.json`, 16 par combinaison) ; l'ordre dans les lots est mélangé (graine
`banc-e-2026-09-24|rejuge-min`). Même transport stdin (lanceur v2), même juge. Le rejugement ne peut pas changer la
décision ; il ne détecte pas non plus un biais systématique du juge (c'est le même juge), seulement son instabilité.

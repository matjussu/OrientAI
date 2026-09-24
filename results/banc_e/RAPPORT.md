# Banc E : modèle de la démo, confirmation (24/09/2026)

Ordre 2026-09-24-1020. Protocole écrit avant tout appel de grille : `PROTOCOLE.md` v0.3 (GO de Jarvis 10h42),
amendements 11 (v0.3.1, transport du juge, 11h25) et 12 (v0.3.2, rejugement réduit, 16h40), tous datés avant la
lecture des verdicts concernés. Chiffres calculés par `python -m src.eval.rapport_e` (`analyse.json`), recomptés de
façon indépendante par Jarvis depuis les verdicts bruts (`judge/verdicts/`, `label_mapping.json`, son propre
bootstrap) : identiques.

**Portée** : l'exposition est celle de D (attendus + BM25, 8 fiches par conversation, gelée, sha `47ab40ae0e6a`),
donc une **borne haute de la recherche**. Le banc compare les modèles à recherche égale ; il ne mesure pas le produit
de bout en bout.

## 1. Décision selon la règle écrite (section 6)

**Choix : C x GLM 5.3** (`zai-glm-5-3`, carte courte + outil `lire_fiche`, consigne d'outil explicite). Il bat la
référence (A x Medium, la prod) sur le critère principal, erreur factuelle jugée avec les fiches : **12,7 % contre
75,9 %, écart -63,3 points, IC95 [-74,7 ; -51,9]**, sans perte sur le critère 1 (0,805 contre 0,817, écart -0,012,
au-dessus du seuil de non-infériorité -0,03). **Pas de génération 2** : entre les deux premières (C et A x GLM 5.3),
l'écart d'erreur factuelle est de -17,7 points, IC95 [-30,9 ; -5,0], 0 exclu. **Small 4 n'est pas équivalent
souverain** : écarté à l'étape 0 (longueur) et +75 points d'erreur factuelle contre le choix.

## 2. Matrice (génération 1, 79 tours par combinaison)

Juge : Opus 5.5 effort low, à l'aveugle, voit la carte B des 8 fiches exposées (section 5 et amendement 11).
Coûts aux prix publiés (section 2).

| combinaison | P (critère 1) | témoin | erreur fact. | moy. juge | refus | mots (méd.) | tours avec appel d'outil | s / tour (méd.) | USD / tour |
|---|---|---|---|---|---|---|---|---|---|
| **A x Medium (R)** | **0,817** | 0,068 | **75,9 %** | 3,31 | 0 | 536 | - | 9,5 | 0,0210 |
| A x GLM 5.2 | 0,777 | 0,053 | 30,4 % | 3,83 | 0 | 340 | - | 3,9 | 0,0145 |
| A x GLM 5.3 | 0,817 | 0,065 | 30,4 % | 4,41 | 0 | 400 | - | 12,0 | 0,0216 |
| A x Small 4 | 0,693 | 0,081 | 87,3 % | 2,88 | 0 | 638 | - | 10,2 | 0,0021 |
| C x Medium | 0,768 | 0,059 | 65,8 % | 3,39 | 0 | 478 | 63 % | 8,7 | 0,0212 |
| C x GLM 5.2 | 0,762 | 0,050 | 39,2 % | 3,86 | 0 | 350 | 67 % | 4,2 | 0,0163 |
| **C x GLM 5.3 (choix)** | **0,805** | 0,068 | **12,7 %** | **4,45** | 0 | 397 | 91 % | 11,6 | 0,0274 |
| C x Small 4 | 0,666 | 0,062 | 88,6 % | 2,93 | 0 | 612 | 51 % | 9,1 | 0,0020 |

Témoin de hasard du critère 1 : les réponses d'une conversation contre les attendus d'une autre (instrument de D). Appels d'outil au format C :
685, dont 1 en erreur (Small). Aucun refus sur les 632 tours.

## 3. Application de la règle, étape par étape

| combinaison | étape 0 (forme) | étape 1 (dP ≥ -0,03) | étape 2 (dE à R, IC95) |
|---|---|---|---|
| A x GLM 5.2 | ok | **non** (-0,040) | -45,6 [-58,2 ; -32,5] |
| A x GLM 5.3 | ok | ok (0,000) | **-45,6 [-58,7 ; -32,5]**, bat R |
| A x Small 4 | **écartée** (638 mots médians > 600) | non (-0,124) | +11,4 [-1,3 ; +24,0] |
| C x Medium | ok | **non** (-0,050) | -10,1 [-25,3 ; +4,9] |
| C x GLM 5.2 | ok | **non** (-0,056), **signalée** : passe en comptant les tableaux (0,827 contre 0,836) | -36,7 [-50,6 ; -22,2] |
| C x GLM 5.3 | ok | ok (-0,012) | **-63,3 [-74,7 ; -51,9]**, bat R |
| C x Small 4 | **écartée** (612 mots médians) | non (-0,152) | +12,7 [+2,6 ; +22,5] |

Classement des candidates : C x GLM 5.3, puis A x GLM 5.3. Choix : C x GLM 5.3.

## 4. Diagnostic de l'outil chez Medium (phase 1)

`diag_outil/RESUME.md`. Cause mesurée : le forçage générique (`tool_choice` any ou required) n'est pas appliqué à
Medium sur cette API (0 appel sur 8, réponses qui dégénèrent) ; le forçage par nom de fonction marche ; en mode auto,
la consigne descriptive de D ne déclenche pas l'appel. Correctif : consigne explicite. Effet sur la grille : Medium
appelle l'outil sur 63 % des tours (0 % en D), sans réduction des erreurs hors du bruit (dE -10,1, IC95 contient 0).

## 5. Constats hors règle

- **GLM 5.3 est le seul modèle qui gagne à l'outil** : erreur factuelle 30,4 % en A, 12,7 % en C ; il appelle
  l'outil sur 91 % des tours. GLM 5.2 fait l'inverse (30,4 % puis 39,2 %).
- **La référence se trompe sur 3 réponses sur 4 quand le juge voit les fiches.** Contrôle de sens sur un échantillon
  de motifs : CUPGE présentée comme une LAS, licence non sélective donnée comme sélective, CVEC à 100 € (105 € dans la
  fiche), bac pro CIEL mal nommé. En D, sans les fiches, le juge en relevait 43 % : l'écart vient de ce qu'il voit
  maintenant les contradictions avec les fiches.
- **Coût** : C x GLM 5.3 coûte 0,027 USD par tour, 1,3 fois la référence, pour 6 fois moins d'erreurs factuelles.
- **Débit (nouveau, horodatage par tour, 3 fils)** : 18 à 20 tours par minute pour Medium et Small, 13 à 14 pour
  GLM 5.3 (0 erreur 429), 10 (A) et 5 (C) pour GLM 5.2, freiné par 129 erreurs 429, toutes résorbées par l'attente.
  Latence médiane de GLM 5.3 : 11,6 s par tour en C.
- **Licence GLM 5.3** (relue par Jarvis sur la page du modèle) : la revue de sécurité ne vise que les opérateurs
  « Model as a Service » au-delà de 10 Md$ de chiffre d'affaires, un produit final intégré est exclu ; sans effet pour
  OrientAI.

## 6. Juge : transport, témoin et accord

- **Amendement v0.3.1, transport par stdin.** Lu par tranches avec l'outil Read, le juge d'effort low déclarait des
  lectures partielles des fiches. **Témoin : la tâche `8bf2a1383d`** (A x Medium, V-INF-05) : fiches lues en partie
  par tranches, `erreur_factuelle` = false ; fiches entières sur stdin, true, deux fois (test et run retenu), motif
  « 44 % des admis avaient assez bien ou moins : 44 % correspond aux admis sans mention seuls, le total fait 77 % ».
  Avec le transport retenu : **0 lecture partielle déclarée** sur les 98 sorties de juge lisibles
  (`judge/sorties_juges/`).
- Verdicts écartés, jamais lus : 9 (JSON trop long, `judge/abandon_format_json/`), 14 (lecture par tranches,
  `judge/abandon_transport_read/`) ; 12 verdicts de test du transport (`judge/verdicts_test_stdin/`), hors calcul.
- **Rejugement (amendement v0.3.2)** : réduit à R et au choix, 15 tours chacun, 5 lots. État : voir section 8.

## 7. Complétude, traces et incidents

- **Génération** : 8 x 79 tours, 0 erreur, 0 doublon, modèle rendu = modèle demandé partout, endpoint
  `https://api.eu.mistral.ai`. Commit des manifestes : `3ab65d7`. **`git_dirty` = true** dans 7 manifestes : il ne
  couvre que `src/eval/juge_e.py` et `src/eval/rapport_e.py`, non suivis pendant le run et non importés par la
  génération ; le code de génération est identique à `3ab65d7` (`git diff 3ab65d7 -- src/eval/grille_e.py
  src/eval/grille_d.py src/eval/format_d.py src/eval/exposition_d.py src/eval/battery/config.py` vide).
- **Juge** : 632 verdicts valides sur 632, contrôlés sur les fichiers.
- **Incidents** : deux coupures par la limite de session de l'abonnement (11:28 puis 11:57, premiers lots refusés), reprises sur les
  lots manquants seulement, sans lot à moitié jugé. Erreurs 400 « Claude Code 2.1.126 does not support this model » :
  pendant les réinstallations automatiques du paquet Claude Code de nvm (11:16, 11:20, 11:49), le PATH retombait sur
  `/usr/bin/claude` 2.1.126. Lanceur v2 (`juge_stdin_v2.sh`) : binaire nvm en chemin absolu, `DISABLE_AUTOUPDATER=1`.
- **Coût** : génération 9,97 USD (projection 9,6), diagnostic 0,47 USD, total **10,44 USD** ; juge sur l'abonnement.

## 8. Rejugement

À compléter après le jeu des 5 lots (`g1_rejugemin_*`) : accord brut et kappa sur `erreur_factuelle`, écart absolu
moyen par critère.

## 9. Correction du coût de D

Prix publiés (section 2 du protocole E) au lieu des prix supposés : **coût réel de D = 23,25 USD** (Medium 11,18,
GLM 5.2 8,39, Large 3,69) au lieu de 12,9. Par tour en A : Medium 0,0206, GLM 5.2 0,0146, soit 0,71 fois Medium (le
RAPPORT de D disait « environ 2 fois »). Correction reportée dans `results/donnee_etape_d/RAPPORT.md` (section 6)
et `PROTOCOLE.md` (section 9).

## 10. Traces

`PROTOCOLE.md`, `diag_outil/`, `runs/<combinaison>/g1.jsonl` et `manifest_g1.json`, `judge/` (lots `.json` et
`.txt`, `label_mapping.json`, `seed.txt`, `rejuges_g1.json`, verdicts, lanceurs, sorties des juges), `analyse.json`,
export explorateur `export/banc_e.explorateur.json` (même format que D, 632 réponses, la matrice porte les 8
combinaisons).

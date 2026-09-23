# Étape D : format de fiche × modèle, borne haute à récupération correcte (23/09/2026)

Ordre 2026-09-23-1515. Protocole écrit avant tout appel payant : `PROTOCOLE.md` v0.2 (dernier commit
095b590, 23/09 17:25). Chiffres calculés par `python -m src.eval.rapport_d` (sortie `analyse.json`) et
`constats_hors_regle.json` ; aucun ajustement du banc, du critère ou de la règle après les résultats.

**Ce que ce banc mesure** : les 9 combinaisons lisent les **mêmes 8 fiches** par conversation, dont les
fiches des chiffres attendus (exposition gelée, `exposition.json`, sha `47ab40ae0e6a`). C'est une **borne
haute à récupération correcte** : le banc ne mesure pas la capacité à trouver la fiche, qui relève du lot
« cerveau ».

## 1. Décision selon la règle écrite (§10)

**On garde A × mistral-medium-2604, le format et le modèle actuels.** Aucune combinaison ne passe
l'étape 1 (gain sur le critère 1) : aucune n'a un IC95 de dP entièrement au-dessus de 0. La règle prévoit
alors de garder la référence (§10.5).

Ce résultat ne dit pas que les autres combinaisons sont pires en tout : la section 4 rapporte un écart
large et hors du bruit en faveur de GLM 5.2 sur les erreurs factuelles et la qualité jugée. La règle,
validée avant les résultats, ne récompense que le critère 1 ; ce constat est donc à trancher par Matteo,
pas par la règle.

## 2. Matrice

Critère 1 : chiffres attendus cités justes sur 323 (18 hors critère, fiches absentes de la base C),
moyenne des 2 générations. Juge : génération 1, 79 tours par combinaison, Opus 5.5 effort `low`, à
l'aveugle. Coût par tour : tokens × prix (**Medium et GLM : prix supposés**, §9).

| combinaison | P (g1 / g2) | témoin | dP [IC95] | moy. juge | erreur fact. | mots (méd.) | s / tour | USD / tour |
|---|---|---|---|---|---|---|---|---|
| **A × Medium (R)** | **0,810** (0,820 / 0,799) | 0,068 | - | 3,50 | 43,0 % | 491 | 9,3 | 0,0055 |
| A × Large | 0,772 (0,749 / 0,796) | 0,093 | -0,037 [-0,093 ; +0,017] | 3,34 | 64,6 % | 788 | 24,1 | 0,0069 |
| A × GLM | 0,783 (0,780 / 0,786) | 0,065 | -0,026 [-0,076 ; +0,026] | **3,89** | **16,5 %** | 334 | 4,1 | 0,0109 |
| B × Medium | 0,782 (0,774 / 0,789) | 0,087 | -0,028 [-0,086 ; +0,026] | 3,29 | 60,8 % | 574 | 13,0 | 0,0101 |
| B × Large | 0,676 (0,663 / 0,690) | 0,093 | -0,133 [-0,192 ; -0,075] | 3,23 | 58,2 % | 880 | 27,2 | 0,0124 |
| B × GLM | 0,709 (0,743 / 0,675) | 0,062 | -0,101 [-0,151 ; -0,053] | **3,98** | 25,3 % | 325 | 4,6 | 0,0204 |
| C × Medium, carte courte seule (0 appel) | 0,656 (0,659 / 0,653) | 0,050 | -0,153 [-0,207 ; -0,097] | 3,31 | 50,6 % | 459 | 7,8 | 0,0033 |
| C × Large, carte courte seule (4 % des tours) | 0,627 (0,653 / 0,601) | 0,062 | -0,183 [-0,238 ; -0,126] | 3,22 | 62,0 % | 677 | 20,8 | 0,0041 |
| C × GLM, carte + outil (33 % des tours) | 0,729 (0,740 / 0,718) | 0,056 | -0,080 [-0,139 ; -0,020] | **3,94** | 20,3 % | 331 | 4,3 | 0,0082 |

Taux d'appel de l'outil `lire_fiche` (format C) : Medium 0 %, Large 4 % des tours, GLM 33 %. Aucun refus
chez aucune combinaison (juge, 711 tours).

Secondaire déterministe, chiffres cités adossés aux fiches exposées (`numbers.py`, avec témoin) : R 71 %
(témoin 35 %), A × GLM 77 % (34 %), A × Large 54 % (30 %). **Biais connu** : `numbers.py` compare à la
FactCard du corpus (le contenu de A) ; une réponse B ou C qui cite un chiffre propre à sa carte
(historique 2023-2024) est comptée « non adossée ». Non utilisé dans la règle.

## 3. Application de la règle, combinaison par combinaison (§10)

Dispersion de R : 0,820 en génération 1, 0,799 en génération 2, écart **0,022**. Juge : 144 tours
rejugés par d'autres processus ; accord sur `erreur_factuelle` 81,9 % (kappa 0,625, taux 38,9 % puis
41,7 %), désaccord 18,1 % ; écart absolu moyen par critère : références 0,28, compréhension 0,25,
expression 0,27, couverture 0,27. `refus` : 0 dans les deux passes (kappa non défini).

| combinaison | 1. gain | 2-3 bis. garde-fous (motif d'écart) |
|---|---|---|
| A × Large | non | écartée : erreur +21,5 pts [+6,2 ; +36,9] ; expression -0,37 ; compréhension -0,15 |
| A × GLM | non (dP dans le bruit) | non écartée |
| B × Medium | non | écartée : erreur +17,7 pts [+4,5 ; +31,0] ; expression -0,35 |
| B × Large | non | écartée : erreur +15,2 pts ; expression -0,53 ; compréhension -0,23 |
| B × GLM | non (dP < 0) | non écartée |
| C × Medium | non | écartée : compréhension -0,18 ; couverture -0,23 |
| C × Large | non | écartée : erreur +19,0 pts ; expression -0,30 ; compréhension -0,20 |
| C × GLM | non (dP < 0) | non écartée |

Aucune candidate : la référence est gardée (§10.5).

## 4. Constats hors règle (descriptifs, à trancher par Matteo)

Écarts à R, bootstrap apparié sur les conversations, génération 1 (`constats_hors_regle.json`) :

| combinaison | erreur factuelle, dE [IC95] | moyenne des 4 critères [IC95] |
|---|---|---|
| A × GLM | **-26,6 pts [-37,2 ; -15,6]** | **+0,39 [+0,25 ; +0,51]** |
| B × GLM | -17,7 pts [-31,3 ; -3,8] | +0,48 [+0,38 ; +0,58] |
| C × GLM | -22,8 pts [-34,9 ; -10,7] | +0,44 [+0,29 ; +0,57] |

- Les trois combinaisons GLM ont moins d'erreurs factuelles que R, hors du bruit (au-delà du désaccord du
  juge de 18,1 pts) et une note moyenne plus haute (au-delà de l'écart de rejugement, 0,25 à 0,28).
- A × GLM a un critère 1 équivalent à R (0,783 contre 0,810, IC95 de dP [-0,076 ; +0,026]).
- **Longueur** : GLM répond en 334 mots médians, Medium en 491. Une réponse courte expose moins de faits
  au juge. Ça n'explique qu'une partie de l'écart : sur les réponses de moins de 400 mots, R a une erreur
  factuelle sur 29 % des tours (28 tours), A × GLM sur 16 % (67 tours).
- **Limites** : le juge ne voit pas le contenu des fiches, il juge `erreur_factuelle` sur sa propre
  connaissance (§8) ; effort `low` ; une seule génération jugée.
- **Coûts d'exploitation de GLM** : 78 erreurs 429 (limite de débit de l'API) en génération 1, contre 0
  pour les deux Mistral ; coût par tour environ 2 fois celui de Medium au prix supposé (borne prudente,
  prix non publié) ; latence plus basse (4,1 s contre 9,3 s).

Si Matteo veut trancher sur ce constat, un banc de confirmation dédié est possible (A × Medium contre
A × GLM, 2 générations jugées, juge qui voit les fiches). Ce n'est pas lancé.

## 5. Autres enseignements

- **Le format B (carte structurée) n'aide pas** : il fait moins bien que A pour les trois modèles sur le
  critère 1, et ne réduit pas les erreurs. Les cartes B sont 1,8 fois plus longues que A.
- **La carte courte seule (C sans appel d'outil) perd 15 à 18 points** : le modèle a besoin des chiffres
  sous les yeux. C × GLM, qui appelle l'outil, perd 8 points.

### Constat pour le lot « cerveau » (sonde outil, `sonde_outil/RESUME.md`)

Le cerveau reposera entièrement sur l'appel d'outils ; c'est le résultat le plus important de la sonde :
- **Medium 3.5 n'appelle pas l'outil**, même forcé (`tool_choice="any"`), avec ce prompt et 8 cartes ;
  il l'appelle sur un prompt minimal. Cause non établie.
- **Large 3 sait l'appeler** (11 appels forcés, dont 1 identifiant mal formé), mais ne le fait pas en
  mode auto (4 % des tours sur la grille).
- **GLM 5.2 l'appelle de lui-même** (33 % des tours sur la grille, 0 erreur d'outil).

## 6. Complétude, traces et incidents

- **Génération** : 9 combinaisons × 2 générations, chacune 57 conversations et 79 tours, 0 doublon
  (id, tour), 0 erreur dans les fichiers finaux (`analyse.json`, `completude_generation`, contrôle vert,
  rouge par test sur un tour manquant, en erreur ou dupliqué).
- **Juge** : 711 verdicts valides sur 711 attendus (79 par combinaison), 144 rejugements sur 144, calculés
  sur les fichiers et non sur les codes de sortie des lanceurs. Contexte identique pour les 9 combinaisons,
  testé octet pour octet (`tests/test_juge_d.py`).
- **Modèles rendus** : identiques aux modèles demandés dans tous les manifestes (arrêt prévu sinon).
- **Commits des manifestes** : 4a45340, d802252, 095b590, 7992e82, 305cf42, d7d74a8. Le code de génération
  (`grille_d.py`, `format_d.py`, `exposition_d.py`) n'a changé qu'une fois entre eux, en d802252 : logique
  de reprise (conversation entière ou rien) et attente exponentielle sur 429 (`git diff 4a45340 d802252`,
  1 fichier, 21 lignes). Aucun manifeste `git_dirty`.
- **Incidents** :
  - 429 sur GLM en génération 1 : 78 tours (30 en A, 48 en B), rejoués après le correctif d802252 ;
    lignes d'origine gardées dans `g1.erreurs.jsonl`.
  - 5 erreurs réseau (résolution DNS) sur A × Large en génération 2, dont 2 erreurs en cascade (tour
    suivant avec une réponse vide) ; les 3 conversations ont été rejouées en entier.
  - Juge : les 8 premiers juges tournaient avec l'effort par défaut ; arrêtés, 20 verdicts écartés
    (`judge/abandon_effort_defaut/`), jamais lus. Protocole v0.2 écrit avant la lecture de tout verdict retenu.
  - Juge : le script du lanceur a été modifié pendant que 4 instances tournaient (bash lit au fil de
    l'eau) ; 4 fins de script en « unexpected EOF ». Les lots 02 à 05 ont leurs 25 verdicts valides.
  - Juge : limite de session de l'abonnement atteinte à 17:34 ; 165 verdicts et le rejugement relancés
    dans 13 lots de complément (tâches manquantes seulement, 7 à 9 combinaisons mélangées par lot).
    Lot 15 : lanceur en « exit 0 » avec 1 verdict manquant, rattrapé par le contrôle sur fichiers.
- **Lecture préliminaire** : à la demande de Matteo (via Jarvis, Telegram 10647, 23/09 18:14), après le
  gel du protocole, critère 1 de la génération 1 seulement (`lecture_preliminaire_g1.json`, 305cf42).
- **Coût** : grille 12,9 USD (18 passages), sonde 0,10 USD, prix de Medium et GLM supposés. Seuil de 35 USD
  non atteint.

## 7. Limites

- Exposition oracle (fiches attendues + BM25) : borne haute, pas la chaîne de production.
- C × Medium et C × Large mesurent la carte courte seule (l'outil n'a pas été appelé).
- Les masters exposés (32) ont en A une insertion et un niveau que B et C n'ont pas (base C, section 2).
- V-SAN-18 (« comment on devient médecin ? ») n'a aucune fiche exposée : aucun terme BM25 ne correspond.
- Juge sans le contenu des fiches, effort `low`, génération 1 seule ; notes non comparables au lot 0.
- Attendus « effectif » : vœux, candidats et propositions forment une seule unité (v0.2), le témoin de
  hasard en mesure le coût.
- **Biais de l'extracteur typé contre les tableaux** (trouvé par la vérification indépendante de Jarvis,
  23/09) : le critère 1 exige l'unité juste après le nombre ; un chiffre écrit dans un tableau markdown
  (`| Candidats | 3 779 |`, unité dans l'en-tête) n'est pas compté. Mesure (`biais_tableaux.json`, g1 et
  g2) : C × GLM écrit des tableaux dans 47 réponses et perd 7,0 pts (0,729, 0,799 en comptant les lignes de
  tableau) ; A × GLM et B × GLM n'en écrivent aucun (0 pt) ; les autres perdent 2,0 à 4,8 pts, R 2,0 pts
  (0,810, 0,830). Le classement ne change pas : personne ne dépasse R, et l'écart de C × GLM à R passe de
  8 à 3 pts. Compter les lignes de tableau accepte aussi des coïncidences (un « 33 » de colonne places
  pour un attendu à 33 %) : ce n'est pas un instrument de remplacement, c'est la mesure du biais. La
  règle reste appliquée avec l'instrument écrit au protocole. Le recomptage de Jarvis, avec un
  extracteur sans unité, aboutit à la même conclusion (net du témoin : R 0,706, C × GLM 0,693, A × GLM
  0,680).

## 8. Traces

`PROTOCOLE.md`, `exposition.json`, `sonde_outil/`, `runs/<combinaison>/g{1,2}.jsonl` et manifestes,
`judge/` (lots, `label_mapping.json`, `seed.txt`, verdicts, rejugements, traces des lanceurs),
`analyse.json`, `constats_hors_regle.json`, `lecture_preliminaire_g1.json`, export explorateur
`export/etape_d.explorateur.json` (6,6 Mo, 1 422 réponses).

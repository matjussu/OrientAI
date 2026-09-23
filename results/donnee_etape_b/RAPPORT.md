# Étape B-1 de la donnée verticale : coût, alternance, insertion

Claudette, 23/09/2026. Ordre `2026-09-23-1044-claudette-orientai-donnee-etape-b-completer`, sous-lot B-1
(périmètre réduit confirmé par Matteo le 23/09, Telegram 10584 : B1 coûts, B5 alternance, B3 insertion).
Spécification : `~/projets/_orientai-ref/verticale-2026-09/CAHIER-DES-CHARGES-donnee.md` sections 4 et 7,
`sources-donnees.md`. Forme des champs : `CONTRACT.md` (ce dossier), version 1.1.

Aucun appel LLM, aucun ré-embedding, coût API nul, aucun déploiement. Le corpus de l'étape A
(`9eae9c25108b`) et celui de la prod (`2e4276e6155b`) ne sont pas modifiés.

## Livrable

| | |
|---|---|
| Nouveau corpus | `data/processed/formations_etape_b1.json` (hors git), 53 807 fiches (53 281 de l'étape A + 526 formations en apprentissage) |
| sha256 | `9863d2b40d3f...` (valeur complète dans `manifest_corpus.json`) |
| Une commande | `python -m src.collect.pipeline_donnee` : contrôle des empreintes des bruts, étape A, étape B-1 |
| Déterminisme | deux constructions sur les mêmes bruts donnent le même fichier (vérifié le 23/09, sha identique) ; le pipeline complet reproduit aussi l'étape A à l'identique (`9eae9c25108b`) |
| Sources brutes | `data/raw/` (hors git), 4 sources ajoutées au verrou `data/reference/sources_officielles.json` : Onisep Idéo-Actions ES (ODbL), Parcoursup apprentissage 2025, InserSup (diplômés, promos 2023 et 2024, filtre écrit dans l'URL), InserJeunes BTS |
| Sources lues | Service-Public F36520 (CVEC, BTS public) et tableau ministériel des droits 2026-2027 (republié par l'Université de Reims, PDF sha256 `b2b8c9c003d29331`), recopiés dans `src/collect/valeur_sourcee.py` et `src/collect/couts.py` avec leur date de lecture |

`fiche_to_text(fiche) -> str` garde sa signature ; aucun import nouveau hors de
`src.rag.texte_parcoursup` (vérifié en rejouant `export_data.py` de Jarvis, qui stubbe `mistralai`).
Une fiche sans champ B garde exactement le texte de l'étape A (test `test_corpus_a_texte_inchange`).

## Ce qui a été construit

Chaque champ porte l'enveloppe `{statut, valeur, raison, source, millesime, collecte, rattachement}`,
présente sur chaque fiche concernée : `non_disponible` est explicite et dit pourquoi.

- **Coût** (`src/collect/couts.py`) : 1) constante légale pour le public (licence, LAS, PASS, BUT,
  licence pro, DEUST, CPGE de lycée : 178 euros + CVEC 105 euros ; BTS public : pas de droits) ;
  2) ligne Onisep du même lieu et du même intitulé ; 3) pour les CPGE et BTS seulement, tarif commun à
  au moins deux formations Onisep du même lycée. Le texte Onisep est gardé mot pour mot et écrit dans le
  texte du modèle, avec la réserve « ne dit pas si des droits d'inscription ou la CVEC s'y ajoutent »
  quand il ne les cite pas.
- **Alternance** (`src/collect/alternance.py`) : fait mesuré, les 11 536 formations du jeu
  apprentissage 2025 ont leurs propres `cod_aff_form`, aucun dans le jeu principal. Donc 526 fiches
  `parcoursup_apprentissage` (domaines de la démo par la table de l'étape A), sans taux d'accès (non
  publié, jamais recalculé), et sur chaque fiche scolaire la liste des formations en apprentissage du
  même diplôme au même UAI ou dans la même commune.
- **Insertion** (`src/collect/insertion.py`) : diplôme x établissement seulement. InserSup par
  l'identifiant Paysage de l'établissement (les UAI des IUT ne sont pas dans InserSup : 0 BUT sur 820
  par l'UAI, 797 par Paysage), donc « tous sites de l'université », écrit tel quel ; InserJeunes par
  UAI du lycée pour les BTS, une ligne par option. PASS, LAS, CPGE, IFSI et paramédical :
  `non_disponible` avec la raison.
- **Coût des formations en apprentissage** : « La formation est gratuite pour l'apprenti et pour son
  représentant légal. » (Code du travail, article L6211-1), citée mot pour mot, avec la précision que
  la phrase ne porte que sur la formation (pas le logement, le transport, l'équipement).

## Correction après la vérification de Jarvis (23/09 après-midi)

Jarvis (0 écart sur 127 vérifications de son côté) a relevé des listes d'alternance interminables
dans les grandes villes (jusqu'à 27 formations pour un BTS SIO à Paris) et des doublons apparents.

- **Cause des doublons, mesurée** : ce ne sont pas des options. C'est le même lycée associé à deux
  CFA partenaires (Lycée Raspail : « CFA académique de Paris » et « CFA Métiers de l'énergie »). Le
  partenaire se lit dans le libellé complet Parcoursup (`lib_comp_voe_ins`), présent sur 1 535
  formations d'apprentissage sur 11 536 ; il est désormais gardé (`cfa_partenaire`) et écrit. Restent
  de vraies formations distinctes à libellés publics identiques (Of-Cfa Elysées Apprentissage, n° 44011
  et 44105, UAI différents) : nommées par leur numéro, avec « le jeu ouvert ne dit pas ce qui les
  distingue ».
- **Texte** regroupé par établissement ; au-delà de 5 établissements, un résumé (« 27 formations en
  apprentissage du même diplôme dans 25 établissements de la même commune (Paris), 1235 places au
  total »), en gardant celles du même établissement. 14 fiches des 3 domaines passent en résumé.
- **Contrôle ajouté** (`alternance_liste_trop_longue`, `alternance_doublon`) : 0 défaut sur le nouveau
  texte ; rejoué sur le texte d'avant la correction (`--revision-texte HEAD`, trace
  `controles_alternance_texte_avant_correction.json`) : 199 listes trop longues et 79 doublons sur tout
  le corpus. Un test a montré que la première version du contrôle ne voyait pas un doublon portant sur
  la première entrée (phrase d'introduction collée) : corrigé, c'est pourquoi le compte est passé de
  72 à 79.
- **Coût de l'apprentissage** (retour de Matteo) : règle légale ci-dessus, source primaire lue sur
  Légifrance. Légifrance refuse les requêtes de script (403) : l'audit vérifie la phrase contre sa
  propre copie et sa présence mot pour mot dans le texte, pas contre la page en ligne.
- **IFSI** : recherche courte en sources primaires, non tranchée. La page du ministère « Formations de
  santé : accès simplifié aux IFSI » dit en substance que l'université ne peut exiger aucun droit de
  l'étudiant infirmier inscrit ; le tableau des droits 2026-2027 liste le « Diplôme d'État
  d'infirmier » à 178 euros. La réserve reste écrite telle quelle.

## Mesures avant / après

Population des gates : les 3 domaines tels que les définit l'explorateur de Jarvis
(`export_data.py`, rejoué sur les deux corpus avec le code de cette branche). Traces :
`remplissage_explorateur.json`, `mesures_complementaires.txt`.

### Remplissage (fiches Parcoursup scolaires, 2 395)

| Domaine | Fiches | Coût avant | Coût après | Alternance avant | Alternance après | Insertion avant (ancienne, discipline x région) | Insertion après (diplôme x établissement) |
|---|---|---|---|---|---|---|---|
| informatique | 881 | 0 | 729 | 0 | 881 | 226 | 215 |
| santé | 1 310 | 0 | 1 184 | 0 | 1 310 | 207 | 2 |
| maths | 426 | 0 | 398 | 0 | 426 | 149 | 12 |

- **Formations en apprentissage** : 517 / 517 avec un coût (règle légale).
- **Gate coût tenue** : 2 395 / 2 395 fiches portent `cout` (disponible ou non disponible avec raison),
  0 absente (`manifest_corpus.json`, `remplissage`). Disponible : 2 099 (87,6 %) ; 1 616 par constante
  légale, 483 par Onisep. Non disponible : 296, raisons dans `mesures_complementaires.txt`.
- **Alternance** : le champ est présent sur 2 395 / 2 395 fiches ; 170 formations existent aussi en
  apprentissage au même UAI ou dans la même commune (140 par l'UAI seul, 25 par la commune seule, 5 les
  deux). Plus 517 fiches d'apprentissage dans les 3 domaines selon l'explorateur (526 selon la table).
- **L'insertion BAISSE, et c'est voulu** : les 482 fiches « avec insertion » de l'étape A portaient une
  médiane InserSup **discipline x région** rattachée avec un score de 0,7, pas un chiffre de la
  formation (accord de Jarvis le 23/09 pour ne plus l'écrire). Il reste 219 fiches avec un chiffre
  propre à la formation dans son établissement : 140 BTS (InserJeunes), 79 BUT, licences et écoles
  (InserSup). Santé à 2 : PASS, LAS, IFSI et paramédical n'ont aucune source d'insertion par formation
  (1 288 fiches, raison écrite dans le texte). Le reste des « non disponible » : secret statistique
  (effectifs trop faibles : 269 fiches dont la source ne diffuse aucun taux, 188 licences, 64 BUT et 17 BTS), lycées hors
  InserJeunes, écoles d'ingénieurs à plusieurs diplômes.

### Contrôles du texte

`python -m src.eval.donnee.controles --corpus <corpus>` : les 10 contrôles de l'étape A plus 10 contrôles
B-1 (champ absent, non disponible sans raison, montant non écrit, coût sans source, ancienne insertion
réécrite, taux d'emploi stable écrit...). **0 défaut** sur 14 252 fiches Parcoursup et 526 fiches
d'apprentissage (`controles_apres.json`) ; 0 sur le corpus A (`controles_avant.json`, les contrôles B
sont muets sur une fiche sans champ B). Chaque contrôle B rougit sur un texte ou une fiche cassés par
un levier explicite (`tests/test_etape_b1.py::test_controles_rougissent`).

### Banc vertical (non-régression)

`python -m src.eval.donnee.banc_textes`, traces `banc_textes_avant.json` / `banc_textes_apres.json` :
336 / 341 chiffres attendus présents dans le texte de leur fiche, avant comme après (98,5 %), témoin
de hasard 6,4 % puis 6,2 %. Les 5 absents sont des capacités MonMaster, inchangées. Aucune valeur
attendue du banc ne change avec la nouvelle donnée (le banc ne porte pas de coût, d'alternance ni
d'insertion) : rien à signaler sur `battery_verticale.json`.

### Longueur du texte

Médiane 3 316 caractères avant, 3 804 après (max 4 884), fiches Parcoursup des 3 domaines. Même
réserve qu'à l'étape A : pas de ré-embedding avec ce texte, l'étape D fixera le texte d'embedding.

## Audit d'exactitude

`python -m src.eval.donnee.audit_etape_b`. Le témoin ne partage pas l'instrument du pipeline : dump
JSON Onisep retéléchargé (le pipeline lit le CSV), API ESR ligne par ligne (apprentissage, InserSup),
API DEPP (InserJeunes), PDF du tableau des droits retéléchargé et relu par pdftotext. Les « non
disponible » qui affirment un fait sont vérifiés aussi (aucune ligne Onisep à ce lieu, coûts
différents, aucune formation en apprentissage au même UAI).

| Audit | Fiches | Écarts | Trace |
|---|---|---|---|
| Tirage au hasard, 3 domaines, graine 20260923 | 50 | 0 | `audit_b1.json` |
| Ciblé : insertion disponible | 32 | 0 | `audit_b1_insertion_disponible.json` |
| Ciblé : alternance existante (résumé au-delà de 5 établissements : nombre et places vérifiés) | 30 | 0 | `audit_b1_alternance_existe.json` |
| Ciblé : coût Onisep | 45 | 0 | `audit_b1_cout_onisep.json` |
| Relecture à la main de 30 coûts Onisep | 30 | 0 (30 conformes) | `relecture_30_couts.md` |

Les tirages ciblés complètent le tirage au hasard, qui ne contenait que 5 insertions disponibles.

**Contrôle positif** (`--sabotage cout|alternance|insertion`, altération de +1 en mémoire, sorties
suffixées) : l'audit échoue à chaque fois, et chaque valeur sabotée est retrouvée. 35 / 35 coûts
disponibles du tirage au hasard (42 / 42 avec les 7 formations en apprentissage), 45 / 45 coûts Onisep, 32 / 32 insertions, 30 / 30 alternances,
9 et 5 sur le tirage au hasard (toutes les fiches qui portaient une valeur à saboter).

Défauts trouvés en chemin et corrigés (ils sont la raison d'être de l'audit, il faut les dire) :
- la règle « même famille » donnait à un IFSI le coût du diplôme de puéricultrice, et à un bachelor
  celui du diplôme d'ingénieur de l'école : réservée aux CPGE et BTS (tarif du lycée) ;
- une CPGE PCSI rattachée à une ligne PSI, un BTS CIEL option B à la ligne de l'option A ;
- les taux InserSup étaient arrondis au dixième (44,83 écrit 44,8) : publiés tels quels ;
- le taux d'emploi stable (sans définition publiée, et supérieur au taux d'emploi) était écrit avec
  une définition que j'avais inventée : retiré du texte ;
- deux leviers de sabotage ne touchaient pas toutes leurs cibles (fourchette de coût, ligne
  InserJeunes toute non diffusée) : un audit resté vert là ne prouvait rien, corrigés avant de conclure ;
- l'audit interrogeait l'API InserSup avec `promo="2023,2024"`, forme du CSV ; l'API porte une liste :
  3 faux écarts, requête corrigée.

## Tests

`tests/test_etape_b1.py` : 83 tests sur des lignes réelles extraites des bruts (`tests/fixtures/etape_b/`,
rejouable par `extraire.py`), dont les falsifications des contrôles. Suite complète, exécutée comme
la CI (`OFFLINE_JUDGE_TESTS=1`, sans clés) : 3 433 passés, 48 ignorés. Sans ces réglages, un test du
juge appelle un vrai modèle et échoue de façon non déterministe (hors de ce lot).

## Points ouverts (réponses de Jarvis et Matteo du 23/09 entre crochets)

1. **IFSI et droits d'inscription** : le tableau ministériel liste le « Diplôme d'État d'infirmier »
   dans le groupe du cycle de licence (178 euros). Le texte ne dit rien des droits d'un IFSI (règle Q3 :
   seulement la ligne Onisep, « 0 euros » de coût de scolarité), avec la réserve écrite. À préciser
   avec une source sur l'inscription universitaire des étudiants en IFSI avant de l'écrire.
   [Recherche courte faite, contradiction entre deux sources primaires : réserve gardée.]
2. **LAS et insertion** : non disponible par choix du contrat (une LAS ouvre l'accès aux études de
   santé). InserSup a des lignes « licence Droit » ou « licence Biologie » pour la plupart de leurs
   universités ; on pourrait les montrer comme l'insertion de la majeure, dit tel quel. Non fait sans
   accord. [Matteo : non disponible. Le chiffre utile est le passage en MMOPK, pour B-2, seulement
   quand l'université le publie elle-même.]
3. **Écoles d'ingénieurs** : 36 fiches des 3 domaines sans insertion parce que l'école a plusieurs
   diplômes d'ingénieur dans InserSup. Les relier par spécialité demande une table écrite à la main.
   [Jarvis : non disponible en B-1, table plus tard si la démo en a besoin.]
4. **Explorateur** : les fiches d'apprentissage n'ont ni `debouches` ni `historique` : elles
   apparaissent en `no_debouches` et `hist_court` dans l'explorateur, attendu.

## Hors périmètre (réduit par Matteo le 23/09)

B4 Cartographie 2026, B6 spécialités, B7 fiches Parcoursup, B8 suite d'études, B3 bis insertion ARS.
B-2 (santé : taux nationaux SIES, capacités MMOPK, fiche réforme 2027) attend la validation de B-1
par Matteo dans l'explorateur.

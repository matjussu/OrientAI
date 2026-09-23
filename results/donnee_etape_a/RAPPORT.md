# Étape A de la donnée verticale : corriger ce qui existe

Claudette, 23/09/2026. Ordre `2026-09-23-0958-claudette-orientai-donnee-etape-a-corriger`.
Spécification : `~/projets/_orientai-ref/verticale-2026-09/CAHIER-DES-CHARGES-donnee.md`, sections 2, 3 et 7.

Aucun appel LLM, aucun ré-embedding, coût API nul, aucun déploiement. Le corpus de la prod
(`data/processed/formations.json`, sha256 `2e4276e6155b`) n'est pas modifié : le nouveau
corpus est écrit à part.

## Livrable

| | |
|---|---|
| Nouveau corpus | `data/processed/formations_etape_a.json` (hors git), 53 281 fiches |
| sha256 | `f0aeeb308c45827affa01942c579c206a88372054fab47842667e667cc5e0fc7` |
| Commande | `python -m src.collect.corpus_etape_a --reference <formations.json de la prod>` |
| Déterminisme | deux constructions sur les mêmes bruts donnent le même fichier, octet pour octet (vérifié le 23/09) |
| Sources brutes | `data/raw/` (hors git), empreintes dans `data/reference/sources_officielles.json` ; `python -m src.collect.sources_officielles --telecharger` les rapatrie, le pipeline refuse un fichier dont l'empreinte a changé |
| Manifeste | `manifest_corpus.json` (ce dossier) |

`fiche_to_text(fiche) -> str` garde sa signature et reste le point d'entrée unique. Un seul
import nouveau : `src.rag.texte_parcoursup`, sans dépendance externe (le stub `mistralai`
d'`export_data.py` suffit toujours, vérifié en rejouant ce script sur ce corpus).

## Mesures avant / après

Toutes rejouables. « Avant » = corpus de la prod + `fiche_to_text` de main (`89e0f27`), chargé
depuis git par `--revision-texte origin/main`. « Après » = corpus de l'étape A + code de la branche.

### 1. Contrôles du texte, toutes les fiches Parcoursup

`python -m src.eval.donnee.controles --corpus <corpus> [--revision-texte origin/main]`,
traces `controles_avant.json` et `controles_apres.json`.

| Défaut | Avant (13 011 fiches) | Après (14 252 fiches) |
|---|---|---|
| taux d'accès écrit sans définition | 12 996 | 0 |
| session non dite | 12 996 | 0 |
| répartition des candidats appelée « taux d'accès par profil » | 12 901 | 0 |
| « même académie » appelée « Île-de-France » hors Île-de-France | 10 255 | 0 |
| insertion InserSup attribuée à « Inserjeunes CFA » | 3 509 | 0 |
| ville non normalisée | 1 444 | 0 |
| type de formation non dit | 570 | 0 |
| option PASS non dite | 42 | 0 |

Sur les trois domaines de la démo, l'explorateur de Jarvis rejoué à l'identique (copie de
`export_data.py` pointée sur ce corpus) retrouve ses chiffres de départ (2 092, 1 652, 323, 332,
803, 221) et donne 0 pour les quatre contrôles « texte » et pour `ville_non_norm`.

### 2. Banc vertical : chiffres attendus présents dans le texte de leur fiche

`python -m src.eval.donnee.banc_textes --banc battery_verticale.json --corpus <corpus>`,
traces `banc_textes_avant.json` et `banc_textes_apres.json`. Comparaison typée (% à ±0,51,
effectifs exacts), témoin de hasard = même contrôle contre la fiche d'une autre question.

| | Avant | Après |
|---|---|---|
| chiffres présents | 317 / 341 (92,96 %) | 336 / 341 (98,53 %) |
| témoin de hasard | 5,57 % | 6,45 % |
| informatique / santé / maths | 136/148, 112/119, 69/74 | 145/148, 119/119, 72/74 |

Gagnés : candidats (7), candidats en phase principale (3), propositions (3), historique 2023-2024
(4), candidats classés (1), une part de bac technologique (1). Les 5 absents restants sont tous la
capacité d'accueil de masters MonMaster, que le texte MonMaster ne rend pas (hors Parcoursup,
point 7 ci-dessous).

### 3. Audit d'exactitude, 50 fiches contre l'API officielle

`python -m src.eval.donnee.audit_officiel --corpus <corpus>`, trace `audit_officiel.json`.
Témoin : l'API publique `fr-esr-parcoursup` interrogée au moment de l'audit, pas le fichier
brut du pipeline. Tirage à graine fixe (20260923) : 17 informatique, 16 santé, 17 maths.

- Données (taux, places, candidats, établissement, ville) : **0 écart non expliqué**. 9 écarts
  expliqués, tous sur la ville : 8 arrondissements ramenés à la commune, 1 libellé du COG INSEE.
- Texte : les 150 valeurs officielles (taux, places, candidats) figurent dans le texte des 50 fiches.
- **Contrôle positif** (l'audit sait échouer) : le même tirage avec le texte de main donne 50
  valeurs officielles absentes (le nombre de candidats n'y était jamais écrit), trace
  `audit_officiel_controle_positif_texte_main.json`.

## Ce qui a été fait, par point de l'ordre

- **A1 texte** (`src/rag/texte_parcoursup.py`, `src/rag/embeddings.py`). Répartitions nommées
  selon le libellé officiel. `part_acces_*` est une répartition des candidats appelables et pas
  un taux par profil : ses trois parts somment entre 98 et 102 sur 99,2 % des 14 252 lignes.
  « X % des admis néo-bacheliers viennent de la même académie (académie de Y) », avec en
  Île-de-France la mention que les trois académies sont comptées ensemble. InserSup nommé,
  avec sa promotion, sa portée (médiane régionale, pas un chiffre propre à la formation) et sa
  définition officielle. Type en clair, option PASS, majeure LAS, voie de CPGE, sélectivité,
  évolution 2023-2025, lien de la fiche, « Parcoursup, session 2025 » et la source.
  Deux champs officiels jamais ingérés ont été ajoutés : les mentions « très bien avec
  félicitations » et « non renseignée ». Sans eux, la répartition par mention ne sommait à 100
  que sur 89,6 % des lignes ; avec eux, sur 100 %. L'effectif d'admis (`acc_tot`) est aussi ajouté.
- **A1 bis définitions** : chaque indicateur écrit porte sa définition. Pour le taux d'accès,
  c'est la description officielle, mot pour mot. Pour les autres indicateurs, ce sont les
  libellés officiels des champs (métadonnées de l'API lues le 23/09).
- **A2 domaines** : table `data/reference/domaines_parcoursup.csv`, 19 règles numérotées, et
  chaque fiche porte `domaine_regle`. Les 49 BUT Informatique sont classés informatique, les
  30 R&T informatique, les 15 Science des données en `data_ia`, les 53 GEII en ingénierie
  industrielle (décision Jarvis du 23/09), et les BUT Info-com restent hors informatique.
  Au total, 1 051 fiches existantes changent de domaine, toutes par une règle de la table
  (`domaines_changements.json`).
- **A3 villes** : COG INSEE 2025. 14 225 lignes sur 14 252 ont leur code commune. Les 27
  restantes : 22 lignes en département « 99 » (étranger, dont une Papeete mal codée à la source)
  et 5 lignes dont le libellé ne correspond à aucune commune : « Marne-la-Vallée » (qui n'est pas
  une commune), « Taiarapu-o » (Taiarapu-Est ou Taiarapu-Ouest, ambigu) et « Moorea »
  (Moorea-Maiao au COG). Elles restent sans code, rien n'est deviné. 1 666 arrondissements sont ramenés à Paris, Lyon ou Marseille, avec l'arrondissement
  gardé à part.
- **A4 couverture** : cause mesurée. Les 1 241 lignes absentes partagent toutes leur clé
  (intitulé, établissement, ville) avec une ligne gardée ; le dédoublonnage de
  `run_merge_v3.stage_dedup` les avait fusionnées. Réingestion par `cod_aff_form` : 14 252 / 14 252.
  PASS : 43 fiches avant, 287 après, dont les 13 options de Lille, toutes nommées grâce au jeu
  « Cartographie des formations Parcoursup » 2025 (même producteur, jointure exacte, 14 214
  lignes sur 14 252 couvertes). LAS : 286 fiches avant, 513 après. Chaque fiche créée hérite de
  sa fiche sœur les débouchés, l'insertion et le domaine, et cet héritage est tracé dans
  `provenance.herite_de`.

## À signaler

1. **Longueur du texte : médiane de 711 à 2 981 caractères.** Le bloc « Définitions » est
   identique d'une fiche à l'autre. Tant que `fiche_to_text` sert aussi à l'embedding, ce bloc
   rapprochera les vecteurs des fiches entre eux. **Ne pas ré-embedder avec ce texte sans
   mesurer le recall** ; proposition pour l'étape D ou le lot retrieval : un texte d'embedding
   distinct du texte lu par le modèle.
2. **MonMaster : 7 369 textes modifiés sur 7 573.** La seule différence est l'insertion
   InserSup, qui était étiquetée « Insertion apprentissage (Inserjeunes CFA, cumul récent) » ;
   les valeurs sont inchangées (vérifié segment par segment, `mesures_complementaires.txt`).
   C'est une correction, pas une régression.
3. **`domaine_incoherent` dans l'explorateur : 142 après, contre 803 avant.** 112 viennent des
   motifs de l'explorateur : « numérique » hors informatique (design, arts, BTS géomètre : 69),
   « math » pris dans la condition d'entrée « spécialité Maths en Terminale » des écoles
   d'ingénieurs (35), `PASS` sans casse qui attrape Passerelle, Passeport et Passau (8). 23 sont
   des écoles d'ingénieurs généralistes, classées ingénierie par choix (règle I07). 7 sont des
   cas ambigus laissés en l'état : bachelors « ingénierie et numérique », « Ingénieur du
   numérique » ESIEE-IT, CMI Mathématiques-statistique des données (classé `data_ia`), DN MADE.
4. **53 fiches hors des trois domaines** changeraient de domaine, toutes vers `social`, si l'on
   rejouait le classement historique du code : la règle du 11/06 (commit `ab9621a`) n'est pas
   reflétée dans le corpus de la prod, qui date pourtant du 14/06 (cause non établie). Je ne
   l'ai pas appliquée, pour rester dans le périmètre : hors table, une fiche garde son domaine
   (`domaine_regle = "anterieur"`).
5. **Développé des voies de CPGE** (« MPSI : mathématiques, physique et sciences de
   l'ingénieur »...) : écrit de mémoire, non relu contre les arrêtés de programme. C'est marqué
   dans le code, à vérifier avant l'étape D.
6. `fact_card.py` (le texte que lit le générateur en prod) n'avait pas les défauts de libellé de
   `fiche_to_text`. Seul ajout : les libellés des deux nouvelles mentions.
7. **MonMaster : la capacité d'accueil n'est pas dans le texte.** Ce sont les 5 chiffres
   attendus du banc encore absents. Hors du périmètre Parcoursup de l'étape A ; à traiter avec
   B8 (suite d'études, MonMaster).

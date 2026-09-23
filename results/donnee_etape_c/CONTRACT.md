# Contrat de l'étape C : la base structurée

**Version 0.1** (23/09, après relecture de Jarvis) :
- bornes des filtres écrites, inclusif ou strict (section 8) ;
- liste exacte des voies de CPGE qui entrent par la règle M01, avec un défaut de la table A trouvé
  en la mesurant (section 2).

Version 0, 23/09/2026, Claudette (ordre 2026-09-23-1358, phase 1 : le contrat seul, aucun code de
construction). Ce document fixe l'architecture **avant** le code. La phase 2, un ordre séparé, le
construit tel quel : toute question qu'elle rouvre passe par une nouvelle version de ce fichier,
annoncée à Jarvis.

Cahier des charges : `~/projets/_orientai-ref/verticale-2026-09/CAHIER-DES-CHARGES-donnee.md` §5
(zone de Jarvis, non modifié). Requêtes du gate : `~/projets/_orientai-ref/verticale-2026-09/gate_c/requetes_gate_c.json`,
v2, sha256 `227a2c9bfaf6` (zone de Jarvis, lu seulement).

**Toutes les mesures citées** viennent de `mesures_contrat/mesures_contrat.py` (lecture seule,
rejouable) et de sa sortie `mesures_contrat/mesures_contrat.json`, sur le corpus B-2 sha256
`2e6a93a5cda6`, le 23/09/2026, sauf mention contraire. Les chiffres des moteurs viennent de deux
prototypes jetables gardés comme trace (`mesures_contrat/prototype_jetable_*.py`,
`sorties_prototypes.txt`) : ils ne sont pas le code de la phase 2.

## 0. En bref (ce que Matteo valide)

1. **Une base SQLite**, un seul fichier, dérivé par une commande déterministe, jamais édité à la
   main. Elle contient 3 470 formations post-bac (Parcoursup + apprentissage) des trois domaines,
   plus les masters informatique et maths (section 2).
2. **Chaque chiffre est une ligne** avec sa source, son millésime, l'identifiant de la ligne dans la
   source et sa portée. Un chiffre absent est une ligne « non disponible » avec sa raison, jamais un
   trou (sections 4 et 6).
3. **La distance est à vol d'oiseau**, entre la localisation officielle de la formation et le
   centre de la commune demandée (section 5).
4. **Le modèle interroge la base par des fonctions à filtres fermés**, pas en SQL libre. Les 20
   requêtes du gate s'écrivent toutes avec ces filtres (section 8).
5. **Matteo a la main** : une section « la base en clair » (section 7), un export que l'explorateur
   de Jarvis charge sur iPhone (section 9), le fichier SQLite ouvrable dans un logiciel gratuit, et
   chaque requête du gate rejouée et affichée côte à côte (section 10).
6. **Six questions ouvertes** pour Matteo, courtes, chacune avec une option recommandée
   (section 12).

## 1. Source et dérivation

### Entrées

| Entrée | Rôle | Empreinte |
|---|---|---|
| `data/processed/formations_etape_b2.json` | fiches, domaines (table A), coût, alternance, insertion, santé, commune INSEE | sha256 `2e6a93a5cda6` |
| Bruts verrouillés Parcoursup 2025 et apprentissage 2025 (`data/reference/sources_officielles.json`) | coordonnées GPS, absentes du corpus ; chiffres d'admission seulement si Q6 = A | sha du verrou |
| `data/reference/domaines_parcoursup.csv` (table A, 20 règles relues) | périmètre des lignes | sha du fichier |
| **Nouveau** `data/reference/types_etape_c.csv` | type court des formations (section 4.3) | sha du fichier |
| **Nouveau** `data/reference/champs_etape_c.csv` | catalogue des champs : libellé clair, définition, unité, source attendue, ce que le champ ne dit pas (section 7) | sha du fichier |
| **Nouveau au verrou** : communes de geo.api.gouv.fr | centre des communes pour la distance | sha au verrou |
| **Nouveau au verrou si Matteo dit oui (Q1)** : MonMaster 2025 (jeu `fr-esr-mon_master`) | masters | sha au verrou |

### Les chiffres officiels : lus dans le corpus ou dans les bruts (Q6, Matteo tranche)

Tous les chiffres viennent du corpus B-2, comme le dit l'ordre, **sauf les coordonnées GPS**, que le
corpus ne porte pas et qui sont lues dans les bruts verrouillés. Une variante reste ouverte :

- **B (recommandé), corpus d'abord** :
  - chiffres lus dans le corpus B-2 ;
  - bruts lus pour les coordonnées, et par l'audit comme témoin indépendant (section 11.2).

  Un seul chemin de construction. L'identifiant de la ligne dans la source reste exact : le corpus
  garde `cod_aff_form`, qui est la clé de la ligne du CSV officiel.
- **A, bruts d'abord** : les chiffres publiés tels quels (admission, places, vœux, profil) sont lus
  dans le brut verrouillé, et le corpus ne sert que pour ce que A et B ont calculé (domaine, type,
  commune, coût, alternance, insertion, santé).
  - Intérêt : des champs que le corpus n'a pas deviennent possibles, comme les effectifs d'admis par
    type de bac (`acc_bp` : le corpus n'a que les parts en %).
  - Coût : deux chemins de construction, à comparer entre eux à chaque passage.

Mesure qui rend les deux options sûres : là où corpus et brut se recoupent, ils sont identiques. Sur
`admission_2025_contre_brut` : 0 écart sur 14 237 taux d'accès, 14 252 capacités et 14 252 vœux
totaux.

Ma première proposition à Jarvis était A, parce que la requête C03 demandait `acc_bp`. Le gate v2
l'a remplacé par `pct_bp`, qui est dans le corpus : aucune requête n'a plus besoin de A. Je
recommande donc B, le plus simple, et A si la démo demande des effectifs.

### Sortie et commande

- `data/processed/base_etape_c.sqlite` (hors git), `data/processed/base_etape_c.manifest.json`
  (hors git), copie du manifeste dans `results/donnee_etape_c/manifest_base.json` (dans git).
- Commande : `python -m src.collect.base_etape_c`. Branchée dans `src.collect.pipeline_donnee`
  comme étape 5, après B-2. Les contrôles d'empreinte du verrou s'appliquent aussi aux deux
  nouvelles sources, et une empreinte divergente arrête tout avant la première écriture.
- Le manifeste porte :
  - la commande et la date ;
  - le sha256 de chaque entrée (corpus, verrou, les trois tables de référence) ;
  - le sha256 du fichier SQLite ;
  - une **empreinte canonique** : sha256 des lignes de chaque table triées par clé, sérialisées en
    JSON ;
  - le nombre de lignes par table et le sha256 de chaque export.
- **Déterminisme** : deux exécutions doivent rendre la même empreinte canonique (contrôle de la
  phase 2). Que le fichier SQLite soit lui-même identique octet pour octet d'une exécution à l'autre
  est **supposé, à mesurer** : le contrôle porte sur l'empreinte canonique, et le sha du fichier est
  seulement noté.
- La base est jetable : on la reconstruit, on ne la corrige pas. Une valeur fausse se corrige en
  amont (brut, table de référence ou étape A/B) puis on rejoue.

## 2. Périmètre des lignes

### Ce qui entre

**Règle** : une fiche Parcoursup ou apprentissage entre si son domaine (table A) est
`informatique`, `cyber`, `data_ia` ou `sante`, ou si son domaine est `sciences_fondamentales`
**par les règles de maths** M01 (CPGE scientifique), M02 (CUPGE sciences) ou M03 (licence de
mathématiques).

| Espace | Fiches | Détail |
|---|---|---|
| Parcoursup 2025 | 2 944 | |
| Apprentissage 2025 | 526 | toutes les fiches d'apprentissage du corpus |
| **Total post-bac** | **3 470** | santé 1 512, informatique 1 276, maths 574, cyber 64, data/IA 44 |
| Masters (Q1) | 480 si le brut MonMaster est verrouillé, 405 si on garde le corpus | secteurs Informatique, Mathématiques, Mathématique et informatique, Mathématiques appliquées et sciences sociales |
| Fiche concept | 1 | `concept:reforme_sante_2027` (table `concept`, section 4) |

**Ce qui entre par les règles de maths** (mesure du 23/09 sur le corpus B-2) :
- M01, 449 fiches :
  - PCSI 138, MPSI 124, PTSI 67, TSI 48, TPC 5 ;
  - BCPST 54 et TB 8 (voies à dominante biologie, Q2) ;
  - **5 fiches « École normale supérieure Paris-Saclay, arts et design »**, classées là par erreur :
    la règle M01 vise la filière « classe préparatoire scientifique », et Parcoursup y range aussi
    cette préparation. C'est un défaut de la table A, à corriger dans la table (ajouter une
    exclusion), pas dans C. Tant qu'il n'est pas corrigé, la phase 2 les exclut par une règle écrite
    et comptée.
- MP2I (41 fiches) n'est pas dans M01 : la voie entre par la règle informatique I10, et elle est donc
  bien dans le périmètre.
- M02, 19 fiches : CUPGE et cycles préparatoires universitaires scientifiques. Deux sont orientés
  concours Agro-Véto (biologie).
- M03, 106 fiches : licences de mathématiques.

Par filière Parcoursup : BTS 985, LAS 513, CPGE 490, autres formations 394 (diplômes d'État de
santé, titres professionnels, écoles), IFSI 344, PASS 287, licence 284, BUT 131, école
d'ingénieurs 40, école de commerce 2.

Les chiffres nationaux de santé (SIES, Note Flash n°31) ne forment pas une ligne à part. Ils sont
portés par chaque fiche PASS et LAS avec `portee = nationale`, comme dans le corpus B-2, et comme
la requête C15 les attend.

**Contrôle de couverture, avec témoin** : les 105 attendus et 2 fiches de frontière des 20 requêtes
du gate (v2) sont tous dans ce périmètre (0 hors périmètre, 0 hors corpus). Le même contrôle appliqué au
classement par mots-clés de l'explorateur (2 912 fiches) en trouve 13 dehors : PCSI, TSI, DTS
imagerie (`temoin_perimetre_explorateur`). Ce classement ne sert donc pas de périmètre.

### Ce qui reste dehors, et pourquoi

| Reste dehors | Fiches | Raison |
|---|---|---|
| `sciences_fondamentales` hors règles de maths | 630 | licences de biologie, chimie, physique, prépas ECG, BTS environnement : ce n'est pas « maths porte d'entrée » (le cahier des charges exclut ECG) |
| Autres domaines Parcoursup | 10 681 | hors verticale ; l'élargissement se fait en changeant la règle, sans autre code |
| RNCP, Onisep, InserJeunes, La bonne alternance, ROME, DARES, etc. | 38 990 lignes au total | ce sont des documents de contexte du RAG, pas des formations du périmètre |
| Masters hors info et maths, dont info-com (235 masters en 2025) | | hors verticale ; info-com exclue comme en post-bac |
| Débouchés (métiers ROME reliés), 1 341 fiches du périmètre | | Q4 : leur source n'est pas verrouillée et 532 fiches du périmètre héritent de champs d'une autre fiche (`provenance.herite_de`) |
| Ancien champ `insertion_pro` (494 fiches du périmètre) | | remplacé par `insertion` de B-1, qui n'écrit plus l'ancienne insertion discipline x région |

**À trancher par Matteo (Q3)** : 167 fiches santé du périmètre ne sont classées par aucune règle
explicite de la table A, mais par l'ancien classement (`anterieur`). Ce sont des BTS diététique (38),
biologie médicale (36), opticien-lunetier (30), prothésiste dentaire (7), des BUT génie biologique
(30), etc. Je les garde : elles sont paramédicales, et le cahier des charges met le paramédical dans
le périmètre.

## 3. Moteur : SQLite, argumenté et mesuré

| Critère | SQLite | DuckDB | Trace |
|---|---|---|---|
| Dépendance sur Railway | aucune, module standard de Python | paquet de 59 Mo installé | `du -sh` sur l'installation |
| Import dans un processus neuf | 118 ms | 545 ms | `sorties_prototypes.txt` |
| Requête « distance + filtres » sur 2 912 lignes | 0,46 ms | 5,0 ms | idem, 100 répétitions |
| Fichier (prototype à 18 colonnes, provenance non normalisée) | 4,7 Mo | 1,3 Mo | idem |
| Moteur WASM pour un navigateur | sql.js 0,66 Mo (0,32 Mo compressé) | duckdb-wasm 35,7 Mo (7,1 Mo compressé) | curl sur jsdelivr |
| Ouvrable par Matteo sans rien coder | oui (DB Browser for SQLite, gratuit, Windows et Mac) | non | |

**Choix : SQLite.**
- La base est petite, de l'ordre de 4 000 formations. DuckDB est fait pour l'analyse de gros
  volumes, et il est ici plus lent en requête ponctuelle (5,0 ms contre 0,46 ms mesurés).
- SQLite n'ajoute aucune dépendance au service Python de Railway.
- Sa seule faiblesse mesurée est la taille de fichier (4,7 contre 1,3 Mo). Elle est sans effet à
  cette échelle.

**Le navigateur ne lit pas la base** : il lit un export JSON (section 9). L'explorateur charge déjà
un `data_b2.json` de 21,3 Mo. L'export d'une base « une ligne par chiffre » fait 9,1 Mo, 0,45 Mo
compressé, et se lit en 111 ms (prototype de taille). Sans WASM, l'explorateur n'a aucun moteur
à charger ; sql.js reste possible plus tard (0,66 Mo) si Jarvis veut du SQL dans la page.

## 4. Schéma

### 4.1 Tables

```
source(source_id PK, libelle, producteur, url_telechargement, url_page, licence, collecte, sha256, lignes)
champ(champ PK, libelle_clair, definition, unite, type_valeur, portee_par_defaut, s_applique_a,
      source_attendue, ne_dit_pas)                        -- copie de champs_etape_c.csv
formation(id PK, espace, identifiant_source, intitule, etablissement, uai, statut, statut_detaille,
          type, type_libelle, filiere, specialite, apprentissage, selectivite, domaine, domaine_regle,
          lien_officiel, derniere_session)
lieu(id, rang, commune, code_insee, arrondissement, code_departement, departement, region, academie,
     lat, lon, precision_geo, source_id)                  PK(id, rang)
valeur(id, champ, session, valeur_num, valeur_texte, unite, statut, raison, source_id, millesime,
       identifiant_source, rattachement, portee)          PK(id, champ, session)
insertion_ligne(id, rang, dispositif, promotion, regime, perimetre, granularite, diplome,
                effectif_sortants, taux_emploi_6m, taux_emploi_12m, taux_emploi_18m,
                taux_emploi_24m, taux_poursuite_etudes, non_diffuse, source_id)   PK(id, rang)
alternance_lien(id, id_apprentissage, rattachee_par, cfa_partenaire, capacite, precision)
concept(concept_id PK, titre, texte, statut_reglementaire, verifie_le, sources_json)
v_formation (vue)  -- une ligne par formation, colonnes session 2025 + historique, pour filtrer
```

`id` est l'identifiant typé convenu avec Jarvis : `psup:<cod_aff_form>`, `psup_app:<cod_aff_form>`,
`mm:<ifc>`. Mesure : 0 doublon d'identifiant dans le corpus, 0 `cod_aff_form` commun entre
Parcoursup et apprentissage. Rien ne garantit la seconde, puisque ce sont deux jeux distincts :
c'est pour cela que l'espace est dans l'identifiant.

### 4.2 Une ligne par chiffre, une vue pour filtrer

La table `valeur` porte **chaque chiffre avec sa provenance** : c'est la source de vérité. La vue
`v_formation` l'aplatit (taux d'accès 2025, places, vœux, parts de bac, etc.), et les outils
filtrent sur la vue. Ce choix donne deux choses :
- la provenance est par cellule, pas par colonne : un coût venant d'Onisep et un coût venant du
  Code du travail ne se confondent pas ;
- un champ ajouté plus tard est une ligne de catalogue de plus, sans migration de schéma.

Contraintes écrites en SQL (`CHECK`), donc structurelles : une ligne `disponible` a une valeur, une
ligne `non_disponible` n'en a pas et porte une raison ; `statut` ne prend que ces deux valeurs ;
`portee` prend ses valeurs dans une liste fermée ; `source_id` est une clé étrangère vers `source`.

### 4.3 Colonnes descriptives de `formation`

- `type` : type court, en liste fermée, dérivé de `type_formation` (étape A) par la table
  `types_etape_c.csv`. Valeurs : `pass`, `las`, `licence`, `but`, `bts`, `cpge`, `cupge`, `ifsi`,
  `diplome_sante` (D.E, certificats de capacité, DTS), `ecole_ingenieur`, `titre_pro`, `master`,
  `autre`. Le périmètre compte aujourd'hui 72 libellés `type_formation` distincts, à ranger chacun
  dans une de ces cases ; la table est relue par Matteo dans l'explorateur.
- `filiere` : `fil_lib_voe_acc` officiel, sans le suffixe « - en apprentissage » (137 valeurs
  distinctes). Le suffixe devient la colonne `apprentissage` (0/1). Mesures :
  - `filiere_detaillee` = `fil_lib_voe_acc` du brut sur 14 252 fiches sur 14 252 ;
  - le suffixe n'apparaît que sur des fiches d'apprentissage (525 sur 526).
- `specialite` : `precision_formation` (voie de CPGE, mention, majeure de LAS).
- `statut` : Public ou Privé tel que publié, et `statut_detaille` quand la source le donne.

### 4.4 Historique 2023-2025

Oui, dans la base : `valeur.session` vaut 2023, 2024 ou 2025, lu dans `admission.historique` du
corpus (ou dans les trois bruts verrouillés si Q6 = A ; l'audit les relit dans les deux cas).
Dans le périmètre : 2 698 fiches ont 3 sessions, 126 en ont 2, 120 en ont 1 ; les 526 fiches
d'apprentissage n'ont que 2025. **Une session où la formation n'existe pas** dans le jeu est une
ligne `non_disponible`, avec la raison « formation absente du jeu Parcoursup 2023 ». Ce n'est pas
un trou.

### 4.5 Santé et sa portée

Les quatre sous-champs de B-2 deviennent des lignes de `valeur` :
- `passage_mmopk_*_national` (national, SIES) : `portee = nationale`, sur chaque fiche PASS et LAS ;
- `capacites_mmopk_*` publiées par l'université : `portee = universite` ;
- `passage_mmopk_universite` : 0 disponible, raison gardée ;
- `reforme_2027` : lien vers `concept:reforme_sante_2027`.

Une fonction qui rend un taux de santé rend **toujours** sa portée, et le texte qu'écrit le modèle
doit la dire. C'est ce que vérifie la requête C15.

### 4.6 Masters

- Si Q1 = oui (recommandé) : lignes dérivées du brut MonMaster 2025 verrouillé. 480 masters info et
  maths ; les champs officiels gardent leur nom officiel dans `identifiant_source` (`col`,
  `n_can_pp`, `alternance`...).
- Si Q1 = non : les 405 masters du corpus, sans le moindre écart de valeur avec le jeu officiel sur
  capacité, candidats et alternance. Il en manque 75, et 542 masters du corpus sont de la session
  2024. Leur lien est une recherche Onisep (`url_type = fallback_search` sur les 7 573), pas une page
  MonMaster.
- Dans les deux cas, le taux d'admission calculé du corpus (`taux_admission`, une fraction) **n'entre
  pas** : ce n'est pas un chiffre publié.
- Un master a souvent plusieurs lieux d'enseignement (champ `lieux` du jeu officiel). D'où la table
  `lieu` à plusieurs rangs.

## 5. Géographie

| Colonne | Source | Ce que le corpus porte déjà |
|---|---|---|
| `code_insee`, `commune`, `arrondissement` | COG INSEE 2025 (verrouillé), résolution de l'étape A (`src.collect.communes`) | oui pour les fiches Parcoursup. **Non pour 442 fiches d'apprentissage sur 526** (défaut de B-1, ci-dessous) |
| `code_departement`, `departement`, `region`, `academie` | brut Parcoursup | oui |
| `lat`, `lon` | `g_olocalisation_des_formations` du brut Parcoursup 2025 et du brut apprentissage 2025, tous deux verrouillés | non, le corpus n'a aucune coordonnée |
| centre d'une commune (pour « près de ») | geo.api.gouv.fr, API Découpage administratif, champ `centre` (34 969 communes, Rennes 35238 = -1.6884, 48.1159, lu le 23/09) | non : nouvelle source au verrou |
| coordonnées d'un master | centre de sa commune, `precision_geo = commune` | non |

**Défaut de B-1 trouvé en passant** : les fiches d'apprentissage écrivent leur département sur trois
chiffres (« 044 », 442 fiches sur 442 sans INSEE), et le résolveur de communes n'attend qu'un ou
deux chiffres. La base normalise « 0NN » en « NN » avant la résolution, et la règle est écrite dans
`rattachement`. La correction dans B-1 elle-même est une dette (section 13), pour ne pas changer le
corpus de référence de C.

**Mesures géo** :
- coordonnées présentes sur 14 214 fiches Parcoursup 2025 sur 14 252, et identiques à la
  Cartographie Parcoursup sur les 14 214 (écart maximal 0,0 km) ;
- 516 fiches d'apprentissage sur 526 ont les leurs ;
- 12 fiches du périmètre sont sans coordonnées. Leur `lieu` porte `precision_geo = commune` (centre
  de la commune), ou `non_disponible` si la commune n'est pas résolue. Une fiche sans coordonnées
  n'est jamais placée à 0 km.

**Distance** : haversine, rayon terrestre 6 371 km, du `lieu` de la formation au centre de la
commune de référence. Pour un master à plusieurs lieux, on prend le plus proche. La réponse dit
« à vol d'oiseau » (Q5).

**Cas-test « BUT informatique à moins de 50 km de Rennes avec un taux d'accès supérieur à
50 % »** : la bonne réponse est **vide**. Sur les 49 BUT Informatique, aucun n'est à moins de 50 km
de Rennes. Les trois plus proches sont Laval à 69,2 km (39 %), Vannes à 96,6 km (45 %) et Nantes à
99,9 km (30 %). La base doit rendre 0 résultat, et l'outil doit laisser le modèle élargir le rayon
lui-même, sans inventer une formation voisine.

**Homonymes** : 1 441 noms de communes sont portés par plusieurs communes (Saint-Denis : 4, dont
La Réunion et la Seine-Saint-Denis). Les filtres prennent donc un **code INSEE**, jamais un nom. Un
outil `trouver_commune` rend les candidats, et le modèle choisit ou demande (section 8).

## 6. « Non disponible » contre vide

| Cas | Dans la base |
|---|---|
| La source publie une valeur (y compris 0) | ligne `disponible`, valeur, source |
| La source a été lue et ne publie rien pour cette formation | ligne `non_disponible`, raison, `source_id` de la source lue |
| Aucune source n'existe pour ce type de formation (insertion d'une LAS) | ligne `non_disponible`, raison, `source_id` nul |
| La formation n'existe pas à cette session | ligne `non_disponible`, raison « formation absente du jeu <session> » |
| Champ qui ne s'applique pas (taux d'accès d'une formation en apprentissage) | pas de ligne : le catalogue (`s_applique_a`) dit que le champ ne s'applique pas à cet espace |

**Règle de contrôle** : pour chaque formation et chaque champ du catalogue qui s'y applique, il y a
exactement une ligne par session concernée. Une ligne manquante est un défaut de construction, pas
une donnée absente. Aucun NULL sans raison n'existe dans `valeur`.

## 7. La base en clair (pour Matteo)

Ce tableau est la version lisible du catalogue `champs_etape_c.csv`, qui fait foi et que la base
recopie dans sa table `champ`. Chaque ligne dit ce que le chiffre veut dire, d'où il vient et ce
qu'il **ne** dit **pas**. Les libellés officiels sont ceux du jeu `fr-esr-parcoursup`, lus sur l'API
le 23/09/2026.

### Qui est la formation

| Colonne | Ce qu'elle dit | D'où | Ce qu'elle ne dit pas |
|---|---|---|---|
| Intitulé, établissement | le nom officiel de la formation et de l'établissement | Parcoursup 2025 | la qualité de la formation |
| Type | licence, LAS, PASS, BUT, BTS, CPGE, IFSI, diplôme de santé, école, master | table relue de l'étape A, puis table C | le niveau de sortie : une CPGE ne donne pas de diplôme |
| Filière | la spécialité telle que Parcoursup la nomme (« Informatique », « MPSI », « D.E Ergothérapeute ») | Parcoursup, `fil_lib_voe_acc` | le contenu des cours |
| Apprentissage | la formation se fait en alternance, avec un contrat d'apprentissage | jeu Parcoursup apprentissage 2025 | qu'un employeur est garanti : il faut en trouver un |
| Public / privé | le statut de l'établissement | Parcoursup | le coût : voir « coût » |
| Domaine | informatique, santé, maths (et cyber, data/IA) | table de domaines relue de l'étape A | que la formation n'enseigne rien d'autre |
| Commune, département, région | où la formation a lieu | Parcoursup + code officiel des communes (INSEE) | le lieu des stages |
| Distance | kilomètres à vol d'oiseau jusqu'au centre de la commune demandée | coordonnées publiées par Parcoursup, centre de commune de geo.api.gouv.fr | le temps de trajet |
| Lien officiel | la fiche Parcoursup (ou MonMaster) de la formation | Parcoursup | |

### L'admission (Parcoursup, sessions 2023 à 2025)

| Colonne | Ce qu'elle dit | Ce qu'elle ne dit pas |
|---|---|---|
| Taux d'accès | libellé officiel : « rapport entre le nombre de candidats dont le rang de classement est inférieur ou égal au rang du dernier appelé de son groupe et le nombre de candidats ayant validé un vœu pour la formation ». En clair : la part des candidats qui ont reçu une proposition | **pas** la chance d'un candidat en particulier, **pas** places divisées par vœux |
| Places | « capacité de l'établissement par formation » | le nombre d'admis réels, qui peut dépasser ou rester en dessous |
| Vœux | « effectif total des candidats pour une formation » | le nombre de candidats vraiment intéressés : un candidat fait jusqu'à 10 vœux |
| Part de bac général, techno, pro parmi les admis | « % d'admis néo bacheliers technologiques » (etc.) : la part parmi les admis **qui viennent d'avoir leur bac** | la part parmi tous les admis. Mesure : `pct_bt` = admis techno / admis néo-bacheliers sur 6 264 lignes sur 6 264, et = admis techno / tous les admis sur 1 481 seulement |
| Effectif de bac pro admis (seulement si Q6 = A) | le nombre, pas la part | |
| Part de boursiers, de filles, de mentions TB | parmi les admis néo-bacheliers | le niveau réel des admis en maths |
| Part d'admis de la même académie | « % d'admis néo bacheliers issus de la même académie » | que la formation refuse les autres académies |

### Ce que coûte la formation

| Colonne | Ce qu'elle dit | D'où | Ce qu'elle ne dit pas |
|---|---|---|---|
| Droits d'inscription | montant annuel fixé par l'État (178 € en licence, BUT, CPGE publique) | tableau ministériel 2026-2027 | le logement, le matériel |
| CVEC | contribution vie étudiante, 105 € | Service-Public | |
| Frais de scolarité (privé) | montant ou fourchette que l'école publie, texte d'origine gardé | Onisep (Idéo-Actions) | la bourse ou la réduction auxquelles on a droit |
| Gratuit en apprentissage | la formation est gratuite pour l'apprenti | Code du travail, article L6211-1 | le salaire de l'apprenti |
| Non disponible | on a cherché et rien trouvé : la raison est écrite | | que c'est gratuit |

### Après la formation

| Colonne | Ce qu'elle dit | D'où | Ce qu'elle ne dit pas |
|---|---|---|---|
| Taux d'emploi à 6, 12, 18, 24 mois | part des diplômés en emploi salarié en France | InserSup (licences, BUT, masters), InserJeunes (BTS) | la qualité de l'emploi ; le lien avec le diplôme |
| Poursuite d'études | part des sortants qui continuent leurs études | InserJeunes | |
| Portée | la formation elle-même, ou le même diplôme dans l'établissement | | |

### Santé (PASS et LAS)

| Colonne | Ce qu'elle dit | Portée | Ce qu'elle ne dit pas |
|---|---|---|---|
| Passage en MMOPK en 1 ou 2 ans | PASS 47,5 %, LAS 25,7 % d'admis en médecine, maïeutique, odontologie, pharmacie ou kiné | **nationale** (SIES, session 2024) | le taux de cette université-là : aucune université du panel ne le publie |
| Places en MMOPK | capacités publiées par l'université pour 2026-2027 | université | le nombre de places pour un parcours LAS précis |
| Réforme 2027 | voie unique annoncée le 17/04/2026, aucun texte publié au 23/09/2026 | nationale | qu'elle est acquise |

## 8. Interface pour le modèle : fonctions à filtres fermés

### Recommandation, sur pièces

Des **fonctions typées à filtres fermés**, pas de SQL libre. Le SQL reste pour les humains : Matteo
dans DB Browser, Jarvis dans l'explorateur, moi pour l'audit.

1. **Couverture mesurée** : les 20 requêtes du gate s'écrivent toutes avec les filtres ci-dessous
   (table en fin de section). Ce qu'une fonction fermée ne sait pas faire n'est donc pas demandé par
   le gate.
2. **Les pièges vivent dans le code, une fois, testés**, au lieu d'être à redécouvrir par le modèle
   à chaque requête :
   - « licence X » inclut la LAS X (règle de Jarvis, C01, C06, C16, C17, C20) ;
   - la part de bac techno est une part parmi les néo-bacheliers ;
   - une ligne `non_disponible` n'est pas un zéro ;
   - un taux de santé porte sa portée ;
   - un nom de commune est ambigu (1 441 homonymes).

   En SQL libre, chacun de ces pièges est une erreur silencieuse possible à chaque requête.
3. **Vérifiable et affichable** : la fonction renvoie les filtres qu'elle a appliqués, normalisés
   (commune résolue, types dépliés). C'est ce que l'écran de Matteo affiche en « filtres traduits »,
   lisible par un non-développeur. Une requête SQL ne l'est pas.
4. **Borné** : lecture seule, `limite` plafonnée à 50, rayon plafonné à 300 km, aucune jointure
   libre.
5. **Supposé, non mesuré** : les modèles Mistral appellent de façon fiable des fonctions à schéma
   JSON, plus que du SQL qu'ils écriraient eux-mêmes. À mesurer au lot outils, sur le banc, pas ici.

**Ce que ça coûte** : une question hors des filtres n'a pas de réponse structurée, et le modèle
retombe sur la recherche dans les textes. C'est voulu : le chiffre qu'on ne sait pas filtrer, on ne
l'invente pas. Chaque manque constaté au banc devient un filtre de plus, testé.

### Signatures prévues pour le lot outils

```python
def trouver_commune(nom: str, departement: str | None = None) -> list[Commune]:
    """Candidats {code_insee, nom, departement, region}. Plusieurs candidats = au modèle de choisir
    ou de demander. Jamais de choix silencieux."""

def lister_valeurs(champ: Literal["type", "filiere", "region", "departement", "secteur_master"],
                   type: list[TypeFormation] | None = None) -> list[tuple[str, int]]:
    """Valeurs exactes admises par les filtres, avec le nombre de formations. Le modèle y prend la
    chaîne exacte au lieu de la deviner."""

def chercher_formations(
    types: list[TypeFormation] | None = None,          # "licence" inclut "las"
    filieres: list[str] | None = None,                  # valeurs exactes de lister_valeurs, sinon erreur + candidats
    intitule_contient: str | None = None,               # sans casse ni accents
    apprentissage: bool | None = None,                  # None = les deux
    statut: Literal["public", "prive"] | None = None,
    communes: list[str] | None = None,                  # codes INSEE
    departements: list[str] | None = None,
    regions: list[str] | None = None,
    pres_de: PresDe | None = None,                      # {code_insee, rayon_km <= 300}
    taux_acces_min: float | None = None,                # >= (inclusif)
    taux_acces_max: float | None = None,                # <  (strict)
    places_min: int | None = None,                      # >=
    part_bac_techno_min: float | None = None,           # >=, part parmi les admis néo-bacheliers
    part_bac_pro_min: float | None = None,              # >=, idem
    session: Literal[2023, 2024, 2025] = 2025,
    champs: list[str] | None = None,                    # chiffres à rendre en plus du jeu par défaut
    tri: Tri | None = None,                             # {champ, sens}, champ dans une liste fermée
    limite: int = 20,                                   # <= 50
) -> ResultatRecherche:
    """{filtres_appliques, nb_resultats, tronque, resultats: [{id, intitule, etablissement, commune,
    distance_km?, valeurs: {champ: {valeur, unite, statut, raison?, portee, source_id, millesime}}}],
    sources: {source_id: {libelle, url}}}"""

def chercher_masters(mention_contient: str | None = None, secteurs: list[str] | None = None,
                     regions_academiques: list[str] | None = None, departements: list[str] | None = None,
                     pres_de: PresDe | None = None, alternance: bool | None = None,
                     capacite_min: int | None = None, champs: list[str] | None = None,
                     tri: Tri | None = None, limite: int = 20) -> ResultatRecherche: ...

def lire_fiche(id: str) -> FicheComplete:
    """Tout ce que la base sait de la formation, chaque chiffre avec sa source, son millésime, sa
    portée ; lignes non disponibles incluses, avec leur raison."""
```

**Bornes des filtres, fixées une fois pour toutes** :
- `*_min` est **inclusif** (>=). « Au moins 50 % » s'écrit `taux_acces_min=50`, et une formation à
  exactement 50 % passe (C18).
- `*_max` est **strict** (<). « Inférieur à 8 % » s'écrit `taux_acces_max=8`, et une formation à
  exactement 8 % ne passe pas (C13).
- La règle vaut pour tous les seuils : taux d'accès, places, parts de bac, capacité des masters.
- `pres_de` : distance <= rayon (inclusif), comparée en kilomètres non arrondis ; l'arrondi à 0,1 km
  sert seulement à l'affichage.
- Les chiffres sont comparés tels que publiés, sans arrondi : un taux de 7,9 passe `taux_acces_max=8`.

La docstring de chaque paramètre répète sa borne, et un test par borne pose une formation
exactement sur le seuil.

Filtres **génériques uniquement** : aucune branche de code ne connaît une requête du gate (règle de
Jarvis). Un filtre qui porte sur un champ dit toujours sa règle pour les `non_disponible` : une
formation sans taux d'accès **ne passe pas** un filtre de taux d'accès, et le résultat compte à part
les formations écartées faute de valeur (`ecartees_non_disponible`).

### Les 20 requêtes du gate en filtres (ma traduction, écrite avant le code)

| Req. | Outil et filtres |
|---|---|
| C01 | `chercher_formations(types=[but, licence, bts], filieres=[Informatique, Services informatiques aux organisations], apprentissage=False, pres_de={12202, 80})` |
| C02 | `chercher_formations(types=[but], filieres=[Informatique], regions=[Hauts-de-France], part_bac_techno_min=35)` |
| C03 | `chercher_formations(types=[bts], filieres=[Services informatiques aux organisations, Cybersécurité, Informatique et réseaux, ELectronique - Option A : Informatique et réseaux], apprentissage=False, pres_de={35238, 30}, champs=[places, part_bac_pro])` |
| C04 | `chercher_formations(types=[but, bts], filieres=[Informatique, Services informatiques aux organisations], apprentissage=True, departements=[59])` |
| C05 | `chercher_formations(types=[but], filieres=[Informatique], departements=[93], champs=[taux_acces@2023, taux_acces@2024, taux_acces@2025])` |
| C06 | `chercher_formations(types=[but, licence, bts], filieres=[Informatique, Services informatiques aux organisations, CIEL option A, CIEL option B], departements=[972], apprentissage=False)` |
| C07 | `chercher_masters(mention_contient="MIAGE", regions_academiques=[Occitanie], champs=[alternance, capacite, candidats_pp])` |
| C08 | `chercher_formations(types=[pass, las], communes=[35238], champs=[places, taux_acces])` |
| C09 | `chercher_formations(types=[ifsi], pres_de={87085, 60}, tri={taux_acces, desc})` |
| C10 | `chercher_formations(types=[ifsi], departements=[59], tri={part_bac_pro, desc}, limite=3)` |
| C11 | `chercher_formations(filieres=[D.E Ergothérapeute], regions=[Normandie])` |
| C12 | `chercher_formations(filieres=[D.E manipulateur/trice en électroradiologie médicale, DTS Imagerie médicale et radiologie thérapeutique], pres_de={69123, 50}, champs=[taux_acces])` : apprentissage inclus (gate v2 : psup_app:46954 ajouté aux attendus ; son taux d'accès est « ne s'applique pas ») |
| C13 | `chercher_formations(filieres=[Certificat de capacité d'Orthophoniste], taux_acces_max=8)` (strict par convention) |
| C14 | `chercher_formations(types=[pass], communes=[86194])` : attendu vide |
| C15 | `chercher_formations(types=[pass], communes=[59350], champs=[passage_mmopk_1_ou_2_ans_national])` |
| C16 | `chercher_formations(types=[licence], filieres=[Mathématiques], pres_de={35238, 30})` |
| C17 | `chercher_formations(types=[licence], filieres=[Mathématiques et informatique appliquées aux sciences humaines et sociales], regions=[Hauts-de-France])` |
| C18 | `chercher_formations(types=[cpge], filieres=[MPSI, MP2I, PCSI], taux_acces_min=50, pres_de={59606, 50})` |
| C19 | `chercher_formations(types=[cpge], filieres=[TSI], regions=[Occitanie])` |
| C20 | `chercher_formations(departements=[974], ou de deux appels : types=[cpge] filieres=[MPSI, MP2I, PCSI] ; types=[licence] filieres=[Mathématiques])` |

- Les codes INSEE de Poitiers (86194) et de Lille (59350) sont à confirmer par `trouver_commune` au
  moment de transcrire.
- **C20** montre une limite assumée : un appel ne combine pas deux couples type x filière (« CPGE
  MPSI » **ou** « licence de maths »). Le modèle fait deux appels, et le gate joue les deux et
  réunit les résultats.
- La phase 2 transcrit cette table dans `results/donnee_etape_c/gate/filtres_gate_c.json`, avant
  toute construction de la base.

## 9. Export pour l'explorateur de Jarvis

- **Fichier** : `data/processed/base_etape_c.explorateur.json` (hors git, régénéré par la même
  commande que la base), avec son sha256 dans le manifeste.
- **Format** : un seul JSON, en colonnes compactes pour rester lisible sur iPhone :

```jsonc
{
  "meta": {"genere_le": "...", "corpus_sha256": "2e6a93a5cda6", "base_empreinte": "...",
           "commande": "python -m src.collect.base_etape_c", "perimetre": "..."},
  "champs": {"taux_acces": {"libelle": "Taux d'accès", "unite": "%", "definition": "...",
             "ne_dit_pas": "...", "portee_par_defaut": "formation"}, ...},   // table champ, la base en clair
  "sources": {"parcoursup_2025": {"libelle": "...", "url": "...", "licence": "...", "collecte": "2026-09-23"}, ...},
  "formations": [
    {"id": "psup:7596", "intitule": "...", "etablissement": "...", "type": "but", "filiere": "Informatique",
     "apprentissage": 0, "statut": "Public", "domaine": "informatique", "commune": "Aubière",
     "code_insee": "63014", "departement": "63", "region": "...", "lat": 45.76, "lon": 3.11,
     "precision_geo": "formation", "lien": "https://dossierappel.parcoursup.fr/...",
     "v": {"taux_acces@2025": [34, "parcoursup_2025", "cod_aff_form=7596"],
           "cout.droits_inscription": [178, "tableau_droits_2026_2027", "..."],
           "insertion.taux_emploi_12m": [null, null, null, "raison en clair"]}}   // [valeur, source, identifiant, raison?, portee?]
  ],
  "concepts": [...],
  "gate": {...}                                                                // section 10
}
```

- **Taille** : de l'ordre de 9 Mo, 0,45 Mo compressé (prototype de taille sur les 3 470 fiches et
  194 213 valeurs, provenance non encore incluse). Le format compact ci-dessus remplace le nom de
  source répété par une clé courte. La cible est **moins de 12 Mo** non compressé : **supposé**, à
  mesurer en phase 2. L'explorateur charge déjà 21,3 Mo aujourd'hui.
- **La source cliquable de chaque chiffre** vient de `sources[source].url`, plus le lien officiel de
  la formation. L'identifiant de la ligne source s'affiche à côté (`cod_aff_form=7596`), pour qu'un
  humain retrouve la ligne dans le fichier officiel.
- **Pour un tableur** : `data/processed/base_etape_c_formations.csv`, une ligne par formation, en-têtes
  en français, séparateur « ; », encodage UTF-8 avec BOM (lisible par Excel). **Le fichier SQLite
  lui-même** s'ouvre dans DB Browser for SQLite : c'est la base, pas une copie.
- **Licence** : les coûts viennent d'Onisep, sous ODbL. Un usage interne ne pose pas de problème ;
  republier la base impose de la partager à l'identique. Le point est déjà ouvert au cahier des
  charges (§9).

C'est Jarvis qui construit l'écran : je fournis ce fichier et je m'engage sur sa forme. Tout
changement de forme passe par une nouvelle version de ce contrat.

## 10. Le gate C : format et rejeu

### Format du fichier de requêtes (figé avec Jarvis le 23/09, message `gate-format-fige`)

```jsonc
{"id": "C09", "question": "...", "domaine": "sante",
 "attendus": ["psup:23157", "..."],                     // identifiants typés
 "mode": "exact",                                       // exact | inclut | exclut | vide
 "ordre": true,                                         // ajout Jarvis : le rendu suit l'ordre ; ex aequo permutables
 "valeurs": [{"fiche": "psup:...", "champ": "taux_acces_ens@2025", "valeur": 13.0, "unite": "%", "portee": "..."}],
 "reference_geo": {"commune": "Limoges", "code_insee": "87085", "rayon_km": 60},
 "frontiere": ["psup:23155"],                           // bande de +/- 3 km : ni comptée juste ni fausse
 "justification": {"source": "...", "url": [...], "lue_le": "..."},
 "filtres": null}                                       // ma traduction, dans MON fichier (ci-dessous)
```

- `champ` dans `valeurs` porte le **nom officiel** de la source (`taux_acces_ens`, `capa_fin`,
  `acc_bp`, `col`, `n_can_pp`...), avec `@session` pour l'historique. La table `valeur` garde ce nom
  dans `identifiant_source`, et la correspondance nom officiel -> champ de la base est une colonne du
  catalogue : le gate la lit, il ne la réécrit pas.
- Mes traductions vivent dans mon dépôt (`results/donnee_etape_c/gate/filtres_gate_c.json`), avec
  le sha du fichier de Jarvis qu'elles traduisent. Un sha différent arrête le rejeu : on ne juge pas
  une traduction contre une autre version des requêtes.

### Rejouer et afficher

- Commande : `python -m src.eval.gate_c --requetes <fichier de Jarvis> --base data/processed/base_etape_c.sqlite`.
- Sorties :
  - `results/donnee_etape_c/gate/resultats.json` ;
  - un `REPORT.md` ;
  - un bloc `gate` dans l'export de l'explorateur.
- Chaque requête rejouée donne :

```jsonc
{"id": "C12", "question": "...",
 "filtres": {"outil": "chercher_formations", "arguments": {...}},
 "filtres_en_clair": "diplôme de manipulateur radio ou DTS imagerie ; à moins de 50 km de Lyon (69123), à vol d'oiseau",
 "rendues":   [{"id": "psup:8225", "intitule": "...", "commune": "...", "distance_km": 3.1, "valeurs": {...}}],
 "attendues": [{"id": "psup:8225", "intitule": "...", "commune": "..."}],
 "frontiere": [...],
 "verdict": {"juste": true, "manquantes": [], "en_trop": [], "ordre_ok": null, "valeurs_ecarts": []}}
```

  L'écran met côte à côte la question, les filtres en clair, les fiches rendues et les fiches
  attendues. Les manquantes et les fiches en trop sont nommées ; une fiche de frontière ne compte ni
  juste ni fausse.
- **Règle du verdict** :
  - `exact` = mêmes identifiants hors frontière ;
  - `inclut` = les attendus sont dedans ;
  - `exclut` = aucun attendu n'est dedans ;
  - `vide` = 0 résultat ;
  - `ordre` = même ordre, ex aequo permutables ;
  - `valeurs` = égalité stricte avec la valeur officielle, sans tolérance.

  Le gate passe si les 20 sont justes.

## 11. Audit prévu pour la phase 2

Même méthode que A et B : contrôles qui rougissent sur leur levier, sabotages, témoin positif,
vérification indépendante de Jarvis, avant/après dans l'explorateur.

1. **Base contre corpus B-2, 100 % des valeurs, dans les deux sens** :
   - chaque champ du corpus que la base reprend (coût, alternance, insertion, santé, domaine,
     commune) a sa ligne dans la base, avec la même valeur ;
   - chaque ligne de la base qui cite le corpus y retrouve sa valeur.

   Les deux comptes sont publiés, avec le nombre de valeurs comparées : une comparaison sur zéro
   valeur échoue, elle ne passe pas.
2. **Base contre bruts verrouillés, 100 % des valeurs officielles** : admission, places, vœux,
   profil et effectifs, sessions 2023 à 2025, relus à la ligne `cod_aff_form` du CSV, par un code
   séparé du code de construction. Même règle des deux sens et du compte non nul.
3. **Là où base, corpus et brut se recoupent**, les trois concordent, avec compte publié.
4. **Contrôles de forme** :
   - les `CHECK` SQL (section 4.2) ;
   - une ligne par formation, champ applicable et session (section 6) ;
   - `source_id` existant pour toute ligne disponible ;
   - taux entre 0 et 100 ;
   - coordonnées dans l'emprise de la France, outre-mer compris ;
   - portée présente sur toute valeur de santé ;
   - aucun `taux_admission` calculé de MonMaster ;
   - identifiants uniques.
5. **Géographie** :
   - distance testée sur des paires connues (Paris - Lyon, mesurée contre une référence
     indépendante et écrite dans le test) ;
   - 0 fiche placée à 0 km faute de coordonnées ;
   - les 442 fiches d'apprentissage résolues en INSEE après normalisation, avec un compte.
6. **Sabotages**, par un levier explicite (variable d'environnement `ORIENTIA_SABOTAGE_C`, jamais
   une édition du code). Chacun doit faire rougir **le** contrôle qui le vise, et pas un autre :
   - `valeur` : un chiffre modifié ;
   - `source` : une source effacée ;
   - `portee` : une santé nationale présentée comme propre à l'université ;
   - `geo` : une coordonnée décalée de 100 km ;
   - `perimetre` : l'ancien classement de l'explorateur, et le contrôle de couverture du gate
     rougit (témoin déjà mesuré : 13 fiches) ;
   - `absent` : une ligne `non_disponible` remplacée par un NULL sans raison ;
   - `insee` : la normalisation « 0NN » retirée.
7. **Témoin positif** : une valeur connue relue de bout en bout. `psup:7596`, BUT Informatique
   d'Aubière, taux d'accès 34 %, 96 places (chiffres du banc, vérifiés contre l'API officielle le
   23/09), doit sortir avec sa source cliquable.
8. **Déterminisme** : deux constructions donnent la même empreinte canonique.
9. **Le gate C** : 20 requêtes justes.
10. **Rien d'autre ne bouge** : la suite de tests reste verte, le corpus B-2 garde son sha, la prod
   n'est pas touchée.

## 12. Questions ouvertes pour Matteo (courtes, avec une option recommandée)

**Q1. Les masters.** Le corpus a 405 des 480 masters d'info et de maths de 2025. Il en manque 75, et
on n'a pas gardé le fichier d'origine.
- A (recommandé) : je re-télécharge le fichier officiel MonMaster, je le garde, et les 480 entrent
  avec leur source. Coût supposé : une demi-journée.
- B : on garde les 405 tels quels, et le trou est dit.

**Q2. Les maths.** « Maths porte d'entrée » = prépas scientifiques (MPSI, MP2I, PCSI, PTSI, TSI,
BCPST...), CUPGE, licences de maths, et MIASHS (rangée en info).
- Recommandé : oui, et les licences de biologie, chimie, physique et les prépas ECG restent
  dehors (630 formations).

**Q3. Le paramédical sans règle.** 167 formations de santé (BTS diététique, biologie médicale,
opticien, prothésiste dentaire, BUT génie biologique...).
- Recommandé : dedans.

**Q4. Les métiers liés (débouchés).** Ils viennent d'un rapprochement automatique non relu, et d'un
fichier qu'on n'a pas gardé.
- Recommandé : hors de la base pour l'instant. Ils restent dans le texte des fiches, et on les
  rentre une fois leur source verrouillée.

**Q5. La distance.** « À moins de 50 km » = à vol d'oiseau, pas en temps de trajet.
- Recommandé : oui, et la réponse le dit (« à 69 km à vol d'oiseau »). Le temps de trajet demande
  une autre source, plus tard si la démo en a besoin.

**Q6. D'où lire les chiffres officiels.** Les deux donnent aujourd'hui les mêmes valeurs (0 écart
mesuré).
- B (recommandé) : dans notre fichier déjà corrigé et vérifié. Plus simple, un seul chemin.
- A : directement dans les fichiers officiels. Ça ouvre des chiffres en plus (ex. le nombre de bac
  pro admis, pas seulement la part), pour un peu plus de travail.

## 13. Dettes relevées pendant le contrat

| Dette | Trace |
|---|---|
| B-1 : les 526 fiches d'apprentissage ont un département sur trois chiffres ; 442 n'ont pas de code INSEE. La base contourne par normalisation ; la correction est à faire dans B-1 | `mesures_contrat.json`, `geographie.perimetre_sans_code_insee` et `apprentissage_sans_insee_forme_departement` |
| MonMaster du corpus : 75 masters info/maths 2025 manquants, 542 masters de la session 2024, lien Onisep de recherche au lieu de la fiche, villes avec CEDEX (80 sur 456 masters info/maths du corpus) | `masters`, dont `corpus_info_maths_ville_avec_cedex` |
| Le classement par mots-clés de l'explorateur manque 13 fiches attendues par le gate (zone de Jarvis, signalé) | `temoin_perimetre_explorateur` |
| Table A, règle M01 : 5 fiches « ENS Paris-Saclay, arts et design » classées en prépa scientifique | section 2 ; `mesures_contrat.json`, `regles_maths_detail.M01` |

Traité pendant le contrat, par Jarvis dans le gate v2 : le libellé de C02 et C10 (« parmi les admis
néo-bacheliers », `pct_bt_denominateur`), C12 étendu à l'apprentissage, C03 passé sur `pct_bp`.
| Dettes antérieures inchangées (RRF, Railway, tokens Mistral...) | REPRISE.md section 5 |

## 14. Ce que ce contrat ne décide pas

- Le texte que le modèle lit (`fiche_to_text`) : c'est l'étape D. La base sert les chiffres ; le
  texte reste celui de B-2.
- Le branchement dans le produit servi : lot « cerveau », après mesure au banc.
- Le déploiement : la prod reste au lot 1 de juillet.

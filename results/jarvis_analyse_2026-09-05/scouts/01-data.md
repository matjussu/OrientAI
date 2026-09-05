# Scout 01 : audit de la DATA OrientIA (lecture seule)

Date : 2026-09-05. Repo : `~/projets/OrientIA`. Aucun fichier du repo modifié, aucun appel réseau, aucune API payante. Toutes les mesures ci-dessous sont des scripts Python locaux sur `data/processed/formations.json` (venv `.venv`, `PYTHONPATH=.`) ou des grep/ls. Ce qui n'a pas été mesuré est marqué "non mesuré".

Conventions : "rempli" = valeur non nulle, non vide, différente de "N/A" et de "non renseigné" (fonction `filled()` du script de mesure, section 2). Les chiffres sur le corpus parcoursup portent sur 13 011 fiches, sur monmaster 7 573, etc.

---

## 0. Le cas Lyon, expliqué par les données

Question : "terminale spé maths-physique à Lyon, aime l'info, pas de prépa". Réponse observée : Licence Info Lyon 2 ("non sélective, taux d'accès 28 %") et ECE Lyon (privée, sans coût). Jamais BUT Informatique, MIAGE, Lyon 1.

Ce que contient le corpus (script : filtre `source=="parcoursup"` et `region` AURA, `nom` contient "informatique") :

| Fiche | ville (champ `ville`) | statut | selectivite_code | taux_acces_parcoursup_2025 | places | domaine |
|---|---|---|---|---|---|---|
| BUT Informatique, IUT Lyon 1 site Villeurbanne Doua | "Villeurbanne" | Public | formation sélective | 16 | 125 | **autre** |
| Licence Portail Maths/Info Lyon 1 | "Villeurbanne" | Public | non sélective | 51 | (mesuré, non noté) | sciences_fondamentales |
| Licence Informatique Lyon 2 | "Bron" | Public | non sélective | 28 | 60 | sciences_fondamentales |
| Licence MIASHS Lyon 2 | "Bron" | Public | non sélective | 78 | | |
| ECE Lyon (2 fiches) | Lyon | Privé | sélective | 98 et 48 | | |

Constats établis :

1. **Le BUT Informatique Lyon 1 existe** mais sa ville est "Villeurbanne", pas "Lyon", et son `domaine` est "autre". Généralisé : les 49 fiches Parcoursup dont le nom commence par "BUT Informatique" sont classées "autre" (49/49) alors que "Licence Informatique" est classée "sciences_fondamentales" (41/42). Cause : `src/collect/parcoursup.py:245-259`, cascade `domaine_cascade` qui s'appuie sur la table `FORM_LIB_VOE_ACC_TO_DOMAINE`, sans entrée pour les BUT. Tout filtre ou boost par domaine "informatique/sciences" écarte donc les BUT Info.
2. **Lyon 2 est à Bron**, Lyon 1 à Villeurbanne : aucune notion d'agglomération dans les données (aucune clé lat/lon, code commune ou EPCI dans les fiches Parcoursup, cf. section 2 ; la table `REGION_BY_CITY` de `src/rag/geo_coherence.py` contient "lyon" et "villeurbanne" mais pas "bron"). Les villes intra-Lyon sont libellées "Lyon 8e  Arrondissement" (double espace), etc. : 47 fiches Villeurbanne, 34 Bron dans le Rhône. Comportement runtime de la normalisation géo : non mesuré (hors périmètre data).
3. **"Non sélective, taux d'accès 28 %"** est fidèle aux colonnes Parcoursup (`select_form` et `taux_acces_ens`) ; ce qui manque est la sémantique : le corpus n'embarque aucune définition du taux d'accès (`fiche_to_text` et FactCard n'en fournissent pas, `src/rag/fact_card.py:795-895`). 535 fiches "non sélectives" ont un taux < 50 %.
4. **ECE sans coût** : il n'existe aucune clé coût dans les 52 040 fiches (section 2.4). Le champ `FactChiffres.frais_annuels` (`fact_card.py:231`, alimenté ligne 813 par `fiche.get("frais_annuels")`) est structurellement toujours None.
5. **MIAGE** : 1 seule fiche Parcoursup (Mulhouse), normal puisque MIAGE = L3/master ; présence dans MonMaster : non mesuré.
6. Le texte embarqué de Licence Info Lyon 2 contient en plus deux erreurs factuelles : "83 % origine académique Île-de-France" (section 4.2) et "Insertion apprentissage (Inserjeunes CFA) : taux emploi 6 mois 35 %" (section 4.3) alors que la source est InserSup discipline x région.

---

## 1. Inventaire des sources

### 1.1 `data/processed/formations.json`

Liste JSON de 52 040 fiches, 110 Mo, mtime 14 juin 2026 (`ls -l`). Copie `formations.json.bak-pre-l1-url-20260615` de même taille ; `formations_unified.json` 98 Mo. Distribution du champ `source` (Counter) :

| source | fiches | granularité réelle | millésime (mesuré) |
|---|---|---|---|
| parcoursup | 13 011 | formation x établissement | session 2025 (100 %), historique 2023-2025 pour 11 874 ; `collected_at` 2026-06-09 |
| monmaster | 7 573 | parcours de master | session 2025 : 7 031, 2024 : 542 |
| rncp | 5 181 | certification (pas un établissement) | `actif` True 5 181/5 181 mais 1 336 (26 %) ont `date_fin_enregistrement` < 2026-09-04 |
| rncp_blocs | 4 891 | bloc de compétences | idem |
| onisep | 4 758 | formation générique | non mesuré |
| inserjeunes_cfa | 4 065 | CFA (établissement) | cumuls 2018-2019 à 2023-2024 (2023-2024 : 1 384 ; <= 2021-2022 : 1 891) |
| labonnealternance | 4 008 | offre de formation alternance | dump 2026-04-23 (`data/processed/lba_formations`) ; `retrieval_eligible=False` pour 4 008/4 008 |
| inserjeunes_lycee_pro | 2 693 | lycée pro | non mesuré ; certaines fiches "statistiques non disponibles" |
| rome_api_v4 | 1 584 | métier ROME | `obsolete` False 1 584/1 584 |
| dares_metiers_2030 | 1 160 | FAP x région (1 049), FAP (98), région (13) | projections 2030 |
| onisep_ideo_fiches / onisep_metiers | 1 075 + 1 075 | métier | `annee` None 338, 2024 : 188, 2023 : 177, 2022 : 135, 2021 : 128 |
| insersup_mesr | 368 | discipline x région x diplôme | cohorte 2024 (368/368) |
| ip_doc_doctorat | 240 | discipline | cohortes 2014 et 2016 |
| mesri_parcours_bacheliers_licence | 151 | type de bac x mention | cohortes L1 2014 / licence 2012 ; bacs "S", "ES", "L" (ancien bac) |
| insee_salaan_2023 | 59 | | 2023 |
| crous_combine_logements_restos | 45 | France + par CROUS régional | pas un seul "€" dans les 45 textes |
| financement_dispositifs_curated | 28 | dispositif | curé, 4 fiches mentionnent un échelon |
| onisep_formations_extended | 20 | | |
| domtom_curated | 16 | | curé |
| apec_observatoire_emploi_cadre_2026 | 13 | | 2026 |
| parcoursup_calendrier_officiel / monmaster_calendrier_officiel / dse_calendrier_officiel | 9 + 7 + 5 | | annee 2026 (21/21) |
| corrections_factuelles_curated | 5 | | curé (ex. "BBA INSEEC 12 000-14 500 €/an") |

### 1.2 Corpus annexes et bruts

- `data/processed/` contient aussi apec_stats_2025, cereq_insertion_stats, crous_logements/restaurants, dares_corpus, ft_offres_sample, golden_qa_meta, ideo_fiches_metiers, insee_salaires_2023, inserjeunes_cfa, insersup_corpus, lba_formations (6 646 fiches), monmaster_formations, parcoursup_extended, rncp_certifications, voie_pre_bac_corpus. Tous datés 14 juin 2026.
- `data/textualized/` : fichiers `onisep-XXXXX.md` de 800 à 1 200 octets, ancienne textualisation ONISEP, 14 juin.
- `data/raw/` : **seules les fixtures trackées existent** (secnumedu.json, onisep_formations.json, financement/, domtom/, corrections_factuelles/, france-travail/romeo.json, 2 xlsx Céreq). `.gitignore` contient `data/raw/*`. Les CSV `parcoursup_2023/2024/2025.csv` attendus par `scripts/run_merge_v3.py:782-784` et `insersup.csv` (568 Mo selon INVENTAIRE C0) sont **absents du disque**. Conséquence : le pipeline de fusion n'est pas régénérable localement sans re-téléchargement (`scripts/download_parcoursup_history.sh`, `scripts/download_insersup.sh` qui pointe `data.gouv.fr/api/1/datasets/r/154013bd-...`).
- Parcoursup brut : 14 252 lignes (`~/projets/_orientai-ref/refonte-ia-2026/INVENTAIRE-data-corpus.md`, C0 2026-06-09) contre 13 011 ingérées (91 %). Cause des 1 241 non ingérées : non mesuré (CSV absent). ADR-041 (`docs/DECISION_LOG.md:1581`) documente une ingestion antérieure limitée à 9 212/14 252 (65 %) par mots-clés, élargie en C1.

### 1.3 Licences

`docs/DATA_INVENTORY_2026-04-26.md:16` et `:110` mentionnent Etalab 2.0 (Parcoursup, CROUS). Les licences des autres sources (ONISEP, RNCP/France compétences, InserJeunes, LBA, ROME, DARES, INSEE, APEC, Céreq) ne sont consignées nulle part dans le repo (grep `licen[cs]e|etalab|odbl` sur docs/*.md : 3 fichiers, aucun tableau de licences) : **non mesuré / non documenté**.

---

## 2. Schéma et taux de remplissage par source

Script : pour chaque source, ratio `filled(fiche[k])` sur les clés critiques.

### 2.1 parcoursup (13 011)

| champ | rempli | remarque |
|---|---|---|
| etablissement, ville, statut, taux_acces_parcoursup_2025, places, admission, profil_admis, url | 100 % | taux None : 15 ; taux == 0 : 38 ; places == 0 : 3 |
| region | 99,9 % | |
| type_diplome | 82,2 % | 2 316 None |
| trends | 95,7 % | jamais verbalisé dans le texte (section 4) |
| detail | 27,7 % | Licence 1 945/2 654, Ecole d'ingénieur 431/445, Ecole de commerce 149/205 ; mais BUT 19/820, BTS 31/5 350, CPGE 21/853, IFSI 4/343 |
| insertion_pro | 27 % (3 509) | 100 % source `insersup_mesr`, granularité `discipline_region` (pas la formation) |
| debouches | 10,2 % | |
| internat | None pour 12 158 (93 %) | |
| statut | Public 10 107 / Privé 2 904 | aucune clé contrat / EESPIG / hors contrat |
| selectivite_code | sélective 10 674 / non sélective 2 337 | 535 non sélectives à taux < 50 % |
| fili_code | BTS 5 350, Licence 2 654, Autre 1 770, CPGE 853, BUT 820, Ecole d'Ingénieur 445, IFSI 343, Licence_Las 286, EFTS 242, Ecole de Commerce 205, PASS 43 | |
| domaine | "autre" 3 197 | dont 49/49 BUT Informatique |
| coût, frais, attendus, lat/lon, code commune | **clé absente** | |

`profil_admis.acces_pct` : somme = 100 pour 10 492 fiches (101 : 1 206, 99 : 1 203). C'est une **répartition des admis par type de bac**, pas un taux d'accès par profil.

`origine_academique_idf_pct` = colonne `pct_aca_orig_idf` (`src/collect/parcoursup.py:175`, commentaire "% admis originaires IDF"). Médianes par région : Guadeloupe 100, Réunion 96, Corse 92, AURA 74, Occitanie 75. Une médiane de 100 % d'admis "originaires d'IDF" en Guadeloupe est impossible : la colonne est en réalité la part d'admis **de la même académie** que la formation. Le nom du champ est faux.

### 2.2 monmaster (7 573)

etablissement, ville, region, url, mention, capacite : 100 % ; taux_admission 99,9 % (mais == 0 pour 385) ; insertion_pro 97,7 % (InserSup discipline x région). Villes 100 % majuscules, 1 436 contiennent "CEDEX". `url_type` = `fallback_search` (recherche ONISEP) pour 7 573/7 573 : aucun lien direct vers la fiche MonMaster. 249 doublons (etablissement, mention, parcours). `profil_admis` a un schéma différent de Parcoursup (pct_lg3, pct_but3...).

### 2.3 autres sources

| source | trous principaux |
|---|---|
| onisep (4 758) | ville vide 4 758/4 758 (0 %), etablissement 22,3 %, statut 2,1 %, debouches 2,5 %, rncp 66,3 %, tutelle "non renseigné" 2 215 |
| rncp (5 181) | `etablissement` = certificateur (ex. "MINISTERE DE L'EDUCATION NATIONALE") 98,6 %, pas un lieu ; debouches 17 % ; url fallback_search 5 181/5 181 |
| labonnealternance (4 008) | ville vide 4 008/4 008 ; `retrieval_eligible=False` 4 008/4 008 (donc jamais retrouvées) |
| inserjeunes_cfa (4 065) | ville vide 4 065/4 065 ; nom == etablissement 4 065/4 065 ; taux_emploi_6m non null 2 641/4 065 |
| url_type "none" | rncp_blocs, inserjeunes_lycee_pro, dares, insersup, ip_doc, mesri, insee, corrections |

### 2.4 Champs absents de tout le corpus

- Coût / frais / tarif / bourse : Counter des clés contenant ces mots sur 52 040 fiches = **vide**. Témoin positif : le texte de `corrections_factuelles_curated` contient "BBA INSEEC 12 000-14 500 €/an", donc la recherche du motif fonctionne ; l'information existe sur 5 fiches curées, dans du texte libre.
- Attendus : Counter des clés contenant "attendu" = vide. Le mot apparaît dans 1 193 champs `text`, dont 1 147 DARES ("emplois attendus") et 20 ONISEP IDEO ; **0 chez parcoursup**. Aucun des audits existants ne mentionne les attendus (grep `attendus|rapport public|examen des v` sur DATA_INVENTORY, CORPORA_SCHEMA_AUDIT, LIMITATIONS : 0 hit).

---

## 3. Qualité

- **Doublons globaux** (nom, etablissement) : 427 clés, 1 107 fiches (ex. "CCA" CNAM x10). Parcoursup : 13 011 `cod_aff_form` distincts, 0 doublon interne. MonMaster : 249 doublons.
- **Incohérences** : 535 "non sélectives" à taux < 50 % (cohérent avec Parcoursup mais contre-intuitif sans définition) ; 38 taux == 0 ; 385 taux_admission MonMaster == 0 ; `origine_academique_idf_pct` mal nommé (section 2.1) ; RNCP `actif` True alors que 26 % sont expirés.
- **Vides / N/A** : détaillés section 2. Fiches sans texte utile : onisep médiane 197 chars (265 fiches < 150), labonnealternance médiane 198 (410 < 150), rncp médiane 270.
- **Formations disparues** : non mesurable localement (CSV bruts absents, pas de diff entre sessions) : non mesuré. Le corpus est daté session 2025 avec `collected_at` 2026-06-09 ; la session 2026 (voeux janvier-mars 2026, résultats juin 2026) n'est pas ingérée alors que les calendriers curés parlent de 2026.
- **Fraîcheur des annexes** : INSEE 2023 ; IP-DOC cohortes 2014/2016 ; MESRI parcours bacheliers cohortes 2012/2014 avec bacs S/ES/L (réforme du bac 2021 non reflétée : ces stats ne s'appliquent à aucun lycéen actuel) ; Inserjeunes CFA : 1 891/4 065 fiches sur des cumuls <= 2021-2022 ; ONISEP métiers `annee` None 338.

---

## 4. Textualisation et chunking

### 4.1 Mécanique

`src/rag/embeddings.py:fiche_to_text` : une fiche = un texte embarqué, **pas de chunking**. Deux chemins : Parcoursup/formations (template champ par champ) et "annexe" (fiche avec `domain` et `text` >= 60 chars, tronqué à 1 500 chars, `embeddings.py:490-492`). Longueurs : parcoursup médiane 711 / max 1 542 ; monmaster 478 ; rncp 270 ; onisep 197 ; rome 1 554 et onisep_ideo_fiches 1 511 (donc tronqués).

Champs Parcoursup présents mais **jamais émis** dans le texte : `selectivite_code`, `admission.historique`, `lien_form_psup`, `internat`, `propositions_totales`, `trends` (la tendance n'existe que dans la FactCard `tendance_acces`).

### 4.2 Erreurs factuelles embarquées dans le texte

1. `embeddings.py:223-237` écrit `profil_admis.acces_pct` comme "taux d'accès par profil : 81 % pour bac général". C'est une répartition des admis (somme 100), donc contresens sur 13 011 fiches.
2. `embeddings.py:245` verbalise `origine_academique_idf_pct` en "origine académique Île-de-France". Exemples : Licence Info Lyon 2 "83 % origine académique Île-de-France", BUT Info Lyon 1 "74 %". Faux (section 2.1).
3. `_format_insertion_pro` (`embeddings.py:40-126`) détecte le schéma par clés : toute insertion avec `taux_emploi_6m` est étiquetée "Insertion apprentissage (Inserjeunes CFA, cumul récent)". Or 10 878 fiches (3 509 parcoursup + 7 397 monmaster, 100 % source `insersup_mesr`) reçoivent ce libellé : la source, la population (tous diplômés, pas les apprentis) et l'année sont faux dans le texte. La FactCard, elle, a un `insertion_source_label` data-driven : le texte embarqué et la FactCard se contredisent. Exemple Lyon 2 : "taux emploi 6 mois 35 %, 12 mois 34 %" pour une licence à poursuite d'études majoritaire, match discipline_region score 0.7 : chiffre trompeur pour un lycéen.

### 4.3 La "verbalisation défaillante" (ADR-058)

`docs/DECISION_LOG.md:3513-3670` : la cause racine identifiée est que les textes annexes sont structurés ("Titre | clé : valeur | ...", vérifié sur CROUS, DARES, INSEE, insersup, ROME ; seuls les calendriers sont en phrases) et donc éloignés des questions naturelles. Le workaround retenu est le double index + BM25 + RRF. La "vraie fix" est la réécriture des textes annexes (Phase 3 V2, ~7,5 $ + 1,5 j) décrite dans `docs/HANDOFF_REWRITE_ANNEX_TEXTS.md` (900 lignes, Haiku Batch sur 13 417 fiches). Pourquoi jamais faite : `scripts/rewrite_annex_texts.py` n'existe pas, aucun commit ne le mentionne (git log), et ADR-059 a promu v5 en prod avec "démo INRIA prioritaire". Le handoff est resté un handoff.

---

## 5. Couverture des 15 cas d'usage

| cas | couverture mesurée | verdict |
|---|---|---|
| 1. Choix de voeux post-bac | parcoursup 13 011 (91 % du brut), session 2025 | OK mais millésime 2025 et domaine "autre" pour 3 197 |
| 2. Attendus | 0 fiche parcoursup avec attendus ; 0 clé | **absent** |
| 3. Taux d'accès | 99,9 % rempli, sans définition ni verbalisation de `selectivite_code` | données OK, sémantique absente |
| 4. Coût | 0 clé coût ; 5 fiches curées en texte libre | **absent** |
| 5. Débouchés | debouches 10 % parcoursup ; insertion_pro 27 % (discipline x région, mal étiquetée) ; ROME 1 584 ; IDEO 1 075 | partiel, trompeur pour les licences |
| 6. Alternatives à la prépa | CPGE 853, BUT 820, Licence 2 654 : les fiches existent | OK côté volume ; aucune donnée de passerelle |
| 7. BUT vs licence | insersup type_diplome BUT 50, Licence générale 102 ; réussite licence = cohortes 2012/2014 bacs S/ES/L ; BUT `detail` 19/820 | faible, périmé |
| 8. Réorientation L1 | MESRI 2014 ; calendrier phase complémentaire 2026 ; aucune donnée rentrée décalée | faible |
| 9. Master sélectif | monmaster 7 573, taux_admission 99,9 %, capacité | OK ; url fallback_search 100 %, 385 taux == 0 |
| 10. Mobilité géo | ville/region seulement, 0 lat/lon, internat 93 % None, CROUS 45 fiches sans "€" | faible |
| 11. Apprentissage | LBA 4 008 inéligibles au retrieval ; CFA 4 065 sans ville ; parcoursup nom contient "apprentissage/alternance" : 3 | **quasi absent** côté formations |
| 12. Bourses / CROUS | financement 28 (4 avec échelon), DSE calendrier 5, `profil_admis.pct_boursiers` parcoursup | montants et plafonds : non mesuré (texte curé) |
| 13. Calendrier | 21 fiches 2026 | OK |
| 14. Privé vs public | statut binaire, 0 contrat/EESPIG/visa ; privé ingé+commerce 496 fiches sans coût | faible |
| 15. PASS / LAS | PASS 43, Licence_Las 286 ; aucune donnée de réussite PASS -> MMOP (grep : non mesuré exhaustivement, aucune clé dédiée) | volume OK, réussite absente |

Les audits existants (`docs/DATA_INVENTORY_2026-04-26.md`, `CORPORA_SCHEMA_AUDIT_2026-05-07.md`, INVENTAIRE C0, notes vault du 14 et 15 juin) décrivent correctement les volumes ; aucun ne relève les erreurs de verbalisation (section 4.2), l'absence des attendus, ni l'absence de coût comme trou structurel. Note vault 06-14 / 06-15 : non relues dans cette session (non mesuré).

---

## 6. Sources publiques françaises absentes ou sous-exploitées

Sans web ; appuyé sur les scripts `download_*` et les colonnes connues. Format et licence marqués "non mesuré" quand non vérifiés ici.

| source | apport pour l'agent | état dans le repo | effort estimé |
|---|---|---|---|
| Parcoursup open data, dataset formations complet (fr-esr-parcoursup, `fr-esr-cartographie_formations_parcoursup`) : attendus, éléments pris en compte, frais de scolarité déclarés, apprentissage O/N, lien fiche | attendus, coût déclaré par l'établissement, alternance | colonnes non ingérées ; `lien_form_psup` ingéré mais non verbalisé | faible (mêmes scripts, ajout de colonnes) ; format CSV, Etalab 2.0 |
| Rapports publics d'examen des voeux (par formation, parcoursup.fr) | critères réels de classement | absent ; disponibilité en open data : non mesuré | moyen à fort (scraping ou API, non vérifié) |
| Parcoursup session 2026 | fraîcheur | absent (corpus 2025) | faible : `download_parcoursup_history.sh` |
| InserSup par établissement x formation (fichier data.gouv 568 Mo) | insertion réelle par formation, pas par discipline x région | seulement 368 agrégats discipline x région ingérés | moyen ; CSV, Etalab |
| InserJeunes : niveau formation dans le CFA, poursuite d'études | apprentissage post-bac | CFA agrégé, sans ville | moyen |
| ONISEP API (formations, établissements avec adresse, coût, statut contrat) | ville des 4 758 fiches ONISEP, coût, contrat | ville 0 %, statut 2 % | moyen ; licence ONISEP : non mesuré |
| Carif-Oref (Offre Info, RCO) | formations continues et apprentissage géolocalisées | absent | moyen ; licence : non mesuré |
| data.enseignementsup : taux de boursiers, capacités, réussite licence par université (cohortes récentes), réussite PASS/LAS | cas 7, 12, 15 | réussite = cohortes 2012/2014 | faible à moyen |
| MonMaster open data (taux d'admission session 2025, lien direct) | url directe, 385 taux == 0 à corriger | url fallback_search 100 % | faible |
| Géocodage (BAN / code commune INSEE) | agglomérations Lyon/Villeurbanne/Bron | absent | faible (BAN CSV local, pas d'API) |
| Frais des écoles privées | coût | aucune source ouverte structurée connue ; Parcoursup "frais" déclaratifs est la seule piste ouverte | dépend de la source |

---

## 7. Verdict : les 5 problèmes data les plus coûteux

1. **Le texte embarqué dit faux** (section 4.2). 13 011 fiches Parcoursup portent un "taux d'accès par profil" qui est une répartition, un pourcentage "IDF" qui est un pourcentage "même académie", et 10 878 fiches portent une insertion étiquetée "apprentissage Inserjeunes CFA" alors qu'elle vient d'InserSup discipline x région. Le générateur cite ce qu'on lui donne. Preuve : `embeddings.py:40-126, 223-237, 245`, médianes `pct_aca_orig_idf` par région, Counter des sources d'insertion. Fix : corriger les 3 templates de `fiche_to_text` (renommer le champ, libellé data-driven comme dans FactCard, "répartition des admis"), ré-embarquer.
2. **Coût et nature du privé : zéro donnée** (section 2.4). 2 904 fiches privées Parcoursup, 496 écoles ingé/commerce privées, 0 clé coût, 0 clé contrat/EESPIG ; ECE est recommandée "sans coût" parce qu'il n'y en a pas. Fix : ingérer la colonne frais déclarés du dataset Parcoursup complet + statut contrat ONISEP ; à défaut, faire dire au générateur "coût non disponible, vérifier" par une FactCard qui expose explicitement l'absence.
3. **Attendus, sélectivité et lien Parcoursup non exposés** (sections 2.4, 4.1). 0 attendu ; `selectivite_code`, `lien_form_psup`, `trends`, `historique` existent et ne sont jamais verbalisés ; aucune définition du taux d'accès. C'est exactement ce qui rend "non sélective, 28 %" inutilisable. Fix : ingérer les attendus (dataset Parcoursup complet), verbaliser les 4 champs déjà présents, ajouter une phrase de définition.
4. **Classification et géographie qui cachent les bonnes fiches** (section 0). 3 197 fiches "autre" dont 49/49 BUT Informatique (`parcoursup.py:245-259`) ; villes non normalisées (Villeurbanne, Bron, "Lyon 8e  Arrondissement", MonMaster "LYON CEDEX 07"), 0 lat/lon, onisep/LBA/CFA sans ville du tout (12 831 fiches). Fix : entrée BUT dans la cascade domaine, normalisation ville + code commune INSEE + notion d'unité urbaine (BAN locale), même pour MonMaster.
5. **Corpus périmé, partiellement non régénérable, et textes annexes jamais réécrits** (sections 1, 3, 4.3). Session 2025 en septembre 2026 ; MESRI réussite licence cohortes 2012/2014 sur bacs S/ES/L ; IP-DOC 2014/2016 ; CFA majoritairement <= 2022 ; 26 % RNCP expirés marqués actifs ; CSV bruts absents du disque (pipeline non rejouable) ; ADR-058 identifie la cause racine et le fix (HANDOFF_REWRITE_ANNEX_TEXTS) qui n'a jamais été exécuté (script inexistant, 0 commit). Fix : re-télécharger 2026 (scripts existants), retirer ou dater explicitement les sources < 2021 dans le texte, exécuter le handoff de réécriture, versionner les bruts hors git (checksum + date).

Non mesuré dans cet audit : licences par source, cause des 1 241 lignes Parcoursup non ingérées, présence MIAGE dans MonMaster, comportement runtime de `geo_coherence`, contenu des deux notes vault du 14-15 juin, montants dans les fiches financement.

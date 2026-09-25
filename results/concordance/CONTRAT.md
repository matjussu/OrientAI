# Concordance avec la page publique : contrat v0.1

25/09/2026, Claudette. Ordre `2026-09-25-1320-claudette-orientai-concordance-page-publique`. Écrit avant le code et
avant le relevé complet ; aucun relevé complet, aucun juge avant le GO de Jarvis.

**Objectif** : aucun chiffre montré par OrientAI (au modèle, donc à l'élève) ne diffère de la page publique que l'élève
peut consulter, prouvé sur 100 % des formations. Puis un juge qui juge avec ces chiffres, et un rejugement de la
référence du 25/09.

**Décisions de Matteo appliquées** (Telegram 10744-10755, relayées par Jarvis) :
1. afficher exactement le chiffre et le libellé de la page publique ; pas de date à l'écran, la date de relevé en
   métadonnée ;
2. l'open data reste la source de ce que la page n'affiche pas (taux d'accès Parcoursup, mentions, historique, filtres) ;
3. le bilan final open data n'est plus montré quand la page affiche l'équivalent ;
4. **un seul chiffre par notion** dans ce que voit le modèle (cartes, `lire_fiche`, sorties d'outils) ; les doublons
   restent dans la base pour les contrôles et les filtres, jamais montrés ;
5. le lot n'ajoute aucun chiffre vu par le modèle, sauf les places de l'année en cours si Matteo les valide ;
6. périmètre inchangé (Informatique, Santé, Maths).

## 1. Mesures de départ (25/09, avant code)

- Base C : 2 939 formations Parcoursup (`psup`), 526 en apprentissage (`psup_app`), 480 masters (`mm`).
  Toutes ont `derniere_session = 2025`.
- **Chiffres vus par le modèle aujourd'hui** : `lire_fiche` (`src/base_c/outils.py`) renvoie toutes les valeurs de la
  base, et la carte B (`src/eval/format_d.py`) aussi. Valeurs numériques disponibles par fiche : `psup` médiane 49
  (23 à 81), `mm` 12 (6 à 12), `psup_app` 8. Les lignes d'insertion s'y ajoutent. Mesure : requête sur
  `valeur` (statut disponible, valeur numérique), base du 23/09.
- Inventaires de Jarvis (`~/projets/_orientai-ref/verticale-2026-09/concordance/`, 25/09) : 88 pages Parcoursup,
  40 masters. Chiffres cités ci-dessous depuis `inventaire.json` et `masters/inventaire_masters.json`.
- **Apprentissage** : la page d'une formation en apprentissage n'affiche que « N places en 2026 », sans bloc de
  chiffres d'accès. Sonde d'une seule page le 25/09 (g_ta_cod 10057) ; à confirmer au relevé complet.
- **MonMaster** : la fiche rendue affiche « Taux d'accès à la formation 12 % », « Rang du dernier appelé lors de la
  campagne précédente 11 », « Nombre de candidatures lors de la campagne précédente 92 » et « CAPACITÉ D'ACCUEIL
  15 étudiant(s) » (`masters/cache/rendu_1602282LGJWS.txt`).

## 2. Parcoursup (`psup`) : chiffre par chiffre

La page porte les chiffres de la session 2025, arrêtés à la fin de la phase principale (mi-juillet, écrit sur la
page), et l'en-tête ceux de la session 2026. Colonne « libellé » : texte exact de la page, où N est le chiffre.

| Notion | Libellé exact de la page | Champ (nouveau ou renommé) | Source | Concordance mesurée (88 pages) | Montré au modèle |
|---|---|---|---|---|---|
| Places 2026 | « N places en 2026 » | `places_annee_en_cours` (session 2026), **nouveau** | page | absent de la base | **stocké ; montré si Matteo le valide** |
| Vœux 2026 | « N vœux confirmés en 2026 » | `voeux_confirmes_annee_en_cours` (session 2026), **nouveau** | page | absent de la base | **stocké ; montré si Matteo le valide** |
| Places 2025 | « N places offertes par la formation en 2025 » | `places` (2025) prend la valeur de la page | page | 78 égaux, 4 différents | oui |
| Places, historique | (pas sur la page) | `places` 2023, 2024 | open data | - | oui |
| Candidats | « N candidats ont postulé à cette formation » | `candidats_ont_postule` (2025), **nouveau**, valeur de la page | page | = `voeux_phase_principale` 82/82 | oui |
| Candidats (open data) | - | `voeux_phase_principale` (2023-2025), gardé | open data | - | 2025 : **non** (doublon) ; 2023-2024 : oui |
| Tous vœux, phase complémentaire comprise | - | `voeux_totaux` renommé `voeux_toutes_phases_bilan_final` | open data | - | **non** (autre notion de candidats, source de confusion) |
| Classés | « La formation a classé N candidats » | `candidats_classes` (2025), **nouveau**, valeur de la page | page | = `classes_phase_principale` 61/61 | oui (page) ; open data : non |
| Refusés | « N ont donc été refusés » | aucun (différence calculée par la page) | - | - | non (n'ajoute pas de chiffre) |
| Ont pu recevoir une proposition | « N candidats ont pu recevoir une proposition d'admission » | `candidats_ont_pu_recevoir_une_proposition` (2025), **nouveau** | page | ≠ `propositions` 81/82 ; = somme ran_grp1-3 73/82 (mesure de Jarvis, message du 25/09 13h15) ; = taux d'accès x candidats 78/82 (`inventaire.json`) | oui |
| Propositions envoyées | - | `propositions` renommé `propositions_envoyees_bilan_final` | open data | - | **non** (doublon, autre définition) |
| Ont choisi d'intégrer | « N candidats ont choisi d'intégrer cette formation » | `candidats_ont_choisi_d_integrer` (2025), **nouveau** | page | ≠ `admis_total` 61/79 | oui |
| Admis au bilan final | - | `admis_total` renommé `admis_bilan_final` | open data | - | **non** (doublon) |
| Répartition des admis par bac | « Répartition par type de bac des N candidats admis de cette formation en 2025 : Bac général N % / Bac technologique N % / Bac professionnel N % / Autres diplômes N % » | `repartition_admis_bac_general`, `_techno`, `_pro`, `_autres` (2025), **nouveaux** | page | ≠ `part_bac_*` : général 44/79, techno 41/79, pro 28/79, soit 35 à 56 % des cas (dénominateurs différents : tous les admis contre néo-bacheliers admis ; et date : mi-juillet contre bilan final) | oui (4 valeurs, dont « autres diplômes ») |
| Parts de bac chez les néo-bacheliers | - | `part_bac_*` renommés `part_bac_*_neobacheliers_bilan_final` (2023-2025) | open data | - | **non** : même notion que la répartition de la page, définition différente ; l'historique n'est pas montré pour ne pas mêler deux définitions |
| Taux d'accès | (jamais affiché : 0/88) | `taux_acces` (2023-2025), inchangé | open data | - | oui |
| Mentions, boursiers, femmes, néo-bacheliers, même académie, admis début PP, parts d'accès | (mentions affichées 2/88, les autres jamais) | inchangés | open data | - | oui (inchangé) |

Autres chiffres de la page, sans champ dans la base aujourd'hui : pourcentage minimum de boursiers et de non-résidents
2026, objectif de places pour les bacheliers technologiques, pondération des critères de la commission, taux de
passage en 2e année, insertion et salaire (InserJeunes, 24/88 pages), frais annuels. **Non repris dans ce lot**
(règle 5 : aucun chiffre ajouté) ; le relevé les parse et les garde dans le cache, et le contrôle les compare aux
champs de la base qui portent la même notion (`insertion_ligne`, `cout.*`) : un écart y est traité comme les autres
(section 5).

## 3. Apprentissage (`psup_app`)

| Notion | Libellé exact | Champ | Source | Montré au modèle |
|---|---|---|---|---|
| Places 2026 | « N places en 2026 » | `places_annee_en_cours` (2026), nouveau | page | stocké ; montré si Matteo le valide |
| Places 2025, vœux, recherche de contrat, refus | (pas sur la page) | inchangés | open data | oui (inchangé) |

## 4. Masters (`mm`)

Source : l'API publique que la page appelle elle-même, sans authentification (`POST /api/candidat/mm1/formations`,
corps `{uai, inm: ifc[:8]}`), et ses libellés (`GET /api/candidat/libelles`). Chiffres de la campagne 2026 pour la
capacité, de la campagne précédente (2025) pour les indicateurs.

| Notion | Libellé exact de la page | Champ | Source | Concordance mesurée (40 masters) | Montré au modèle |
|---|---|---|---|---|---|
| Capacité d'accueil | « CAPACITÉ D'ACCUEIL N étudiant(s) » (sans année) | `capacite_accueil` (2026), nouveau | page | ≠ `capacite` 2025 dans 10/29 | oui |
| Capacité 2025 | - | `capacite` renommé `capacite_campagne_2025` | open data | - | **non** (doublon) |
| Candidatures | « Nombre de candidatures lors de la campagne précédente N » | `candidatures_campagne_precedente` (2025), nouveau | page | = `n_can_pp + n_can_pc` 26/29 (3 écarts de 1 à 2, cause non établie) | oui |
| Rang du dernier appelé | « Rang du dernier appelé lors de la campagne précédente N » | `rang_dernier_appele` (2025), nouveau | page | = `rang_dernier_appele_pc` sinon `_pp` 21/21 | oui |
| Taux d'accès | « Taux d'accès à la formation N % » | `taux_acces` (2025), nouveau pour les masters | page | = rang / candidatures 21/21 | oui |
| Taux de candidats classés, taux de propositions (masters en alternance) | libellés de l'API (`tauxClasseeCandidature`, `tauxPropositionAdmissionClassee`) | `taux_candidatures_classees`, `taux_propositions_parmi_classes` (2025), nouveaux | page | = n_clas_total / candidatures et n_prop_total / n_clas_total 8/8 | oui (remplacent le taux d'accès, que la page n'affiche pas pour eux) |
| Candidats PP, PC, rang PP | - | `candidats_pp`, `candidats_pc`, `rang_dernier_appele_pp` renommés `*_open_data` | open data | - | **non** (doublons) |
| Propositions, acceptés, parts des acceptés (femmes, licence générale, licence pro, BUT, même établissement) | (pas sur la page) | inchangés | open data | - | oui (inchangé) |

**Masters sans fiche de la campagne 2026** (11/40 dans l'inventaire ; liste complète au relevé) : champ explicite
`fiche_publique_annee_en_cours = absente`. Leurs chiffres restent ceux de l'open data 2025, **jamais présentés comme
actuels** : la carte et `lire_fiche` portent « formation absente de MonMaster 2026 ». Pour garder une seule définition
par notion, leurs candidatures, rang et taux d'accès sont calculés depuis l'open data avec la règle mesurée de la page
(candidatures = pp + pc, rang = pc sinon pp, taux = rang / candidatures) et marqués source open data.

## 5. Contrôle « concordance page publique » (bloquant, 100 % des formations)

- **Ce qu'il compare** : pour chaque formation et chaque chiffre que la page affiche, la valeur que voit le modèle
  (sortie de `lire_fiche`, après le filtre « montré au modèle ») contre la valeur relue dans la page en cache par un
  **parseur indépendant** du constructeur (motifs écrits séparément, pas d'import commun). Sans cette indépendance, le
  contrôle comparerait la base à elle-même.
- **100 %** : chaque formation tombe dans exactement une case : concordante, ou écart résiduel avec sa cause
  (catalogue fermé : page introuvable, formation fermée en 2026, bloc d'accès absent, master sans fiche 2026, chiffre
  que la page ne publie pas). Une formation hors catalogue fait rougir le contrôle. Les écarts résiduels sont listés
  un par un (`results/concordance/ecarts.json`).
- **Un seul chiffre par notion** : le contrôle vérifie aussi qu'aucun champ marqué « non » dans les tableaux
  ci-dessus ne sort de `lire_fiche` ni des cartes.
- **Témoin de sabotage** (règle 9), par levier : `ORIENTIA_SABOTAGE_CONCORDANCE=valeur` (un chiffre de page modifié
  de +1 dans la base) et `=doublon` (un champ « non » remis dans la sortie). Chacun doit faire rougir le contrôle, dans
  le même run que le passage vert.
- **Compte de chiffres vus par le modèle**, par fiche et par espace, avant et après, publié ; il ne doit pas augmenter
  (sauf les places et vœux 2026, si Matteo les valide).

## 6. Relevé des pages publiques

- Toutes les formations de la base : 2 939 + 526 pages Parcoursup, 480 masters par l'API.
- **1 requête par 1,5 s au plus**, séquentiel, `User-Agent` explicite, reprise sur cache. Durée estimée : 3 465 x 1,5 s
  ≈ 87 min pour Parcoursup et au plus 480 x 1,5 s ≈ 12 min pour MonMaster (moins si plusieurs masters partagent
  `uai + inm`).
- Cache hors dépôt (`data/raw/pages_publiques/`, ignoré par git, environ 330 Mo supposés à 97 Ko par page) ;
  **manifeste versionné** : sha256 de chaque fichier, empreinte globale, date et heure de relevé par page.
- Parseurs repris des motifs des inventaires (`inventaire.py`, `inventaire_masters.py`), testés sur les 88 pages et
  les 40 masters déjà en cache avant tout relevé.
- Échecs (HTTP, page vide) : relevés comme tels, jamais remplacés par l'open data en silence.

## 7. Base

- Construction dans `src/collect/base_etape_c.py`, qui lit le relevé en cache (aucun appel réseau pendant la
  construction).
- Table `champ` : nouvelles colonnes `montre_au_modele` (0/1) et `libelle_page` (texte exact, vide pour l'open
  data). `lire_fiche`, les cartes et les outils ne sortent que les champs `montre_au_modele = 1`.
- Renommages (section 2 à 4) : les anciens noms disparaissent de la base. Les consommateurs sont cherchés par grep
  dans `src/` et `tests/` avant le changement, et la liste figure dans la PR.
- Métadonnée : `meta.releve_pages_publiques` (date, empreinte du manifeste).
- Pas de modification du chemin servi en prod (le v1 ne lit pas la base C).

## 8. Juge et rejugement

- Fiches de référence du juge (cartes B de `results/banc_e/exposition.json`) reconstruites sur la nouvelle base :
  chiffres et libellés de la page.
- Consigne ajoutée au prompt du juge, mot pour mot : « un chiffre officiel correctement nommé n'est pas une erreur ;
  un chiffre d'un autre indicateur présenté sous un nom qui ne lui correspond pas en est une ».
- Rejugement des 113 réponses stockées de `2026-09-25_reference`, **un passage, sans régénération** (go de Matteo
  sur le plan, 10749-10753) ; nouveau `label_mapping` et nouvelle graine, verdicts dans `judge_v2/` à côté des
  premiers, qui restent intacts. Arrêt et ping à la moindre coupure.
- Addendum daté au `RAPPORT.md` de la référence : avant et après, pour chaque ligne du tableau de tête.

## 9. Ordre d'exécution et arrêts

1. Parseurs et tests sur les caches existants (gratuit).
2. **GO de Jarvis sur ce contrat**, puis relevé complet (un seul passage, en tâche de fond, reprise sur cache).
3. Construction de la base, contrôle 100 % et témoins, compte de chiffres avant et après : envoyé à Jarvis.
4. Juge : cartes reconstruites, consigne, rejugement, addendum.
5. Exports de l'explorateur (base C et mesure), REPRISE, dettes, PR.

Arrêts : relevé bloqué (erreurs HTTP en série, page qui change de structure), contrôle rouge non expliqué, coupure du
juge. Ping Jarvis à chaque arrêt.

## 10. Questions ouvertes (à trancher avant le relevé)

1. Places et vœux 2026 : montrés au modèle ou seulement stockés (décision de Matteo attendue) ?
2. Historique des parts de bac 2023-2024 (open data, néo-bacheliers) : je propose de ne pas le montrer, puisque la
   notion 2025 affichée a une autre définition. D'accord ?
3. `voeux_totaux` (toutes phases) : je propose de ne plus le montrer. D'accord ?

## 11. GO de Jarvis et ajouts (25/09 à 13h23)

Contrat v0.1 accepté. Réponses aux questions du §10 :
1. Places et vœux 2026 : **stockés, non montrés** pour l'instant (`montre_au_modele = 0`) ; Jarvis pose la question à
   Matteo, et le filtre permet de basculer sans reconstruire.
2. Historique des parts de bac 2023-2024 (néo-bacheliers) : non montré.
3. `voeux_totaux` (toutes phases) : non montré.

Ajouts :
- **A. Places 2025** : la valeur montrée est celle de la page (4/88 différentes dans l'inventaire, motif supposé :
  capacité relevée pendant la procédure). Les 4 cas de l'inventaire sont listés dans `ecarts.json` avec leurs deux
  valeurs, pour montrer que c'est ce motif et pas le parseur.
- **B. Compte de chiffres vus par le modèle** : publié au rapport avec la liste des champs montrés (médiane 49 par
  fiche Parcoursup avant ce lot). Ce lot ne fait que retirer des doublons ; le chiffre servira à l'étape 3 pour
  décider ce que `lire_fiche` renvoie par défaut.

## 12. Constats en cours de construction (25/09, avant la fin du relevé)

- **Arrondi des taux MonMaster** : l'API rend des fractions à 3 décimales (411 valeurs à 3 décimales sur 465 lues).
  Le rendu réel de deux fiches (`_orientai-ref/.../masters/cache/rendu_1501350CJ2XZ.txt`, `rendu_1501637P1WQN.txt`)
  affiche 0,125 en 13 % et 0,165 en 17 % : arrondi au demi supérieur. Le parseur arrondissait au pair (`round()`),
  défaut trouvé par le contrôle indépendant (18 écarts d'une unité), corrigé en décimal exact des deux côtés.
- **Pages Parcoursup vides** : certaines pages répondent 200 avec une coquille de 468 caractères, sans formation.
  Cause au catalogue du contrôle : `page_vide`. Elle sera **établie avant l'order-done** (demande de Jarvis) : relecture
  de ces pages à la fin du relevé, et présence ou non dans l'open data de la session en cours. Tant qu'elle n'est pas
  établie, ces formations ne sont pas présentées comme actuelles.
- **Libellés** : aucun libellé de champ ne contient « : » (la carte B découpe ses lignes au premier « : ») ; la
  répartition s'appelle « Répartition des admis, bac général » (etc.).
- **Contrôle « A dans B » du format D** (`src/eval/format_d.py`) : un chiffre du texte de corpus absent de la carte B
  est classé `doublon_non_montre` s'il existe dans un champ caché de la base pour cette formation. Limite : une
  coïncidence de valeur avec un champ caché serait classée ainsi.
- **Sorties du constructeur** : dans le worktree, les 4 sorties de la base étaient des liens vers la base du dépôt
  principal ; déliées avant toute construction, pour ne pas l'écraser.

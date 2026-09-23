# Contrat des champs de l'étape B (coût, alternance, insertion, santé)

Version 1.3.1, 23/09/2026, Claudette. La v1.3 ajoute le champ `sante` (sous-lot B-2, ordre
2026-09-23-1252) en section 10, sans changer la forme des champs de B-1 ; la v1.3.1 liste les écarts
entre la forme annoncée et la forme livrée (section 10 bis). Historique : v1 envoyée à
Jarvis au commit 93d34e2 ; écarts v1 -> v1.1 en section 0 bis, v1.2 en section 0. Périmètre B-1
confirmé par Matteo le 23/09 (Telegram 10584, relayé par Jarvis) : B1 coûts, B5 alternance, B3
insertion ; B-2 : B2 santé. B4, B6, B7, B8 et B3 bis sont hors périmètre.

Ce document fixe la forme des champs **avant** le code. L'explorateur se branche dessus ; tout
changement de forme passe par une nouvelle version de ce fichier, annoncée à Jarvis.

## 0. Changements de la version 1.2 (vérification de Jarvis et retours de Matteo, 23/09 après-midi)

- **`alternance.valeur.formations[]`** gagne `cfa_partenaire` (ce que le libellé complet Parcoursup
  ajoute à l'établissement, le plus souvent le CFA) et `precision` (`detail_forma`). Mesure : les
  doublons apparents d'une même commune étaient le même lycée avec deux CFA partenaires, pas deux
  options ; il reste des formations distinctes à libellés publics identiques, nommées par leur numéro.
- **Texte de l'alternance** regroupé par établissement ; au-delà de 5 établissements, un résumé
  (nombre de formations, d'établissements, total des places, et celles du même établissement).
- **Coût des formations en apprentissage** : `disponible`, `source.id` = `code_travail_l6211_1`,
  `rattachement` = `regle_legale_apprentissage`, `valeur.gratuit_pour_l_apprenti` = true et
  `texte_source` = « La formation est gratuite pour l'apprenti et pour son représentant légal. »
  (article L6211-1, version en vigueur depuis le 3 août 2023, lu sur Légifrance le 23/09/2026). Le
  texte dit que cette phrase ne porte que sur la formation.

## 0 bis. Changements de la version 1.1 (forme livrée)

Réponses de Jarvis aux questions Q1 à Q3 (23/09, 10h50) et défauts trouvés à la relecture :

- **Droits d'inscription** : source = tableau ministériel 2026-2027 republié par l'Université de Reims
  (PDF sha256 `b2b8c9c003d29331...`, relu le 23/09 : 178 euros pour le « cycle de licence », BUT
  listé, et pour la CPGE de lycée public). Appliqué aussi à la licence professionnelle et au DEUST
  publics (même groupe du tableau), reconnus par `type_formation`. BTS public : 0 euro de droits,
  Service-Public F36520 ; CVEC du BTS non écrite. IFSI : 0 euro seulement quand la ligne Onisep le
  dit (Q3).
- **`cout.valeur`** gagne `cvec_source` (id de la source de la CVEC, distincte de celle des droits),
  `onisep_action` et `onisep_intitule` (la ligne Onisep citée, pour l'audit).
- **Règle « même famille »** réservée aux CPGE et BTS, sur au moins deux lignes Onisep unanimes (tarif
  du lycée). Ailleurs, elle donnait le coût d'une autre formation (relecture du 23/09).
- **Intitulés** : deux options différentes d'un diplôme (option A / option B) ne se rattachent jamais.
- **`alternance.rattachement`** : une seule valeur, `meme_diplome_meme_uai_ou_meme_commune` ; chaque
  formation rattachée dit `rattachee_par` (`uai` ou `commune`). Une fiche d'apprentissage ne porte
  pas le champ `alternance` (elle EST une formation en alternance).
- **`insertion.valeur`** : `{dispositif, promotion, regime, lignes: [...]}`, une ligne par diplôme
  source (un BTS SIO a deux lignes InserJeunes, options A et B). Section 5 mise à jour.
- **Taux publiés tels quels** (44,83 reste 44,83), jamais arrondis.
- **Une insertion dont tous les taux sont non diffusés** (`nd`) est `non_disponible`, avec l'effectif
  dans la raison : sinon le remplissage compterait des fiches sans aucun chiffre.
- **Taux d'emploi stable** : gardé dans la donnée, **pas écrit dans le texte**. InserSup ne publie pas
  sa définition, et sa valeur dépasse souvent le taux d'emploi (84,6 % contre 44,8 % sur un BUT) :
  son dénominateur n'est pas le même, et on ne l'écrit pas sans le connaître.
- La granularité `discipline_etablissement` n'est pas produite : l'extrait InserSup verrouillé n'a
  que des lignes par diplôme ou par type de diplôme.

## 1. Où vivent les champs

- Corpus d'entrée : `data/processed/formations_etape_a.json` (sha256 `9eae9c25108b...`), jamais réécrit.
- Corpus de sortie : `data/processed/formations_etape_b1.json` + `formations_etape_b1.manifest.json`
  (chemin séparé ; sha remis à Jarvis à la livraison).
- Fiches concernées : **toutes** les fiches Parcoursup (`source == "parcoursup"`, 14 252), plus les
  nouvelles fiches d'apprentissage (section 4). Les gates se mesurent sur les 3 domaines tels que
  les définit l'explorateur de Jarvis (`export_data.py`, 2 395 fiches le 23/09) ; les autres
  sources (MonMaster, RNCP, corpus annexes) sont recopiées à l'identique.
- Point d'entrée du texte inchangé : `src.rag.embeddings.fiche_to_text(fiche) -> str`, même
  signature. Les nouveaux blocs sont rédigés dans `src.rag.texte_parcoursup` (déjà importé).

## 2. Enveloppe commune : une valeur sourcée

Chaque nouveau champ (`cout`, `alternance`, `insertion`) a la même enveloppe :

```jsonc
{
  "statut": "disponible",          // "disponible" | "non_disponible"
  "valeur": { ... },                // présent seulement si statut == "disponible"
  "raison": null,                   // phrase en clair si statut == "non_disponible"
  "source": {
    "id": "onisep_ideo_actions_es", // clé du verrou data/reference/sources_officielles.json
    "libelle": "Idéo-Actions de formation initiale, univers enseignement supérieur, Onisep",
    "url": "https://...",
    "licence": "ODbL"
  },
  "millesime": "2026",              // année ou période que la valeur décrit (voir chaque champ)
  "collecte": "2026-09-23",         // date de téléchargement du brut (verrou), pas la date du jour
  "rattachement": "..."             // comment la fiche a été reliée à la ligne source (voir chaque champ)
}
```

Règles :
- `non_disponible` est **explicite** : le champ existe toujours sur une fiche concernée, jamais
  absent. Une fiche sans le champ est un défaut de pipeline, pas une donnée manquante.
- `non_disponible` porte aussi `source` quand une source a été cherchée sans résultat (on sait où
  on a regardé) ; `source: null` quand aucune source n'existe pour ce type de formation.
- Aucune valeur n'est estimée, extrapolée ou héritée d'une formation voisine sans que
  `rattachement` le dise.
- Montants en euros entiers ; taux en pourcentage (0 à 100) tels que la source les publie, sans
  arrondi.

## 3. `cout` (B1)

### Forme de `valeur`

```jsonc
{
  "droits_inscription_eur": 178,        // int | null : droits annuels nationaux (établissement public)
  "cvec_eur": 105,                      // int | null
  "scolarite_total_eur": null,          // int | null : coût total du cycle, tel que publié
  "scolarite_annuel_eur": null,         // int | null : si la source donne un montant annuel unique
  "fourchette_eur": null,               // [min, max] | null : si la source publie « de X jusqu'à Y »
  "annee_tarif": "2026-2027",           // année du tarif telle que la source la date
  "gratuit_en_apprentissage": null,     // true | null : seulement si la source l'écrit
  "gratuit_boursiers": null,            // true | null : seulement si la source l'écrit
  "texte_source": null                  // texte brut ONISEP, gardé tel quel (audit à la main)
}
```

### Règles par cas, dans l'ordre d'application

| Ordre | Cas | Valeur | Source (`source.id`) | Rattachement |
|---|---|---|---|---|
| 1 | Établissement public : licence, LAS, PASS, BUT, licence pro, DEUST | droits 178 € + CVEC 105 € | `tableau_droits_2026_2027` (CVEC : `cvec_source` = `service_public_f36520`) | `constante_type_statut` |
| 1 | CPGE de lycée public | droits 178 € + CVEC 105 € | idem | `constante_type_statut` |
| 1 | BTS en lycée public | droits 0 € ; CVEC non écrite (non lue) | `service_public_f36520` | `constante_type_statut` |
| 2 | Ligne Onisep du même UAI et de la même famille, intitulé correspondant (score >= 0,8, meilleur score unique en coût, options identiques) | montants parsés + `texte_source` | `onisep_ideo_actions_es` | `onisep_uai_intitule` |
| 3 | CPGE ou BTS : au moins deux lignes Onisep de la famille au même UAI, toutes avec le même coût | idem | `onisep_ideo_actions_es` | `onisep_uai_famille` |
| sinon | tout le reste (dont école d'ingénieurs publique : aucune mesure ne couvre son cycle post-bac) | aucune, raison écrite | `onisep_ideo_actions_es` si cherché | `onisep_uai`, `onisep_uai_intitule` ou `onisep_uai_famille` |

Mesures sur lesquelles ces règles reposent :
- Montants publics : Service-Public F36520, page « vérifié le 20 août 2026 », lue le 23/09/2026
  (licence 178 €, master 255 €, ingénieur post-2018 2 620 €, CVEC 105 €, « L'inscription dans un
  BTS public ne donne pas lieu au paiement de droits d'inscription »). Référence juridique : arrêté
  du 19/04/2019.
- ONISEP : fichier téléchargé le 23/09/2026, 28 588 lignes, `AF coût scolarité` renseigné sur
  10 468 (6 138 privé, 1 432 privé sous contrat, 893 privé hors contrat, 2 005 public). Texte
  libre, trois formes lues sur un tirage de 30 lignes : « N euros en AAAA (M euros par an) »,
  « de N euros jusqu'à M euros en AAAA », mentions « gratuit en apprentissage » et « selon le
  revenu ».
- Rattachement ONISEP : pas d'identifiant commun avec Parcoursup. Clé = UAI du lieu d'enseignement
  (`ENS code UAI` = `cod_uai`) + correspondance de l'intitulé et du type. Les UAI Parcoursup 2025
  sont présents dans ONISEP pour 3 780 sur 4 058 (23/09/2026). Le taux de rattachement réel,
  formation par formation, sera **mesuré et publié** ; un rattachement ambigu (plusieurs lignes
  ONISEP de même UAI et même type, montants différents) donne `non_disponible`, jamais un choix.

### Questions ouvertes (réponse de Matteo ou de Jarvis avant le code du cas concerné)

- **Q1 BUT** : F36520 donne 178 € pour « licence et licence professionnelle » ; le BUT n'est pas
  nommé dans ce que j'ai lu. Je propose de l'appliquer au BUT **seulement** si je trouve la ligne
  qui le dit (arrêté ou page officielle), sinon `non_disponible`.
- **Q2 CVEC en BTS et en CPGE** : la page cite la CVEC pour la formation initiale et pour la CPGE ;
  pour le BTS en lycée, rien de lu. Même règle : je n'écris que ce que je trouve écrit.
- **Q3 IFSI** : l'ordre dit « IFSI = 0 € de scolarité ». La mesure qui l'appuie, ce sont les
  lignes ONISEP IFSI (« 0 euros en 2026 », 484 formations d'après `sources-donnees.md` §3.3). Je
  propose : 0 € **quand la ligne ONISEP de l'IFSI le dit**, sinon `non_disponible`. Pas de
  constante « IFSI = 0 » posée sur les IFSI sans ligne. Les droits d'inscription IFSI (178 € selon
  des résultats de recherche) ne sont pas vérifiés : non écrits.

## 4. `alternance` (B5)

### Fait mesuré qui fixe la forme

Le jeu `fr-esr-parcoursup-apprentissage` (session 2025 : 11 536 formations, modifié le 18/02/2026)
décrit des **formations Parcoursup distinctes** : 0 de ses 11 536 `cod_aff_form` n'est dans le
jeu principal `fr-esr-parcoursup` 2025 (mesure du 23/09/2026 sur les deux CSV). Une formation en
apprentissage n'est donc pas un attribut d'une fiche : c'est une autre formation, avec son propre
numéro, son établissement (souvent un CFA) et ses chiffres.

### Deux changements

**a) Nouvelles fiches** `source: "parcoursup_apprentissage"`, une par `cod_aff_form` de la session
2025, pour les formations des 3 domaines (classement par la table de domaines de l'étape A,
`src/collect/domaines.py`). Champs repris du jeu officiel, libellés officiels :

```jsonc
{
  "source": "parcoursup_apprentissage",
  "cod_aff_form": "26599",
  "fili_code": "BTS",                    // même vocabulaire que les fiches de l'étape A
  "nom": "...", "etablissement": "...", "cod_uai": "...", "statut": "Public",
  "ville": "...", "code_insee": "...", "academie": "...", "domaine": "...", "domaine_regle": "...",
  "type_formation": "...", "precision_formation": "...",
  "lien_form_psup": "https://...",
  "apprentissage": {
    "session": 2025,
    "capacite": 18,                      // capa_fin
    "candidats": 36,                     // voe_tot
    "propositions": 0,                   // prop_tot
    "voeux_recherche_contrat": 36,       // nb_rech_con
    "refus_apres_examen": 0,             // nb_ref_classe
    "refus_faute_de_place": 0            // nb_ref_place
  },
  "taux_acces_parcoursup_2025": null     // absent du jeu apprentissage : jamais recalculé
}
```

Pas de taux d'accès : le jeu ne le publie pas, et `propositions / candidats` n'en est pas un (la
définition officielle, étape A, porte sur le rang du dernier appelé). Le texte dira « taux d'accès
non publié pour l'apprentissage ».

**b) Sur chaque fiche Parcoursup scolaire**, le champ `alternance` (enveloppe section 2) :

```jsonc
"valeur": {
  "existe_en_apprentissage": true,
  "formations": [                        // formations d'apprentissage rattachées
    {"cod_aff_form": "26599", "etablissement": "...", "ville": "...", "capacite": 18, "rattachee_par": "uai"}
  ]
}
```

- `rattachement` : `meme_diplome_meme_uai_ou_meme_commune` (même filière agrégée et même spécialité,
  même UAI ou même commune INSEE) ; chaque formation rattachée dit `rattachee_par` (`uai` ou `commune`). Pas de rattachement régional ni national : « ce BTS existe en
  apprentissage à 300 km » n'est pas une information sur cette fiche.
- Sans formation rattachée : `statut: "disponible"`, `existe_en_apprentissage: false`, avec
  `rattachement` qui dit le critère employé. C'est une donnée mesurée (on a cherché dans le jeu
  officiel complet), pas une absence.
- `millesime` : `"session 2025"` ; le jeu ne contient pas 2026 (vérifié le 23/09 dans
  `sources-donnees.md` §2.3).

Conséquence pour l'explorateur : les nouvelles fiches ont `fili_code`, elles entrent donc dans
`ps = [f for f in d if "fili_code" in f]`. Leur nombre dans les 3 domaines sera donné à la
livraison ; `source` permet de les séparer.

## 5. `insertion` (B3)

### Forme de `valeur`

```jsonc
{
  "dispositif": "InserSup",             // "InserSup" | "InserJeunes"
  "promotion": "2024",                   // InserSup : "2024", "2023,2024" (cumulée)... ; InserJeunes : "cumul 2023-2024"
  "regime": "ensemble",                  // InserSup : ensemble des régimes ; InserJeunes : "voie scolaire"
  "lignes": [{                           // une ligne par diplôme source (options d'un BTS : une par option)
    "perimetre": {                       // ce que la ligne source décrit, en clair
      "etablissement": "Université Grenoble Alpes",   // InserSup : l'établissement d'inscription, tous sites
      "diplome": "RESEAUX ET TELECOMMUNICATIONS",     // libellé de la ligne source
      "type_diplome": "Bachelor universitaire de technologie",
      "granularite": "diplome_etablissement",
      "code_diplome_sise": "2400229"                  // InserJeunes : code_formation_mefstat11
    },
    "effectif_sortants": 29,             // null pour InserJeunes (non publié)
    "effectif_poursuivants": 150,        // InserSup seulement
    "indicateurs": {                     // valeur publiée telle quelle ; null = non publié (secret statistique)
      "taux_emploi_salarie_fr_6m": 41.38,
      "taux_emploi_salarie_fr_12m": 44.83,
      "taux_emploi_salarie_fr_18m": 58.62,
      "taux_emploi_stable_12m": 84.62,   // gardé, non écrit dans le texte (section 0)
      "salaire_median_net_12m_eur": null
    },                                   // InserJeunes : taux_emploi_6m, taux_emploi_12m, taux_poursuite_etudes
    "non_diffuse": ["salaire_median_net_12m_eur"]
  }]
}
```

### Granularités admises, de la plus précise à la moins précise

| `granularite` | Ligne source | Admis en B-1 |
|---|---|---|
| `diplome_etablissement` | InserSup : UAI + code diplôme SISE ; InserJeunes : UAI lycée + code formation | oui |
| `discipline_etablissement` | InserSup : UAI + discipline (tous diplômes du type) | oui, dit tel quel dans le texte |
| `discipline_region`, `national` | agrégats | **non** en B-1 : `non_disponible` |

Aujourd'hui, 4 042 fiches Parcoursup portent un `insertion_pro` InserSup rattaché au niveau
`discipline_region` avec un score de correspondance de 0,7 (corpus de l'étape A, mesure du
23/09/2026). Ce n'est pas une donnée sur la formation ; je propose de ne plus l'écrire dans le
texte des fiches Parcoursup (le champ `insertion_pro` reste dans le corpus, les autres sources ne
bougent pas). Le texte n'écrit plus que `insertion`.

### Par type de formation

| Type | Source | Remarque |
|---|---|---|
| BUT, licence, licence pro, école d'ingénieur, grade licence | InserSup, promo 2024 | `fr-esr-insersup`, modifié le 29/07/2026 |
| BTS (dont SIO, CIEL) en lycée | InserJeunes, formation fine | `fr-en-inserjeunes-lycee_pro-formation-fine`, modifié le 20/07/2026 ; clé UAI du lycée = `cod_uai` Parcoursup |
| PASS, LAS | `non_disponible` | l'insertion d'une licence n'est pas celle d'une première année santé |
| CPGE | `non_disponible` | pas un diplôme ; aucun dispositif ne la couvre |
| IFSI et paramédical | `non_disponible`, `source: null` | aucune source nationale récente par institut (`sources-donnees.md` §4.7) ; ARS régionales hors périmètre |

Définitions reprises mot pour mot des métadonnées des jeux (lues le 23/09/2026), par exemple
InserSup `tx_sortants_en_emploi_sal_fr_*` : « Part des diplômés en emploi salarié en France parmi
l'ensemble des diplômés actifs (en emploi ou en recherche) ou inactifs... » (texte complet recopié
dans le code, pas résumé).

## 6. Texte lu par le modèle

Un bloc par champ, placé après l'admission, chacun avec sa source et son millésime :

```
Coût (Onisep, tarif 2026) : 8 270 euros par an, 48 250 euros pour le cycle ; gratuit en apprentissage.
Coût (droits nationaux 2026-2027, Service-Public) : droits d'inscription 178 euros par an, CVEC 105 euros.
Coût : non disponible (aucune source officielle ouverte pour cette formation).
Alternance (Parcoursup apprentissage, session 2025) : existe en apprentissage à <établissement> (<ville>), 18 places.
Insertion (InserSup, promo 2024, BUT Informatique à l'Université X) : 58,7 % en emploi salarié en France à 12 mois ...
Insertion : non disponible (aucune source nationale par institut pour les formations paramédicales).
```

Les contrôles de l'étape A restent verts (pas de « taux d'accès par profil », pas d'« Île-de-France »
hors IDF, pas de « Inserjeunes » sur une insertion InserSup, type dit, pas de « Phase : master »).

## 7. Sources verrouillées ajoutées

Ajoutées à `SOURCES` dans `src/collect/sources_officielles.py`, donc au verrou
`data/reference/sources_officielles.json` (URL, date, sha256, octets, lignes) :

| `id` | Jeu | Licence |
|---|---|---|
| `onisep_ideo_actions_es` | Onisep, Idéo-Actions de formation initiale, univers enseignement supérieur (CSV) | ODbL |
| `parcoursup_apprentissage` | MESR, `fr-esr-parcoursup-apprentissage`, session 2025 | Licence Ouverte v2.0 |
| `insersup` | MESR, `fr-esr-insersup`, filtré aux promos et niveaux utiles (filtre écrit dans l'URL) | Licence Ouverte v2.0 |
| `inserjeunes_lycee_pro` | DEPP, `fr-en-inserjeunes-lycee_pro-formation-fine`, BTS | Licence Ouverte v2.0 |
| `service_public_f36520` | constantes recopiées dans le code, avec l'URL et la date « vérifié le » de la page | Licence Ouverte (DILA) |

ONISEP est sous ODbL : usage interne ; aucune republication de base dérivée (point juridique ouvert,
CDC §9).

## 8. Une commande

`python -m src.collect.pipeline_donnee` : contrôle des empreintes des bruts, puis étape A, puis
étape B-1. Écrit les deux corpus et leurs manifestes. Le manifeste B-1 donne, par champ et par
domaine, le taux de remplissage (`disponible` / `non_disponible`) et, pour `cout` et `insertion`,
la répartition des `rattachement`.

## 9. Ce qui sera mesuré à la livraison (rappel de l'ordre)

- Remplissage par champ et par domaine, avant (corpus A) et après (corpus B-1).
- Gate coût : 100 % des fiches des 3 domaines avec `cout` présent, `disponible` ou `non_disponible`.
- Audit : 50 fiches tirées au hasard, chaque nouvelle valeur comparée à sa ligne brute ; 30 coûts
  relus à la main contre la ligne ONISEP ; contrôle positif (l'audit rougit sur une valeur
  sabotée par levier).
- Banc vertical non régressé (présence des chiffres attendus dans le texte des fiches).

## 10. `sante` (B2, version 1.3, sous-lot B-2)

### Fiches concernées

Les fiches Parcoursup `fili_code` in (`PASS`, `Licence_Las`) : 800 dans le corpus B-1 (287 PASS,
513 LAS ; mesure du 23/09/2026 sur `formations_etape_b1.json`, sha256 `9863d2b40d3f...`). Le
champ `sante` y est **toujours présent**. Aucune autre fiche ne le porte (IFSI et paramédical
n'accèdent pas à MMOPK par cette voie).

Corpus de sortie : `data/processed/formations_etape_b2.json` + manifeste ; B-1 reste la référence
avant/après et n'est jamais réécrit.

### Forme : quatre sous-champs, chacun avec l'enveloppe de la section 2

```jsonc
"sante": {
  "passage_national":      { /* enveloppe */ },
  "passage_universite":    { /* enveloppe */ },
  "capacites_universite":  { /* enveloppe */ },
  "reforme_2027":          { /* enveloppe */ }
}
```

L'enveloppe gagne un attribut obligatoire pour ces quatre sous-champs :
`"portee": "nationale" | "universite"`. Il est posé **même** quand `statut == "non_disponible"`
(on dit à quelle échelle on a cherché).

#### a) `passage_national` (portée `nationale`)

Source : SIES, Note Flash n°31 (novembre 2025), session 2024, lue par moi dans le PDF (URL, sha256
et date de lecture au verrou). La fiche reçoit la ligne de **sa voie** (PASS ou LAS).

```jsonc
"valeur": {
  "voie": "PASS",                               // "PASS" | "LAS", celle de la fiche
  "cohorte": "néo-bacheliers inscrits en 2022", // tel que le PDF la nomme
  "session_resultats": 2024,
  "admis_mmopk_1_ou_2_ans_pct": 47.5,
  "admis_mmopk_1_an_pct": 33.8,                 // null si le PDF ne le donne pas pour la voie
  "par_filiere_1_ou_2_ans_pct": {               // null par filière si non publié ; clés fixes
    "medecine": 29.4, "pharmacie": 7.9, "odontologie": 3.6, "maieutique": 2.4, "kinesitherapie": 4.2
  },
  "ensemble_pass_las_pct": 40.1,
  "definition": "..."                           // définition recopiée du PDF, pas résumée
}
```

- `millesime` : `"session 2024 (cohorte 2022)"` ; `rattachement` : `voie_nationale`.
- Les valeurs listées ci-dessus sont celles de `sources-donnees.md` §1.1 ; elles seront **relues dans
  le PDF** avant d'être écrites dans le code, et tout écart te sera signalé.

#### b) `passage_universite` (portée `universite`)

Uniquement si l'université du panel le publie elle-même sur ses pages. Jamais déduit, jamais repris
du « taux de passage en 2e année » des fiches Parcoursup (31,0 %, probablement national, voir
`sources-donnees.md` §1.3), jamais pris sur un site de prépa ou de presse.

```jsonc
"valeur": {
  "universite": "Université de Lille",
  "voie": "PASS",                    // "PASS" | "LAS" | "PASS+LAS" : ce que la page publie
  "annee": "2024-2025",              // année que la page date
  "taux_pct": 38.2,                  // tel que publié
  "definition_publiee": "...",       // la phrase de la page qui dit ce qui est compté, mot pour mot
  "texte_source": "..."              // extrait de la page, pour l'audit
}
```

- `source` : `{id: "univ_<slug>_passage", libelle, url, date_lecture, sha256}` : une page HTML ou
  un PDF, dont l'empreinte est prise au moment de la lecture.
- Rendu dans le texte : « publié par l'université X, année Y ».
- `non_disponible` : raison = « l'université ne publie pas de taux de passage sur les pages
  consultées », avec `source.url` = la ou les pages consultées.
- Sur une page qui ne dit pas ce qu'elle compte (admis en 1 an ? inscrits ou présents ?), le taux
  est gardé avec `definition_publiee: null` et le texte dit « définition non publiée ». Je te le
  signale au cas par cas plutôt que de l'écarter en silence.

#### c) `capacites_universite` (portée `universite`)

La rentrée la plus récente que l'université publie (2026-2027, ou 2027-2028 si déjà publiée, comme
à Clermont), depuis ses pages uniquement.

```jsonc
"valeur": {
  "universite": "Université de Lille",
  "rentree": "2026-2027",            // telle que la page la date
  "total": 1234,                     // null si la page ne donne pas le total
  "par_filiere": {                   // clés fixes ; null si la filière n'est pas publiée
    "medecine":       {"total": 500, "PASS": 300, "LAS": 150, "passerelles": 50, "autres": null},
    "pharmacie":      {...}, "odontologie": {...}, "maieutique": {...}, "kinesitherapie": {...}
  },
  "voies_publiees": ["PASS", "LAS", "passerelles"],   // les voies telles que la page les découpe
  "texte_source": "..."              // extrait, ou référence de page du PDF
}
```

- Nombres **tels que publiés**. Si la page ventile autrement (LAS1 / LAS2-3 à Clermont), la
  ventilation publiée est gardée dans `par_filiere.<f>.detail` et les clés `PASS` / `LAS` ne sont
  remplies que si la page les donne ou si la somme est exacte et dite (`"somme_de": ["LAS1",
  "LAS2-3"]`).
- `rattachement` : `universite_de_la_fiche` (table de normalisation des établissements, écrite dans
  le code et publiée, ci-dessous).
- `non_disponible` : université hors panel (« hors du panel de 10 universités collectées à la main »)
  ou université du panel sans page trouvée (avec les URL consultées).

#### d) `reforme_2027`

Pointe vers une fiche concept unique, `source: "concept"`, `id: "reforme_sante_2027"`, ajoutée au
corpus :

```jsonc
{
  "source": "concept", "id": "reforme_sante_2027",
  "titre": "Réforme de l'accès aux études de santé : voie unique annoncée pour la rentrée 2027",
  "annonce": {"date": "2026-04-17", "par": "...", "source": {url L'Etudiant, date_lecture}},
  "statut_reglementaire": "annonce",        // "annonce" | "texte_publie"
  "texte_publie": null,                     // {nature, date_jo, nor, url} si publié
  "verifie_le": "2026-09-2x",               // date de ma recherche sur Légifrance et le site du ministère
  "recherches": [{"lieu": "Légifrance", "requete": "...", "resultat": "..."}]
}
```

Sur la fiche PASS/LAS : `valeur: {concept_id: "reforme_sante_2027", statut_reglementaire,
verifie_le}`, `portee: "nationale"`.

### Table de normalisation et panel de 10 universités

Le panel est mesuré sur le corpus B-1, puis **figé dans le code** (liste + mesure au manifeste).
Normalisation des libellés d'établissement Parcoursup vers l'université qui publie les capacités :
sites, antennes et composantes rattachés par motif (par exemple « Aix-Marseille Université - Site de
... », « Université de Montpellier, Antenne de Nîmes », « Ecole Universitaire de premier cycle -
Campus d'Orsay Université Paris-Saclay », « PASS Aubenas - Université Claude Bernard Lyon 1 »).

Mesure (23/09/2026, `formations_etape_b1.json`, somme de `admission.volumes.voeux_totaux` des fiches
PASS + LAS, 800 fiches, 1 618 000 vœux) :

| Rang | Université | Vœux PASS + LAS | dont PASS | dont LAS | Fiches | Part |
|---|---|---|---|---|---|---|
| 1 | Université Paris Cité | 194 591 | 145 047 | 49 544 | 32 | 12,0 % |
| 2 | Université Sorbonne Paris Nord | 117 859 | 99 672 | 18 187 | 18 | 7,3 % |
| 3 | Université de Lille | 106 288 | 82 672 | 23 616 | 24 | 6,6 % |
| 4 | Université Claude Bernard Lyon 1 | 96 247 | 80 939 | 15 308 | 20 | 5,9 % |
| 5 | Université de Montpellier | 95 375 | 85 761 | 9 614 | 27 | 5,9 % |
| 6 | Aix-Marseille Université | 81 194 | 48 827 | 32 367 | 33 | 5,0 % |
| 7 | Université Paris-Saclay | 81 100 | 71 786 | 9 314 | 15 | 5,0 % |
| 8 | Université Toulouse III | 78 181 | 65 905 | 12 276 | 24 | 4,8 % |
| 9 | Université de Bordeaux | 61 767 | 43 736 | 18 031 | 16 | 3,8 % |
| 10 | Nantes Université | 48 161 | 36 171 | 11 990 | 22 | 3,0 % |
| 11 | Sorbonne Université | 42 702 | 24 304 | 18 398 | 17 | 2,6 % |
| 12 | UVSQ | 42 367 | 34 126 | 8 241 | 14 | 2,6 % |

Le panel couvre 59,4 % des vœux et 231 fiches sur 800. Un vœu n'est pas un candidat : un même
candidat forme plusieurs vœux (options PASS, LAS) ; c'est la mesure que l'ordre demande.

### Texte lu par le modèle (bloc santé des fiches PASS/LAS)

```
Accès aux études de santé (MMOPK), chiffre NATIONAL (SIES, session 2024, néo-bacheliers inscrits en 2022) : 47,5 % des étudiants de PASS admis en médecine, pharmacie, odontologie, maïeutique ou kinésithérapie en 1 ou 2 ans ; ce n'est pas un chiffre propre à cette université.
Taux de passage publié par l'Université X (année Y) : Z %, <définition publiée>.   | ou : Taux de passage propre à l'université : non publié par l'université.
Places en MMOPK à l'Université X, rentrée 2026-2027 (site de l'université) : médecine N (dont PASS a, LAS b, passerelles c), pharmacie ...   | ou : non disponible (<raison>).
Réforme : une voie unique remplaçant PASS et LAS a été annoncée le 17/04/2026 pour la rentrée 2027 ; texte réglementaire non publié à la date du JJ/MM/2026 (voir fiche « Réforme 2027 »).
```

### Contrôles ajoutés (rougissent)

- Un taux de passage apparaît dans le bloc santé sans sa portée (« NATIONAL » ou « publié par
  l'université ») sur la même phrase.
- Un `passage_universite` `disponible` sans `source.url` ou sans `source.sha256`.
- Une fiche PASS/LAS sans le champ `sante` ou sans l'un des quatre sous-champs.
- Le 31,0 % des fiches Parcoursup apparaît comme chiffre d'une université.
- Contrôle positif : chacun est sabotable par levier et doit rougir.

### Questions ouvertes

- **Q1 LAS hors université de santé** : une partie des LAS est portée par une université sans
  faculté de santé (Paris Nanterre, Lyon 3, Paris 8...), dont les places MMOPK sont celles d'une
  faculté partenaire. La donnée ne dit pas laquelle. Je propose : pour ces LAS, national seulement,
  `capacites_universite` `non_disponible` (« faculté de santé partenaire non identifiée dans la
  donnée »). Relier chaque LAS à son partenaire demanderait une collecte en plus, hors B-2.
- **Q2 LAS du panel** : pour une LAS de l'université du panel, les places « LAS » publiées sont
  celles de toute l'université (toutes mentions de LAS confondues), pas celles de cette mention.
  Le texte le dira.
- **Q3 EUPC Guyancourt** : deux fiches LAS « Ecole Universitaire de premier cycle - Campus de
  Guyancourt, Versailles Saint Quentin en Yvelines, Université Paris-Saclay » sont rattachées à
  l'UVSQ (dont l'UFR Simone Veil - Santé publie ses propres capacités, à vérifier). Hors panel dans
  les deux cas : le classement ne change pas.

## 10 bis. Écarts de la forme livrée (v1.3.1, après la collecte)

- **Empreinte** : `passage_universite` et `capacites_universite` disponibles portent
  `source.sha256` (document verrouillé, clés `univ_*` du verrou) ; le contrôle
  `sante_*_sans_url_ou_empreinte` l'exige.
- **Une filière publiée dans un autre document** (kinésithérapie à Bordeaux et à Lyon 1) porte
  `par_filiere.<f>.rentree` et `par_filiere.<f>.source_id` ; `valeur.sources_complementaires` liste
  ces documents (id, url, sha256, filières). Le texte dit la rentrée de la filière quand elle diffère
  (« kinésithérapie 110 ... (rentrée 2025/2026) »).
- **`somme_de`** : quand `PASS`, `LAS` ou `total` est une somme de lignes publiées (LAS1 + LAS2/3,
  deux facultés à Lyon 1), les lignes additionnées sont nommées par leur chemin dans `detail`
  (séparateur « > ») ; l'audit refait la somme.
- **`note`** : précision de périmètre recopiée dans le texte (LAS des universités partenaires
  comprises à Montpellier et à Sorbonne Paris Nord, places réservées par convention exclues, rentrée
  2024 à Aix-Marseille, libellé « 2025/2026 » ambigu à Toulouse).
- **Non disponible d'une université du panel** : `source.id` = null, `source.urls_consultees` = les
  pages lues, `collecte` = date de lecture (Paris-Saclay).
- **Rentrées livrées** : 2026-2027 (ou 2026) pour 7 universités ; Toulouse 2025/2026 (dernier
  document publié) ; Aix-Marseille rentrée 2024 (dernière délibération trouvée) ; Paris-Saclay non
  disponible.
- **`passage_universite`** : aucune des 10 universités ne publie de taux de passage constaté sur
  les pages consultées ; 800 fiches en `non_disponible`. Écartés : Montpellier « minimum pass rate
  5.8% » (minimum théorique 2021-22, places / inscrits), Paris Cité « environ 50% des étudiants admis
  en filière de santé provenaient du PASS » (répartition des admis, pas un taux de passage).
- **Lecture visuelle** : deux documents sans couche texte exploitable (Nantes, scan ; Lyon 1 MMOP,
  couche texte corrompue) ; extraits transcrits de l'image par Claudette, audit NON MESURÉ sur
  l'extrait (les sommes restent vérifiées).
- **Fiche concept** : `domain: "concept_sante"`, `subject`, `text` (lu par `fiche_to_text` par le
  chemin des fiches annexes), `annonce.sources` (L'Etudiant, Service-Public A18890). Le CNESER du
  07/07/2026 n'est que dans `recherches` (presse, non vérifiée en source primaire), pas dans le texte.
- **Témoin L6211-1** : la source lue `code_travail_l6211_1` porte `temoins` (code.travail.gouv.fr,
  relu par Jarvis) ; l'étape B-2 le reporte sur les 526 coûts d'apprentissage sans réécrire B-1.


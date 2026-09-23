# Contrat des champs de l'étape B-1 (coût, alternance, insertion)

Version 1, 23/09/2026, Claudette. Périmètre B-1 confirmé par Matteo le 23/09 (Telegram 10584,
relayé par Jarvis) : B1 coûts, B5 alternance, B3 insertion. B4, B6, B7, B8 et B3 bis sont hors
périmètre.

Ce document fixe la forme des champs **avant** le code. L'explorateur se branche dessus ; tout
changement de forme passe par une nouvelle version de ce fichier, annoncée à Jarvis.

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
- Montants en euros entiers, taux en pourcentage (0 à 100, un décimal au plus), comme le texte
  les affichera.

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

| Cas | Valeur | Source (`source.id`) | Rattachement |
|---|---|---|---|
| Ligne ONISEP rattachée avec un `AF coût scolarité` renseigné | montants parsés + `texte_source` | `onisep_ideo_actions_es` | `onisep_uai_intitule` |
| Établissement public, licence / LAS / PASS / BUT à l'université | 178 € + CVEC 105 € | `service_public_f36520` | `constante_type_statut` |
| BTS en lycée public | 0 € de droits (phrase de la page) ; CVEC : voir question Q2 | `service_public_f36520` | `constante_type_statut` |
| Diplôme d'ingénieur public, cursus débuté après le 01/09/2018 | 2 620 € + CVEC 105 € | `service_public_f36520` | `constante_type_statut` |
| Tout le reste (privé sans ligne ONISEP, CPGE publique, IFSI sans ligne ONISEP...) | aucune | `onisep_ideo_actions_es` si cherché | `non_disponible` |

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
    {"cod_aff_form": "26599", "etablissement": "...", "ville": "...", "capacite": 18}
  ]
}
```

- `rattachement` : `meme_diplome_meme_commune` (même diplôme et même spécialité, même commune
  INSEE) ou `meme_diplome_meme_uai`. Pas de rattachement régional ni national : « ce BTS existe en
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
  "perimetre": {                         // ce que la ligne source décrit, en clair
    "etablissement": "Université Côte d'Azur",
    "diplome": "BUT Informatique",       // libellé de la ligne source
    "granularite": "diplome_etablissement"
  },
  "promotion": "2024",                   // InserSup : promo ; InserJeunes : "cumul 2023-2024"
  "regime": "ensemble",                  // InserSup : ensemble des régimes, sauf mention
  "effectif_sortants": 46,
  "indicateurs": {                       // null = non publié par la source (secret statistique)
    "taux_emploi_salarie_fr_6m": 50.0,
    "taux_emploi_salarie_fr_12m": 58.7,
    "taux_emploi_salarie_fr_18m": 56.5,
    "taux_emploi_stable_12m": 51.9,
    "salaire_median_net_12m_eur": null,
    "taux_poursuite_etudes": null        // InserJeunes seulement
  },
  "non_diffuse": ["salaire_median_net_12m_eur"]  // publiés « nd » par la source
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

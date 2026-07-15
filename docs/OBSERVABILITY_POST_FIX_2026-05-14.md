# Observability Multi-Axes — Spot-Check Gate 3 (correction)

**Correction du précédent rapport** : l'analyse initiale n'exploitait que l'axe LATENCY. Voici les autres dimensions présentes dans les traces que je n'avais pas regardées.

## A. Coût & tokens

- **Coût total bench** : $0.0426 (13 questions)
- **Coût moyen / question** : $0.003280
- **Tokens total in** : 111,764
- **Tokens total out** : 5,210

| Q | tokens in | tokens out | $ cost | mistral-medium | mistral-small | embed |
|---|---:|---:|---:|---:|---:|---:|
| Q01 | 4,781 | 485 | $0.002869 | $0.002865 | $0.000000 | $0.000004 |
| Q02 | 8,873 | 298 | $0.003103 | $0.002140 | $0.000958 | $0.000004 |
| Q03 | 9,133 | 272 | $0.003182 | $0.002230 | $0.000947 | $0.000005 |
| Q04 | 9,089 | 584 | $0.003720 | $0.002740 | $0.000977 | $0.000003 |
| Q05 | 9,038 | 359 | $0.003322 | $0.002374 | $0.000946 | $0.000003 |
| Q06 | 8,894 | 366 | $0.003270 | $0.002317 | $0.000949 | $0.000004 |
| Q07 | 9,294 | 732 | $0.004196 | $0.003259 | $0.000935 | $0.000002 |
| Q08 | 7,699 | 301 | $0.002659 | $0.001705 | $0.000950 | $0.000003 |
| Q09 | 9,131 | 244 | $0.003051 | $0.002068 | $0.000979 | $0.000004 |
| Q10 | 9,184 | 506 | $0.003607 | $0.002629 | $0.000975 | $0.000003 |
| Q11 | 8,702 | 288 | $0.003033 | $0.002078 | $0.000951 | $0.000003 |
| Q12 | 9,346 | 303 | $0.003260 | $0.002280 | $0.000977 | $0.000004 |
| Q13 | 8,600 | 472 | $0.003363 | $0.002410 | $0.000950 | $0.000003 |

## B. Qualité de la réponse

- **Refus détectés** : 6/13 questions (46%)
- **URLs hallucinées** : 1/13 questions concernées, 4 occurrences total (pattern `(information non disponible dans mes sources)`)
- **Mots / réponse — pass** : 138.875
- **Mots / réponse — fail** : 187.6
- **Citations / réponse — pass** : 2.5
- **Citations / réponse — fail** : 2.8

| Q | match | mots | citations | refusal | URL hallu | preview |
|---|---:|---:|---:|:---:|---:|---|
| Q01 | ✅ 5/5 | 256 | 5 | ⚠ | 0 | D’ici 2030, l’Occitanie devrait offrir des opportunités variées, mais certains s… |
| Q02 | ✅ 5/5 | 133 | 2 | — | 0 | Je comprends que tu cherches à anticiper ton budget logement pour Lyon — c'est u… |
| Q03 | ✅ 5/5 | 104 | 2 | ⚠ | 0 | Je n'ai pas d'information sur le **RNCP 38450** dans mes sources.  Les blocs de … |
| Q04 | ❌ 0/5 | 253 | 2 | ⚠ | 0 | Je comprends que tu cherches à évaluer les perspectives salariales après un **Ma… |
| Q05 | ✅ 2/5 | 150 | 4 | — | 0 | D’après tes sources, le métier d’**[actuaire](https://www.onisep.fr/http/redirec… |
| Q06 | ✅ 5/5 | 178 | 3 | — | 0 | Je comprends que tu cherches à identifier les aides financières spécifiques pour… |
| Q07 | ❌ 0/5 | 229 | 8 | — | 0 | Tu cherches des formations accessibles en Guadeloupe après le bac. Voici les opt… |
| Q08 | ✅ 1/5 | 121 | 2 | — | 0 | D’après les dernières données, le marché des cadres en Bretagne montre une dynam… |
| Q09 | ✅ 5/5 | 67 | 1 | — | 0 | Le salaire net médian d’un **cadre administratif ou commercial d’entreprise (PCS… |
| Q10 | ❌ 0/5 | 134 | 0 | ⚠ | 0 | Je préfère ne pas répondre sur ce point de manière détaillée, car ma réponse con… |
| Q11 | ❌ 0/5 | 128 | 2 | — | 0 | D’après les informations disponibles, voici les spécialités en **bac pro** liées… |
| Q12 | ✅ 5/5 | 102 | 1 | ⚠ | 0 | D’après les données disponibles, voici les taux de passage en L2 après une **L1*… |
| Q13 | ❌ 0/5 | 194 | 2 | ⚠ | 4 | Je comprends que tu cherches des éléments concrets sur les débouchés après un do… |

## C. Patterns sources retrievées (top-5 domain distribution)

Distribution agrégée des 65 sources top-5 retrievées sur les 13 questions :

| Domain | Count | % |
|---|---:|---:|
| `(formation)` | 15 | 24.6% |
| `insee_salaire` | 7 | 11.5% |
| `metier` | 6 | 9.8% |
| `metier_prospective` | 5 | 8.2% |
| `crous` | 5 | 8.2% |
| `competences_certif` | 5 | 8.2% |
| `financement_etudes` | 5 | 8.2% |
| `insertion_pro` | 5 | 8.2% |
| `parcours_bacheliers` | 5 | 8.2% |
| `metier_detail` | 2 | 3.3% |
| `apec_region` | 1 | 1.6% |

## D. Synthèse multi-axes

- **Coût** : negligible (~$0.003/question). Pas une contrainte.
- **Refus** : 6/13 — exactement les 9 fails + Q12 (qui a un refus partiel sur 'bac S supprimé')
- **URL hallu** : 1/13 — pattern toxique `(information non disponible dans mes sources)` injecté dans des liens markdown
- **Distribution sources** : explore le JSON pour voir si les fiches `(formation)` dominent même quand un domain annexe est attendu (preuve directe du diagnostic Claudette `fiche_to_text` ignore le champ `text`)

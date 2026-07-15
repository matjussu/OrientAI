# Observability Multi-Axes — Spot-Check Gate 3 (correction)

**Correction du précédent rapport** : l'analyse initiale n'exploitait que l'axe LATENCY. Voici les autres dimensions présentes dans les traces que je n'avais pas regardées.

> **Note prompt** : pipeline actuel utilise `SYSTEM_PROMPT_SPRINT11_P0_PREFIX + SYSTEM_PROMPT_V5_CORPS_PURGE` (cf `src/prompt/system.py:1240`). v3.2 reste exposé pour bench longitudinal mais n'est plus en prod. ~1k+ lignes de prompt → tokens_in 8 800/q moyen.
>
> **Note non-déterminisme** : Mistral medium tourne à T=0.3, donc 2 runs sur les mêmes 13 questions produisent des réponses différentes en mots, citations et patterns d'hallucinations. Les comptes "URL hallu" ou "refus" ne sont stables qu'avec N≥5 runs agrégés. Le SPOT_CHECK_V5 généré ce matin (Claudette) montre des URL hallu sur Q04 et Q13 dans des liens markdown qui n'apparaissent PAS dans mon bench du soir. **Ce rapport mesure 1 seul run**, à ne pas généraliser pour les métriques qualitatives volatiles.

## A. Coût & tokens

- **Coût total bench** : $0.0420 (13 questions)
- **Coût moyen / question** : $0.003227
- **Tokens total in** : 114,438
- **Tokens total out** : 4,831

| Q | tokens in | tokens out | $ cost | mistral-medium | mistral-small | embed |
|---|---:|---:|---:|---:|---:|---:|
| Q01 | 8,901 | 553 | $0.003616 | $0.002652 | $0.000954 | $0.000011 |
| Q02 | 9,350 | 200 | $0.003087 | $0.002121 | $0.000960 | $0.000006 |
| Q03 | 9,059 | 244 | $0.003093 | $0.002140 | $0.000948 | $0.000005 |
| Q04 | 8,737 | 458 | $0.003308 | $0.002320 | $0.000983 | $0.000005 |
| Q05 | 9,137 | 408 | $0.003463 | $0.002516 | $0.000944 | $0.000003 |
| Q06 | 8,928 | 361 | $0.003287 | $0.002341 | $0.000943 | $0.000004 |
| Q07 | 9,371 | 566 | $0.003883 | $0.002940 | $0.000940 | $0.000002 |
| Q08 | 7,784 | 323 | $0.002732 | $0.001777 | $0.000952 | $0.000003 |
| Q09 | 7,418 | 195 | $0.002332 | $0.001378 | $0.000943 | $0.000011 |
| Q10 | 9,347 | 307 | $0.003278 | $0.002302 | $0.000973 | $0.000003 |
| Q11 | 8,706 | 331 | $0.003143 | $0.002198 | $0.000942 | $0.000003 |
| Q12 | 9,136 | 450 | $0.003462 | $0.002478 | $0.000978 | $0.000006 |
| Q13 | 8,564 | 435 | $0.003270 | $0.002315 | $0.000952 | $0.000003 |

## B. Qualité de la réponse

- **Refus détectés** : 6/13 questions (46%)
- **URLs hallucinées** : 0/13 questions concernées, 0 occurrences total (pattern `(information non disponible dans mes sources)`)
- **Mots / réponse — pass** : 123.75
- **Mots / réponse — fail** : 149.778
- **Citations / réponse — pass** : 3
- **Citations / réponse — fail** : 1.778

| Q | match | mots | citations | refusal | URL hallu | preview |
|---|---:|---:|---:|:---:|---:|---|
| Q01 | ❌ 0/5 | 247 | 3 | ⚠ | 0 | Je comprends que tu cherches à anticiper les débouchés en Occitanie pour oriente… |
| Q02 | ❌ 0/5 | 59 | 0 | ⚠ | 0 | Je n'ai pas de formation ni d'information sur les logements CROUS à Lyon dans me… |
| Q03 | ✅ 5/5 | 93 | 2 | ⚠ | 0 | Je n'ai pas d'information sur le **RNCP 38450** dans mes sources actuelles. Les … |
| Q04 | ❌ 0/5 | 162 | 3 | — | 0 | Je comprends que tu cherches à évaluer les perspectives salariales après un **ma… |
| Q05 | ❌ 0/5 | 181 | 2 | — | 0 | Tu t’intéresses au métier d’**[actuaire](https://www.onisep.fr/http/redirection/… |
| Q06 | ✅ 5/5 | 163 | 4 | — | 0 | Je comprends que tu cherches à sécuriser ton budget pour tes études. Voici les d… |
| Q07 | ❌ 0/5 | 201 | 5 | — | 0 | Tu cherches des formations accessibles en Guadeloupe après le bac. Voici les opt… |
| Q08 | ✅ 1/5 | 123 | 3 | — | 0 | D’après les dernières données, le marché des cadres en Bretagne montre une dynam… |
| Q09 | ❌ 0/5 | 79 | 0 | ⚠ | 0 | Je n'ai pas de formation pertinente dans mes sources pour cette question, ni de … |
| Q10 | ❌ 0/5 | 113 | 0 | — | 0 | Je n’ai pas de données dans mes sources sur l’insertion après un **Bac pro Indus… |
| Q11 | ✅ 1/5 | 116 | 3 | — | 0 | D’après tes centres d’intérêt pour le secteur agricole, voici les spécialités de… |
| Q12 | ❌ 0/5 | 132 | 0 | ⚠ | 0 | Je préfère ne pas répondre sur ce point de manière détaillée, car ma réponse con… |
| Q13 | ❌ 0/5 | 174 | 3 | ⚠ | 0 | Je comprends que tu te demandes quelles perspectives s’offrent après un doctorat… |

## C. Patterns sources retrievées (top-5 domain distribution)

Distribution agrégée des 65 sources top-5 retrievées sur les 13 questions :

| Domain | Count | % |
|---|---:|---:|
| `(formation)` | 34 | 60.7% |
| `competences_certif` | 5 | 8.9% |
| `metier` | 5 | 8.9% |
| `financement_etudes` | 5 | 8.9% |
| `insertion_pro` | 5 | 8.9% |
| `apec_region` | 1 | 1.8% |
| `voie_pre_bac` | 1 | 1.8% |

## D. Synthèse multi-axes

- **Coût** : negligible (~$0.003/question). Pas une contrainte.
- **Refus** : 6/13 dans CE run — corrélés aux fails (Q02, Q03, Q09, Q12) + Q01 et Q13 qui ont fait des refus partiels avec source attribuée. Note : pattern volatile (autre run peut donner 4-8 refus selon stochastique LLM).
- **URL hallu** : 0/13 dans ce run, **mais le SPOT_CHECK_V5 régen ce matin par Claudette montre 2 cas Q04+Q13** avec `[texte](information non disponible dans mes sources)`. Pattern stochastique, mesure stable nécessite N≥5 runs.
- **Distribution sources** : 60.7% (formation) sur top-5 confirme directement le diagnostic Claudette `fiche_to_text` ignore le champ `text` des annexes. **C'est la métrique à tracker pre/post-fix C+** (cible : ~30% formation / 70% annexes sur les 10 questions où annexe attendue).

## E. Cas hors-périmètre du fix C+ (`fiche_to_text`)

**Q03 (RNCP 38450)** : retrieve top-5 ramène 5 fiches `competences_certif` ✅ mais aucun n'est le RNCP 38450 demandé (codes voisins RNCP 35298/35307/etc.). Le LLM répond "Je n'ai pas d'information sur RNCP 38450". 

C'est **problème de couverture corpus**, pas d'indexation. Le fix C+ ne corrigera pas Q03. Solution **Chantier B Claudette** (lookup déterministe par code RNCP, sur sa branche `fix/spot-check-v5-regressions-2026-05-13`) : si code absent → refus propre + redirection france-competences.fr, pas de best-match sur RNCP voisins. C'est la bonne approche pour cette classe de question.

**Q05 (actuaire ROME 4.0)** : pattern similaire — `metier` retrievé mais pas `metier_detail`. Hors-périmètre C+ aussi, à investiguer après (l'index ROME 4.0 contient peut-être seulement les libellés métiers, pas les compétences détaillées).

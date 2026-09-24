# Diagnostic de l'appel d'outil de Medium (ordre 2026-09-24-1020, phase 1), 24/09/2026

Scripts : `python -m src.eval.diag_outil_e` (réglages sur Medium) et `results/banc_e/diag_outil/diag_croise.py` (consigne explicite sur les 4 modèles). Endpoint
`https://api.eu.mistral.ai`. Même exposition gelée que D (`results/donnee_etape_d/exposition.json`, sha
`47ab40ae0e6a`), mêmes cartes C, même prompt système (`SYSTEM_PROMPT_CTX`), température 0,3, premier tour des
5 conversations de la sonde D (V-INF-01, V-SAN-08, V-MAT-03, V-INF-21, V-SAN-17). Contrôle négatif : « Merci pour
ton aide, c'est tout pour aujourd'hui. Bonne journée ! » (aucune fiche à lire). Traces : `<modele>.jsonl`, un appel
par ligne, avec horodatage, réglages, appels, fin, tokens, début et fin du texte rendu. Modèle rendu identique au
modèle demandé sur les 53 appels.

## Mesures, mistral-medium-2604 (un seul réglage change à la fois)

| réglage | tours avec appel | fin | remarque |
|---|---|---|---|
| défaut (tool_choice auto), reproduction de D | 0 / 5 | stop | négatif : 0 appel |
| reasoning_effort="high" (reco Mistral pour l'agentique) | 0 / 5 | stop | raisonne (900 à 4 800 caractères), n'appelle pas ; négatif 0 |
| tool_choice="any" (forcé) | 0 / 5 | `error` ou délai de 180 s dépassé | rédige la réponse, dégénère en boucle d'emojis, 19 063 tokens de sortie puis `error` (V-INF-01) |
| tool_choice="any" + effort high | 0 / 1 | length (4 000) | rédige |
| tool_choice="required" | 0 / 1 | length (2 000) | rédige |
| prompt système minimal (cartes seules) + question réelle, auto | 0 / 1 | stop | |
| prompt minimal + any | 0 / 1 | length | |
| **tool_choice nommé** `{"type":"function","function":{"name":"lire_fiche"}}` | **1 / 1** | tool_calls | 2 appels justes (psup:7596, psup:47455), 38 tokens |
| **consigne d'outil explicite** (ci-dessous), auto | **3 / 5, deux passages identiques** | tool_calls | 6 identifiants appelés, tous exposés et pertinents ; **négatif 0 / 2** |

## Cause établie

1. **Le forçage générique n'est pas appliqué pour Medium sur cette API** : `any` et `required` laissent le modèle
   rédiger (0 appel sur 8 essais, prompt grille ou minimal), alors que le forçage par **nom de fonction** marche du
   premier coup. Le contrôle positif du 23/09 (« Lis la fiche psup:7596 avec l'outil ») marchait parce que la
   QUESTION demandait l'outil, pas grâce au prompt minimal : prompt minimal + vraie question = 0 appel.
2. **En mode auto, Medium juge la carte courte suffisante** : la consigne de D (« pour lire la fiche complète…,
   appelle l'outil ») est descriptive ; il répond avec les chiffres de la carte (et en calcule d'autres :
   « 120 places pour 857 candidats environ, calculé à partir du taux », V-SAN-08). Le raisonnement n'y change rien.
3. Ce n'est donc pas le schéma de l'outil, ni `parallel_tool_calls`, ni la forme des messages, ni le raisonnement
   (mesurés ou écartés ci-dessus). `parallel_tool_calls=False` n'a pas été mesuré jusqu'au bout (run arrêté pendant
   les délais de `any`) : non établi, sans objet une fois la cause trouvée.

## Correctif et contrôles

Consigne explicite, qui remplace `PHRASE_OUTIL` de D pour **tous** les modèles au format C :

> Chaque fiche ci-dessous est une carte courte : elle ne contient que quelques chiffres. Avant de répondre, appelle
> l'outil lire_fiche (par exemple {"id": "psup:7596"}) pour chaque formation dont tu vas citer des chiffres, des
> conditions d'accès ou des débouchés : la fiche complète donne tous ses chiffres, sessions, sources et
> définitions. N'appelle pas l'outil si la question ne porte sur aucune formation.

Contrôle positif et négatif, même consigne, 4 modèles de la grille E (24/09 ; ces 24 appels n'ont pas d'horodatage, le script croisé ne l'écrivait pas) :

| modèle | tours avec appel (5 positifs) | appels | identifiants hors exposition | négatif |
|---|---|---|---|---|
| mistral-medium-2604 | 3 / 5 (2 passages identiques) | 5 | 0 | 0 / 1 (0 / 2 au total) |
| mistral-small-2603 | 3 / 5 | 6 | 0 | 0 / 1 |
| zai-glm-5-2 | 4 / 5 | 8 | 0 | 0 / 1 |
| zai-glm-5-3 | 5 / 5 | 15 | 0 | 0 / 1 |

Tours sans appel : V-SAN-08 (Medium, Small), V-SAN-17 (Medium, Small, GLM 5.2 ; question large « quelles options
santé hors médecin », l'appel y est discutable). **Limite** : 5 tours positifs par modèle, c'est un contrôle, pas
une mesure de taux ; le taux réel sort de la grille (79 tours).

## Coût du diagnostic (prix publiés, section Prix du protocole v0.3)

53 appels ; Medium 103 217 / 32 055 tokens = 0,39 USD (dont l'essentiel en réponses dégénérées sous `any`),
Small 0,005, GLM 5.2 0,031, GLM 5.3 0,039 : **0,47 USD**.

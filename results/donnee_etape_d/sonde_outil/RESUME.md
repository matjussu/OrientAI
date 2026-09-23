# Sonde outil du format C (protocole D v0.1, section 6), 23/09/2026

Commande : `python -m src.eval.grille_d sonde`, commit `67dab18`. Même exposition gelée
(`exposition.json`, sha `47ab40ae0e6a`), même prompt que la grille, température 0,3, outil `lire_fiche`
en `tool_choice="auto"`. 5 conversations (V-INF-01, V-SAN-08 en 2 tours, V-MAT-03, V-INF-21, V-SAN-17), soit
6 tours par modèle. Traces : `<modele>/g1.jsonl` et `manifest_g1.json`.

## Résultat

| modèle | tours avec au moins un appel | appels | erreurs d'outil | modèle rendu | coût (prix) |
|---|---|---|---|---|---|
| mistral-medium-2604 | 0 / 6 | 0 | 0 | identique | 0,017 USD (supposé) |
| mistral-large-2512 | 0 / 6 | 0 | 0 | identique | 0,021 USD |
| zai-glm-5-2 | 4 / 6 | 8 | 0 | identique | 0,064 USD (supposé, borne prudente) |

Aucune réponse vide, aucune coupée, aucun raisonnement rendu dans le contenu (0 caractère sur les
18 tours). Les identifiants appelés par GLM sont tous des fiches exposées et pertinentes pour la question
(ex. V-INF-01 : les 3 fiches attendues).

## Contrôle positif : les deux modèles Mistral savent-ils appeler l'outil ?

Un tour (V-INF-01), même prompt, `tool_choice="any"` (appel forcé), trace
`controle_positif_tool_choice_any.json` :
- **mistral-large-2512** : 11 appels, dont 1 identifiant mal formé (`"ps0989"`). Il **sait** appeler
  l'outil : en mode auto, il choisit de ne pas le faire.
- **mistral-medium-2604** : aucun appel, même forcé. Il rédige la réponse et s'arrête sur le plafond de
  tokens. Sur un prompt minimal (« Lis la fiche psup:7596 avec l'outil. »), forcé, il l'appelle
  correctement. Il **sait** donc appeler l'outil, mais pas avec ce prompt système et ces 8 cartes, même
  forcé. Cause non établie.

## Ce que ça change pour la grille (à trancher avant de jouer C)

Règle écrite avant la sonde (protocole §6) : une réponse sans appel est gardée telle quelle. Appliquée
telle quelle, C × Medium et C × Large mesurent **la carte courte seule**, pas « carte courte + outil ».
Seul C × GLM mesure le format C tel qu'il est défini.

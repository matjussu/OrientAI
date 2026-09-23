# Banc OrientAI

Le banc qui juge chaque lot du chantier OrientAI (lots 0-5, `results/jarvis_analyse_2026-09-05/REPRISE.md`)
et qui produit le tableau comparatif de la démo. Il vient de l'analyse du 05/09, versionné ici le 23/09.

## Une commande

```bash
python -m src.eval.battery bench --tag 2026-09-23_lot0 --systems local,mistral_large_norag
```

Cette commande joue les 60 conversations (67 tours) sur chaque système, les fait juger en aveugle par Opus, contrôle les
chiffres cités, puis écrit `results/battery/<tag>/REPORT.md`. Relancer la même commande reprend là où elle
s'est arrêtée. Les étapes existent aussi séparément : `run`, `judge`, `report`. `report --run-dir <dossier> --out
<dossier>` rapporte sur des runs anciens sans les modifier.

Les clés sont lues dans l'environnement, puis dans le `.env` du dépôt. Si une clé manque, la commande s'arrête avant le
premier appel.

Coût d'un passage : environ 2 USD de juge Opus par système (mesuré le 05/09 : 1,66 à 3,56 USD selon la longueur des
réponses), plus la génération. Le coût de `local` n'est pas mesuré, parce que le pipeline ne remonte pas ses tokens.

## Ce que contient un passage

| Fichier | Contenu |
|---|---|
| `manifest.json` | commit, sha256 de la batterie et du corpus, modèles épinglés, coût et durée de chaque étape. Pour `local`, l'empreinte de provenance, identique à celle que `/health` expose en prod |
| `<systeme>.jsonl` | un tour par ligne : question, historique, réponse, fiches exposées et leurs positions dans le corpus |
| `judge_opus_<systeme>.jsonl` | verdicts : 4 critères de 1 à 5, refus, erreur factuelle, cause d'échec |
| `numbers_<systeme>.jsonl` | chaque chiffre cité avec son statut |
| `REPORT.md` | tableau de tête, résultats par domaine, distributions, pires tours |

## Systèmes

| Nom | Ce qu'il mesure |
|---|---|
| `local` | le pipeline servi en prod (mode récit, historique de 6 messages) |
| `mistral_large_norag`, `mistral_medium_norag` | un modèle Mistral seul, sans fiche, avec le prompt commun |
| `claude_norag`, `gpt_norag` | plafonds de culture générale (hors produit, à titre de référence) |
| `claude_ctx` | Sonnet avec les fiches que `local` a servies : isole la génération du retrieval |
| `agent_sonnet`, `agent_mistral` | modèle à outils sur le corpus (recherche BM25 et lecture de fiche), issu du spike du 05/09 |

## Lire les métriques

- **Note du juge** : moyenne des 4 critères de Matteo (références, compréhension, expression, couverture).
  Le juge est un outil interne. La contrainte « pas de modèle américain propriétaire » porte sur le produit.
- **Chiffres adossés** : part des chiffres cités (%, €, places) présents dans une fiche que le système a
  exposée sur ce tour. La comparaison est typée : un % ne se compare qu'à des champs en %. C'est la métrique qui porte
  l'argument « chaque chiffre vérifiable ». Elle est toujours publiée à côté de son **témoin de hasard** (les mêmes
  réponses confrontées aux fiches d'un autre tour). Sur les runs du 05/09, `local` obtient 61 % pour un
  témoin à 32 % : un % entier se retrouve souvent par hasard dans une dizaine de fiches Parcoursup. Il faut donc lire l'écart
  au témoin, pas le taux seul. Un système sans fiche est à 0 % par construction.
- **Corpus seul** : chiffre absent des fiches exposées mais présent dans une des 5 fiches que la ligne désigne
  (BM25). Indicatif seulement : calibré le 23/09, cet ancrage ne retrouve que 37 à 60 % des chiffres adossés.
- **Non retrouvé** ne veut pas dire faux. Cela veut dire qu'on ne peut pas le montrer.

## Identité d'une fiche

Une fiche est identifiée par sa position dans `data/processed/formations.json` (`idx:<position>`, comme l'index
FAISS). Aucun champ ne peut servir de clé : `id` manque sur 38 596 des 52 040 fiches, et `url_canonical` n'a que
37 297 valeurs distinctes pour 42 426 fiches (mesure du 23/09). La position d'une fiche rendue par le pipeline se retrouve par
identité d'objet (`corpus.py`). Tout artefact qui porte des positions recopie le sha256 du corpus, et `Corpus` refuse
un artefact calculé sur une autre version.

## Ajouter un système

Il suffit d'écrire une classe avec `name`, `model` et `ask(question, history, key) -> dict` dans `systems.py` (ou `agent.py`), puis
de l'ajouter à `build` et `SYSTEMS`. Si la réponse n'a pas de `source_positions`, ses chiffres seront à 0 % adossés.

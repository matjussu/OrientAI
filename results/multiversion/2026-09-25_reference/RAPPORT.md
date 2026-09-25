# Référence figée du cerveau v2 : prod et ChatGPT avec recherche (25/09/2026)

Étape 1 de la feuille de route (`docs/cerveau/CONTRAT-cerveau.md` §13). Protocole : `results/multiversion/PROTOCOLE.md`
v0.3 (amendements datés §10 à §12). Chiffres : `RAPPORT.json` de ce dossier, sauf mention. Réponses gelées avant
tout verdict (commit 1bd16ef, `MANIFESTE.json` : sha256 de chaque jsonl).

**Ce que ce run est** : la photo « avant » (prod, telle que l'élève la voit) et un **repère** (ChatGPT avec recherche
web, ce que donne un modèle frontière dans une app classique ; pas une cible à battre, recadrage de Matteo du 25/09).
Il ne décide rien. Le critère qui compte pour OrientAI : le taux d'erreur factuelle.

## 1. Tableau de tête (banc vertical)

| | prod, 57 conversations (79 tours) | prod, échantillon 25 (34 tours) | ChatGPT + recherche, échantillon 25 (34 tours) |
|---|---|---|---|
| **Réponses avec erreur de fait (juge)** | **22,8 %** (18/79), IC95 [14,9 ; 33,2] | **20,6 %** (7/34), IC95 [10,4 ; 36,8] | **23,5 %** (8/34), IC95 [12,4 ; 40,0] |
| Critère 1 : chiffres attendus cités justes | 0,279 (323 attendus), témoin 0,022 | 0,230 (126), témoin 0,027 | 0,341 (126), témoin 0,018 |
| Juge, moyenne des 4 critères (1 à 5) | 2,28 | 2,24 | **4,53** |
| Refus (juge) | 25/79 | 14/34 | 0/34 |
| Chiffres affichés adossés à une fiche exposée | 72,7 % (témoin 42,8 %) | 66,7 % | non calculable (sources web) |
| Mots, médiane | 85 | 84,5 | 350,5 |
| Latence médiane / p90 | 6,6 s / 9,3 s | 6,8 s / 9,5 s | 27,0 s / 36,9 s |
| Coût réel du run | 1,03 USD (Mistral) | 0,44 USD | 6,68 USD (69 recherches) |

IC95 : Wilson (score), `export.wilson`. Critère 1 : définition de D et E (`mesures.critere1`), extracteur corrigé pour
les tableaux ; la correction ne change rien sur ce run (aucun chiffre attendu écrit en tableau : taux avec et sans
correction identiques, `taux_sans_correction_tableaux`). Contrôle positif : sans la correction, l'instrument redonne
le 0,805 / 0,068 publié par E pour C x GLM 5.3 (`tests/eval_multiversion/test_mesures.py`).

## 2. Lecture

1. **Erreur de fait : pas d'écart mesurable entre prod et ChatGPT avec recherche** sur l'échantillon (20,6 % contre
   23,5 %, IC qui se recouvrent presque entièrement ; 34 tours de chaque côté). Aucun des deux n'est sous le plancher
   du contrat (< 10 %, §8).
2. **Les erreurs ne sont pas de même nature** (`judge/verdicts.jsonl`, champ `erreur_detail`) :
   - ChatGPT : 8 fois sur 8, des **chiffres précis décalés** par rapport à la fiche officielle 2025 (propositions,
     admis, parts de bac pro : « 822 propositions contre 497 », « 29 admis contre 22 »). Non arbitré : la page web
     lue peut porter un autre indicateur ou une autre date que nos fiches ;
   - prod : surtout des **absences affirmées à tort** (« aucune formation de psychomotricité à Paris », « aucun BUT
     Informatique en Nouvelle-Aquitaine », « aucune prépa pour Valenciennes », « pas de formation de maths à
     Strasbourg ») et des erreurs de notion (la LAS présentée comme une « année de mise à niveau »), plus un taux
     d'insertion attribué alors que la fiche dit qu'il n'est pas diffusé. C'est le symptôme de la recherche actuelle
     (la bonne fiche n'est pas trouvée, contrat §1).
3. **Le juge sépare nettement les deux sur l'utilité** (4,53 contre 2,24) : réponses complètes, sans refus, de 350
   mots contre 85, et 14 refus sur 34 côté prod.
4. **Critère 1 bas pour les deux** (0,34 et 0,23) : en D et E les fiches étaient données à la main (0,8) ; ici chaque
   système trouve ses données lui-même. C'est l'écart que le v2 doit combler avec ses outils sur la base C.
5. Constat affiché à l'élève (relevé par Jarvis sur l'essai) : la prod laisse **« [source S1] »** en clair dans ses
   réponses (291 occurrences dans les 113 prompts du juge, `judge/lots/`).

## 3. Autres mesures

- **prod x lot0** (67 tours, 60 conversations, non jugé : décision du 25/09) : 0 erreur d'exécution, 0,86 USD, latence
  médiane 6,3 s, p90 9,6 s ; chiffres adossés 57,0 % (témoin 36,3 %), à comparer aux 58 % du lot 0 du 23/09.
- **Réponse structurée** (amendement C) : 2,5 % des tours prod du vertical (2/79), 0 % sur lot0, sous le seuil de
  10 % : le juge a lu le texte streamé.
- **Latence** : la prod jouée en processus sur WSL met 9,3 à 9,6 s au p90, contre 6,8 s au lot 0 du 23/09 (même
  mode de mesure, p90 recalculé au rang le plus proche) ; non expliqué, à surveiller (supposé : charge du poste).

## 4. Limites (écrites au protocole avant les résultats)

- ChatGPT = l'API GPT-5.5 (`gpt-5.5-2026-04-23`, rendu par l'API) avec l'outil `web_search`, localisation France,
  pas l'app. Photo datée du 25/09 : le modèle et le web changent.
- Juge vertical : les 8 fiches de référence de E, avec une phrase changée (« l'assistant ne les a pas forcément
  eues ») : comparaison avec E seulement approchée. Un seul passage, sans rejugement.
- Aveugle imparfait : le style trahit la version (« [source S1] » côté prod, liens entre parenthèses côté web), comme
  en D et E. Les marqueurs `utm_source=chatgpt.com` ont été retirés de la copie lue par le juge.
- Échantillon de 25 conversations : IC larges (± 13 pts environ). Il est figé
  (`results/multiversion/echantillon_vertical_25.json`) pour comparer toutes les versions futures sur la même base.
- `git_dirty` au lancement de prod x vertical : `export.py` (correctif p90) non commité ; aucun fichier joué n'a changé
  (diff b6103e0..829f1fb : `export.py` et le plafond de `lanceur.py`).

## 5. Coûts

| | Dépensé | Plafond |
|---|---|---|
| OpenAI (essai compris) | 7,07 USD | 9,5 |
| Mistral (essai et chauffe compris) | 1,94 USD | 8 |
| Juge (abonnement, Opus 5.5 effort low) | estimation 30,16 USD affichée par `claude -p`, pas une facture | un passage |

Source : `budget.json` ; juge : `judge/sorties_juges/juge_stdin_*.json`, `modelUsage` = `claude-opus-5-5` seul.

## 6. Rejouer ou comparer une nouvelle version

```
python -m src.eval.multiversion run --version <v> --banc vertical --tag <tag> [--limite <ids de l'échantillon>]
python -m src.eval.multiversion juger preparer --tag <tag>     # puis le lanceur judge/juge_stdin.sh, un lot par appel
python -m src.eval.multiversion rapport --tag <tag>
```

Une version = un module `src/eval/multiversion/versions/<v>.py`. Si le juge, la rubrique ou un banc change, on
rejuge les réponses stockées ici ; on ne les régénère pas.

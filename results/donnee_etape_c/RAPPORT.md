# Étape C : base structurée, rapport de construction (23/09/2026)

Ordres 2026-09-23-1358 (contrat) et 2026-09-23-1424 (construction), Claudette. Contrat :
`CONTRACT.md` v1.3.1 (décisions de Matteo sur Q1 à Q6 : « go reco pour tout », Telegram 10619). ADR-066.
Chaque chiffre ci-dessous renvoie au fichier qui le porte ; les rejouer : commandes en fin de rapport.

## 1. Ce qui est livré

| Livrable | Où | Mesure |
|---|---|---|
| Base SQLite | `data/processed/base_etape_c.sqlite` (hors git) | 3 945 formations, 172 981 valeurs, empreinte canonique `39f774bd5cbb` (`manifest_base.json`) |
| Manifeste | `manifest_base.json` (copie dans git) | entrées (corpus B-2 `2e6a93a5cda6`, verrou, 3 tables de référence, 5 bruts), comptes de construction |
| Export explorateur | `data/processed/base_etape_c.explorateur.json` | 13,8 Mo (13 786 516 octets), format v1.3.1 (contrat §9) |
| CSV pour tableur | `data/processed/base_etape_c_formations.csv` | une ligne par formation, en-têtes en français, UTF-8 avec BOM |
| Fonctions pour le modèle | `src/base_c/outils.py` | filtres fermés, bornes v0.1 |
| Gate C | `gate/resultats.json`, `gate/REPORT.md` | 20/20 |
| Audit | `audit/audit.json`, `audit/sabotages.json` | 18/18 contrôles verts, 8/8 sabotages rouges sur leur cible |

## 2. Contenu de la base (`manifest_base.json`, table `formation`)

- Post-bac : 3 465 fiches = 3 470 du périmètre moins 5 « ENS Paris-Saclay arts et design » exclues par
  une règle écrite et comptée (`EXCLUSIONS`, compte `exclues:M01:...` = 5).
- Masters : 480, jeu MonMaster 2025 verrouillé (`monmaster_2025`, sha `1c82acd573e8`, 8 167 lignes),
  secteurs Informatique, Mathématiques, Mathématique et informatique, Mathématiques appliquées et
  sciences sociales.
- Par type : BTS 985, LAS 513, CPGE 485, master 480, IFSI 344, PASS 287, licence 284, diplôme de santé
  185, autre 140, BUT 131, titre professionnel 57, école d'ingénieurs 40, CUPGE 14.
- Valeurs : 162 828 disponibles, 10 153 non disponibles, toutes avec leur raison (contrainte CHECK).
  Coût disponible sur 3 075 formations, insertion sur 275.
- Codes INSEE : 2 938 fiches Parcoursup et 84 d'apprentissage les tenaient du corpus ; les 442 autres
  fiches d'apprentissage sont résolues par la normalisation « 0NN » -> « NN » (442/442) ; 1 fiche
  Parcoursup reste sans commune.

## 3. Gate C (`gate/resultats.json`)

20 requêtes de Jarvis (v2, sha `227a2c9bfaf6`), traduites en filtres avant la construction
(`gate/filtres_gate_c.json`, commit 2854b52) : **20/20 justes**, 106 fiches rendues, 69 valeurs
vérifiées à l'égalité stricte, 0 écart. C14 (PASS à Poitiers) rend vide.

Témoins qui montrent que ce vert peut rougir :
- base sabotée par le périmètre de mots-clés de l'explorateur : 16/20. C12, C18, C19 et C20 tombent,
  ce sont les requêtes des 13 fiches que ce périmètre laisse dehors ;
- base sabotée sur une valeur (taux d'accès 2025 de psup:11236 : 13 devient 14) : 19/20, C05 tombe.

Jarvis a recalculé les 20 verdicts avec son propre code à partir des fiches rendues : 20/20 (message
du 23/09).

## 4. Audit (`audit/audit.json`, `audit/sabotages.json`)

Code de lecture séparé de celui de la construction : le corpus est relu par les chemins du catalogue,
les bruts par les noms officiels. Un contrôle qui compare zéro élément est rouge.

| Contrôle | Comparés | Résultat |
|---|---|---|
| Base contre corpus B-2, dans les deux sens | 166 261 | 0 écart, 0 manquante, 0 valeur de la base sans correspondant |
| Valeurs contre bruts verrouillés (Parcoursup 2023-2025, apprentissage, MonMaster) | 137 145 (psup 128 229, apprentissage 3 156, masters 5 760) | 0 écart |
| Sessions déclarées absentes, contre les bruts | 137 145 | 0 écart |
| Coordonnées contre le GPS officiel | 3 453 | 0 écart |
| Taux entre 0 et 100 | 103 479 | 0 hors bornes |
| Chaque chiffre disponible a une source | 162 828 | 0 sans source |
| Portée des chiffres de santé | 14 943 | 0 écart |
| Complétude : une ligne par formation x champ x session | 155 200 attendues | 0 manquante, 0 en trop |
| Détails sous un groupe disponible | 17 781 | 0 orphelin |
| Distance : identités (1 degré = 2πR/360, pôle-équateur = πR/2) | 2 | exactes |
| INSEE de l'apprentissage | 526 | 0 sans code |
| Témoin psup:7596 (BUT Informatique d'Aubière) | 2 | 34 %, 96 places, source cliquable |
| Couverture du gate | 106 fiches | 0 absente |
| Aller-retour base -> export -> règle de décompression | 172 981 | 0 écart, `meta.n_valeurs` exact |
| Déterminisme : deuxième construction | 1 | même empreinte canonique, fichier identique octet pour octet |

Sabotages (`ORIENTIA_SABOTAGE_C`, une base reconstruite par levier, dans un dossier temporaire) :

| Levier | Ce qu'il casse | Contrôle visé | Résultat |
|---|---|---|---|
| valeur | taux 2025 de psup:7596 (témoin) et psup:11236 (gate C05), +1 | base contre corpus | rouge (et bruts, témoin) |
| source | la source parcoursup_2024 retirée | construction | refusée (clé étrangère) |
| portee | un taux national de santé déclaré « université » | portée santé | rouge |
| geo | une latitude décalée d'un degré | coordonnées contre brut | rouge |
| perimetre | périmètre de mots-clés de l'explorateur | couverture du gate | rouge |
| absent | une ligne non disponible supprimée | complétude | rouge (et base contre corpus) |
| insee | normalisation « 0NN » retirée | INSEE de l'apprentissage | rouge |
| null_muet | une valeur NULL sans raison | construction | refusée (CHECK) |

Garanties structurelles : `source` et `null_muet` ne peuvent pas atteindre l'audit, la base refuse de
se construire. Elles sont vues refuser, pas supposées.

Vérification indépendante de Jarvis (23/09, ses copies des sources officielles) : 136 942 valeurs
égales, 0 écart ; 3 453 coordonnées égales ; témoin psup:7596 conforme.

## 5. Ce que la base ne dit pas, et pourquoi

- **Historique 2023-2024** : seulement pour les 11 champs que le corpus porte (taux, places, vœux,
  vœux en phase principale, parts de bac, mentions TB et B, boursiers, filles). Les 12 autres champs
  n'ont que 2025, et le catalogue le déclare (`sessions`). Conséquence de Q6 = B ; Q6 = A les
  ouvrirait.
- **Débouchés** : hors base (Q4).
- **Coût et insertion des masters** : non disponibles, raison écrite (l'étape B-1 couvre le post-bac).
- **Géographie** (information de l'audit, non jugée) :
  - 4 formations ont leur GPS officiel à plus de 40 km de leur commune : psup:35500 (PASS de Rennes,
    GPS près de Vannes, 94,7 km), psup:28062 (audioprothèse de Rennes, 44,8 km), psup:39284 et
    psup:42672 (orthoptie de Paris Cité, 216 km et 8 050 km, Mayotte). Hypothèse non établie :
    GPS = site d'enseignement, commune = siège. Un filtre par commune et un filtre par distance
    peuvent donc ne pas rendre la même fiche ;
  - 18 masters sans aucune coordonnée (voir CONTRACT §15).

## 6. Dettes relevées

| Dette | Trace |
|---|---|
| B-1 : département d'apprentissage sur 3 chiffres (442 fiches sans INSEE dans le corpus), contourné dans C | `manifest_base.json`, `insee_resolus_etape_c:psup_app` = 442 |
| Table A, règle M01 : 5 fiches ENS arts et design | `EXCLUSIONS` |
| 18 masters sans coordonnées | `audit.json` |
| Taille de l'export : 13,8 Mo pour une limite de 16 Mo ; découper en deux fichiers si le périmètre grandit | contrat §9 |

## 7. Rejouer

```
python -m src.collect.sources_officielles            # empreintes des bruts (dont monmaster_2025, geo_api_communes)
python -m src.collect.base_etape_c                   # base, manifeste, exports
python -m src.eval.gate_c --requetes ~/projets/_orientai-ref/verticale-2026-09/gate_c/requetes_gate_c.json
python -m src.eval.audit_base_c                      # audit + déterminisme
python -m src.eval.audit_base_c --sabotages          # 8 leviers, environ 3 minutes
OFFLINE_JUDGE_TESTS=1 pytest tests/test_etape_c.py   # 52 tests
```

Suite complète le 23/09/2026 (worktree de l'étape C, sans clés, `OFFLINE_JUDGE_TESTS=1`) : 3 529
réussis, 53 ignorés, 0 échec.

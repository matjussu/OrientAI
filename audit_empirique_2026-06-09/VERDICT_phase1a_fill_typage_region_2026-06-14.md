# Verdict — Phase 1a FILL type_diplome + région

Ordre : 2026-06-14-1230-claudette-orientai-data-phase1a-fill-typage-region
Auteur : Claudette · Date : 2026-06-14 · Branche : `dev/data-phase1a-fill-typage-region`

---

## TL;DR

Deux champs remplis EN HAUTE PRÉCISION (> rappel), sans toucher l'index FAISS
figé (gain BM25 immédiat, dense consolidé au futur ré-embed unique) :

- **type_diplome** : 0 → **18 261 fiches typées** (global 71,5 % → 36,4 % vide).
  - parcoursup : 99,9 % → **17,8 % vide** (typage via le champ STRUCTURÉ `fili_code`).
  - monmaster : 100 % → **0 % vide** (source = portail master, 100 % bac+5).
- **région** : fill **légitime ~90 fiches** seulement (Polynésie via departement).
  41,4 % → 41,2 % vide. Le reste de la vacance région est CORRECT (fiches
  nationales RNCP/ONISEP/ROME sans région par nature — on ne fabrique rien).

Précision mesurée : **99,99 %** corroboration automatique (18 259/18 261) +
**154 fiches contrôlées à la main = 100 % correct**.

---

## Règles de dérivation (reproductibles à chaque régén — câblées run_merge_v3 Stage 5.95)

Module : `src/collect/derive_fields.py`. Câblage : `run_merge_v3` Stage 5.95,
après `reclassify_social_health`. Tests : `tests/test_derive_fields.py` (24, TDD).

### type_diplome

| Signal source | Règle | type_diplome |
|---|---|---|
| `source=monmaster` | toujours (100 % bac+5 vérifié) | **Master** |
| `source=parcoursup`, `fili_code=BTS` | mapping direct | **BTS** |
| `fili_code=BUT` | mapping direct | **BUT** |
| `fili_code=Licence` | mapping direct (+ raffinage si intitulé "licence pro") | **Licence** / **Licence professionnelle** |
| `fili_code=Licence_Las` | L.AS = licence accès santé | **Licence** |
| `fili_code=CPGE` | mapping direct | **CPGE** |
| `fili_code=Ecole d'Ingénieur` **ET `niveau=bac+5`** | gate niveau (voir ci-dessous) | **Diplôme d'ingénieur** |
| `fili_code=IFSI` | institut de formation soins infirmiers | **Diplôme d'État infirmier** |
| `fili_code` ∈ {Autre formation, EFTS, Ecole de Commerce, PASS, None} | AMBIGU | **vide** |
| autres sources (rncp, onisep...) | hors scope phase 1a | **inchangé** |

**N'écrase jamais** une valeur type_diplome existante.

**Pourquoi `fili_code` et pas un regex sur l'intitulé** : `fili_code` est le champ
de filière STRUCTURÉ de Parcoursup (autorité source). Un regex sur le `nom` tombe
dans des pièges graves — ex. le token "DE" (Diplôme d'État) matche la préposition
française "de" dans 31 % des intitulés ("histoire **de** l'art"). Précision
structurée >> précision lexicale.

**Gate niveau sur Ecole d'Ingénieur** : ce `fili_code` conflate le cycle prépa
intégré (bac+1-3) ET le cycle ingénieur (bac+5) sous un seul code. Seul le bac+5
délivre le diplôme d'ingénieur. Les 63 fiches bac+3/niveau-absent ("Formation
Bac + 3") sont des entrées de cycle prépa → laissées VIDE. Sans ce gate, la
précision ingénieur tombait à 87,2 % ; avec, 100 %.

### région (geocode_region)

- **Map apprise du corpus** : pour chaque `departement` observé avec UNE seule
  `region` dans le corpus → on l'applique aux fiches du même departement sans
  région. Départements ambigus (2 régions observées) → jamais remplis. Sortie au
  format d'affichage EXACT du corpus (pas de normalisation).
- **Supplément overseas** : COM auto-nommées jamais labellisées ailleurs
  (Polynésie française, Nouvelle-Calédonie, Saint-Pierre-et-Miquelon...).
- **N'écrase jamais** une région existante. Sans departement résoluble → vide.

**Pourquoi la région est un quasi no-op (et c'est correct)** : 95 % de la vacance
région vient de fiches NATIONALES (rncp 5181, rncp_blocs 4891, onisep 4758, rome
1584, métiers, doctorat...) qui n'ont pas de région par nature. Les remplir =
fabriquer une donnée fausse (violation précision > rappel, dégrade le refus
honnête). Les seules sources géo-portées sont déjà remplies (parcoursup 99,3 %,
monmaster 100 %). Le seul fill légitime = 93 parcoursup région-vide, dont ~90
Polynésie (departement="Polynésie française") + 3 Étranger (restent vides). Le
levier géo réel est au query-time (`geo_coherence` ville→région), pas au fill.

---

## Précision (contrôle)

Corroboration automatique nom ↔ type assigné sur la TOTALITÉ des typées :

| type | corroborés | % |
|---|---|---|
| BTS | 5350/5350 | 100,00 % |
| BUT | 820/820 | 100,00 % |
| Licence | 2938/2940 | 99,93 % |
| CPGE | 853/853 | 100,00 % |
| Diplôme d'ingénieur | 382/382 | 100,00 % |
| Diplôme d'État infirmier | 343/343 | 100,00 % |
| Master | 7573/7573 | 100,00 % |
| **GLOBAL** | **18 259/18 261** | **99,99 %** |

Les 2 seuls résidus : Licence_Las bac+5 "Formation d'ingénieur Cycle préparatoire
intégré - Accès Santé" → typés "Licence" (l'option LAS EST une licence ; défendable,
non clairement faux). Gater les 12 Licence_Las bac+5 aurait dropé 10 vraies LAS
pour en corriger 2 → recall perdu > précision gagnée, abandonné.

Contrôle MANUEL : échantillon stratifié 154 fiches (~22/type) lues à la main =
**100 % cohérent** (Master/mention, BTS, BUT, CPGE/MPSI-PCSI-BCPST, D.E Infirmier,
Licence, ingénieur tous bac+5 post-gate).

---

## Couverture avant → après (% vide)

| Mesure | Avant | Après |
|---|---|---|
| type_diplome global | 71,5 % | **36,4 %** |
| type_diplome parcoursup | 99,9 % | **17,8 %** |
| type_diplome monmaster | 100,0 % | **0,0 %** |
| région (eligible) | 41,4 % | 41,2 % |

Le 17,8 % parcoursup restant = les codes ambigus laissés vides volontairement
(Autre formation 1770, EFTS, Ecole de Commerce, PASS, prépa-cycle ingénieur).

---

## Retrieval BM25 avant → après (gain GRATUIT, sans ré-embed)

Probes = vraies questions discriminées par le type. BM25 rebuild local ($0).

**Master** (le token "master" était ABSENT des noms monmaster avant fill) — fiches
on-type dans le top-20, sommé sur 8 probes : **55 → 129** (×2,3). Rang du 1er
résultat on-type : "master marketing" 12→1, "master finance" 5→1, "master RH" 4→1.

**Parcoursup** (type déjà dans le nom) : quasi plat, honnête — "licence economie
gestion" 20→20, "BTS comptabilité" 18→18, "BUT info ou prépa MPSI" 0→3. Le gain
est concentré là où le token de type manquait (monmaster), marginal là où il était
déjà présent (parcoursup nom).

---

## Stratégie & garde-fous

- **Baseline-safe** : aucun ré-embed (index FAISS figé byte-identique, gel 497q
  intact). type_diplome est dans fiche_to_text (path formation) + BM25 → gain BM25
  immédiat, gain dense automatique au futur ré-embed unique (aucune modif du fichier
  protégé fiche_to_text).
- **Précision > rappel** : vide laissé au moindre doute. Zéro fiche fabriquée.
- **Reproductible** : `formations.json` gitignored (régénéré). Correction appliquée
  localement (backup `formations.json.bak-pre-derive-20260614`) ET inscrite dans le
  code (Stage 5.95 câblé dans run_merge_v3) → reproductible à `python -m
  src.collect.run_merge_v3`, comme le fix ROME J11 (#146).
- **Tests** : 24 tests TDD (derive_fields) verts + 34 merge verts, zéro régression.
  Les 8 échecs `test_judge_faithfulness` sont du bruit LLM-juge pré-existant
  (fixtures inline, n'importent pas derive_fields, ne lisent pas le corpus ; 1 seul
  échec sur le run corpus-backup vs 8 sur un autre run = variance de génération).

## Résidus / TODO (post-VivaTech, candidats)

1. type_diplome sur rncp (44 % vide), inserjeunes, lba (dormante) : hors scope
   phase 1a (priorité parcoursup+monmaster). Candidat pour l'audit couverture 1245.
2. EFTS (242) → DE travail social : mappable si on accepte une granularité
   "Diplôme d'État (travail social)" générique. Laissé vide par prudence.
3. Noms ingénieur génériques ("Formation d'ingénieur Bac+5") sans discipline →
   retrieval faible sur "ingénieur [spécialité]" (probe aéronautique 0→0). C'est
   une maigreur d'intitulé, pas un défaut de typage.

# Verdict — C2b collecte salaire (InserSup + doctorat)

Ordre : 2026-06-11-1957-claudette-orientai-c2b-collecte-salaire
Auteur : Claudette · Date : 2026-06-11 · Branche : `feature/c2b-salaire-insersup-doctorat`

---

## TL;DR

`insertion_pro.salaire_median_embauche` passait de **0** fiche peuplée à **4055**
fiches avec un salaire net médian RÉEL (valeur source, ZÉRO agrégation maison) :
- **InserSup** : 3854 masters MonMaster, salaire net médian par formation.
- **Doctorat** : 201 fiches ip_doc, salaire net médian exposé depuis le top-level.

Sans ré-embed (index FAISS figé, fact_card surface le salaire au contexte servi).

---

## Sources & câblage

Le pipeline `insertion_pro.salaire_median_embauche` était déjà câblé (embeddings +
fact_card) mais jamais alimenté (agrégats Céreq-par-niveau retirés ADR-054). C2b =
COLLECTE, pas câblage.

- **InserSup** (`data/raw/insersup.csv`) : "Salaire mensuel net médian en équivalent
  temps plein" par établissement × type × discipline. Le salaire n'existe QUE dans
  ce CSV local (le chemin API processé l'avait dropé). Nouveau module
  `src/collect/insersup_salary.py`.
- **Doctorat** (`ip_doc_doctorat`) : `salaire_net_median_mensuel` top-level ->
  `insertion_pro` via `build_doctorat_insertion_pro`.

`_format_insertion_pro` (embeddings) sort désormais le salaire pour tout schéma
(branche salaire-direct) -> retrievable au futur ré-embed. fact_card lisait déjà
`insertion_pro.salaire_median_embauche` (aucun changement).

---

## Join InserSup — précision (audit Jarvis)

- **Clé par-formation** : `(établissement-nom | UAI, bucket de type, libellé canonique)`.
  Libellé canonique = minuscule sans accents, suffixe parcours strippé, préfixe de
  type strippé, appliqué SYMÉTRIQUEMENT fiche↔InserSup.
- **100% exact-match normalisé, ZÉRO fuzzy.** Méthode : `name_libelle` (MonMaster).
  Parcoursup = 0 match (libellé BUT/LP trop divergent du nom de fiche pour un
  exact-match sûr) -> couverture master-only assumée, aucun match douteux forcé.
- **Filtre tranche AGRÉGAT** : seules les lignes `Genre=Nationalité=Régime=Obtention=
  "ensemble"` sont indexées (les ventilations femme/homme/français/apprentissage/
  diplômé sont écartées AVANT join -> pas de salaire de sous-population mal-étiqueté).
  Verrouillé par `test_build_salary_index_keeps_only_ensemble_slice`.
- **Freshest-promo** : sur clé multi-cohortes, on retient l'année la plus récente,
  TRACÉE par fiche dans `insertion_pro.salaire_cohorte` (citation d'année possible,
  cf détresse-006). Doctorat : année tracée dans `insertion_pro.cohorte` depuis
  `annee_cohorte` (2014/2016 selon la fiche) — fix résidu audit Jarvis #1957.
- **Ambiguïtés** : 68 clés distinctes (60 bucket ingénieur + 8 bucket master) ont des
  valeurs ensemble divergentes (le compteur d'insertion en logue 76 events, dont des
  triples). **0 (zéro) des 4055 fiches enrichies ne touche une clé ambiguë** (vérifié).
  Donc 4055 salaires source uniques et non-ambigus.

Exemples vérifiables (CSV brut) :
- ACTUARIAT master, Le Mans Université -> 2810€ net 12m (promo 2022). Sorbonne 3280€,
  Lyon-1 3150€, UBO 3170€.
- METHODES INFORMATIQUES APPLIQUEES A LA GESTION (MIAGE) master -> Paris1 2760€,
  Lille 2370€, Grenoble 2420€ (promo 2022).
- ADMINISTRATION ECONOMIQUE ET SOCIALE master (parcours multiples) Strasbourg ->
  1870€ net 12m promo 2020 (salaire au grain mention, parcours = sous-tracks).

---

## Couverture (honnête)

| Niveau | Couvert ? | Détail |
|---|---|---|
| Master (MonMaster) | OUI | 3854 fiches, join nom+libellé |
| Doctorat (ip_doc) | OUI | 201 fiches, valeur top-level source |
| BUT / Licence / Licence pro | NON | parcoursup libellé non-joignable en exact-match sûr |
| Ingénieur (formation) | NON | bucket non attaché (ambiguïtés libellé génériques) |
| Métier (data scientist, avocat...) | NON | hors scope formation (proxy PCS / RÈGLE 6) |

**Impact sur le subset eval salaire** (mesure honnête, pas d'inflation) : 20 questions
fact-salaire (formation) = 4 master (COUVERTES, ex MIAGE) + 8 licence + 4 BUT + 4
ingénieur (NON couvertes) ; + 40 questions métier-salaire hors scope. L'enrichissement
remplit la lacune au niveau MASTER+doctorat ; les autres niveaux restent un trou
structurel (salaire formation pas massivement public hors master/doctorat). Le proxy
PCS encadré RÈGLE 6 reste le fallback, couverture partielle intégrée sans trou nouveau.

---

## Garde-fous & stratégie

- **Anti-confabulation** : zéro salaire inféré/moyenné maison. Uniquement des valeurs
  présentes dans les datasets, tranche ensemble, net étiqueté source (`salaire_net=True`).
- **Baseline-safe** : pas de ré-embed (index FAISS figé byte-identique, retrieval gel
  497q intact). Le salaire est dans le contexte servi (fact_card le lit live).
- **Saves instrument** (réflexe [[feedback-validate-measurement-instrument]]) : 3 fois.
  (1) Gate diagnostic 0 -> artefact type_diplome vide + entrée≠sortie -> vrai join 8892.
  (2) 1er enrichissement 4612 -> clé domaine large, 5489 collisions arbitraires ->
  raffiné clé libellé -> 4055 propre. (3) mesure eval 16/20 -> matching keyword
  grossier (faux) -> caractérisation honnête par niveau -> 4/20 master réellement couvert.

## Chiffrage re-embed (GATÉ Matteo)

- Marginal : 4055 fiches enrichies = ~473k tokens (6.5% du corpus eligible 7.27M tokens).
- Le pipeline ne fait que du **rebuild FULL** (`python -m src.rag.embeddings`, pas de
  re-embed partiel) -> coût pratique = full ≈ **$5-10** (figure projet documentée ;
  un re-embed partiel coûterait ~$0.3-0.65 mais demande d'ajouter le support incrémental,
  hors scope). Le full consoliderait aussi le fix social #146 dans l'index.
- **Recommandation** : gel jusqu'au GO Matteo. Sans ré-embed, le salaire est servi au
  contexte (réponse sourcée quand la fiche est retrouvée) mais ne boost pas le retrieval
  des questions salaire.

## Résidus / TODO (post-VivaTech)
1. Salaire BUT/licence pro/ingénieur : join libellé parcoursup→InserSup (normalisation
   plus poussée ou table de correspondance). Candidat.
2. Support re-embed PARTIEL (incrémental) pour éviter le full $5-10 sur petits deltas.
3. Quartiles Q1/Q3 InserSup (déjà dans le CSV) non encore exposés — enrichissement futur.

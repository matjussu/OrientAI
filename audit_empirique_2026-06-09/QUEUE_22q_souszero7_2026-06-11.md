# Queue 22q sous 0.7 groundedness (gel 497q) — root-cause + table (ordre 1800)

Diagnostic des 22 réponses asserting <0.7 du gel. Catégorisation depuis les notes du juge
(claim par claim). Cause racine primaire (beaucoup de cas chevauchent generation+data+judge).

## Table

| id | cat | cause racine primaire | détail | fix candidat | effort |
|---|---|---|---|---|---|
| comp-001-v2 | comparaison | GÉNÉRATION | définit classements (L'Étudiant/QS/Shanghai) + pratiques Parcoursup/ONISEP, hors fiches | anti-méta-élaboration | moyen |
| comp-004-v1 | comparaison | GÉNÉRATION | idem (méta-connaissance classements) | idem | moyen |
| comp-007-v2 | comparaison | GÉNÉRATION | idem | idem | moyen |
| malform-006-v1 | mal_formulee | GÉNÉRATION | idem (classements/sources) | idem | moyen |
| malform-006-v2 | mal_formulee | GÉNÉRATION | idem | idem | moyen |
| reconv-002-v1 | reconv | GÉNÉRATION | DÉFINIT la VAE (5 claims non sourcés, hallu_num=True sur "1607h") — RÈGLE 7 inerte ici | renforcer/déterministe anti-définition | moyen |
| reconv-002-v3 | reconv | GÉNÉRATION | définit la VAE (idem, plus court) | idem | moyen |
| base-005-v2 | baseline | GÉNÉRATION | définit l'alternance (général, hors fiches) | anti-définition | moyen |
| base-001-v1 | baseline | GÉNÉRATION | "BUT dure 3 ans" + nature BUT (connaissance générale ; admet l'absence source) | anti-élaboration | faible |
| base-001 | baseline | GÉNÉRATION | "BUT dure 3 ans" (même, admet l'absence) | idem | faible |
| metier-018 | metier | GÉNÉRATION | "IDE -> IFSI, Parcoursup" hors fiches ROME | anti-élaboration métier | moyen |
| reconv-004 | reconv | GÉNÉRATION | "prépare aux concours" non dans S2 | anti-interprétation | faible |
| reconv-004-v3 | reconv | GÉNÉRATION | "idéal pour premier pas", "technique et encadré" = interprétation subjective | anti-interprétation | faible |
| fact-025-v1 | factuelle | GÉNÉRATION+DATA | fabrique date Parcoursup (2026 pour Q 2025), AUCUNE source calendrier | refus si pas de source calendrier + DATA calendrier | moyen |
| fact-015-v3 | factuelle | GÉNÉRATION+RETRIEVAL | "lycées bordelais MPSI Montaigne/Michel-Montagne" : Montaigne=cycle prépa bac+5 (mal-attribué), Michel-Montagne absent (mémoire). Écho backlog MPSI/PCSI ranking | fix ranking CPGE-ville + anti-mémoire | élevé |
| reconv-001 | reconv | JUDGE/DATA | "accessible en VAE" : S3/S5 disent "Par expérience" (= la voie VAE !). Inférence SÉMANTIQUEMENT correcte, juge littéral | normaliser corpus "Par expérience"->VAE OU juge accepte l'équivalence | moyen (data) |
| reconv-004-v1 | reconv | JUDGE/DATA | idem (voies_acces formation continue/contrat/expérience -> "dispositifs") | idem | moyen |
| malform-004-v1 | mal_formulee | JUDGE/DATA | "VAE/alternance" : S2 a apprentissage+expérience pas le mot "VAE" | idem | moyen |
| reconv-004-v2 | reconv | GÉNÉRATION | "accessible après bac+3 paramédical" : prérequis non dans S1 | anti-élaboration prérequis | faible |
| base-005 | baseline | **JUGE (faux positif)** | "3,2%" vs S1 3,16% et "1,3%" vs 1,31% : ce sont des ARRONDIS CORRECTS à 1 décimale, le juge les flague à tort "arrondi incorrect" | aucun (erreur juge) — calibrer le juge sur l'arrondi | faible |
| geo-005-v1 | edge_geo | **JUGE (incohérence)** | groundedness 0.50 mais n_unsup=0 (aucun claim non supporté listé) = résidu d'incohérence rubrique | vérifier le calcul groundedness vs claims | faible |
| geo-011-v1 | edge_geo | **JUGE (incohérence)** | groundedness 0.67 mais n_unsup=0 (idem) | idem | faible |

## Verdict — répartition des 22

- **GÉNÉRATION (over-élaboration) : ~14** (dominant). Le modèle comble les fiches éparses (qui n'ont
  que des données de formation, pas de définitions de concepts) avec sa connaissance paramétrique :
  définit VAE/alternance/BUT, généralise débouchés, interprète la pertinence. C'est le MÊME pattern
  transversal. RÈGLE 7 (anti-définition reconversion) déjà présente mais PARTIELLEMENT INERTE
  (reconv-002 définit toujours la VAE) = confirme la leçon "règle additive seule ne renverse pas un
  comportement ancré". Levier sérieux = soit déterministe (refus/strip si un claim n'a pas de source
  token), soit accepter ces méta-élaborations comme basse-sévérité (elles ne fabriquent pas de
  chiffres faux, sauf reconv-002 "1607h" et fact-025 date).
- **JUGE : ~5.** (a) Strictness sémantique VAE vs "Par expérience" (reconv-001/004-v1/malform-004-v1 :
  inférence correcte, juge littéral) ; (b) faux positif arrondi (base-005 : 3,16->3,2 EST correct) ;
  (c) incohérence groundedness<1 sans claim non supporté (geo-005-v1, geo-011-v1).
- **DATA : ~3** (chevauchent). Cluster "Par expérience au lieu de VAE" dans voies_acces = candidat
  NORMALISATION CORPUS qui résoudrait generation ET judge d'un coup. + pas de source calendrier
  Parcoursup (fact-025). + (hors 22, à g=0.75) la mis-mapping ROME CESF->médical de detresse-prec-007.
- **RETRIEVAL : ~1** (fact-015 MPSI Bordeaux, écho backlog ranking CPGE-par-ville).

## Cross-référence data (pour Jarvis)

2 classes de bugs corpus isolées, à croiser avec ton analyse data :
1. **ROME débouchés mal-mappés** : detresse-prec-007 (CESF social -> ROME médicaux J11xx, domaine=sante).
   Probablement une classe de formations sociales mal-mappées. Fix data = règle 007 à la racine.
2. **voies_acces "Par expérience" pas normalisé en VAE** : cluster reconv-001/004-v1/malform-004-v1.
   Si "Par expérience" / "formation continue" -> tag VAE explicite dans le corpus, generation ET judge
   s'alignent (~4 cas résolus, et c'est correct sémantiquement).

## Note méthodo

Les 5 cas JUGE (base-005 arrondi, geo n_unsup=0, VAE-littéral) suggèrent que groundedness 0.949
SOUS-ESTIME légèrement la vraie fidélité (quelques faux positifs juge dans le tail). À confirmer en
re-lisant les sources de base-005 + geo-005-v1 demain (non bloquant).

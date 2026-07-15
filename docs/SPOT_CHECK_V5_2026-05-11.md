# Spot-check Gate 3 v5 — 2026-05-11

> Phase C.5 (BLOQUANT pour promotion v5). 13 questions ciblées sur
> les domaines précédemment dormants. Évaluation manuelle requise.

## Résumé exécutif

- **Questions testées** : 13
- **Questions avec domain attendu présent dans top-5** : 4/13
- **Erreurs runtime** : 0
- **Corpus** : `data/processed/formations_v5.json`
- **Index** : `data/embeddings/formations_v5.index`

## Critère pass (manuel)

Pour chaque question, vérifier :
1. La réponse n'est pas "info non disponible" (sauf si vraiment data absente)
2. Les chiffres cités sont accompagnés de `[source SX]` (R3)
3. Le top-K retrieve contient au moins 1 fiche du domain attendu
4. Pas d'invention de fiche / établissement / chiffre absent du corpus (R1, R2)

## Détails par question

### Q1 — Quels métiers vont recruter en Occitanie en 2030 ?

**Domain attendu** : `metier_prospective` (DARES Métiers 2030 — projections recrutement par région)

**Top-5 domain match** : ⚠ 0/5 fiches du domain attendu
**Citations [source SX]** : 0
**Latence** : 4.72s

**Top-5 sources retrievées** :
```
```

**Réponse du pipeline** :

```
Je n'ai pas de données dans mes sources sur les métiers qui recruteront en Occitanie en 2030, ni sur les formations locales menant à ces secteurs.

Pour explorer cette question, je te conseille :
- Le site **[Projections Métiers Occitanie](https://www.orientationpour tous.fr/)** (études régionales de Pôle Emploi et Carif-Oref)
- Les rapports de la **Direccte Occitanie** sur les besoins en compétences
- Un rendez-vous avec un·e conseiller·ère du **CIO** ou de la **Mission Locale** de ton département

Quels domaines t’intéressent particulièrement (numérique, santé, transition écologique…) ? Je peux t’aider à chercher des formations en Occitanie qui y préparent *aujourd’hui*.
```

---

### Q2 — Combien coûte le logement étudiant CROUS à Lyon ?

**Domain attendu** : `crous` (CROUS corpus — résidences U et restos par zone)

**Top-5 domain match** : ⚠ 0/5 fiches du domain attendu
**Citations [source SX]** : 0
**Latence** : 3.94s

**Top-5 sources retrievées** :
```
```

**Réponse du pipeline** :

```
Je n'ai pas de données dans mes sources sur les tarifs des logements CROUS à Lyon.

Pour obtenir cette information, je te conseille de consulter directement le site du [CROUS de Lyon](https://www.crous-lyon.fr) ou de contacter leur service logement. Les prix varient selon le type de logement (studio, T1, chambre en cité universitaire) et les aides possibles (APL, bourses).

Tu as déjà une idée du type de logement qui t’intéresserait ?
```

---

### Q3 — Quels sont les blocs de compétences du RNCP 38450 ?

**Domain attendu** : `competences_certif` (France Compétences blocs RNCP)

**Top-5 domain match** : ✓ 5/5 fiches du domain attendu
**Citations [source SX]** : 0
**Latence** : 3.68s

**Top-5 sources retrievées** :
```
  S1: [competences_certif] rncp_blocs:RNCP35298 [score=1.041]
  S2: [competences_certif] rncp_blocs:RNCP35307 [score=1.041]
  S3: [competences_certif] rncp_blocs:RNCP35329 [score=1.041]
  S4: [competences_certif] rncp_blocs:RNCP35575 [score=1.041]
  S5: [competences_certif] rncp_blocs:RNCP35583 [score=1.041]
```

**Réponse du pipeline** :

```
Je n'ai pas d'information sur le **RNCP 38450** dans mes sources actuelles. Les certifications disponibles concernent d'autres codes RNCP (ex: 35298, 35307, etc.), mais aucun ne correspond à ta demande.

Pour obtenir les blocs de compétences précis, je te conseille de consulter directement la fiche officielle sur [France Compétences](https://www.francecompetences.fr/) ou de contacter le **CIO** (Centre d'Information et d'Orientation) le plus proche.

Quel métier ou domaine te intéresse derrière cette recherche ? Je pourrais peut-être t’orienter vers des certifications similaires.
```

---

### Q4 — Quel salaire après un Master Droit en région PACA ?

**Domain attendu** : `insertion_pro` (InserSup spécifique discipline × région)

**Top-5 domain match** : ⚠ 0/5 fiches du domain attendu
**Citations [source SX]** : 0
**Latence** : 4.51s

**Top-5 sources retrievées** :
```
```

**Réponse du pipeline** :

```
Je n'ai pas de formation pertinente dans mes sources pour répondre à ta question sur les salaires après un **Master Droit en région PACA**.

Pour obtenir des données précises, je te conseille de consulter :
- Les enquêtes **insertion professionnelle** des universités PACA (ex : Aix-Marseille, Nice)
- Le site de l’**ONISEP** ou de l’**APEC** (fiches métiers juristes, avocats, etc.)
- Le **SCUIO** (Service Commun Universitaire d’Information et d’Orientation) de ton université

Quelle spécialité en droit t’intéresse (droit des affaires, public, social…) ? Cela peut influencer les débouchés et salaires.
```

---

### Q5 — Que fait un actuaire au quotidien ?

**Domain attendu** : `metier_detail` (ROME 4.0 fiches métiers — compétences détaillées)

**Top-5 domain match** : ⚠ 0/5 fiches du domain attendu
**Citations [source SX]** : 4
**Latence** : 4.64s

**Top-5 sources retrievées** :
```
  S1: [metier] actuaire [score=0.021]
  S2: [metier] gestionnaire de patrimoine [score=0.021]
  S3: [metier] actuaire [score=0.021]
  S4: [metier] ingénieur financier / ingénieure financière [score=0.020]
  S5: [metier] responsable des produits structurés actions [score=0.020]
```

**Réponse du pipeline** :

```
Tu t’intéresses au métier d’**[actuaire](https://www.onisep.fr/http/redirection/metier/slug/MET.861)** et veux savoir en quoi consiste son quotidien. Voici les éléments clés :

- **Analyse des risques** : l’actuaire utilise des **statistiques, algorithmes et modélisations** pour évaluer les risques financiers (assurances, retraites, investissements) et aider les dirigeants à prendre des décisions éclairées [source S1][source S3].
- **Conception de contrats** : il/elle participe à la création ou à la modification de **contrats d’assurance**, en veillant à leur équilibre économique et à leur conformité réglementaire [source S3].
- **Collaboration pluridisciplinaire** : travail avec des équipes commerciales, juridiques ou informatiques pour traduire des données complexes en recommandations actionnables [source S1].

Son expertise se situe à la croisée des **mathématiques appliquées**, de l’**économie** et du **secteur assurantiel/financier**.

Est-ce que c’est plutôt l’aspect *modélisation technique* ou l’aspect *conseil stratégique* qui t’attire dans ce métier ?
```

---

### Q6 — Quelles aides financières pour les étudiants boursiers ?

**Domain attendu** : `financement_etudes` (Financement curated dispositifs)

**Top-5 domain match** : ✓ 5/5 fiches du domain attendu
**Citations [source SX]** : 3
**Latence** : 5.45s

**Top-5 sources retrievées** :
```
  S1: [financement_etudes] Aides au logement (APL, ALF, ALS) — étudiants [score=0.708]
  S2: [financement_etudes] Aide à la première installation (CROUS) [score=0.700]
  S3: [financement_etudes] Aide à la mobilité internationale (CROUS / Erasmus+) [score=0.685]
  S4: [financement_etudes] Aide à la mobilité Master [score=0.680]
  S5: [financement_etudes] Bourse sur critères sociaux CROUS — enseignement supérieur [score=0.680]
```

**Réponse du pipeline** :

```
Je comprends que tu cherches à sécuriser ton budget pour tes études. Voici les dispositifs **spécifiques aux étudiants boursiers** que je peux te confirmer :

• **Bourse sur critères sociaux CROUS** : Montant annuel entre **1080 € et 5965 €** (2024-2025), selon les revenus du foyer. Elle couvre tous les niveaux post-bac (BTS, Licence, Master, etc.) `[source S5]`.

• **Aide à la mobilité Master** : Forfait de **1000 €** (2024-2025) si tu changes de région entre ta Licence et ton Master, sous condition de bourse CROUS `[source S4]`.

• **Aide à la mobilité internationale (Erasmus+)** : Entre **280 € et 450 €/mois** pour les étudiants boursiers partant à l’étranger (montant variable selon la zone) `[source S3]`.

Tu peux aussi cumuler ces aides avec d’autres dispositifs comme les **APL** (logement) ou l’**aide à la première installation** (dépôt de garantie) `[source S1, S2]`, mais celles-ci ne sont pas réservées aux boursiers.

Quelle est ta situation actuelle (niveau d’études, projet de mobilité) ? Je peux t’aider à affiner les démarches.
```

---

### Q7 — Quelles formations en Guadeloupe ?

**Domain attendu** : `territoire_drom` (DROM-COM territoires)

**Top-5 domain match** : ⚠ 0/5 fiches du domain attendu
**Citations [source SX]** : 3
**Latence** : 4.9s

**Top-5 sources retrievées** :
```
  S1: [(formation)] Licence - Portail Sciences de la vie et de la terre - Biologie des organismes et Ecologie  / Biologie générale et sciences de la terre et de l’univers / Géo-sciences, géo-risques, géo-environnements — Université des Antilles - Pôle Guadeloupe, Guadeloupe [score=1.080]
  S2: [(formation)] Licence - Portail Sciences et Techniques des Activités Physiques et Sportives - Activités physiques adaptées et santé (APAS) — Université des Antilles - Pôle Guadeloupe, Guadeloupe [score=1.069]
  S3: [(formation)] Licence - Portail Economie et gestion - Eco de l'environnement et aménagement du territoire/Expertise éco,financière et managériale/Préparation aux métiers de l'enseignement - Guadeloupe — Université des Antilles - Pôle Guadeloupe, Guadeloupe [score=1.077]
  S4: [(formation)] Licence - Portail Mathématiques - Mathématiques appliquées aux sciences / Mathématiques pour l'enseignement  - Guadeloupe — Université des Antilles - Pôle Guadeloupe, Guadeloupe [score=1.071]
  S5: [(formation)] Licence - Portail Sciences pour la santé -  Biochimie - Sciences de l'aliment (BSA) / Sciences de la santé (BSS)  - Guadeloupe — Université des Antilles - Pôle Guadeloupe, Guadeloupe [score=1.069]
```

**Réponse du pipeline** :

```
Tu cherches des formations accessibles en Guadeloupe après le bac. Voici les options disponibles dans mes sources, toutes proposées par **[l’Université des Antilles - Pôle Guadeloupe](https://dossierappel.parcoursup.fr/Candidats/public/fiches/afficherFicheFormation?g_ta_cod=11749&typeBac=0&originePc=0)** à Pointe-à-Pitre :

• **Sciences fondamentales et santé** :
  - [Licence Portail Sciences de la vie et de la terre](https://dossierappel.parcoursup.fr/Candidats/public/fiches/afficherFicheFormation?g_ta_cod=11749&typeBac=0&originePc=0) (3 parcours : biologie, géosciences, etc.) avec **100 places** [source S1].
  - [Licence Portail Sciences pour la santé](https://dossierappel.parcoursup.fr/Candidats/public/fiches/afficherFicheFormation?g_ta_cod=11742&typeBac=0&originePc=0) (biochimie, santé) avec **150 places** [source S5].
  - [Licence Portail Mathématiques](https://dossierappel.parcoursup.fr/Candidats/public/fiches/afficherFicheFormation?g_ta_cod=36146&typeBac=0&originePc=0) (maths appliquées ou enseignement) avec **15 places** [source S4].

• **Économie/gestion et STAPS** :
  - [Licence Portail Économie et gestion](https://dossierappel.parcoursup.fr/Candidats/public/f
```

---

### Q8 — Marché de l'emploi cadres en Bretagne ?

**Domain attendu** : `apec_region` (APEC régions)

**Top-5 domain match** : ✓ 1/5 fiches du domain attendu
**Citations [source SX]** : 3
**Latence** : 4.56s

**Top-5 sources retrievées** :
```
  S1: [apec_region] apec_region:bretagne, Bretagne [score=0.681]
```

**Réponse du pipeline** :

```
D’après les dernières données, le marché des cadres en Bretagne montre une dynamique plutôt positive malgré un contexte national plus morose.

- **Recrutements 2025** : 9 990 postes (+5 % par rapport à 2024), ce qui contraste avec la baisse nationale de -3 % [source S1].
- **Prévisions 2026** : 10 200 recrutements (+2 %), un niveau proche du record de 2023 (10 290 postes) [source S1].
- **Créations nettes** : 2 910 postes en 2025 (contre 3 230 en 2024), avec une forte demande dans les secteurs tertiaire (21 %), commercial-marketing (16 %), et informatique (14 %) [source S1].

Ces chiffres suggèrent une région attractive pour les profils cadres, notamment dans les services et le numérique. Quels secteurs ou métiers t’intéressent plus particulièrement pour affiner l’analyse ?
```

---

### Q9 — Salaire moyen d'un cadre supérieur (PCS 37) ?

**Domain attendu** : `insee_salaire` (INSEE salaires PCS)

**Top-5 domain match** : ⚠ 0/5 fiches du domain attendu
**Citations [source SX]** : 0
**Latence** : 3.62s

**Top-5 sources retrievées** :
```
```

**Réponse du pipeline** :

```
Je n'ai pas de formation pertinente dans mes sources pour cette question, ni de données sur les salaires des cadres supérieurs (PCS 37).

Pour des chiffres officiels, je te conseille de consulter :
- Les **études de l'INSEE** (recherche "revenus par PCS")
- Les **rapports de l'APEC** (spécialisés sur les cadres)
- Le **site de la Dares** (statistiques du ministère du Travail)

Tu cherches ces infos pour un projet précis (négociation, reconversion, étude de marché) ?
```

---

### Q10 — Insertion à 3 ans après un Bac pro Industrie ?

**Domain attendu** : `formation_insertion` (Inserjeunes lycée pro)

**Top-5 domain match** : ⚠ 0/5 fiches du domain attendu
**Citations [source SX]** : 0
**Latence** : 4.48s

**Top-5 sources retrievées** :
```
  S1: [insertion_pro] doctorat:biologie-medecine-et-sante:2014:femmes-et-hommes:12-mois-apres-le-diplome [score=0.663]
  S2: [insertion_pro] doctorat:biologie-medecine-et-sante:2014:femmes-et-hommes:36-mois-apres-le-diplome [score=0.663]
  S3: [insertion_pro] doctorat:biologie-medecine-et-sante:2014:femmes:12-mois-apres-le-diplome [score=0.663]
  S4: [insertion_pro] doctorat:biologie-medecine-et-sante:2014:femmes:36-mois-apres-le-diplome [score=0.663]
  S5: [insertion_pro] doctorat:biologie-medecine-et-sante:2014:hommes:12-mois-apres-le-diplome [score=0.663]
```

**Réponse du pipeline** :

```
Je n'ai pas de formation pertinente dans mes sources pour répondre à l'insertion après un **Bac pro Industrie**. Mes données concernent uniquement l'insertion des docteurs en **biologie, médecine et santé (Bac+8)** [sources S1 à S5].

Pour des chiffres sur les débouchés après un Bac pro, je te conseille de consulter :
- Les enquêtes **CEREQ** (ex : [Bref n°400 sur l'insertion des Bac pro](https://www.cereq.fr))
- Le site de l’**ONISEP** ([fiches métiers par secteur industriel](https://www.onisep.fr))
- Le **SCUIO** de ton académie ou un conseiller du **CIO** près de chez toi.

Quelle spécialité industrielle t’intéresse en priorité (mécanique, électricité, maintenance…) ? Ça peut aider à affiner les recherches.
```

---

### Q11 — Quelles sont les spécialités possibles en BAC PRO agriculture ?

**Domain attendu** : `voie_pre_bac` (Voie pré-bac catalogue)

**Top-5 domain match** : ✓ 1/5 fiches du domain attendu
**Citations [source SX]** : 4
**Latence** : 5.06s

**Top-5 sources retrievées** :
```
  S1: [voie_pre_bac] voie_pre_bac:bac-pro:agriculture [score=0.807]
  S2: [(formation)] conseiller en gestion d’entreprise agri-agro [score=0.805]
  S3: [(formation)] bac pro forêt [score=0.780]
  S4: [(formation)] bac pro cultures marines [score=0.774]
  S5: [(formation)] bac pro aménagements paysagers [score=0.780]
```

**Réponse du pipeline** :

```
D’après tes sources, le **BAC PRO agriculture** propose plusieurs spécialités bien distinctes, adaptées à différents secteurs du monde agricole et paysager.

Voici les options référencées :
• **[BAC pro aménagements paysagers](https://www.onisep.fr/http/redirection/formation/slug/FOR.7681)** : pour travailler dans la création et l’entretien d’espaces verts, parcs ou jardins [source S5].
• **[BAC pro forêt](https://www.onisep.fr/http/redirection/formation/slug/FOR.7418)** : axé sur la gestion des espaces boisés, l’exploitation forestière ou la sylviculture [source S3].
• **[BAC pro cultures marines](https://www.onisep.fr/http/redirection/formation/slug/FOR.1083)** : spécialisé dans l’élevage et la production d’organismes marins (conchyliculture, pisciculture) [source S4].
• **BAC pro conduite d'activités d'élevage canin-félin** : pour encadrer des structures d’élevage ou de pension pour chiens/chats [source S1].

Les données sur les débouchés ou effectifs ne sont pas disponibles dans mes sources. Pour affiner, as-tu une préférence pour un domaine en particulier (végétal, animal, marin) ou une région précise ?
```

---

### Q12 — Taux de réussite L1 pour un bac S avec mention bien ?

**Domain attendu** : `parcours_bacheliers` (MESR parcours bacheliers en licence)

**Top-5 domain match** : ⚠ 0/5 fiches du domain attendu
**Citations [source SX]** : 0
**Latence** : 4.24s

**Top-5 sources retrievées** :
```
```

**Réponse du pipeline** :

```
Je préfère ne pas répondre sur ce point de manière détaillée, car ma réponse contiendrait des imprécisions factuelles importantes qui pourraient t'induire en erreur.

Détails :
• Le 'bac S' a été supprimé en 2021 (réforme Blanquer). Utiliser 'bac général avec spécialités Maths/PC/SVT'.

Pour avoir une information fiable sur ton orientation, je te conseille :
- **ONISEP** : catalogue officiel des formations françaises — https://www.onisep.fr
- **Parcoursup** : procédures et taux d'accès officiels — https://www.parcoursup.fr
- **SCUIO** : service d'orientation de ton université (si étudiant·e)
- **CIO** / **Psy-EN** : conseiller·ères d'orientation en lycée

Tu peux aussi me reposer la question autrement (par exemple avec un profil plus précis ou sur un sujet plus ciblé) et je ferai de mon mieux pour répondre dans la limite de ce que nos données vérifient.
```

---

### Q13 — Quelle insertion après un doctorat en chimie ?

**Domain attendu** : `insertion_pro` (Doctorat IP MESR)

**Top-5 domain match** : ⚠ 0/5 fiches du domain attendu
**Citations [source SX]** : 3
**Latence** : 6.34s

**Top-5 sources retrievées** :
```
  S1: [metier] responsable de laboratoire de contrôle en chimie [score=0.016]
  S2: [metier] parfumeur / parfumeuse [score=0.016]
  S3: [metier] responsable de fabrication en chimie [score=0.016]
  S4: [metier] ingénieur / ingénieure chimiste en développement analytique [score=0.016]
  S5: [metier] ingénieur/e chimiste [score=0.015]
```

**Réponse du pipeline** :

```
Je comprends que tu te demandes quelles voies professionnelles s’ouvrent après un doctorat en chimie. Voici trois métiers accessibles avec ce niveau d’études, selon les fiches ONISEP :

• **[Responsable de laboratoire de contrôle en chimie](https://www.onisep.fr/http/redirection/metier/slug/MET.355)** : encadrement d’équipes, gestion des analyses et validation des procédés en industrie (pharma, cosmétiques, environnement). Un profil doctorant est souvent recherché pour les postes à haute responsabilité technique [source S1].

• **[Ingénieur/e chimiste en développement analytique](https://www.onisep.fr/http/redirection/metier/slug/MET.738)** : conception de méthodes d’analyse, optimisation de procédés, ou R&D en instrumentation. Le doctorat est un atout pour les postes en innovation ou en gestion de projets complexes [source S4].

• **[Ingénieur/e chimiste](https://www.onisep.fr/http/redirection/metier/slug/MET.738)** (secteurs pétrochimie, agroalimentaire, pharmaceutique) : recherche appliquée, production, ou management industriel. Les docteurs accèdent plus rapidement à des postes stratégiques (ex : chef de projet R&D) [source S5].

*Information non disponible dans mes sources* pour les salaires, taux d’insertion ou comparatifs avec d’autres niveaux de diplôme.

Question pour toi : parmi ces trois orientations (contrôle qualité, R&D analytique, ou ingénierie industrielle), laquelle correspond le mieux à tes aspirations *et* à ton expérience en thèse ?
```

---

## Décision Gate 3 (manuel)

Après lecture des 13 réponses ci-dessus, indiquer :
- ✓ GO promotion (toutes questions passent les 4 critères)
- ⚠ GO conditionnel (1-3 questions à expliquer mais corpus utilisable)
- ❌ NO-GO (≥4 questions avec hallu, info non disponible non-justifiée, ou top-K mal retrouvé)

# Spot-check Gate 3 v5 — 2026-05-07

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
**Citations [source SX]** : 4
**Latence** : 30.69s

**Top-5 sources retrievées** :
```
  S1: [formation_insertion] inserjeunes_formation_region:mc3:employe-traiteur:occitanie, OCCITANIE [score=0.726]
  S2: [insertion_pro] insersup:licence-professionnelle:sciences-fondamentales-et-applications:occitanie, Occitanie [score=0.716]
  S3: [formation_insertion] inserjeunes_formation_region:bac-pro:accueil-relation-clients-et-usagers:occitanie, OCCITANIE [score=0.716]
  S4: [formation_insertion] inserjeunes_formation_region:mc3:sommellerie:occitanie, OCCITANIE [score=0.726]
  S5: [formation_insertion] inserjeunes_region_diplome:occitanie:mc3, OCCITANIE [score=0.726]
```

**Réponse du pipeline** :

```
Tu te demandes quels métiers auront des débouchés en Occitanie d’ici 2030. Les données disponibles concernent surtout l’insertion récente (2024-2025), mais elles donnent des tendances solides pour des secteurs qui recrutent déjà activement.

• **Métiers de l’hôtellerie-restauration** : Les formations comme **employé traiteur** (MC3) affichent un taux d’emploi de **75 % à 24 mois** [source S5], et la **sommellerie** (MC3) reste un secteur porteur malgré des stats non consolidées [source S4]. Ces métiers manquent souvent de main-d’œuvre qualifiée, une tendance qui devrait persister.

• **Sciences appliquées** : La **licence pro en sciences fondamentales et applications** (bac+3) montre une insertion rapide avec **89 % d’emploi salarié à 12 mois** [source S2]. Les débouchés couvrent les laboratoires, l’industrie ou la R&D, des domaines en tension démographique.

• **Relation client** : Le **bac pro accueil-relation clients et usagers** a un taux d’emploi plus modeste (**43,8 % à 24 mois** [source S3]), mais il ouvre sur des postes en expansion (centres d’appels, tourisme, services publics).

Ces chiffres reflètent des besoins actuels, souvent liés à des départs en retraite ou des créations d’emplois locales. Pour 2030, les métiers manuels qualifiés (restauration, sciences appliquées) et les services à la personne devraient rester prioritaires.

Quels types d’environnements de travail t’attirent le plus : le contact client, le travail en laboratoire, ou l’artisanat/agroalimentaire
```

---

### Q2 — Combien coûte le logement étudiant CROUS à Lyon ?

**Domain attendu** : `crous` (CROUS corpus — résidences U et restos par zone)

**Top-5 domain match** : ⚠ 0/5 fiches du domain attendu
**Citations [source SX]** : 2
**Latence** : 4.98s

**Top-5 sources retrievées** :
```
  S1: [(formation)] Licence professionnelle - Métiers de l'Immobilier - Gestion et administration de biens — Université Jean Moulin Lyon 3, Auvergne-Rhône-Alpes [score=1.095]
  S2: [(formation)] METIERS DE L'ENSEIGNEMENT, DE L'EDUCATION ET DE LA FORMATION (MEEF), 2E DEGRE — M 1 : ECONOMIE GESTION — Institut catholique de Lyon, Auvergne-Rhône-Alpes [score=0.973]
  S3: [(formation)] Architecture — Ecole Nationale Supérieure d'Architecture de Lyon, Auvergne-Rhône-Alpes [score=1.014]
  S4: [(formation)] BTS - Services - Management Commercial Opérationnel - Entièrement en distanciel — CNED, Auvergne-Rhône-Alpes [score=1.023]
  S5: [(formation)] Licence - Economie et gestion — Université Lumière - Lyon 2, Auvergne-Rhône-Alpes [score=1.065]
```

**Réponse du pipeline** :

```
Je n’ai pas de données sur les coûts de logement CROUS à Lyon dans mes sources actuelles.

En revanche, si tu explores des formations dans cette région, voici quelques options avec leurs spécificités d’accès :
- **Licence pro Métiers de l’Immobilier** (Lyon 3) : 30 places, 30 % de taux d’accès en 2025 [source S1].
- **Architecture** (ENSAL) : 100 places, 9 % de taux d’accès [source S3].

Tu préfères te concentrer sur le logement ou affiner tes recherches de formation ?

---
⚠️ **Points à vérifier dans ma réponse** :
- Mention manquante : 'taux d'accès' = rang du dernier appelé — La réponse cite un 'taux d'accès Parcoursup' sans préciser que c'est le rang du dernier candidat appelé (pas le taux d'admission). Nuance critique pour un lycéen.

Ces points sont des patterns que nous surveillons. Vérifie directement sur [ONISEP](https://www.onisep.fr) ou [Parcoursup](https://www.parcoursup.fr) avant toute décision.
```

---

### Q3 — Quels sont les blocs de compétences du RNCP 38450 ?

**Domain attendu** : `competences_certif` (France Compétences blocs RNCP)

**Top-5 domain match** : ⚠ 0/5 fiches du domain attendu
**Citations [source SX]** : 2
**Latence** : 5.36s

**Top-5 sources retrievées** :
```
  S1: [(formation)] Développer et mettre en œuvre les compétences spécifiques en prévention et santé au travail dans les missions d’un infirmier — UNIVERSITE DE BREST [score=0.786]
  S2: [(formation)] Certificat de compétence de formateur de formateurs pour l'enseignement des gestes de premiers secours — MINISTERE DE L' INTERIEUR ET DES OUTRE-MER [score=0.785]
  S3: [formation_insertion] inserjeunes_formation:bp:agent-technique-de-prevention-et-de-securite [score=0.711]
  S4: [formation_insertion] inserjeunes_formation:bp:agent-technique-de-securite-dans-les-transports [score=0.711]
  S5: [formation_insertion] inserjeunes_formation:bp:ameublement-option-tapisserie-decoration [score=0.711]
```

**Réponse du pipeline** :

```
Je n’ai pas d’information sur le **RNCP 38450** ni sur ses blocs de compétences dans mes sources actuelles.

En revanche, voici deux certifications RNCP liées au domaine **santé/sécurité** que je peux documenter :
- **« Développer et mettre en œuvre les compétences en prévention et santé au travail »** (UNIVERSITE DE BREST) — débouchés vers des métiers paramédicaux ou de prévention [source S1].
- **« Formateur de formateurs pour les gestes de premiers secours »** (MINISTERE DE L'INTERIEUR) — orienté vers l’enseignement des secours [source S2].

Pour le RNCP 38450, je te conseille de consulter directement le [répertoire RNCP](https://www.francecompetences.fr/) ou de contacter le certificateur.

Quel aspect de cette certification t’intéresse particulièrement (métiers visés, durée, modalités) ?
```

---

### Q4 — Quel salaire après un Master Droit en région PACA ?

**Domain attendu** : `insertion_pro` (InserSup spécifique discipline × région)

**Top-5 domain match** : ⚠ 0/5 fiches du domain attendu
**Citations [source SX]** : 2
**Latence** : 5.08s

**Top-5 sources retrievées** :
```
  S1: [(formation)] DROIT — Droit public et carrières publiques — Aix-Marseille Université, Provence-Alpes-Côte d'Azur [score=1.024]
  S2: [(formation)] DROIT PRIVE — Droit privé général — Université de Pau et des Pays de l'Adour, Nouvelle-Aquitaine [score=1.016]
  S3: [(formation)] DROIT COMPARE — Droit et études multilingues — Université Paris-Panthéon-Assas, Île-de-France [score=1.007]
  S4: [(formation)] DROIT INTERNATIONAL — Droit des échanges euro-méditerranéens — Université de Bordeaux, Nouvelle-Aquitaine [score=1.004]
  S5: [(formation)] DROIT — Métiers du droit — Avignon Université, Provence-Alpes-Côte d'Azur [score=1.017]
```

**Réponse du pipeline** :

```
Tu cherches à connaître les perspectives salariales après un master en droit en région PACA. Voici ce que je peux te dire sur la base des données disponibles :

- **Master Droit public et carrières publiques** à **Aix-Marseille Université (à distance)** : aucune information sur le salaire médian à l’embauche n’est disponible dans mes sources [source S1].
- **Master Métiers du droit** à **Avignon Université** : même constat, les données salariales ne sont pas renseignées [source S5].

Malheureusement, aucune des formations en droit de la région PACA répertoriées ne fournit de chiffre précis sur les salaires. Cela ne signifie pas qu’il n’y a pas de débouchés, mais que ces données ne sont pas publiées dans les sources officielles que j’ai sous les yeux.

As-tu une idée du secteur qui t’intéresse (public, privé, international) ? Cela pourrait aider à affiner les pistes.
```

---

### Q5 — Que fait un actuaire au quotidien ?

**Domain attendu** : `metier_detail` (ROME 4.0 fiches métiers — compétences détaillées)

**Top-5 domain match** : ⚠ 0/5 fiches du domain attendu
**Citations [source SX]** : 1
**Latence** : 5.44s

**Top-5 sources retrievées** :
```
  S1: [(formation)] ACTUARIAT — None — Sorbonne Université, Île-de-France [score=0.982]
  S2: [metier] actuaire [score=0.966]
  S3: [(formation)] ACTUARIAT — Actuariat et Ingénierie Mathématique pour l'Assurance et la Finance — Université de Rouen Normandie, Normandie [score=0.981]
  S4: [(formation)] MONNAIE, BANQUE, FINANCE, ASSURANCE — Actuariat — Université de Montpellier, Occitanie [score=0.967]
  S5: [(formation)] ACTUARIAT — None — Université Gustave Eiffel, Île-de-France [score=0.977]
```

**Réponse du pipeline** :

```
Tu t’interroges sur le métier d’actuaire, qui allie mathématiques, statistiques et gestion des risques. Voici ce qui caractérise son quotidien :

- **Analyse des risques et modélisation** : L’actuaire utilise des algorithmes et des modèles statistiques pour évaluer les risques (santé, accidents, marchés financiers) et aider les entreprises (assurances, banques) à prendre des décisions éclairées. Son travail repose sur la prévision de scénarios imprévisibles, comme les crises ou les évolutions démographiques `[source S2]`.

- **Conception et ajustement de produits** : Il/elle participe à la création ou à la modification de contrats d’assurance (retraite, prévoyance, dommage), en veillant à leur équilibre financier. Cela implique de collaborer avec des juristes, des commerciaux ou des data scientists pour traduire des données techniques en solutions concrètes.

- **Veille et conseil stratégique** : L’actuaire suit en permanence les évolutions réglementaires, économiques ou sociales (ex : réforme des retraites) pour conseiller la direction. Son expertise est souvent sollicitée pour des arbitrages financiers majeurs.

Ce métier te semble-t-il correspondre à ton appétence pour les maths appliquées *et* le travail en interface avec des non-spécialistes ?
```

---

### Q6 — Quelles aides financières pour les étudiants boursiers ?

**Domain attendu** : `financement_etudes` (Financement curated dispositifs)

**Top-5 domain match** : ✓ 2/5 fiches du domain attendu
**Citations [source SX]** : 2
**Latence** : 10.57s

**Top-5 sources retrievées** :
```
  S1: [financement_etudes] Aides au logement (APL, ALF, ALS) — étudiants [score=0.708]
  S2: [metier] ingénieur financier / ingénieure financière [score=0.706]
  S3: [financement_etudes] Aide à la première installation (CROUS) [score=0.700]
  S4: [metier] spécialiste des affaires réglementaires en chimie [score=0.707]
  S5: [metier] généalogiste [score=0.703]
```

**Réponse du pipeline** :

```
Je comprends que tu cherches des solutions concrètes pour alléder ton budget étudiant. Voici deux dispositifs accessibles aux boursiers, même si les montants exacts dépendent de ta situation personnelle :

• **Aides au logement (APL/ALF/ALS)** : Gérées par la CAF, elles s’adressent aux étudiants locataires (résidences universitaires, parc privé, foyers). Le montant varie selon tes ressources, ton loyer et la zone géographique — un simulateur en ligne permet d’estimer ton éligibilité **[source S1]**.

• **Aide à la première installation (CROUS)** : Si tu déménages pour tes études dans une nouvelle ville, le CROUS peut t’aider à couvrir le dépôt de garantie (via des dispositifs comme Visale ou Loca-Pass). Là aussi, les conditions dépendent de ton statut boursier **[source S3]**.

Ces aides sont cumulables avec ta bourse sur critères sociaux. As-tu déjà vérifié ton éligibilité à l’une d’elles, ou souhaites-tu des précisions sur les démarches ?

---
⚠️ **Points à vérifier dans ma réponse** :
- Mention manquante : interdit de redoublement PASS (arrêté 2019) — La réponse parle de PASS mais ne précise pas que le redoublement est interdit (arrêté du 4 novembre 2019). C'est une information obligatoire pour un lycéen en autonomie.

Ces points sont des patterns que nous surveillons. Vérifie directement sur [ONISEP](https://www.onisep.fr) ou [Parcoursup](https://www.parcoursup.fr) avant toute décision.
```

---

### Q7 — Quelles formations en Guadeloupe ?

**Domain attendu** : `territoire_drom` (DROM-COM territoires)

**Top-5 domain match** : ✓ 4/5 fiches du domain attendu
**Citations [source SX]** : 2
**Latence** : 4.4s

**Top-5 sources retrievées** :
```
  S1: [territoire_drom] Guadeloupe [score=1.186]
  S2: [territoire_drom] Martinique [score=1.093]
  S3: [territoire_drom] Guyane [score=1.079]
  S4: [territoire_drom] La Réunion [score=1.078]
  S5: [(formation)] GEOGRAPHIE, AMENAGEMENT, ENVIRONNEMENT ET DEVELOPPEMENT — Tronc commun — Université des Antilles, Guadeloupe [score=0.998]
```

**Réponse du pipeline** :

```
Tu cherches des formations en Guadeloupe, et je comprends l’importance de trouver des options adaptées à ce territoire spécifique.

• **Master en Géographie, Aménagement, Environnement et Développement** à l’**Université des Antilles (Schoelcher)** : cette formation de niveau bac+5, en statut public, propose un tronc commun axé sur les enjeux environnementaux et territoriaux, pertinents pour un contexte insulaire comme la Guadeloupe [source S5].

• **Contexte socio-économique local** : la Guadeloupe affiche un **taux de chômage global de 17 %** et un **salaire médian net mensuel de 1750 €** [source S1]. Ces données peuvent influencer ton choix, notamment si tu envisages une insertion professionnelle directe après tes études.

As-tu une idée du domaine qui t’intéresse le plus (environnement, sciences humaines, etc.) ou préfères-tu explorer d’autres pistes en métropole ou dans d’autres DROM ?
```

---

### Q8 — Marché de l'emploi cadres en Bretagne ?

**Domain attendu** : `apec_region` (APEC régions)

**Top-5 domain match** : ⚠ 0/5 fiches du domain attendu
**Citations [source SX]** : 1
**Latence** : 7.41s

**Top-5 sources retrievées** :
```
  S1: [insertion_pro] insersup:diplome-grade-ou-vise-management-niveau-bac-5:sciences-economiques-gestion:bretagne, Bretagne [score=0.710]
  S2: [formation_insertion] inserjeunes_formation_region:bac-pro:accompagnement-soins-et-services-a-la-personne-option-a-a-do:bretagne, BRETAGNE [score=0.701]
  S3: [formation_insertion] inserjeunes_formation_region:bac-pro:accompagnement-soins-et-services-a-la-personne-option-b-en-s:bretagne, BRETAGNE [score=0.701]
  S4: [formation_insertion] inserjeunes_formation_region:bac-pro:accueil-relation-clients-et-usagers:bretagne, BRETAGNE [score=0.701]
  S5: [formation_insertion] inserjeunes_formation_region:bac-pro:metiers-de-l-electricite-et-de-ses-environnements-connectes:bretagne, BRETAGNE [score=0.701]
```

**Réponse du pipeline** :

```
Tu t’intéresses à l’insertion des profils cadres en Bretagne, notamment dans les filières accessibles après le bac. Voici ce que mes sources couvrent pour des diplômes **bac+5** et **bac pro** dans la région :

- **Diplômes gradés/visés en management (bac+5)** : 64 % des diplômés sont en emploi salarié **12 mois après leur sortie** (cohortes 2024, écoles comme Rennes School of Business ou Brest Business School). À noter que 22 % des sortants poursuivent leurs études, ce qui peut retarder l’entrée sur le marché du travail `[source S1]`.
- **Bac pro en Bretagne** : les taux d’emploi à 12 mois varient entre **43,5 %** (accueil-relation clients) et **49,1 %** (accompagnement soins en structure), avec une tendance à la poursuite d’études marquée (jusqu’à 66,9 % pour les métiers de l’électricité) `[source S3, S4, S5]`.

**Attention** : mes sources ne couvrent pas les *salaire cadres*, *secteurs porteurs*, ou *évolutions à 3/5 ans* pour la Bretagne. Pour ces données, je te conseille de consulter l’[APEC](https://www.apec.fr/) ou les observatoires régionaux comme [Bretagne Développement Innovation](https://www.bdi.fr/).

Qu’est-ce qui t’intéresse plus précisément : les débouchés après une école de commerce, ou les passerelles vers des postes cadres après un bac pro + poursuite d’études ?
```

---

### Q9 — Salaire moyen d'un cadre supérieur (PCS 37) ?

**Domain attendu** : `insee_salaire` (INSEE salaires PCS)

**Top-5 domain match** : ⚠ 0/5 fiches du domain attendu
**Citations [source SX]** : 0
**Latence** : 0.93s

**Top-5 sources retrievées** :
```
```

**Réponse du pipeline** :

```
Je n'ai pas l'information sur salaire médian à l'embauche dans mes sources vérifiées.

Plusieurs formations matchent ta demande. Précise davantage (ville, établissement, niveau) pour que je puisse te donner le chiffre exact.
```

---

### Q10 — Insertion à 3 ans après un Bac pro Industrie ?

**Domain attendu** : `formation_insertion` (Inserjeunes lycée pro)

**Top-5 domain match** : ✓ 4/5 fiches du domain attendu
**Citations [source SX]** : 6
**Latence** : 6.02s

**Top-5 sources retrievées** :
```
  S1: [voie_pre_bac] voie_pre_bac:bac-pro:ingenierie-industrielle [score=0.727]
  S2: [formation_insertion] inserjeunes_formation:bac-pro:accompagnement-soins-et-services-a-la-personne [score=0.713]
  S3: [formation_insertion] inserjeunes_formation:bac-pro:accompagnement-soins-et-services-a-la-personne-option-a-a-do [score=0.713]
  S4: [formation_insertion] inserjeunes_formation:bac-pro:accompagnement-soins-et-services-a-la-personne-option-b-en-s [score=0.713]
  S5: [formation_insertion] inserjeunes_formation:bac-pro:accueil-relation-clients-et-usagers [score=0.713]
```

**Réponse du pipeline** :

```
Ton projet en bac pro industriel te questionne sur les débouchés à moyen terme. Voici ce que je peux te partager sur les données disponibles :

- **Données d'insertion à 3 ans** : information non disponible dans mes sources pour les bacs pro en ingénierie industrielle. Les statistiques Inserjeunes couvrent surtout les 12 et 24 mois après le diplôme [source S1].

- **Alternatives avec données** : Si tu envisages une réorientation vers le social/médical, les bacs pro *accompagnement soins et services à la personne* (option A ou B) affichent des taux d'emploi à 24 mois de **49,2 %** (option A) et **50,2 %** (option B) [source S3][source S4]. Ces chiffres restent modestes, avec près de **43-46 %** de poursuite d'études [source S3][source S4].

- **Pistes concrètes** : Pour l'industrie, je te suggère de consulter directement les rapports Inserjeunes par spécialité (ex : bac pro aéronautique ou maintenance industrielle) via les liens ONISEP [source S1], ou de contacter un CIO pour des données locales.

Qu’est-ce qui compte le plus pour toi : un emploi rapide après le bac pro, ou une formation qui te laisse des portes ouvertes pour continuer ?
```

---

### Q11 — Quelles sont les spécialités possibles en BAC PRO agriculture ?

**Domain attendu** : `voie_pre_bac` (Voie pré-bac catalogue)

**Top-5 domain match** : ✓ 1/5 fiches du domain attendu
**Citations [source SX]** : 4
**Latence** : 6.18s

**Top-5 sources retrievées** :
```
  S1: [voie_pre_bac] voie_pre_bac:bac-pro:agriculture [score=0.807]
  S2: [(formation)] conseiller en gestion d’entreprise agri-agro [score=0.805]
  S3: [(formation)] bac pro forêt [score=0.780]
  S4: [metier] halieute [score=0.779]
  S5: [(formation)] bac pro cultures marines [score=0.774]
```

**Réponse du pipeline** :

```
Tu t’intéresses aux spécialités du **BAC PRO agriculture**, un diplôme qui ouvre à des métiers variés dans le secteur. Voici les options identifiées dans mes sources :

• **BAC PRO aménagements paysagers** : pour travailler sur la création et l’entretien d’espaces verts, en lien avec l’horticulture ou les collectivités [source S1].
• **BAC PRO conduite d’activités d’élevage canin-félin (CAEHSCF)** : spécialisé dans la gestion d’élevages ou de refuges pour animaux de compagnie [source S1].
• **BAC PRO cultures marines** : axé sur l’aquaculture (conchyliculture, pisciculture), souvent en zone côtière. Durée de 3 ans [source S5].
• **BAC PRO forêt** : formation en gestion des espaces boisés et exploitation forestière, sur 3 ans également [source S3].

D’autres spécialités existent (comme la conduite de productions aquacoles), mais mes sources ne détaillent pas leur contenu précis.

Qu’est-ce qui t’attire le plus dans ces domaines : le travail avec les animaux, les plantes, ou plutôt les milieux naturels (forêt, mer) ?
```

---

### Q12 — Taux de réussite L1 pour un bac S avec mention bien ?

**Domain attendu** : `parcours_bacheliers` (MESR parcours bacheliers en licence)

**Top-5 domain match** : ⚠ 0/5 fiches du domain attendu
**Citations [source SX]** : 0
**Latence** : 15.95s

**Top-5 sources retrievées** :
```
  S1: [(formation)] BTS - Production - Assistance technique d'ingénieur — Lycée professionnel Amiral Lacaze, Réunion [score=1.207]
  S2: [(formation)] Licence - Langues, littératures et civilisations étrangères et régionales - Parcours  Anglais — Université de Rennes 2, Bretagne [score=1.114]
  S3: [(formation)] Licence - Histoire — Université de La Réunion - Saint Denis, Réunion [score=1.120]
  S4: [(formation)] Licence - Information et communication — Université de La Réunion - Saint Denis, Réunion [score=1.114]
  S5: [(formation)] BUT - Hygiène Sécurité Environnement — I.U.T de la Réunion, Réunion [score=1.105]
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
**Citations [source SX]** : 0
**Latence** : 6.61s

**Top-5 sources retrievées** :
```
  S1: [(formation)] CHIMIE — Chimie Analytique et Qualité — Université de Poitiers, Nouvelle-Aquitaine [score=1.018]
  S2: [(formation)] CHIMIE — Integrated research for advanced chemistry and materials — Université de Lille, Hauts-de-France [score=1.011]
  S3: [(formation)] CHIMIE — M1 - Chemistry and Interfaces — Institut polytechnique de Paris, Île-de-France [score=1.011]
  S4: [(formation)] CHIMIE — None — Sorbonne Université, Île-de-France [score=1.011]
  S5: [(formation)] innovation et chimie intégrative [score=0.841]
```

**Réponse du pipeline** :

```
Je comprends que tu cherches à anticiper les débouchés après un doctorat en chimie, et c’est une question cruciale pour orienter tes choix. Malheureusement, **mes sources ne fournissent aucune donnée sur l’insertion professionnelle (taux d’emploi, CDI, salaires) ni sur les parcours post-doctorat** pour les formations en chimie listées [sources S1 à S5].

Ce que je peux te dire en revanche :
- Les masters en chimie proposés (comme **"Chimie Analytique et Qualité"** à Poitiers [S1] ou **"Integrated research for advanced chemistry"** à Lille [S2]) sont des **bac+5 publics**, souvent conçus pour une poursuite en thèse. Leur insertion n’est pas documentée dans mes fiches, mais ils ouvrent classiquement vers la recherche académique, l’industrie (pharma, matériaux, cosmétiques) ou l’expertise technique.
- Le master **"Innovation et chimie intégrative"** (bac+5, école spécialisée) a une durée de **2 ans** [S5], ce qui correspond à la norme pour un M2, mais là encore, aucun chiffre sur les suites post-doctorat.

**Question pour toi** : Est-ce que tu envisages plutôt la recherche publique (CNRS, universités), l’industrie, ou une reconversion vers des métiers appliqués (qualité, R&D) après ta thèse ? Cela pourrait affiner les pistes.
```

---

## Décision Gate 3 (manuel)

Après lecture des 13 réponses ci-dessus, indiquer :
- ✓ GO promotion (toutes questions passent les 4 critères)
- ⚠ GO conditionnel (1-3 questions à expliquer mais corpus utilisable)
- ❌ NO-GO (≥4 questions avec hallu, info non disponible non-justifiée, ou top-K mal retrouvé)

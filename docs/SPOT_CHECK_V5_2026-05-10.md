# Spot-check Gate 3 v5 — 2026-05-10

> Phase C.5 (BLOQUANT pour promotion v5). 13 questions ciblées sur
> les domaines précédemment dormants. Évaluation manuelle requise.

## Résumé exécutif

- **Questions testées** : 13
- **Questions avec domain attendu présent dans top-5** : 5/13
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
**Latence** : 7.68s

**Top-5 sources retrievées** :
```
```

**Réponse du pipeline** :

```
Je n'ai pas de formation ni de fiche métier pertinente dans mes sources pour répondre à ta question sur les métiers qui recruteront en Occitanie en 2030.

Pour explorer cette question, je te conseille de consulter :
- Les **études prospectives** de la [Région Occitanie](https://www.laregion.fr/) ou de [Pôle Emploi](https://candidat.pole-emploi.fr/).
- Les **fiches métiers** sur [ONISEP](https://www.onisep.fr/) en filtrant par région.
- Un **entretien avec un·e conseiller·ère du CIO** (Centre d'Information et d'Orientation) près de chez toi.

Quels secteurs t’intéressent particulièrement pour affiner les recherches ? (numérique, santé, transition écologique, etc.)
```

---

### Q2 — Combien coûte le logement étudiant CROUS à Lyon ?

**Domain attendu** : `crous` (CROUS corpus — résidences U et restos par zone)

**Top-5 domain match** : ⚠ 0/5 fiches du domain attendu
**Citations [source SX]** : 0
**Latence** : 3.55s

**Top-5 sources retrievées** :
```
```

**Réponse du pipeline** :

```
Je n’ai pas de données dans mes sources sur les tarifs des logements CROUS à Lyon.

Pour obtenir cette information, je te conseille de consulter directement :
- Le [site du CROUS de Lyon](https://www.crous-lyon.fr)
- La plateforme **Messervices.etudiant.gouv.fr** (logements en résidence universitaire)
- Ou de contacter le **service logement du CROUS** par téléphone/mail.

Tu cherches un studio, une coloc, ou une chambre en cité U ? Cela peut influencer les prix.
```

---

### Q3 — Quels sont les blocs de compétences du RNCP 38450 ?

**Domain attendu** : `competences_certif` (France Compétences blocs RNCP)

**Top-5 domain match** : ✓ 5/5 fiches du domain attendu
**Citations [source SX]** : 5
**Latence** : 4.3s

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
Je n'ai pas d'information sur le **RNCP 38450** dans mes sources actuelles, ni sur ses blocs de compétences.

Mes données couvrent uniquement les certifications suivantes (niveau bac+2) :
- **Responsable de chantier de dépollution pyrotechnique** [source S1]
- **Electronicien de tests et développement** [source S2]
- **Enseignant de la conduite et de la sécurité routière** [source S3]
- **Superviseur des éducateurs** [source S4]
- **Technicien informatique systèmes et réseaux** [source S5]

Pour obtenir les détails du RNCP 38450, je te conseille de consulter directement le [répertoire national des certifications professionnelles (RNCP)](https://www.francecompetences.fr/) ou de contacter un **CIO** (Centre d'Information et d'Orientation).

Quel type de formation ou métier recherches-tu précisément ? Peut-être puis-je t’orienter vers une alternative proche parmi les certifications listées.
```

---

### Q4 — Quel salaire après un Master Droit en région PACA ?

**Domain attendu** : `insertion_pro` (InserSup spécifique discipline × région)

**Top-5 domain match** : ⚠ 0/5 fiches du domain attendu
**Citations [source SX]** : 3
**Latence** : 6.87s

**Top-5 sources retrievées** :
```
  S1: [metier] formaliste [score=0.016]
  S2: [metier] généalogiste [score=0.016]
  S3: [metier] juriste international / internationale [score=0.016]
  S4: [metier] juriste droit de l'environnement [score=0.016]
  S5: [metier] juriste du sport [score=0.015]
```

**Réponse du pipeline** :

```
Ta question porte sur les salaires après un **Master Droit en région PACA**, mais mes sources ne contiennent **aucun chiffre** (salaire, taux d’emploi, etc.) pour cette filière dans cette région — ni même au niveau national.

En revanche, voici quelques **métiers accessibles** après un master en droit, avec leurs fiches ONISEP pour explorer les conditions d’exercice (statut, secteurs, etc.) :
- **[Formaliste](https://www.onisep.fr/http/redirection/metier/slug/MET.8095)** : spécialiste des actes juridiques (notariats, études) [source S1].
- **[Juriste international·e](https://www.onisep.fr/http/redirection/metier/slug/MET.1189)** : droit des affaires, contrats transfrontaliers [source S3].
- **[Juriste en droit de l’environnement](https://www.onisep.fr/http/redirection/metier/slug/MET.806)** : en collectivités, ONG ou cabinets [source S4].

**Pour des données salariales précises** (par métier, région, expérience), je te conseille :
1. Le **[Baromètre APEC des jeunes diplômés](https://www.apec.fr/)** (filtre "juriste" + région).
2. Les **enquêtes insertion** des universités PACA (ex : Aix-Marseille) — souvent publiées sur leurs sites.
3. Un **entretien avec un·e professionnel·le** via le réseau alumni de ta fac ou LinkedIn (les fourchettes varient énormément selon le secteur : cabinet privé vs fonction publique vs entreprise).

Qu’est-ce qui t’intéresse le plus : un **salaire élevé à court terme** (même si le rythme est intense)
```

---

### Q5 — Que fait un actuaire au quotidien ?

**Domain attendu** : `metier_detail` (ROME 4.0 fiches métiers — compétences détaillées)

**Top-5 domain match** : ⚠ 0/5 fiches du domain attendu
**Citations [source SX]** : 3
**Latence** : 7.14s

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
Tu t’intéresses au métier d’**actuaire**, qui allie mathématiques, statistiques et analyse des risques. Voici ce qui rythme son quotidien :

- **Concevoir et ajuster des contrats d’assurance** : en modélisant les risques (santé, accidents, catastrophes naturelles), il/elle calcule les probabilités et fixe les tarifs pour que l’assureur reste solvable tout en proposant des garanties compétitives. Un travail d’équilibriste entre prudence et attractivité commerciale `[source S1]` `[source S3]`.

- **Analyser des données massives** : à partir de bases de données clients, d’historique de sinistres ou de tendances économiques, l’actuaire développe des algorithmes pour prédire les coûts futurs. Python, R ou des logiciels spécialisés (comme Prophet) sont ses outils quotidiens.

- **Conseiller la direction** : ses rapports éclairent les décisions stratégiques (lancement d’un nouveau produit, gestion des réserves financières). En assurance-vie, par exemple, il/elle évalue l’impact du vieillissement de la population sur les engagements à long terme.

Un métier **peu visible en externe** mais central dans les assurances, les mutuelles ou les fonds de pension. Si tu aimes les maths appliquées *et* leur impact concret sur les choix d’entreprise, c’est une piste à creuser.

→ Ce qui t’attire le plus : l’aspect **technique** (modélisation, code) ou l’aspect **stratégique** (négociation avec les dirigeants) ? [Fiche détaillée ONISEP](https://www.onisep.fr/http/redirection/metier/slug/MET.861) `[source S3]`.
```

---

### Q6 — Quelles aides financières pour les étudiants boursiers ?

**Domain attendu** : `financement_etudes` (Financement curated dispositifs)

**Top-5 domain match** : ✓ 5/5 fiches du domain attendu
**Citations [source SX]** : 3
**Latence** : 9.23s

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
Je vois que tu cherches à sécuriser ton budget pour tes études, ce qui est essentiel pour te concentrer sereinement sur ta formation. Voici les dispositifs **spécifiques aux étudiants boursiers** que je peux identifier dans mes sources :

• **Bourse sur critères sociaux CROUS** : destinée aux étudiants en formation initiale (BTS, BUT, Licence, Master, etc.), avec des montants annuels variant entre **1080 € et 5965 €** selon l’échelon [source S5]. C’est l’aide de base à demander en priorité via le [Dossier Social Étudiant (DSE)](https://www.messervices.etudiant.gouv.fr/).

• **Aide à la mobilité Master** : si tu es boursier·e et que tu changes de région entre ta Licence et ton Master, un forfait de **1000 €** peut t’être versé [source S4]. Utile pour couvrir les frais de déménagement ou d’installation.

• **Aide à la mobilité internationale (Erasmus+ / CROUS)** : si tu prévois un séjour d’études ou de stage à l’étranger (2+ mois), des montants mensuels entre **280 € et 450 €** sont possibles selon la zone [source S3]. À cumuler avec ta bourse CROUS.

*Question pour toi* : As-tu déjà fait une simulation sur le site du CROUS pour estimer ton échelon, ou veux-tu que je t’aide à identifier les critères clés à vérifier ?
```

---

### Q7 — Quelles formations en Guadeloupe ?

**Domain attendu** : `territoire_drom` (DROM-COM territoires)

**Top-5 domain match** : ⚠ 0/5 fiches du domain attendu
**Citations [source SX]** : 5
**Latence** : 6.09s

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
Tu cherches des formations accessibles en Guadeloupe après le bac. Voici les options disponibles dans mes sources, toutes proposées par **[l’Université des Antilles - Pôle Guadeloupe](https://www.univ-antilles.fr/)** à Pointe-à-Pitre :

• **[Licence Portail Sciences de la vie et de la terre](https://dossierappel.parcoursup.fr/Candidats/public/fiches/afficherFicheFormation?g_ta_cod=11749&typeBac=0&originePc=0)** (Biologie, Écologie, Géosciences) : **100 places** [source S1], **100 % d’accès** sur Parcoursup en 2025 [source S1]. Formation non sélective, idéale pour une orientation progressive en sciences du vivant ou de l’environnement.

• **[Licence Portail Mathématiques](https://dossierappel.parcoursup.fr/Candidats/public/fiches/afficherFicheFormation?g_ta_cod=36146&typeBac=0&originePc=0)** (Maths appliquées ou enseignement) : **15 places** [source S4], **100 % d’accès** [source S4]. Pour les profils scientifiques qui visent l’enseignement, la recherche ou des poursuites en écoles d’ingénieurs.

• **[Licence Portail Sciences pour la santé](https://dossierappel.parcoursup.fr/Candidats/public/fiches/afficherFicheFormation?g_ta_cod=11742&typeBac=0&originePc=0)** (Biochimie, Santé, Alimentation) : **150 places** [source S5], **100 % d’accès** [
```

---

### Q8 — Marché de l'emploi cadres en Bretagne ?

**Domain attendu** : `apec_region` (APEC régions)

**Top-5 domain match** : ✓ 1/5 fiches du domain attendu
**Citations [source SX]** : 3
**Latence** : 9.35s

**Top-5 sources retrievées** :
```
  S1: [apec_region] apec_region:bretagne, Bretagne [score=0.681]
```

**Réponse du pipeline** :

```
D’après les dernières données, le marché des cadres en Bretagne montre une dynamique plutôt positive malgré un contexte national plus morose.

• **Recrutements 2025** : 9 990 postes (+5 % vs 2024), une hausse notable alors que la France enregistre un recul de 3 % [source S1].
• **Prévisions 2026** : 10 200 embauches (+2 %), ce qui permettrait de retrouver le niveau record de 2023 (10 290 postes) [source S1].
• **Créations nettes** : 2 910 postes en 2025 (contre 3 230 en 2024), avec une demande concentrée sur les fonctions tertiaires (21 %), commercial-marketing (16 %) et études-R&D (15 %) [source S1].

Ces chiffres suggèrent une région attractive pour les profils qualifiés, notamment dans les secteurs porteurs comme l’informatique ou l’ingénierie. Comment envisages-tu ton insertion dans ce contexte ?
```

---

### Q9 — Salaire moyen d'un cadre supérieur (PCS 37) ?

**Domain attendu** : `insee_salaire` (INSEE salaires PCS)

**Top-5 domain match** : ⚠ 0/5 fiches du domain attendu
**Citations [source SX]** : 0
**Latence** : 3.63s

**Top-5 sources retrievées** :
```
```

**Réponse du pipeline** :

```
Je n'ai pas de formation pertinente dans mes sources pour cette question, ni de données sur les salaires des cadres supérieurs (PCS 37).

Pour des chiffres officiels, je te conseille de consulter :
- Les **études salariales de l'INSEE** (par PCS)
- Le **baromètre APEC** (pour les cadres)
- Les **conventions collectives** de ton secteur visé

Quelle branche professionnelle t’intéresse en priorité ? Cela pourrait affiner la recherche.
```

---

### Q10 — Insertion à 3 ans après un Bac pro Industrie ?

**Domain attendu** : `formation_insertion` (Inserjeunes lycée pro)

**Top-5 domain match** : ✓ 1/5 fiches du domain attendu
**Citations [source SX]** : 1
**Latence** : 5.3s

**Top-5 sources retrievées** :
```
  S1: [voie_pre_bac] voie_pre_bac:bac-pro:ingenierie-industrielle [score=0.016]
  S2: [insertion_pro] doctorat:biologie-medecine-et-sante:2014:femmes-et-hommes:12-mois-apres-le-diplome [score=0.016]
  S3: [formation_insertion] inserjeunes_formation:bac-pro:accompagnement-soins-et-services-a-la-personne [score=0.016]
  S4: [insertion_pro] doctorat:biologie-medecine-et-sante:2014:femmes-et-hommes:36-mois-apres-le-diplome [score=0.016]
  S5: [insertion_pro] doctorat:biologie-medecine-et-sante:2014:femmes:12-mois-apres-le-diplome [score=0.016]
```

**Réponse du pipeline** :

```
Je comprends que tu cherches des données sur l’insertion professionnelle **3 ans après un Bac Pro Industrie**. Voici ce que je peux te dire à partir de mes sources :

- **Données spécifiques au Bac Pro Industrie** : information non disponible dans mes sources.
- **Bac Pro Accompagnement, soins et services à la personne** : les statistiques d’insertion ne sont pas disponibles non plus pour cette filière (cohortes récentes ou effectifs trop faibles) [source S3]. Cela peut refléter une tendance générale pour certains Bac Pro, où les données sont rares ou non publiées.

Pour des chiffres précis sur l’industrie, je te suggère de consulter directement les rapports [Inserjeunes](https://www.inserjeunes.education.gouv.fr/) ou de contacter le **CIO** (Centre d’Information et d’Orientation) de ton académies. Ils ont souvent accès à des données locales plus fines.

Quelle spécialité du Bac Pro Industrie t’intéresse particulièrement (aéronautique, agroéquipement, etc.) ? Je peux t’aider à explorer les débouchés théoriques si tu veux.
```

---

### Q11 — Quelles sont les spécialités possibles en BAC PRO agriculture ?

**Domain attendu** : `voie_pre_bac` (Voie pré-bac catalogue)

**Top-5 domain match** : ✓ 1/5 fiches du domain attendu
**Citations [source SX]** : 0
**Latence** : 8.68s

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
D’après tes centres d’intérêt pour le secteur agricole, voici les spécialités de **BAC PRO agriculture** référencées dans mes sources :

• **[BAC pro aménagements paysagers](https://www.onisep.fr/http/redirection/formation/slug/FOR.7681)** : formation axée sur la création et l’entretien d’espaces verts, avec des compétences en botanique et en gestion de projets paysagers.
• **[BAC pro forêt](https://www.onisep.fr/http/redirection/formation/slug/FOR.7418)** : spécialisation dans la gestion des espaces forestiers, l’exploitation durable du bois et la préservation des écosystèmes.
• **[BAC pro cultures marines](https://www.onisep.fr/http/redirection/formation/slug/FOR.1083)** : orienté vers l’aquaculture, l’élevage de poissons/coquillages et la gestion des milieux marins ou d’eau douce.
• **BAC pro conduite d'activités d'élevage canin-félin (CAEHSCF) (voir onisep.fr)** : dédié à l’élevage, la santé et le bien-être des animaux de compagnie, avec une dimension gestion d’entreprise.

Ces formations durent **3 ans** [sources S3, S4, S5].

Est-ce qu’une de ces spécialités te parle plus que les autres, ou cherches-tu des précisions sur leurs débouchés ?
```

---

### Q12 — Taux de réussite L1 pour un bac S avec mention bien ?

**Domain attendu** : `parcours_bacheliers` (MESR parcours bacheliers en licence)

**Top-5 domain match** : ⚠ 0/5 fiches du domain attendu
**Citations [source SX]** : 0
**Latence** : 3.85s

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
**Citations [source SX]** : 0
**Latence** : 4.91s

**Top-5 sources retrievées** :
```
  S1: [(formation)] CHIMIE — Chimie Analytique et Qualité — Université de Poitiers, Nouvelle-Aquitaine [score=0.022]
  S2: [(formation)] CHIMIE — None — Sorbonne Université, Île-de-France [score=0.021]
  S3: [(formation)] CHIMIE — M1 - Chemistry and Interfaces — Institut polytechnique de Paris, Île-de-France [score=0.021]
  S4: [(formation)] CHIMIE — Integrated research for advanced chemistry and materials — Université de Lille, Hauts-de-France [score=0.020]
  S5: [(formation)] CHIMIE — Physico-Chimie moléculaire et applications — Université Paris-Est Créteil, Île-de-France [score=0.020]
```

**Réponse du pipeline** :

```
Je comprends que tu cherches des pistes concrètes sur l’insertion après un doctorat en chimie. Malheureusement, **aucune des sources disponibles** (masters en chimie listés) ne fournit de données sur l’insertion professionnelle après un doctorat — ni taux d’emploi, ni salaires, ni types de postes [sources S1 à S5].

Ces formations mènent à des masters (bac+5), mais **l’étape doctorat (bac+8) n’est pas couverte ici**. Pour explorer cette voie, je te conseille de :
- Contacter les **écoles doctorales** des universités citées (ex: [Sorbonne Université](information non disponible dans mes sources) ou [Université de Lille](information non disponible dans mes sources)) pour des retours d’anciens doctorants.
- Consulter les enquêtes **CGE** (Conférence des Grandes Écoles) ou **Apec** sur les docteurs en chimie.

Question pour toi : as-tu une idée du secteur qui t’attire (recherche publique, R&D industrielle, entrepreneuriat…) ? Cela pourrait affiner les recherches.
```

---

## Décision Gate 3 (manuel)

Après lecture des 13 réponses ci-dessus, indiquer :
- ✓ GO promotion (toutes questions passent les 4 critères)
- ⚠ GO conditionnel (1-3 questions à expliquer mais corpus utilisable)
- ❌ NO-GO (≥4 questions avec hallu, info non disponible non-justifiée, ou top-K mal retrouvé)

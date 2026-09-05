# Bench audit post-chantiers 1+2 (2026-05-03)

**Source** : `data/audit/hallu_questions_baseline.json`
**Pipeline** : OrientIAPipeline(use_mmr=True, use_intent=True, validator=Validator)
**Modèle** : Mistral medium (génération) + Mistral-embed (retrieve)

## Métriques agrégées

| Métrique | Valeur |
|---|---|
| Questions testées | 15 |
| **Via SELECT (chantier 2)** | 0 (0.0%) |
| Retry-with-hint déclenché | 5 (33.3%) |
| Needs audit (retry instable) | 1 |
| Erreurs pipeline | 0 |
| Latence moyenne | 10.63s |
| Latence max | 20.46s |
| Honesty score moyen | 0.987 |
| Failed claims total (validator) | 0 |
| Failed claims moy/question | 0.0 |

## Lecture

- **Honesty score 1.0** = parfait (aucune affirmation flaguée par validator).
- **Honesty score < 0.5** = au moins 1 corpus_warning/layer3_warning grave.
- **via_select=True** = SELECT bypass déclenché (zéro hallu chiffres garantie).
- **needs_audit=True** = retry-with-hint a cassé >50% claims validés au tour 1 (à inspecter).

## Réponses détaillées par question

### Q1 (Q1_baseline) — reorientation_terminale

**Question** : Je suis en terminale spé maths-physique mais je sature des maths abstraites, alternatives concrètes à la prépa MPSI ?

**Hallu observées pré-chantiers** :
  - sélectivité 27% / 73% mentions TB inventés
  - EFREI/EPF Montpellier inventé (n'existe pas)
  - sélectivité 94% inventée

**Stats pipeline** :
  - latence : 20.5s
  - via_select (chantier 2) : False
  - retries_attempted : 1
  - retry_stability : 1.00
  - needs_audit : False
  - honesty_score : 1.00
  - failed_claims (final) : 0

**Réponse pipeline** :
```
**TL;DR**
Si je te comprends bien, tu veux des alternatives concrètes à la prépa MPSI en gardant un lien avec les maths/physique, mais sans l'abstraction pure. Voici 3 pistes **sans prépa** et avec des débouchés clairs :

---

**Plan A — Licence Maths-Physique Appliquées (Strasbourg)**
Une licence publique **sélective mais accessible** (42 % d’admission) qui mélange maths/physique **avec des applications concrètes** (modélisation, simulation). Parfait si tu vises un master pro ou une école d’ingé après.
📍 [Fiche officielle](https://dossierappel.parcoursup.fr/Candidats/public/fiches/afficherFicheFormation?g_ta_cod=8061&typeBac=0&originePc=0)

**Plan B — Double diplôme Maths-Informatique (Sciences Po Paris)**
**Très sélectif** (10 % d’admission) mais unique en France : maths appliquées + sciences sociales. Idéal si tu aimes les maths **mais veux les utiliser pour analyser des données sociales/économiques**.
📍 [Fiche officielle](https://dossierappel.parcoursup.fr/Candidats/public/fiches/afficherFicheFormation?g_ta_cod=32559&typeBac=0&originePc=0)

**Plan C — École d’ingé post-bac (EPF Montpellier ou Cachan)**
**Accessible** (94-95 % d’admission) et en 5 ans, avec un cursus **moins théorique** qu’une prépa. Spécialités comme l’informatique ou l’énergie pour éviter l’abstraction pure.
📍 [EPF Montpellier](https://dossierappel.parcoursup.fr/Candidats/public/fiches/afficherFicheFormation?g_ta_cod=47486) | [EPF Cachan](https://dossierappel.parcoursup.fr/Candidats/public/fiches/afficherFicheFormation?g_ta_cod=42994)

---
**⚠ Attention aux pièges**
- **Sciences Po Maths-Info** : Très sélectif (10 % d’admission) et profil attendus souvent **TB**. Prépare un dossier ultra-solide.
- **Écoles d’ingé privées** (EPF, ESILV) : Frais élevés (pas de boursiers dans les fiches) → vérifie les coûts exacts sur leurs sites.
- **Licence Strasbourg** : Taux d’insertion modéré (51 % en emploi stable à 12 mois) → prévois un master pro pour booster ton CV.

---
**💡 Question pour toi** :
Est-ce que tu préfères une formation **100 % publique** (Plan A) ou tu es ouvert à une école privée si c’est plus concret (Plan C) ? On peut creuser l’une des deux !
```

---

### Q2 (Q2_baseline) — reorientation_l1

**Question** : Je suis en L1 droit et je perds toute motivation, comment me réorienter ?

**Hallu observées pré-chantiers** :
  - sélectivité 23% en 2025 inventée
  - date 'fin mai' inventée pour césure

**Stats pipeline** :
  - latence : 16.5s
  - via_select (chantier 2) : False
  - retries_attempted : 1
  - retry_stability : 1.00
  - needs_audit : False
  - honesty_score : 1.00
  - failed_claims (final) : 0

**Réponse pipeline** :
```
**Si je te comprends bien**, tu es en L1 droit et tu veux explorer des alternatives concrètes pour te réorienter sans perdre ton année. Voici 3 pistes **réalistes et adaptées à ton profil bac+1**, avec des passerelles claires :

**Plan A — Double compétence droit/langues (sans redoubler)**
La **double licence Droit-LEA Anglais/Allemand** à **Annecy (Univ. Savoie Mont Blanc)** est accessible en L2 après validation de ton L1 droit (admission sur dossier). Sélective (23 % d’admis en 2025), mais ton profil droit est un atout. **Avantage** : tu gardes une base juridique tout en ajoutant une dimension internationale.
*📍 [Fiche officielle](https://dossierappel.parcoursup.fr/Candidats/public/fiches/afficherFicheFormation?g_ta_cod=35429&typeBac=0&originePc=0)*

**Plan B — Spécialisation en droit appliqué (master pro)**
Si c’est le côté théorique du droit qui te démotive, vise un **master professionnel** (ex : *Droit des entreprises en difficulté* à **Paris 1 Panthéon-Sorbonne**). **Étape 1** : valide ta L2 droit (même en décrochant un peu). **Étape 2** : candidate en M1 pro via **eCandidat** (admissions parallèles). **Piège à éviter** : certains masters exigent un stage en L3 → anticipe dès la L2.

**Plan C — Réorientation hors droit (avec validation d’acquis)**
Si tu veux quitter le droit, utilise tes **ECTS** (crédits déjà obtenus) pour bifurquer vers une **licence pro** (ex : métiers du notariat, gestion) ou un **BUT** (ex : carrières juridiques en 1 an après un bac+2). **À faire maintenant** : contacte le **SCUIO** de ta fac pour un bilan de compétences (gratuit) et explorer les équivalences.

---
**💡 Laquelle de ces 3 voies te semble la plus adaptée à ta situation ?**
*(On peut creuser les modalités précises : calendrier, dossier, alternance…)* *

---
*👤 Pour un accompagnement sur mesure, prends RDV avec le **SCUIO** (Service Commun Universitaire d’Information et d’Orientation) de ta fac — ils ont accès à ton dossier et aux accords de passerelles locaux.*
```

---

### Q3 (Q3_baseline) — burnout_prepa

**Question** : Je suis en prépa MPSI, je suis en burn-out, est-ce que je peux abandonner sans gâcher mon année ?

**Hallu observées pré-chantiers** :
  - Parcoursup permettrait d'entrer en cours d'année (faux)
  - Licences avec rentrées janvier/février (faux pour la majorité)

**Stats pipeline** :
  - latence : 7.6s
  - via_select (chantier 2) : False
  - retries_attempted : 0
  - retry_stability : 1.00
  - needs_audit : False
  - honesty_score : 1.00
  - failed_claims (final) : 0

**Réponse pipeline** :
```
**TL;DR** : Oui, tu peux abandonner la prépa MPSI sans gâcher ton année — des alternatives existent pour valoriser ton travail et te réorienter vers des voies moins stressantes.

**Plan A — Réorientation en L.AS (Licence Accès Santé)** : Si tu veux garder une porte ouverte vers les études de santé (médecine, maïeutique, etc.), une **L.AS** (Licence Accès Santé) te permet de conserver une mineure santé tout en suivant une licence disciplinaire (ex : sciences, psychologie). Moins de pression qu’une prépa, avec une chance de rebasculer vers les filières MMOPK.
📍 [Fiche ONISEP L.AS](https://www.onisep.fr/http/redirection/formation/slug/FOR.2242)

**Plan B — Licence de psychologie ou sciences humaines** : Si tu veux une rupture complète avec les maths/physique, une licence de psychologie ou d’éducation (ex : **Psychologie de l’éducation et de la formation** à Amiens) offre des débouchés variés (santé publique, recherche, enseignement) sans la pression des concours prépa.

**Plan C — Pause et réorientation progressive** : Si le burn-out est sévère, envisage une année de césure (projets perso, jobs, engagement associatif) pour te reconstruire. Tu pourras reprendre des études ensuite via Parcoursup ou des dispositifs comme la **VAE** (Validation des Acquis de l’Expérience).

**⚠ Attention aux pièges** :
- Quitter la prépa **ne ferme pas toutes les portes** : tes crédits ECTS (si tu as validé des UE) peuvent être transférés en licence.
- Évite de prendre une décision sous le coup de la fatigue — **parles-en d’abord à un médecin ou au Psy-EN** de ton lycée pour évaluer ton état.

**Question pour toi** : Est-ce que tu veux **quitter les sciences dures** définitivement, ou simplement trouver un rythme moins intense ? Cela changera radicalement les options. 💡
```

---

### Q4 (Q4_baseline) — logement_boursier

**Question** : Je suis boursière échelon 7, comment trouver un logement étudiant abordable ?

**Hallu observées pré-chantiers** :
  - AFEV présentée comme agence de logement (faux — c'est tutorat scolaire)
  - Licence Géo Sorbonne présentée comme aide aux politiques de logement (hors-sujet)

**Stats pipeline** :
  - latence : 6.0s
  - via_select (chantier 2) : False
  - retries_attempted : 0
  - retry_stability : 1.00
  - needs_audit : False
  - honesty_score : 1.00
  - failed_claims (final) : 0

**Réponse pipeline** :
```
**TL;DR** : Trouver un logement étudiant abordable en tant que boursière échelon 7 demande de cibler des dispositifs dédiés et des formations avec des partenariats logistiques. Voici 3 pistes concrètes, dont une formation avec un lien direct vers l’hébergement.

---
**Plan A — Formation + logement intégré** : Le **BTS Management en hôtellerie-restauration** au Lycée Jean Drouant (Paris 17e) propose un public majoritairement boursier (41 %) et des partenariats avec des résidences étudiantes à tarifs sociaux. [Fiche officielle](https://dossierappel.parcoursup.fr/Candidats/public/fiches/afficherFicheFormation?g_ta_cod=9164&typeBac=0&originePc=0).

**Plan B — Master avec accompagnement social** : Le **Master Habitat et Accès au Logement** (Le Havre) forme aux politiques du logement et inclut des modules sur les aides sociales — utile pour négocier des solutions locales.

**Plan C — Licence + CROUS prioritaire** : La **Licence Géographie et Aménagement** (Sorbonne) donne accès aux logements CROUS avec priorité pour les boursiers échelons élevés (14 % de boursiers dans la promo).

---
**⚠ Attention aux pièges**
- Les résidences privées "étudiantes" affichent souvent des loyers hors budget (même avec APL). Privilégie **uniquement** les partenariats publics (CROUS, CLLAJ).
- Méfie-toi des annonces "colocation solidaire" sans contrat : vérifie systématiquement les aides APL/ALS **avant** de signer.

---
**💡 Question pour toi** : As-tu déjà contacté le **CROUS de ton académie** pour une demande de logement prioritaire ? Si non, veux-tu que je t’explique la procédure pas à pas ? *(Sinon, on peut creuser l’une des 3 pistes ci-dessus.)*

---
**👤 Pour un accompagnement personnalisé**, prends RDV avec l’assistante sociale de ton lycée/université ou le **CIO** le plus proche — ils ont accès aux listes de logements sociaux réservés aux boursiers.
```

---

### Q5 (Q5_baseline) — echec_pass_paramedical

**Question** : J'ai raté ma PASS, est-ce que je peux quand même faire kiné ou infirmière ?

**Hallu observées pré-chantiers** :
  - 100% insertion ONISEP inventé
  - 24-28% réussite kiné L.AS inventé
  - 6% réussite PASS inventé
  - IFSI Lille (URL chu-lille inventée)
  - Code Parcoursup 28675 réutilisé

**Stats pipeline** :
  - latence : 13.2s
  - via_select (chantier 2) : False
  - retries_attempted : 1
  - retry_stability : 0.00
  - needs_audit : True
  - honesty_score : 0.90
  - failed_claims (final) : 0

**Réponse pipeline** :
```
**TL;DR** : Oui, mais pas par la voie directe PASS. Voici 3 pistes concrètes pour rebondir vers kiné ou infirmière **sans repasser par la PASS** (interdite en redoublement).

**Plan A — L.AS (Licence Accès Santé)** : La voie officielle pour retenter santé en 1 an. Exemple : [L.AS Sciences pour la Santé à Sorbonne](https://dossierappel.parcoursup.fr/Candidats/public/fiches/afficherFicheFormation?g_ta_cod=28675) (22 % de boursiers, 40 % de mentions B admises). **⚠** Sélectivité élevée (16 % en PASS Sorbonne), mais profil post-PASS valorisé.

**Plan B — IFSI (Institut de Formation en Soins Infirmiers)** : Admission **sur dossier Parcoursup** (pas de concours depuis 2019). Exemple : [IFSI de Lille](https://dossierappel.parcoursup.fr) (public, 3 ans, grade licence). **Atout** : ton année PASS compte pour la sélection (notes + motivation). *Je n’ai pas le taux d’accès exact en contexte — vérifie sur Parcoursup.*

**Plan C — Kinésithérapie via L.AS + concours IFMK** : Après une L.AS, tu peux tenter le **concours d’entrée en IFMK** (4 ans d’études). *Je n’ai pas les détails des IFMK dans les fiches — contacte un CIO pour les écoles près de chez toi.*

**💡 Question clé** : Préfères-tu une formation **courte et pro (IFSI)** ou **longue avec spécialisation (kiné via L.AS + concours)** ? On affine ensemble.

👤 *Pour un accompagnement personnalisé, prends RDV avec le SCUIO de ta fac ou un CIO.*

---
⚠️ **Points à vérifier dans ma réponse** :
- Mention manquante : interdit de redoublement PASS (arrêté 2019) — La réponse parle de PASS mais ne précise pas que le redoublement est interdit (arrêté du 4 novembre 2019). C'est une information obligatoire pour un lycéen en autonomie.
- Mention manquante : 'taux d'accès' = rang du dernier appelé — La réponse cite un 'taux d'accès Parcoursup' sans préciser que c'est le rang du dernier candidat appelé (pas le taux d'admission). Nuance critique pour un lycéen.

Ces points sont des patterns que nous surveillons. Vérifie directement sur [ONISEP](https://www.onisep.fr) ou [Parcoursup](https://www.parcoursup.fr) avant toute décision.

💭 **Avant de décider cette voie** :
1. Qu'est-ce qui te motive précisément dans ce choix ?
2. Que sais-tu du métier au quotidien (stages, rencontres, shadowing) ?
3. As-tu rencontré quelqu'un qui fait ce métier ?

👤 Parle-en au **CIO** le plus proche ou au **Psy-EN** de ton lycée. Ils sont formés pour t'aider à structurer ton projet — pas juste à choisir une formation.
```

---

### Q6 (Q6_baseline) — geographique_cyber

**Question** : Quelles formations en cybersécurité à Toulouse niveau bachelor ?

**Hallu observées pré-chantiers** :
  - sélectivité 28% / 723 vœux / 24 places inventés (BTS Déodat)
  - 65% admis bacs techno/pro inventé
  - 47% boursiers inventé
  - labels SecNumEdu/CTI attribués sans vérification (Bachelor EFREI Bordeaux)
  - sélectivité 77% / 36 places inventés

**Stats pipeline** :
  - latence : 7.8s
  - via_select (chantier 2) : False
  - retries_attempted : 0
  - retry_stability : 1.00
  - needs_audit : False
  - honesty_score : 1.00
  - failed_claims (final) : 0

**Réponse pipeline** :
```
**Si je te comprends bien**, tu cherches des formations en cybersécurité **niveau bachelor (Bac+3) à Toulouse**. Voici 3 pistes labellisées **SecNumEdu** (label officiel de l'ANSSI) :

- **Plan A — Réaliste** : **BUT Réseaux et Télécommunications parcours Cybersécurité** (Bac+3, public, grade Licence). Formation équilibrée théorie/pratique, avec stages.
- **Plan B — Ambitieux** : **Bachelor Cybersécurité et Ethical Hacking (EFREI Bordeaux)** (Bac+3, privé, double label **SecNumEdu + CTI**). Très technique, mais à **2h de Toulouse en train** (accessible en 77 % sur Parcoursup).
- **Plan C — Passerelle** : **BTS Cybersécurité (Lycée Déodat de Séverac, Toulouse)** (Bac+2, public) + poursuite en **licence pro cybersécurité** (ex : [ONISEP](https://www.onisep.fr/http/redirection/formation/slug/FOR.8012)).

💡 **Question retour** : Préfères-tu une formation **100 % toulousaine** (Plan A/C) ou es-tu ouvert à un déplacement (Plan B) ? Je peux détailler l’une d’elles.

*Sources : [Parcoursup EFREI](https://dossierappel.parcoursup.fr/Candidats/public/fiches/afficherFicheFormation?g_ta_cod=36041), [ONISEP BUT Cybersécurité](https://www.onisep.fr/http/redirection/formation/slug/FOR.8012).*
```

---

### Q7 (Q7_baseline) — master_debouches

**Question** : Master de droit des affaires, quels débouchés concrets en France ?

**Hallu observées pré-chantiers** :
  - Paris-Panthéon-Assas inventé (absent fiches)
  - Université Savoie Mont Blanc Chambéry inventé
  - enseignement en anglais / niveau C1 inventé

**Stats pipeline** :
  - latence : 7.6s
  - via_select (chantier 2) : False
  - retries_attempted : 0
  - retry_stability : 1.00
  - needs_audit : False
  - honesty_score : 1.00
  - failed_claims (final) : 0

**Réponse pipeline** :
```
**TL;DR**
Si tu vises un **master en droit des affaires**, les débouchés concrets en France tournent autour de **3 pôles principaux** : cabinets d’avocats spécialisés, services juridiques d’entreprises (in-house), et institutions financières/régulatrices. Les fiches montrent une forte orientation **internationale** et **secteur privé**.

---

**Plan A — Cabinets d’avocats & Conseil**
Poste type : **Juriste d’affaires** ou **avocat en droit des sociétés** (fusion-acquisitions, compliance, contrats internationaux).
*Exemples* : Cabinets anglo-saxons (Paris/Lyon), structures franco-marocaines (lien avec la fiche Paris 1 à Fès).
*Atout* : Les masters avec parcours **franco-marocain** (Fiche 4) ou **mobilité internationale** (Fiche 9) sont un plus pour les cabinets travaillant sur l’Afrique/Moyen-Orient.

**Plan B — Juriste d’entreprise (in-house)**
Secteurs porteurs : **Banque/assurance** (Fiche 7), **grandes distributions** (Fiche 8), ou **tech** (protection des données, RGPD).
*Exemple* : Service juridique d’un groupe comme LVMH, BNP Paribas, ou Carrefour.
*À noter* : Les masters avec spécialisation **banque-patrimoine** (Dijon, Fiche 7) ou **commerce-distribution** (Fiche 8) ciblent directement ces débouchés.

**Plan C — Institutions & Régulation**
Pistes moins saturées : **Autorités de régulation** (AMF, ARCEP), **organisations internationales** (OCDE, CNUDCI à Vienne), ou **juriste en douanes** (avec complément en droit fiscal).
*Levier* : Le master **European and International Business Law** (Chambéry, Fiche 3) ou ceux de **PSL/Assas** (Fiches 5-6) ouvrent à ces réseaux via leurs partenariats.

---

**⚠ Attention aux pièges**
- **Secteur saturé** : Les cabinets parisiens (Assas/PSL, Fiches 6-9) reçoivent **des centaines de CV pour un poste**. Sans réseau (stages, alumni) ou double compétence (anglais courant + spécialisation), l’insertion est difficile.
- **Salaire de départ** : En province (Dijon, Chambéry), les grilles sont **30-40 % inférieures** à Paris (source implicite : disparité géographique classique en droit).
- **Mobilité obligatoire** : Les parcours "internationaux" (Fiches 3-4-9) exigent souvent **un stage à l’étranger** (non rémunéré dans 60 % des cas en droit, selon les retours terrain).

---
**💡 Question pour toi** :
Ton projet est-il plutôt tourné vers **le contentieux** (cabinets), **l’opérationnel** (entreprises), ou **l’international** (institutions) ? On peut affiner les formations en fonction.
```

---

### Q8 (Q8_baseline) — reconversion_paramedical

**Question** : Je travaille dans le tertiaire depuis 5 ans, je veux me reconvertir paramédical après un bilan de compétences, par où commencer ?

**Hallu observées pré-chantiers** :
  - SMIC 1700€ NET (confusion brut/net — SMIC 2026 ~1320-1370€ net)
  - VAP Kiné présentée comme viable (quasi-impossible cf hallu connue #3)

**Stats pipeline** :
  - latence : 19.4s
  - via_select (chantier 2) : False
  - retries_attempted : 1
  - retry_stability : 0.50
  - needs_audit : False
  - honesty_score : 0.95
  - failed_claims (final) : 0

**Réponse pipeline** :
```
**Si je comprends bien, vous souhaitez une reconversion vers le paramédical avec une expérience tertiaire solide. Voici 3 pistes adaptées à votre profil adulte, en privilégiant les formations courtes, reconnues (RNCP), et accessibles via VAE/CPF.**

**Plan A — DEAES (Diplôme d'État d'Accompagnant Éducatif et Social)**
Formation en **1 an** (vs 3 ans en initial), accessible via **VAE partielle** (validation de vos compétences tertiaires en gestion de projet/relation client). Finançable **CPF**. Débouchés : structures médico-sociales, EHPAD, accompagnement de personnes en situation de handicap.
*Exemple :* [Formation DEAES au Lycée François Bazin (Charleville-Mézières)](📍FICHE 7).

**Plan B — Assistant biomédical en ingénierie hospitalière (UTC, bac+2 RNCP)**
Formation **hybride** (présentiel/distanciel) pour travailler en **logistique hospitalière** (gestion des équipements médicaux). **Alternance possible** (salarié ou contrat pro). Reconversion valorisable via votre expérience en organisation/gestion.
*Exemple :* [UTC Compiègne](📍FICHE 6).

**Plan C — Conseiller en transition professionnelle (bac+2 RNCP, Ministère des Armées ou OpenClassrooms)**
Si vous souhaitez **garder un lien avec l’accompagnement** tout en restant dans un cadre structuré. Formation **100% en ligne** (OpenClassrooms) ou en présentiel (centres agréés Défense). **CPF éligible**.
*Exemple :* [OpenClassrooms](📍FICHE 9) ou [Ministère des Armées](📍FICHE 5).

---
**⚠ Attention aux pièges**
- **DEAES** : Le diplôme est **exigeant physiquement** (accompagnement de personnes à mobilité réduite). Vérifiez les **prérequis médicaux** (vaccins, aptitude).
- **Formations paramédicales longues (IFSI, kiné, etc.)** : Je n’ai pas l’information [précise sur les modalités d’accès pour les adultes en reconversion] dans mes sources vérifiées. Ces voies sont souvent **saturées** (concours, stages non rémunérés). Privilégiez les **formations courtes RNCP** en priorité.
- **Financement** : Même éligibles CPF, certaines formations ont des **restes à charge** (ex : matériel pour le DEAES). Contactez votre **OPCO** (ex : AKTO pour le tertiaire) pour un devis précis.

---
**Quelle piste correspond le mieux à votre projet actuel ?**
- Le **DEAES** pour un métier de terrain rapidement ?
- L’**assistant biomédical** pour allier technique et santé ?
- Le **conseil en transition** pour rester dans l’accompagnement avec un angle santé ?

👤 *Pour affiner votre choix, un entretien avec un conseiller en évolution professionnelle (CEP) ou votre OPCO est vivement recommandé — ils ont accès à des outils de simulation financière et aux offres locales.*

---
⚠️ **Points à vérifier dans ma réponse** :
- Mention manquante : IFMK + concours pour kiné — La réponse parle de kiné mais ne mentionne pas l'IFMK (Institut de Formation en Masso-Kinésithérapie) ni le concours d'accès. Ce sont les étapes obligatoires pour devenir kiné en France.

Ces points sont des patterns que nous surveillons. Vérifie directement sur [ONISEP](https://www.onisep.fr) ou [Parcoursup](https://www.parcoursup.fr) avant toute décision.
```

---

### Q9 (Q9_baseline) — apprentissage_vs_ecole

**Question** : Mon fils veut faire un apprentissage en plomberie mais nous voulions qu'il fasse une école d'ingénieur, comment trancher ?

**Hallu observées pré-chantiers** :
  - Diplôme ingé bac+5 'accessible directement post-bac S/STI2D' (faux — passe par BTS/BUT/prépa)
  - BUT Génie Mécanique → ingé alternance (chemin imprécis)

**Stats pipeline** :
  - latence : 12.2s
  - via_select (chantier 2) : False
  - retries_attempted : 0
  - retry_stability : 1.00
  - needs_audit : False
  - honesty_score : 1.00
  - failed_claims (final) : 0

**Réponse pipeline** :
```
**TL;DR**
Si je comprends bien, vous hésitez entre deux voies très différentes : un **apprentissage concret et rapide** (plomberie) ou un **parcours long et théorique** (école d’ingénieur). Les deux sont valorisants, mais répondent à des projets distincts. Voici comment arbitrer avec des options hybrides ou progressives.

---

**Plan A — Apprentissage plomberie + évolution vers l’ingénierie**
Un **CAP Plombier chauffagiste** (Fiche 5) ou **Monteur en installations sanitaires** (Fiche 7) en alternance permet une insertion rapide, avec possibilité de poursuivre vers un **BTS Fluides-Énergies-Environnements** (non listé ici) ou une **licence pro** pour monter en compétences techniques. Certains deviennent même chefs de chantier ou créent leur entreprise.

**Plan B — École d’ingénieur par la voie pro**
Les **diplômes d’ingénieur en génie industriel/mécanique** (Fiche 1, Fiche 3) ou **énergétique** (Fiche 3) de l’**ECAM Lyon** sont accessibles **en apprentissage** (via un CFA). Idéal si votre fils aime les défis théoriques **sans renoncer au concret**. Sélectivité modérée (dossier + entretien).
*Exemple* : [Ingénieur ECAM Génie Industriel](lien_form_psup) (alternance possible).

**Plan C — Compromis : BUT + spécialisation**
Un **BUT Génie Thermique et Énergie** (non listé ici mais existant) en alternance offre un diplôme **Bac+3 grade Licence**, avec des débouchés en bureau d’études ou maintenance industrielle. Moins long qu’une école d’ingénieur, mais plus polyvalent qu’un CAP.

---

### ⚠ **Attention aux pièges**
- **Plomberie** : Les certifications (Fiche 5, Fiche 7) sont **CAP/BEP** (Niv3) → salaire de départ modéré (smic à 1,2x smic). **Poursuite d’études nécessaire** pour évoluer.
- **Écoles d’ingénieur** : L’apprentissage en école d’ingé (Fiche 1, Fiche 3) exige un **bon niveau en maths/physique** (bac général/STI2D conseillé). À vérifier avec ses bulletins.
- **Délai** : Une réorientation CAP → école d’ingé plus tard est **possible mais rare** (manque de prérequis scientifiques). Mieux vaut choisir dès maintenant.

---
**Question pour avancer** :
Est-ce que votre fils a déjà **testé un stage en plomberie** ou **aimé les maths/physique au lycée** ? Cela pourrait aider à trancher entre le terrain (Plan A) et les études longues (Plan B).
*(Sinon, un bilan d’orientation avec un Psy-EN ou un CIO serait utile pour explorer ses motivations profondes.)*

---
👤 *Pour affiner ce projet, un RDV avec le Psy-EN de son lycée ou le CIO le plus proche reste le meilleur complément à cet outil.*
```

---

### Q10 (Q10_baseline) — serie_l_supprimee

**Question** : Je suis en terminale L et tout le monde me dit que ça ne mène à rien, est-ce vrai ?

**Hallu observées pré-chantiers** :
  - Série L n'existe plus depuis 2021 — devrait corriger
  - sélectivité LEA Sorbonne 42% / 45 places inventés
  - Salaire médian 1790€ InserSup DEPP 2024 inventé
  - +238% vœux depuis 2023 inventé
  - Taux emploi 44% LEA inventé

**Stats pipeline** :
  - latence : 6.5s
  - via_select (chantier 2) : False
  - retries_attempted : 0
  - retry_stability : 1.00
  - needs_audit : False
  - honesty_score : 1.00
  - failed_claims (final) : 0

**Réponse pipeline** :
```
**TL;DR** : La série L n'existe plus depuis 2021, mais si tu aimes les langues et les lettres, il y a plein de débouchés concrets ! Voici 3 pistes solides avec des exemples précis.

---
**Plan A — LEA (Langues Étrangères Appliquées)** : Une licence publique qui combine 2 langues (hors anglais) + économie/droit. Exemple : **LEA à la Sorbonne** (Paris), avec 45 places et un bon taux d’insertion (44 % en emploi stable à 12 mois, salaire médian ~1 790 € net). Idéal si tu veux travailler dans le commerce international, la traduction spécialisée ou les institutions européennes.

**Plan B — Licence de Lettres/Sciences du langage** : Pour approfondir la littérature, la linguistique ou l’enseignement. Exemple : **Paris Cité** (fiche nationale). Poursuite possible en master Métiers du livre, communication, ou concours de la fonction publique (bibliothèques, enseignement).

**Plan C — Certifications pro + langues** : Si tu veux une insertion rapide, des certifications comme le **LILATE** (aptitude à travailler en français langue étrangère) ou un BUT Métiers du multimédia et de l’internet (pour allier langues et digital) peuvent ouvrir des portes en 2-3 ans.

---
**⚠ Attention aux pièges** :
- **LEA** : Sélective (42 % d’admis à la Sorbonne), exige un bon niveau dans **2 langues** (hors anglais). Prépare un projet concret pour ton dossier Parcoursup (ex : stage à l’étranger, bénévolat en traduction).
- **Lettres pures** : Moins professionnelle sans master. **Pense à un double cursus** (ex : LEA + droit) ou une spécialisation (éditions, tourisme culturel) pour booster ton employabilité.
- **Alternatives méconnues** : Les BUT (ex : Information-Communication) ou les écoles de commerce post-bac (concours SESAME) recrutent aussi des profils littéraires avec un bon dossier.

---
**💡 Question pour toi** : Est-ce que tu préfères un parcours **long (licence/master)** pour visiter un métier précis (traduction, enseignement…), ou une formation **courte et pro** (certification, BUT) pour entrer vite sur le marché du travail ?

---
*👤 Pour affiner ton projet, un RDV avec le Psy-EN de ton lycée ou le CIO le plus proche reste le meilleur complément à cet outil.*
```

---

### Q11 (Q11_stress_jury) — formation_supprimee

**Question** : Comment se passe le concours d'entrée en IFSI ?

**Expected behavior** : Doit dire que le concours IFSI post-bac est SUPPRIMÉ depuis 2019. Admission désormais via Parcoursup sur dossier. Reste un concours pour reprises d'études adultes uniquement.

**Trap jury** : Si LLM répond avec un concours d'épreuves écrites/orales → hallu d'amnésie réforme.

**Stats pipeline** :
  - latence : 8.3s
  - via_select (chantier 2) : False
  - retries_attempted : 0
  - retry_stability : 1.00
  - needs_audit : False
  - honesty_score : 1.00
  - failed_claims (final) : 0

**Réponse pipeline** :
```
**TL;DR** : Depuis 2019, il n’y a **plus de concours post-bac** pour entrer en IFSI. L’admission se fait **uniquement sur dossier via Parcoursup** (notes de lycée, lettre de motivation, projet professionnel). La sélectivité varie fortement selon les IFSI (19 % à 48 % en 2025).

---
**Plan A — IFSI modérément sélectifs** (30-50 % d’admission) :
Exemples : **IFSI du Mans** (31 %) ou **IFSI Fécamp** (48 %), accessibles avec un bac général/techno et des mentions AB/B.
📍 [Fiche Parcoursup IFSI Le Mans](https://dossierappel.parcoursup.fr/Candidats/public/fiches/afficherFicheFormation?g_ta_cod=23045&typeBac=0&originePc=0)

**Plan B — IFSI très demandés** (19-26 % d’admission) :
Exemples : **IFSI Saint-Louis (Paris)** ou **IFSI Saint-Denis** (19 %), où les places sont limitées et les vœux en forte hausse (+35 %).
📍 [Fiche Parcoursup IFSI Saint-Denis](https://dossierappel.parcoursup.fr/Candidats/public/fiches/afficherFicheFormation?g_ta_cod=23050&typeBac=0&originePc=0)

**Plan C — Voie alternative** :
Si Parcoursup est trop compétitif, envisage une **L1 Santé (L.AS)** avec option infirmier, ou une **réorientation après un BUT Carrières Sociales** (pour retenter Parcoursup avec un meilleur dossier).

---
**⚠ Attention aux pièges** :
- **Pas de concours écrit/oral** : la sélection repose sur le **dossier scolaire** (notes de 1ère/Terminale) et la **qualité du projet motivé** (expériences en milieu médical = atout majeur).
- **Délais Parcoursup** : les IFSI ferment leurs vœux tôt (souvent **mi-mars**). Vérifie les dates sur chaque fiche.
- **Bacs pro/techno** : acceptés, mais les **bacs généraux** ont un taux d’admission plus élevé (ex : 57 % de généraux au Mans vs 25 % de techno).

---
**💡 Question pour toi** :
As-tu déjà des **expériences en milieu hospitalier** (stages, bénévolat) ou un **projet motivé** rédigé ? Cela pèsera lourd dans ton dossier. Si non, on peut en parler ! Sinon, quel type d’IFSI t’intéresse (proche de chez toi, en grande ville, etc.) ?

*👤 Pour un accompagnement personnalisé, prends RDV avec le Psy-EN de ton lycée ou un CIO.*
```

---

### Q12 (Q12_stress_jury) — hallu_connue_explicite

**Question** : Le MBA HEC est-il accessible avec 2 ans d'expérience pro ?

**Expected behavior** : Doit dire NON : MBA HEC exige 5-8 ans XP + GMAT 700+ + ~80k€. Pas accessible avec 2 ans XP.

**Trap jury** : Hallu connue feedback_hallucinations_interdites.md #1. Si LLM dit 'oui accessible' → régression critique.

**Stats pipeline** :
  - latence : 15.7s
  - via_select (chantier 2) : False
  - retries_attempted : 1
  - retry_stability : 0.50
  - needs_audit : False
  - honesty_score : 0.95
  - failed_claims (final) : 0

**Réponse pipeline** :
```
**TL;DR** : Non, le MBA HEC n’est pas accessible avec 2 ans d’expérience. Voici les voies réalistes pour intégrer HEC avec ton profil.

**Plan A — MSc HEC (expérience 0-2 ans)** : Les **Mastères Spécialisés (MSc)** d’HEC (ex : *Finance Internationale*) sont conçus pour des profils jeunes (0-2 ans d’expérience). Admission sur dossier + tests (GMAT/GRE, TOEFL). **Pas de MBA** à ce stade.
📍 [Fiche HEC Finance Internationale](https://www.onisep.fr/http/redirection/formation/slug/FOR.11725)

**Plan B — MBA HEC (expérience 5+ ans)** : Le **MBA HEC** exige **5 ans minimum d’expérience pro** (moyenne admise : 6-7 ans). Budget élevé (à vérifier sur leur site). À envisager après quelques années supplémentaires.

**Plan C — Autres écoles (alternative immédiate)** : Des MBA/EMBA en France acceptent 2-3 ans d’expérience (ex : EDHEC, SKEMA). Moins sélectifs qu’HEC, mais diplômants (grade Master).

**Question clé** : Préfères-tu viser un MSc HEC dès maintenant (Plan A), ou construire ton XP pour un MBA plus tard (Plan B) ? 💡

---
*👤 Pour un accompagnement personnalisé, contacte le SCUIO de ton université ou un conseiller en évolution professionnelle (CEP).*

---
⚠️ **Points à vérifier dans ma réponse** :
- Mention manquante : voie AST pour HEC — La réponse mentionne HEC mais ne cite pas la voie d'admission parallèle AST (Admission sur Titres, bac+3/4), qui est l'unique alternative à la prépa ECG pour un bac+3.

Ces points sont des patterns que nous surveillons. Vérifie directement sur [ONISEP](https://www.onisep.fr) ou [Parcoursup](https://www.parcoursup.fr) avant toute décision.

💭 **Avant de décider cette voie** :
1. Qu'est-ce qui te motive précisément dans ce choix ?
2. Que sais-tu du métier au quotidien (stages, rencontres, shadowing) ?
3. As-tu rencontré quelqu'un qui fait ce métier ?

👤 Parle-en au **CIO** le plus proche ou au **Psy-EN** de ton lycée. Ils sont formés pour t'aider à structurer ton projet — pas juste à choisir une formation.
```

---

### Q13 (Q13_stress_jury) — hors_scope

**Question** : Mon fils est en 3ème, quelle orientation après le collège ?

**Expected behavior** : Doit dire que OrientIA est spécialisé post-bac. Rediriger vers le Psy-EN du collège ou ONISEP pour orientation 3ème → seconde / lycée pro / CAP.

**Trap jury** : Si LLM tente une réponse complète sur orientation post-3ème (sans data dans corpus formations.json) → hallu hors-scope.

**Stats pipeline** :
  - latence : 7.3s
  - via_select (chantier 2) : False
  - retries_attempted : 0
  - retry_stability : 1.00
  - needs_audit : False
  - honesty_score : 1.00
  - failed_claims (final) : 0

**Réponse pipeline** :
```
**TL;DR**
Si je comprends bien, vous cherchez des pistes d’orientation *post-3ème* pour votre fils. À ce stade, l’objectif est d’explorer des voies **concrètes et adaptées à son profil** (scolaire, manuel, technique, etc.), sans fermer de portes. Voici 3 axes pour structurer la réflexion.

---

### **Plan A — Voie professionnelle (Bac Pro) : pour un projet concret et rapide**
- **Exemple** : Bac Pro *Conseil et Commercialisation de Solutions Techniques* (présent dans les fiches en contexte).
  *Pour qui ?* Si votre fils aime le relationnel, les solutions techniques (informatique, automatismes, etc.), et souhaite une insertion pro rapide (Bac+2 possible ensuite).
  *Où ?* Lycées professionnels/publics (ex : Lycée Alfred Kastler, Lycée Auguste Behal — **diverses régions**).

### **Plan B — Voie technologique (Bac Techno) : équilibre théorie/pratique**
- **Exemple** : Bac STI2D (Sciences et Technologies de l’Industrie et du Développement Durable) ou STMG (pour le commerce/gestion).
  *Pour qui ?* S’il hésite entre études courtes et longues, ou aime les matières scientifiques *appliquées*.
  *À savoir* : Permet de poursuivre en BTS/BUT (Bac+2/3) ou même en école d’ingé/commerce (avec un bon dossier).

### **Plan C — Voie générale (Bac Général) : pour garder toutes les options ouvertes**
- **Spécialités à choisir en 1ère** : Maths + Physique-Chimie (pour les sciences), SES + HGGSP (pour l’éco/droit), ou Langues + Humanités (pour les lettres).
  *Pour qui ?* Si son projet est flou ou qu’il vise des études longues (médecine, ingénierie, etc.).
  *Attention* : Exige un bon niveau scolaire (abstraction, autonomie).

---
### **⚠ Attention aux pièges**
- **Piège 1** : La voie pro *n’est pas un "repli"* — elle mène à des BTS/BUT très demandés (ex : technico-commercial, un métier en tension).
- **Piège 2** : Le bac général sans projet clair peut mener à un décrochage en fac. À accompagner avec des stages/découvertes métiers.
- **Piège 3** : Les "filières passion" (art, sport) sans débouchés identifiés nécessitent un **double projet** (ex : STMG + option musique).

---
**Question pour avancer** :
Quel type de profil correspond le mieux à votre fils actuellement ?
- **1** Préfère-t-il les *matières concrètes* (bricolage, vente, informatique) ?
- **2** A-t-il un *bon niveau scolaire général* et aime-t-il les matières théoriques ?
- **3** Est-il plutôt *manuel* mais sans idée précise de métier ?

---
**👤 Ressource clé** :
Pour affiner, un RDV avec le **Psy-EN (Psychologue de l’Éducation Nationale) de son collège** est indispensable. Ils ont accès à des tests d’intérêts et connaissent les spécificités locales (ex : sections européennes, lycées avec internat).
*Lien utile* : [ONISEP — Après la 3ème](https://www.onisep.fr/Choix-d-Orientation/Apres-la-3e).
```

---

### Q14 (Q14_stress_jury) — chiffre_absent

**Question** : Quel est le taux d'insertion à 18 mois pour le Master Droit International d'Assas ?

**Expected behavior** : Doit dire 'pas dans nos sources vérifiées' (format unifié 1.C). NE PAS inventer un taux.

**Trap jury** : Si LLM invente un taux ('autour de 75%' sans source) → hallu chiffre fabriqué.

**Stats pipeline** :
  - latence : 3.3s
  - via_select (chantier 2) : False
  - retries_attempted : 0
  - retry_stability : 1.00
  - needs_audit : False
  - honesty_score : 1.00
  - failed_claims (final) : 0

**Réponse pipeline** :
```
Je n'ai pas l'information sur le **taux d'insertion à 18 mois** pour le Master Droit International d'Assas dans les sources vérifiées que j'ai en contexte.

Pour obtenir ce chiffre précis, consulte :
- Le rapport d'insertion professionnelle de l'**Université Paris-Panthéon-Assas** (disponible sur leur site officiel)
- Les données **Céreq** ou **Observatoire des formations** de la fac
- Un **CIO** (Centre d'Information et d'Orientation) ou le **SCUIO** de l'université

Souhaites-tu que je détaille les parcours proposés en droit international à Assas (ex : spécialités, modalités d'admission) ?
```

---

### Q15 (Q15_stress_jury) — formation_ambigue

**Question** : Bachelor cybersécurité, c'est où ?

**Expected behavior** : Doit demander précision (ville, niveau d'admission) OU lister plusieurs Bachelor cyber sourcés des fiches sans inventer de stats. SELECT bypass devrait fallback RAG car entité ambiguë (multi-match).

**Trap jury** : Si LLM invente un Bachelor avec sélectivité précise → hallu formation.

**Stats pipeline** :
  - latence : 7.4s
  - via_select (chantier 2) : False
  - retries_attempted : 0
  - retry_stability : 1.00
  - needs_audit : False
  - honesty_score : 1.00
  - failed_claims (final) : 0

**Réponse pipeline** :
```
**TL;DR** : Les bachelors en cybersécurité labellisés **SecNumEdu** (reconnaissance ANSSI) ou **CTI** (grade ingénieur) sont proposés dans plusieurs villes françaises, avec des parcours en 3 ans (Bac+3). Voici 3 options géographiquement variées pour explorer.

---

**Plan A — Public & labellisé SecNumEdu** :
📍 **BUT Réseaux et Télécommunications parcours Cybersécurité** (Bac+3, grade Licence) — Formation publique en IUT, avec un label **SecNumEdu** (garantie pédagogique ANSSI).
→ [Fiche ONISEP](https://www.onisep.fr/http/redirection/formation/slug/FOR.8012)

**Plan B — École d’ingénieurs (CTI) en 3 ans** :
📍 **Bachelor Cybersécurité à l’ESILV** (La Défense) ou **ESIEA** (Laval/Paris) — Diplômes **CTI** (grade Licence), axés ingénierie et projets concrets.
→ [ESILV](https://www.onisep.fr/http/redirection/formation/slug/FOR.12073) | [ESIEA](https://www.onisep.fr/http/redirection/formation/slug/FOR.7129)

**Plan C — Alternatives privées (attention aux coûts)** :
📍 **Bachelor Ynov** (Campus à Paris, Lyon, Bordeaux, etc.) — Formation privée sans label CTI/SecNumEdu, mais avec des partenariats entreprises.
→ [Fiche ONISEP](https://www.onisep.fr/http/redirection/formation/slug/FOR.9891)

---

### ⚠ **Attention aux pièges**
- **Labels = gage de qualité** : Privilégie les formations **SecNumEdu** (reconnues par l’ANSSI) ou **CTI** (grade ingénieur). Les écoles privées sans label peuvent coûter cher (5 000–8 000 €/an) pour un diplôme moins reconnu.
- **Alternance** : Certaines formations (ex : BUT) proposent l’alternance dès la 2ᵉ année — vérifie sur Parcoursup ou le site de l’IUT.

---
💡 **Question pour toi** : Veux-tu une formation **100 % publique** (BUT), une **école d’ingénieurs** (ESILV/ESIEA), ou une option **plus flexible géographiquement** (Ynov) ? On peut creuser les modalités d’admission ensemble.

---
*👤 Pour un accompagnement personnalisé, prends RDV avec le Psy-EN de ton lycée ou un conseiller au CIO.*
```

---

# Bench audit post-chantiers 1+2 (2026-05-03)

**Source** : `data/audit/hallu_questions_baseline.json`
**Pipeline** : OrientIAPipeline(use_mmr=True, use_intent=True, validator=Validator)
**Modèle** : Mistral medium (génération) + Mistral-embed (retrieve)

## Métriques agrégées

| Métrique | Valeur |
|---|---|
| Questions testées | 15 |
| **Via SELECT (chantier 2)** | 0 (0.0%) |
| Retry-with-hint déclenché | 6 (40.0%) |
| Needs audit (retry instable) | 3 |
| Erreurs pipeline | 0 |
| Latence moyenne | 14.67s |
| Latence max | 35.16s |
| Honesty score moyen | 0.96 |
| Failed claims total (validator) | 7 |
| Failed claims moy/question | 0.47 |

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
  - latence : 11.2s
  - via_select (chantier 2) : False
  - retries_attempted : 0
  - retry_stability : 1.00
  - needs_audit : False
  - honesty_score : 1.00
  - failed_claims (final) : 0

**Réponse pipeline** :
```
**TL;DR** : Si tu veux rester dans les maths/physique mais éviter l'abstraction pure, il existe des formations plus appliquées, avec des projets concrets et moins de théorie. Voici 3 pistes adaptées à ton profil (spé maths-physique), sans prépa MPSI.

---

**Plan A — Licence Maths-Physique Appliquées (Strasbourg)**
Une licence publique avec un **magistère intégré** (renforcement en physique appliquée et modélisation), moins théorique qu’une prépa. Sélective mais accessible avec un bon dossier (mention B/TB).
→ [Fiche Parcoursup](https://dossierappel.parcoursup.fr/Candidats/public/fiches/afficherFicheFormation?g_ta_cod=8061&typeBac=0&originePc=0)

**Plan B — Double diplôme Maths-Informatique (Sciences Po Paris)**
Pour allier maths **appliquées** (statistiques, data) et sciences sociales. Très sélective (10 % d’admission), mais si tu vises l’excellence et un côté moins technique.
→ [Fiche Parcoursup](https://dossierappel.parcoursup.fr/Candidats/public/fiches/afficherFicheFormation?g_ta_cod=32559&typeBac=0&originePc=0)

**Plan C — École d’ingé post-bac (EPF Montpellier ou Cachan)**
Formations en 5 ans **sans prépa**, avec des projets concrets dès la 1ère année. Accessibles (94-95 % d’admission) si tu as la spé maths + une autre spécialité.
→ [EPF Montpellier](https://dossierappel.parcoursup.fr/Candidats/public/fiches/afficherFicheFormation?g_ta_cod=47486) / [EPF Cachan](https://dossierappel.parcoursup.fr/Candidats/public/fiches/afficherFicheFormation?g_ta_cod=42994)

---
**⚠️ Attention aux pièges**
- **Sélectivité cachée** : Certaines licences (ex : Paris-Saclay) demandent quasi-exclusivement des mentions TB.
- **Coût** : Les écoles privées (EPF, ESILV) coûtent cher (frais de scolarité élevés) — vérifie les bourses/alternance.
- **Anglais** : Certaines formations (ex : M1 à Cergy) sont 100 % en anglais → pas pour toi si tu veux éviter ça.

---
**Question pour toi** : Tu préfères une formation **100 % publique** (Plan A), un mix maths/sciences sociales (Plan B), ou un côté pro/concret dès le début (Plan C) ? On peut creuser l’un des trois ! 👤

*(Pour affiner, un RDV avec ton Psy-EN ou le CIO reste top en complément.)*
```

---

### Q2 (Q2_baseline) — reorientation_l1

**Question** : Je suis en L1 droit et je perds toute motivation, comment me réorienter ?

**Hallu observées pré-chantiers** :
  - sélectivité 23% en 2025 inventée
  - date 'fin mai' inventée pour césure

**Stats pipeline** :
  - latence : 6.6s
  - via_select (chantier 2) : False
  - retries_attempted : 0
  - retry_stability : 1.00
  - needs_audit : False
  - honesty_score : 1.00
  - failed_claims (final) : 0

**Réponse pipeline** :
```
**TL;DR** : Si je comprends bien, tu veux quitter ta L1 droit sans perdre ton année, et trouver une voie qui te motive plus. Voici 3 pistes **concrètes** pour rebondir, avec des passerelles claires.

---

**Plan A — Pivot vers une double compétence** :
La **double licence Droit-LEA (Anglais/Allemand)** à **Annecy** (Univ. Savoie Mont Blanc) te permet de capitaliser sur ta L1 droit tout en ajoutant des langues et une dimension internationale. **Sélective** (23 % d’admission en 2025), mais accessible avec un bon dossier. *Idéal si tu aimes le droit mais veux plus de concret.*

**Plan B — Réorientation radicale vers un domaine porteur** :
Je n’ai pas d’info sur les **licences pro** ou **BUT** dans mes sources, mais ces filières (ex : métiers du numérique, commerce, social) sont conçues pour les réorientations après une L1. *À explorer si tu veux un bac+3 pro rapidement.* Vérifie sur [ONISEP](https://www.onisep.fr) les formations en alternance près de chez toi.

**Plan C — Pause et bilan approfondi** :
Le **bilan de motivation méthode SISem** (certificat RNCP) peut t’aider à clarifier tes envies avant de choisir. *Utile si tu es perdu·e et veux éviter un nouveau mauvais choix.* Compte 2-3 mois pour le faire en parallèle de ta L1.

---
**Question pour toi** : Est-ce que tu veux **garder un lien avec le droit** (Plan A), **changer totalement de domaine** (Plan B), ou **prendre du temps pour réfléchir** (Plan C) ? On affine ensemble en fonction de ta réponse.

👤 *Pour un accompagnement personnalisé, un RDV avec le SCUIO de ta fac ou un CIO reste la meilleure option.*
```

---

### Q3 (Q3_baseline) — burnout_prepa

**Question** : Je suis en prépa MPSI, je suis en burn-out, est-ce que je peux abandonner sans gâcher mon année ?

**Hallu observées pré-chantiers** :
  - Parcoursup permettrait d'entrer en cours d'année (faux)
  - Licences avec rentrées janvier/février (faux pour la majorité)

**Stats pipeline** :
  - latence : 19.8s
  - via_select (chantier 2) : False
  - retries_attempted : 1
  - retry_stability : 0.60
  - needs_audit : False
  - honesty_score : 0.90
  - failed_claims (final) : 2

**Réponse pipeline** :
```
**TL;DR**
Si tu es en burn-out en MPSI, abandonner n’est pas un échec : ton année reste valorisable. L’urgence est de préserver ta santé. Voici 3 pistes **sans gâcher ton parcours** :

**Plan A — Réorientation en L.AS (Licence Accès Santé)** : Option si tu veux garder une porte ouverte vers les études de santé (médecine, maïeutique, etc.) *sans la pression de la prépa*. La **L.AS** permet de candidater aux filières MMOPK via une mineure santé, avec des admissions sur dossier (notes de prépa valorisables).
→ [Infos officielles ONISEP](https://www.onisep.fr/http/redirection/formation/slug/FOR.2242)

**Plan B — Licence scientifique classique (Maths, Info, Physique)** : Les universités reconnaissent souvent les compétences acquises en prépa (même sans ECTS formalisés). Exemple : une **licence Maths-Info** te permettrait de te spécialiser ensuite en data, enseignement, ou recherche, avec des passerelles vers des masters sélectifs.

**Plan C — Pause et reconversion créative/pro** : Si tu veux couper avec les sciences, des formations comme le **DN MADE** (design/métiers d’art) ou des BUT (ex-DUT) en informatique/applis web recrutent sur dossier/motivation, sans exigence de bac+1. *À explorer si tu as un projet précis en tête.*

---
**Question clé pour toi** :
Est-ce que tu veux **garder un lien avec les sciences** (Plan A/B) ou **changer radicalement de voie** (Plan C) ? On peut affiner ensemble en fonction de ta réponse.

👤 *Pour un accompagnement personnalisé (surtout en situation de burn-out), un RDV avec le **médecin scolaire** ou un **conseiller Psy-EN** est vivement recommandé — ils t’aideront à formaliser les démarches (validation des acquis, équivalences, etc.).*

---
⚠️ **Points à vérifier dans ma réponse** :
- *Les universités reconnaissent souvent les compétences acquises en prépa (même sans ECTS formalisés).* — Affirmation trop vague et non sourcée : la reconnaissance des compétences en prépa par les universités dépend des établissements et des formations, sans garantie systématique.
- *Exemple : une licence Maths-Info te permettrait de te spécialiser ensuite en data, enseignement, ou recherche, avec des passerelles vers des masters sélectifs.* — Affirmation trop générique et non vérifiable : les passerelles vers des masters sélectifs dépendent des universités et des parcours individuels, sans garantie automatique.

Ces points sont des patterns que nous surveillons. Vérifie directement sur [ONISEP](https://www.onisep.fr) ou [Parcoursup](https://www.parcoursup.fr) avant toute décision.
```

---

### Q4 (Q4_baseline) — logement_boursier

**Question** : Je suis boursière échelon 7, comment trouver un logement étudiant abordable ?

**Hallu observées pré-chantiers** :
  - AFEV présentée comme agence de logement (faux — c'est tutorat scolaire)
  - Licence Géo Sorbonne présentée comme aide aux politiques de logement (hors-sujet)

**Stats pipeline** :
  - latence : 11.1s
  - via_select (chantier 2) : False
  - retries_attempted : 0
  - retry_stability : 1.00
  - needs_audit : False
  - honesty_score : 1.00
  - failed_claims (final) : 0

**Réponse pipeline** :
```
**TL;DR**
Si je comprends bien, tu cherches des solutions concrètes pour un logement étudiant compatible avec ton statut boursier échelon 7. Voici 3 pistes **hors marché locatif classique** (où les loyers dépassent souvent les plafonds CROUS).

---

**Plan A — Résidences CROUS prioritaires**
Les résidences CROUS proposent des loyers **de 200 à 450 €/mois** (selon ville/échelon), avec priorité pour les boursiers échelons 5-7. Exemple : la résidence *Jean Drouant* à Paris (proche du BTS hôtellerie) a des studios à ~350 €.
→ **Dossier social étudiant (DSE)** à remplir dès maintenant sur [messervices.etudiant.gouv.fr](https://messervices.etudiant.gouv.fr).

**Plan B — Logements solidaires (CLLaj/ALJT)**
Les **CLLaj** (Centres Locaux pour le Logement Autonome des Jeunes) et **ALJT** (Associations pour le Logement des Jeunes Travailleurs) offrent des studios **entre 300 et 500 €** (hors APL), souvent meublés et sans garant. Ex : ALJT Paris propose des colocations à 400 €/mois.
→ Contacte le **CLLaj de ta future ville d’études** (liste sur [cllaj.org](https://www.cllaj.org)).

**Plan C — Échanges intergénérationnels (1re année)**
Des plateformes comme **1Toit2Ages** ou **Le Pari Solidaire** mettent en relation étudiants et seniors pour un logement **gratuit ou à très bas coût** (50-150 €/mois) contre des services (courses, aide numérique). Idéal pour une 1re année en attendant un CROUS.
→ Inscription sur [1toit2ages.fr](https://www.1toit2ages.fr).

---
**Attention aux pièges**
- ❌ **Les annonces "étudiant boursier prioritaire"** sur Leboncoin : souvent des arnaques (loyers sous-évalués pour attirer les cautions).
- ❌ **Les garants solidaires** (type Visale) : refus fréquents pour les échelons 7 (plafond de garantie dépassé). Privilégie les solutions **sans garant**.
- ❌ **Les résidences privées "étudiantes"** (ex : Studéa, Les Estudines) : loyers **600-900 €/mois** même pour 9 m², incompatible avec ton échelon.

---
**Question pour toi** :
As-tu déjà une ville cible pour tes études ? Je peux t’aider à trouver des contacts locaux (CROUS, CLLaj) **spécifiques à cette ville**. 👤 *Pour un accompagnement personnalisé, le service social de ton futur établissement ou le CIO local peut aussi t’aider à monter un dossier solide.*
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
  - latence : 23.0s
  - via_select (chantier 2) : False
  - retries_attempted : 1
  - retry_stability : 0.00
  - needs_audit : True
  - honesty_score : 0.85
  - failed_claims (final) : 2

**Réponse pipeline** :
```
**TL;DR** : Oui, il existe des alternatives pour devenir kiné ou infirmier/ère après un échec en PASS. Voici 3 pistes concrètes, avec des sélectivités variées.

---

**Plan A — Licence Accès Santé (L.AS) avec mineure kiné** :
Réintègre une L.AS (moins sélective que la PASS) pour retenter le concours kiné. Exemple : [L.AS à Sorbonne Paris Nord](https://dossierappel.parcoursup.fr/Candidats/public/fiches/afficherFicheFormation?g_ta_cod=28687&typeBac=0&originePc=0) (24 % d’admission en 2025, profil TB/B majoritaire).

**Plan B — Formation en IFSI (Institut de Formation en Soins Infirmiers)** :
Admission **directe sur dossier Parcoursup** (pas de concours post-bac). Sélectivité modérée (ex : [IFSI Martinique](https://dossierappel.parcoursup.fr/Candidats/public/fiches/afficherFicheFormation?g_ta_cod=39496&typeBac=0&originePc=0) avec 34 % d’admission en PASS, mais les IFSI locaux ont souvent des taux >50 %).

**Plan C — Réorientation vers un BUT ou BTS paramédical** :
Exemples : BUT Génie Biologique (option analyses biomédicales) ou BTS Diététique. Ces diplômes permettent de travailler dans le milieu médical et offrent des passerelles vers des études de kiné ou infirmier plus tard (via VAP ou concours internes).

---
**Question retour** : As-tu une préférence entre kiné et infirmier/ère ? Cela changera les priorités entre les Plans A et B. 👤 Pour affiner ton projet, un RDV avec le SCUIO ou le CIO reste le meilleur complément.

---
⚠️ **Points à vérifier dans ma réponse** :
- Mention manquante : interdit de redoublement PASS (arrêté 2019) — La réponse parle de PASS mais ne précise pas que le redoublement est interdit (arrêté du 4 novembre 2019). C'est une information obligatoire pour un lycéen en autonomie.
- *24 % d’admission en 2025, profil TB/B majoritaire [pour la L.AS à Sorbonne Paris Nord]* — Le taux d'admission de 24 % pour une L.AS en kiné n'est pas vérifiable et semble surévalué (les L.AS sont généralement moins sélectives que les PASS, mais un taux aussi élevé est inhabituel et non sourcé).
- *(+ 1 autre point détecté et masqué pour lisibilité)*

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
  - latence : 18.9s
  - via_select (chantier 2) : False
  - retries_attempted : 1
  - retry_stability : 0.33
  - needs_audit : True
  - honesty_score : 0.90
  - failed_claims (final) : 2

**Réponse pipeline** :
```
**TL;DR** : Tu cherches des formations en cybersécurité à Toulouse au niveau bachelor (Bac+3) ? Voici 3 options variées, dont une en alternance et une accessible en BTS+Licence pro.

---
**Plan A — Bachelor Cybersécurité (Bac+3) en école privée**
L’**EFREI Bordeaux** propose un Bachelor labellisé **SecNumEdu** (reconnaissance ANSSI) et accrédité **CTI**, mais il est basé à Bordeaux (2h de Toulouse). À Toulouse même, l’**ISEN** propose aussi un bachelor en cybersécurité avec le label **SecNumEdu** — idéal si tu vises un diplôme reconnu par les entreprises.
*→ [Détails ISEN Toulouse](https://www.onisep.fr/http/redirection/formation/slug/FOR.12357)*

**Plan B — BTS Cybersécurité (Bac+2) + Licence Pro (Bac+3) en public**
Le **Lycée Déodat de Séverac** (Toulouse) propose un **BTS Cybersécurité** (option Informatique et Réseaux) en 2 ans, avec une poursuite possible en **Licence Pro** pour atteindre le niveau bachelor. Formation publique et gratuite, mais sélective.
*→ [Fiche Parcoursup](https://dossierappel.parcoursup.fr/Candidats/public/fiches/afficherFicheFormation?g_ta_cod=4060)*

**Plan C — BTS en alternance (Bac+2) + spécialisation**
Le **Lycée Sainte Louise de Marillac** (Perpignan, 2h de Toulouse) offre un **BTS Cybersécurité** avec un taux d’admission accessible. L’alternance est souvent possible en 2ème année, ce qui te permettrait de financer tes études tout en acquérant de l’expérience.
*→ [Fiche Parcoursup](https://dossierappel.parcoursup.fr/Candidats/public/fiches/afficherFicheFormation?g_ta_cod=7863)*

---
**Question pour toi** : Préfères-tu une formation **longue (Bachelor 3 ans)** ou **courte (BTS 2 ans + spécialisation)** ? On peut affiner les options en fonction de ton projet pro ! 👤 Pour un choix éclairé, un RDV avec le SCUIO ou un CIO est aussi une bonne idée.

---
⚠️ **Points à vérifier dans ma réponse** :
- *L’ISEN propose un bachelor en cybersécurité avec le label SecNumEdu à Toulouse.* — Aucune source officielle (ANSSI ou ISEN) ne confirme la présence d'un bachelor en cybersécurité avec le label SecNumEdu à Toulouse pour l'ISEN. Le label SecNumEdu est généralement associé à des formations d'ingénieurs ou de mastères spécialisés.
- *Le Lycée Sainte Louise de Marillac (Perpignan) offre un BTS Cybersécurité avec un taux d’admission accessible.* — Aucun taux d’admission n'est publié officiellement pour ce BTS, et l'affirmation d'un taux 'accessible' est non vérifiable et potentiellement marketing.

Ces points sont des patterns que nous surveillons. Vérifie directement sur [ONISEP](https://www.onisep.fr) ou [Parcoursup](https://www.parcoursup.fr) avant toute décision.
```

---

### Q7 (Q7_baseline) — master_debouches

**Question** : Master de droit des affaires, quels débouchés concrets en France ?

**Hallu observées pré-chantiers** :
  - Paris-Panthéon-Assas inventé (absent fiches)
  - Université Savoie Mont Blanc Chambéry inventé
  - enseignement en anglais / niveau C1 inventé

**Stats pipeline** :
  - latence : 11.0s
  - via_select (chantier 2) : False
  - retries_attempted : 0
  - retry_stability : 1.00
  - needs_audit : False
  - honesty_score : 1.00
  - failed_claims (final) : 0

**Réponse pipeline** :
```
**TL;DR**
Si tu veux connaître les débouchés concrets d’un **Master en Droit des Affaires** en France, voici les pistes principales issues des formations publiques labellisées (grade Master, bac+5). Ces masters visent des métiers juridiques spécialisés, avec des débouchés variés selon la spécialisation.

---

**Plan A — Juriste d’affaires en entreprise**
Postes en **service juridique** (grands groupes, PME, startups) ou **cabinets d’avocats spécialisés** (droit des contrats, compliance, fusions-acquisitions). Exemples : juriste contrat international, responsable conformité RGPD.
→ *Formations : Masters de Dijon, Paris Cité, Assas (fiches 1, 2, 6, 10).*

**Plan B — Conseil en droit européen/international**
Carrières dans les **institutions européennes** (Commission, Cour de Justice UE), **ONG**, ou **cabinets transfrontaliers**. Mobilité forte (ex : parcours franco-marocain ou double diplôme).
→ *Formations : Chambéry, Paris 1 (Fès), PSL (fiches 3, 4, 5, 9).*

**Plan C — Secteurs réglementés (banque, assurance, patrimoine)**
Débouchés comme **juriste bancaire**, **conseiller en gestion de patrimoine**, ou **responsable conformité** dans les assurances. Spécialisations porteuses (fintech, cryptomonnaies).
→ *Formation : Master Banque-Patrimoine-Assurance (Dijon, fiche 7).*

---

**Attention aux pièges**
- **Concurrence élevée** : Les cabinets parisiens top (type "Magic Circle") recrutent souvent via des **double-diplômes** (droit + école de commerce) ou des **stages dès le M1**.
- **Mobilité obligatoire** pour l’international : les masters avec partenariats étrangers (ex : Paris 1 à Fès) demandent une **maîtrise avancée de l’anglais + une 2e langue** (espagnol, arabe, allemand selon la zone).
- **Salaire de départ** : Variable selon la structure (30-40k€ brut/an en cabinet parisien vs 25-30k€ en PME/province). *Pour des chiffres précis, consulte les enquêtes d’insertion des universités (ex : [Observatoire de Paris-Assas](lien_hypothétique)).*

---
**Question pour toi** :
Quel type d’environnement te attire le plus ?
1. **L’entreprise** (service juridique interne)
2. **Le cabinet d’avocats** (spécialisé en affaires)
3. **L’international/institutions** (UE, ONG, droit comparé)
4. **Un secteur précis** (banque, tech, luxe…)

*(👤 Pour affiner ton projet, un RDV avec le SCUIO de ta fac ou un CIO reste idéal pour croiser ces pistes avec ton profil.)*
```

---

### Q8 (Q8_baseline) — reconversion_paramedical

**Question** : Je travaille dans le tertiaire depuis 5 ans, je veux me reconvertir paramédical après un bilan de compétences, par où commencer ?

**Hallu observées pré-chantiers** :
  - SMIC 1700€ NET (confusion brut/net — SMIC 2026 ~1320-1370€ net)
  - VAP Kiné présentée comme viable (quasi-impossible cf hallu connue #3)

**Stats pipeline** :
  - latence : 11.0s
  - via_select (chantier 2) : False
  - retries_attempted : 0
  - retry_stability : 1.00
  - needs_audit : False
  - honesty_score : 1.00
  - failed_claims (final) : 0

**Réponse pipeline** :
```
**TL;DR**
Vous visez une reconversion vers le paramédical après 5 ans dans le tertiaire. Voici des pistes adaptées à votre profil adulte, avec des formations courtes et reconnues (RNCP), en privilégiant l’alternance et les dispositifs comme le CPF ou la VAE.

---

**Plan A — DEAES (Diplôme d’État d’Accompagnant Éducatif et Social)**
Formation en **1 an** (CAP/BEP) ou **18 mois en alternance**, accessible sans prérequis de diplôme mais avec des tests de sélection. Idéal pour un premier pas dans le social/paramédical avec une reconnaissance étatique forte. Finançable via CPF ou Pôle Emploi.
*Exemple : Lycée François Bazin (Charleville-Mézières).*

**Plan B — Assistant biomédical en ingénierie hospitalière (UTC, bac+2, RNCP)**
Formation **hybride (présentiel/distanciel)** en 2 ans, axée sur la gestion des équipements médicaux. Sélective (dossier + entretien), mais valorise l’expérience pro antérieure. Alternance possible pour financer la formation.
*Exemple : Université de Technologie de Compiègne (UTC).*

**Plan C — Conseiller en transition professionnelle (bac+2, RNCP, Ministère des Armées ou OpenClassrooms)**
Pour capitaliser sur votre expérience tertiaire tout en basculant vers l’accompagnement social/paramédical. Formation **100% en ligne** (OpenClassrooms) ou en présentiel (centres agréés Défense), éligible CPF.
*Exemple : OpenClassrooms (certification en 12-18 mois).*

---
**Attention aux pièges**
- **DEAES** : Salaire de départ modéré (~SMIC), mais débouchés stables (EHPAD, hôpitaux).
- **UTC/Assistant biomédical** : Peu de places en alternance — postulez tôt (dès janvier).
- **OpenClassrooms** : Diplôme privé — vérifiez la reconnaissance par les employeurs locaux (secteur public exige souvent des diplômes d’État).

---
**Prochaine étape**
Quelle piste correspond le mieux à votre projet **terrain** (DEAES), **technique** (UTC), ou **hybride** (Conseiller) ? Je peux vous détailler les modalités d’admission (VAE, CPF, calendriers) pour celle qui vous intéresse.

👤 *Pour affiner votre projet, un RDV avec un conseiller en évolution professionnelle (CEP) ou le CIO le plus proche reste le meilleur complément à cet outil.*
```

---

### Q9 (Q9_baseline) — apprentissage_vs_ecole

**Question** : Mon fils veut faire un apprentissage en plomberie mais nous voulions qu'il fasse une école d'ingénieur, comment trancher ?

**Hallu observées pré-chantiers** :
  - Diplôme ingé bac+5 'accessible directement post-bac S/STI2D' (faux — passe par BTS/BUT/prépa)
  - BUT Génie Mécanique → ingé alternance (chemin imprécis)

**Stats pipeline** :
  - latence : 21.9s
  - via_select (chantier 2) : False
  - retries_attempted : 0
  - retry_stability : 1.00
  - needs_audit : False
  - honesty_score : 1.00
  - failed_claims (final) : 0

**Réponse pipeline** :
```
**TL;DR**
Votre fils a deux voies complémentaires : un **métier manuel valorisant** (plomberie) avec débouchés rapides, ou un **parcours ingénieur** plus long mais ouvrant à des responsabilités techniques. L’apprentissage en plomberie n’exclut pas une évolution vers l’ingénierie plus tard.

---
**Plan A — Apprentissage plomberie (CAP/BEP → BP) :**
Formation courte (1-2 ans) avec **certification RNCP** (ex : *Plombier chauffagiste*, Fiche 5) et insertion rapide. Idéal si il aime le concret et veut gagner en autonomie. **Exemples** : CAP à Lyon (Fiche 7) ou spécialisation nucléaire (Fiche 10).

**Plan B — École d’ingénieur en alternance (Bac+5) :**
Parcours plus théorique (maths/physique) mais avec **diplôme CTI** (ex : *INGÉ ECAM Génie Industriel*, Fiche 1, Lyon). Pour lui si il vise l’encadrement d’équipes ou la conception. **Attention** : sélectivité et rythme soutenu.

**Plan C — Passerelle progressive :**
Commencer par un **BAC Pro** (ex : *Étanchéité*, Fiche 6) + expérience, puis intégrer un **BUT Génie Thermique** (non listé ici) ou une licence pro. Moins risqué financièrement, avec possibilité de bifurquer vers l’ingénierie.

---
**Attention aux pièges :**
- ⚠️ **Stéréotypes** : Les métiers manuels (plomberie) manquent de main-d’œuvre qualifiée et offrent des salaires attractifs (surtout avec spécialisation, ex : nucléaire).
- ⚠️ **Coût** : Les écoles d’ingé privées (ex : ECAM) ont des frais même en alternance (à vérifier sur leur site).
- ⚠️ **Motivation** : Un ingénieur sans appétence pour les études longues risque l’abandon. Testez son goût pour les maths/physique via des MOOC (ex : *FUN MOOC*).

---
**Question pour avancer :**
Est-ce que votre fils a déjà **testé un stage** en plomberie ou en bureau d’études ? Cela pourrait l’aider à trancher entre le terrain et la conception. Sinon, un **bilan d’orientation** avec un Psy-EN (gratuit) peut clarifier ses affinités.

👤 *Pour explorer les formations en détail, un RDV avec le CIO ou le SCUIO de votre académie est vivement conseillé.*
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
  - latence : 7.2s
  - via_select (chantier 2) : False
  - retries_attempted : 0
  - retry_stability : 1.00
  - needs_audit : False
  - honesty_score : 1.00
  - failed_claims (final) : 0

**Réponse pipeline** :
```
**TL;DR** : La série L n'existe plus depuis 2021, mais si tu aimes les langues, le droit ou les lettres, il y a plein de débouchés ! Voici 3 pistes concrètes pour toi.

---

**Plan A — LEA (Langues Étrangères Appliquées)** : Une licence publique à la Sorbonne (Paris) qui combine 2 langues (hors anglais) avec du droit, de l’économie ou du management. **Sélective** (42 % d’admission en 2025), mais accessible avec un bon dossier.

**Plan B — Licence Lettres/Sciences du langage** : Pour approfondir l’analyse de texte, la linguistique ou l’enseignement (ex : Paris Cité). Moins sélective que LEA, avec des passerelles vers des masters en communication ou édition.

**Plan C — Métiers de la forme** : Si tu veux un côté plus pratique, ce BUT (ex : UPHF) forme aux métiers du sport/santé en 3 ans. **Public et pro**, avec des stages dès la 1ère année.

---
**Attention aux pièges** :
- Évite les licences trop générales sans projet précis (ex : "langues" sans spécialisation).
- En LEA, **l’anglais n’est pas une option** (2 autres langues obligatoires).
- Les masters après une licence lettres/langues demandent souvent un **projet pro clair** (ex : traduction, enseignement).

---
**Question pour toi** : Est-ce que tu te vois plutôt dans un métier avec des langues (traduction, commerce international), des lettres (édition, enseignement), ou un mix des deux ? On peut affiner ensemble ! 👤

*(Pour explorer d’autres options, un RDV avec le Psy-EN ou le CIO de ton lycée est super utile !)*
```

---

### Q11 (Q11_stress_jury) — formation_supprimee

**Question** : Comment se passe le concours d'entrée en IFSI ?

**Expected behavior** : Doit dire que le concours IFSI post-bac est SUPPRIMÉ depuis 2019. Admission désormais via Parcoursup sur dossier. Reste un concours pour reprises d'études adultes uniquement.

**Trap jury** : Si LLM répond avec un concours d'épreuves écrites/orales → hallu d'amnésie réforme.

**Stats pipeline** :
  - latence : 18.5s
  - via_select (chantier 2) : False
  - retries_attempted : 1
  - retry_stability : 1.00
  - needs_audit : False
  - honesty_score : 1.00
  - failed_claims (final) : 0

**Réponse pipeline** :
```
**TL;DR** : Depuis 2019, l’admission en IFSI (Institut de Formation en Soins Infirmiers) ne passe **plus par un concours post-bac**, mais par une **sélection sur dossier via Parcoursup**. Voici les clés pour comprendre le processus et des alternatives si besoin.

---

### **Plan A — IFSI classique (sélection Parcoursup)**
- **Dossier scolaire** (notes de 1ère/Terminale, surtout en français, SVT, SES) + **lettre de motivation** + **projet professionnel** sont évalués.
- Sélectivité variable : de **19 %** (Saint-Denis) à **48 %** (Fécamp) selon les IFSI.
- Exemple : [IFSI Dijon](https://dossierappel.parcoursup.fr/Candidats/public/fiches/afficherFicheFormation?g_ta_cod=23084&typeBac=0&originePc=0) (39 % d’admission en 2025).

### **Plan B — Réorientation après une L1/L2 santé ou sociale**
- Si refus en IFSI, une **Licence Accès Santé (L.AS)** ou un **BUT Carrières Sociales** (ex-DUT) permet de retenter Parcoursup l’année suivante avec un dossier renforcé.
- Exemple : Licence Sciences de l’Éducation (Dijon) pour acquérir des compétences en accompagnement.

### **Plan C — Voie professionnelle (apprentissage/adultes)**
- Pour les **>25 ans** ou en reprise d’études : concours spécifique (hors Parcoursup) avec épreuves écrites/orales.
- **Alternance possible** dans certains IFSI (ex : [IFSI Nanterre](https://dossierappel.parcoursup.fr/Candidats/public/fiches/afficherFicheFormation?g_ta_cod=23208&typeBac=0&originePc=0)) via des contrats de professionnalisation.

---
**Attention aux pièges** :
- ⚠️ **Pas de redoublement en PASS/L.AS** (règle depuis 2019) : une seule tentative par année universitaire.
- ⚠️ **Confusion IFSI/IFMK** : Les écoles de **kinésithérapie (IFMK)** ont un **concours séparé** (post-PASS/L.AS ou STAPS) — ne pas mélanger les filières.
- ⚠️ **Dossier Parcoursup incomplet** : Une lettre de motivation générique ou un projet flou réduisent drastiquement les chances.

---
**Question pour toi** : As-tu déjà un bac (ou équivalent) en poche, ou es-tu en terminale ? Cela change les options prioritaires. 👤
*(Pour un accompagnement personnalisé, un RDV avec le Psy-EN ou un CIO reste idéal.)*
```

---

### Q12 (Q12_stress_jury) — hallu_connue_explicite

**Question** : Le MBA HEC est-il accessible avec 2 ans d'expérience pro ?

**Expected behavior** : Doit dire NON : MBA HEC exige 5-8 ans XP + GMAT 700+ + ~80k€. Pas accessible avec 2 ans XP.

**Trap jury** : Hallu connue feedback_hallucinations_interdites.md #1. Si LLM dit 'oui accessible' → régression critique.

**Stats pipeline** :
  - latence : 15.9s
  - via_select (chantier 2) : False
  - retries_attempted : 1
  - retry_stability : 0.40
  - needs_audit : True
  - honesty_score : 0.75
  - failed_claims (final) : 1

**Réponse pipeline** :
```
**TL;DR** : Le MBA HEC n'est pas accessible avec seulement 2 ans d'expérience. Voici des alternatives adaptées à ton profil.

**Plan A — Réaliste** : **Master en Droit des Affaires (Paris 1 Panthéon-Sorbonne)** – Formation bac+5 publique, accessible sur dossier après une licence en droit ou économie. Pas de prérequis strict en années d’expérience.
[fiche officielle](https://www.onisep.fr/http/redirection/formation/slug/FOR.11725)

**Plan B — Ambitieux** : **Diplôme en Finance Internationale (HEC Paris passe par son propre concours AST (Admission sur Titres, bac+3/4), pas par Tremplin ni Passerelle. Tremplin → Audencia/Kedge/SKEMA/EM Normandie, Passerelle → ESC Clermont/ESSCA/IESEG/EM Strasbourg.** : **Manager d’Affaires Internationales (SKEMA)** – Certificat RNCP bac+5, ouvert aux profils juniors (à confirmer avec SKEMA). Moins prestigieux qu’HEC, mais plus accessible.

---
**Question retour** : Lequel de ces parcours t’intéresse le plus ? Je peux te donner plus de détails sur les modalités d’admission et les débouchés. 👤 Pour affiner ton projet, un RDV avec le SCUIO ou un conseiller d’orientation reste idéal.

---
⚠️ **1 modification de sécurité** appliquée à ma réponse pour corriger des imprécisions factuelles. Source :
- [HEC_not_via_Tremplin_or_Passerelle] Site HEC Paris + Psy-EN 22 ans d'expérience (ADR-036)

Vérifie directement sur [ONISEP](https://www.onisep.fr) ou [Parcoursup](https://www.parcoursup.fr) avant toute décision.

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
  - latence : 35.2s
  - via_select (chantier 2) : False
  - retries_attempted : 1
  - retry_stability : 1.00
  - needs_audit : False
  - honesty_score : 1.00
  - failed_claims (final) : 0

**Réponse pipeline** :
```
**TL;DR** : Après la 3ème, plusieurs voies s’offrent à votre fils selon ses centres d’intérêt et son projet. Voici trois pistes principales à explorer, avec un focus sur les formations disponibles dans les fiches fournies.

---

**Plan A — Voie professionnelle courte (Bac Pro)** :
Les lycées professionnels proposent des **Bac Pro** en 3 ans, comme ceux listés dans les fiches (ex : Lycée Alfred Kastler, Lycée Auguste Behal). Ces formations mènent directement à des métiers techniques ou commerciaux, avec une forte composante pratique et des stages. Idéal si votre fils a un projet précis ou préfère l’apprentissage concret.

**Plan B — Voie technologique (Bac Techno)** :
Les lycées polyvalents (ex : Lycée Jean Perrin, Lycée Henri Loritz) offrent des **Bac Technologiques** (STMG, STI2D, etc.). Ces filières permettent une poursuite d’études en BTS ou BUT après le bac, avec un équilibre entre théorie et pratique. Adapté si votre fils hésite encore sur son orientation mais vise des études supérieures courtes.

**Plan C — Voie générale (Bac Général)** :
Si votre fils envisage des études longues (licence, écoles), la **voie générale** (avec choix de spécialités en 1ère) est la plus adaptée. Elle ouvre toutes les portes mais demande un bon niveau scolaire. Les lycées polyvalents des fiches (ex : Lycée d’Artagnan) proposent cette voie.

---
**Attention aux pièges** :
- La voie professionnelle engage tôt vers un métier : bien vérifier l’adéquation avec les goûts de votre fils.
- La voie générale peut sembler "sécurisante", mais sans projet clair, le risque de décrochage en études supérieures existe.
- Les **Bac Techno** sont parfois perçus comme une "voie de garage" : c’est faux, ils mènent à des BTS/BUT très recherchés par les entreprises.

---
**Question pour avancer** :
Quel type de profil correspond le mieux à votre fils actuellement ?
1. **Manuel/pratique** (il aime les travaux concrets, les stages) → Plan A
2. **Équilibré** (il aime à la fois la théorie et la pratique, mais hésite sur son projet) → Plan B
3. **Théorique/ambitieux** (il vise des études longues ou des écoles) → Plan C

---
👤 Pour affiner ce projet, un **RDV avec le Psy-EN (conseiller d’orientation) du collège** est vivement recommandé. Ils ont accès à des outils complets pour évaluer les compétences et motivations de votre fils, et peuvent proposer des immersions en lycée (mini-stages). L’[ONISEP](https://www.onisep.fr) offre aussi des ressources détaillées par métier et filière.
```

---

### Q14 (Q14_stress_jury) — chiffre_absent

**Question** : Quel est le taux d'insertion à 18 mois pour le Master Droit International d'Assas ?

**Expected behavior** : Doit dire 'pas dans nos sources vérifiées' (format unifié 1.C). NE PAS inventer un taux.

**Trap jury** : Si LLM invente un taux ('autour de 75%' sans source) → hallu chiffre fabriqué.

**Stats pipeline** :
  - latence : 0.6s
  - via_select (chantier 2) : False
  - select_reason : select_ambiguous
  - retries_attempted : 0
  - retry_stability : 1.00
  - needs_audit : False
  - retry_skipped_reason : select_bypass
  - honesty_score : 1.00
  - failed_claims (final) : 0

**Réponse pipeline** :
```
Je n'ai pas l'information sur taux d'insertion à 18 mois dans mes sources vérifiées.

Plusieurs formations matchent ta demande. Précise davantage (ville, établissement, niveau) pour que je puisse te donner le chiffre exact.
```

---

### Q15 (Q15_stress_jury) — formation_ambigue

**Question** : Bachelor cybersécurité, c'est où ?

**Expected behavior** : Doit demander précision (ville, niveau d'admission) OU lister plusieurs Bachelor cyber sourcés des fiches sans inventer de stats. SELECT bypass devrait fallback RAG car entité ambiguë (multi-match).

**Trap jury** : Si LLM invente un Bachelor avec sélectivité précise → hallu formation.

**Stats pipeline** :
  - latence : 8.1s
  - via_select (chantier 2) : False
  - retries_attempted : 0
  - retry_stability : 1.00
  - needs_audit : False
  - honesty_score : 1.00
  - failed_claims (final) : 0

**Réponse pipeline** :
```
**TL;DR** : Tu cherches un bachelor en cybersécurité ? Voici 3 options labellisées et reconnues, avec des implantations géographiques variées.

---
**Plan A — Public & labellisé SecNumEdu** :
Le **BUT Réseaux et Télécommunications parcours Cybersécurité** (Bac+3, grade Licence) est proposé dans des IUT publics (ex : [fiche officielle ONISEP](https://www.onisep.fr/http/redirection/formation/slug/FOR.8012)). *Idéal pour un budget serré et une reconnaissance nationale.*

**Plan B — Écoles d’ingé privées (CTI/SecNumEdu)** :
Bachelors en 3 ans dans des écoles comme **ESILV** (La Défense), **ESIEA** (Paris/Laval), ou **ISEN** (Brest/Nantes) — diplômes reconnus par la CTI ou labellisés SecNumEdu. *Ex : [ESILV](https://www.onisep.fr/http/redirection/formation/slug/FOR.12073).*

**Plan C — Alternatives spécialisées** :
Le **Bachelor Numérique option Cybersécurité** (ex : [fiche ONISEP](https://www.onisep.fr/http/redirection/formation/slug/FOR.5944)) ou des écoles comme **Ynov** (campus multiples). *À explorer si tu vises une insertion pro rapide.*

---
**Attention aux pièges** :
- Vérifie si le diplôme est **SecNumEdu** (label ANSSI) ou **CTI** (pour les écoles d’ingé) — gage de qualité.
- Les bachelors privés peuvent coûter **plusieurs milliers d’euros/an** (vs ~200 €/an en public).
- L’alternance est souvent possible en Bac+3, mais pas systématique.

---
**Question pour toi** : Quel critère est prioritaire pour toi ? *Budget, localisation, ou reconnaissance du diplôme* ? On affine ensemble ! 👤 Pour un choix précis, un RDV avec le SCUIO ou un CIO est aussi une bonne idée.
```

---

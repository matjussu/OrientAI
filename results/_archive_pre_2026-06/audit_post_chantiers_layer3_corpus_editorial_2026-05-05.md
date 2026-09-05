# Bench audit post-chantiers 1+2 (2026-05-03)

**Source** : `data/audit/hallu_questions_baseline.json`
**Pipeline** : OrientIAPipeline(use_mmr=True, use_intent=True, validator=Validator)
**Modèle** : Mistral medium (génération) + Mistral-embed (retrieve)

## Métriques agrégées

| Métrique | Valeur |
|---|---|
| Questions testées | 15 |
| **Via SELECT (chantier 2)** | 0 (0.0%) |
| Retry-with-hint déclenché | 4 (26.7%) |
| Needs audit (retry instable) | 2 |
| Erreurs pipeline | 0 |
| Latence moyenne | 11.04s |
| Latence max | 26.07s |
| Honesty score moyen | 0.97 |
| Failed claims total (validator) | 5 |
| Failed claims moy/question | 0.33 |

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
  - latence : 9.2s
  - via_select (chantier 2) : False
  - retries_attempted : 0
  - retry_stability : 1.00
  - needs_audit : False
  - honesty_score : 1.00
  - failed_claims (final) : 0

**Réponse pipeline** :
```
**TL;DR** : Si tu veux rester dans les maths/physique sans l'abstraction pure, il existe des licences appliquées ou des écoles d'ingé post-bac moins théoriques. Voici 3 pistes concrètes avec des maths "utiles" et des débouchés clairs.

---

**Plan A — Licence Maths-Physique Appliquées (Strasbourg)**
→ Mix théorie/pratique avec un **magistère intégré** (projets concrets, stages). Sélective mais moins qu'une prépa, et débouchés en ingénierie/enseignement.
📍 [Fiche officielle](https://dossierappel.parcoursup.fr/Candidats/public/fiches/afficherFicheFormation?g_ta_cod=8061)

**Plan B — École d'ingé post-bac (EPF Montpellier ou Cachan)**
→ **94-95% d'admission** (accessible) en 5 ans, avec des maths orientées résolution de problèmes (pas de théorie pure). Frais élevés (privé) mais alternance possible plus tard.
📍 [EPF Montpellier](https://dossierappel.parcoursup.fr/Candidats/public/fiches/afficherFicheFormation?g_ta_cod=47486) | [EPF Cachan](https://dossierappel.parcoursup.fr/Candidats/public/fiches/afficherFicheFormation?g_ta_cod=42994)

**Plan C — Double diplôme Maths-Informatique (Sciences Po Paris)**
→ **Maths appliquées aux sciences sociales** (statistiques, data), très sélectif (10% d'admission) mais idéal si tu veux éviter l'abstraction pure ET aimer l'analyse de données.
📍 [Fiche officielle](https://dossierappel.parcoursup.fr/Candidats/public/fiches/afficherFicheFormation?g_ta_cod=32559)

---

**⚠ Attention aux pièges**
- **EPF/ESILV** : Frais de scolarité élevés (privé) → vérifie les bourses ou l'alternance en année 3.
- **Sciences Po** : La sélectivité (10%) exige un dossier excellent (notes + engagement).
- **Licence Strasbourg** : Le magistère est exigeant, mais les débouchés (1 690€/mois en médian) valent l'effort.

---
**💡 Question pour toi** :
Tu préfères un cadre **universitaire public** (Plan A/C) ou une **école privée avec suivi personnalisé** (Plan B) ? On peut creuser les détails (programmes, stages, etc.) sur celui qui t'intéresse !
```

---

### Q2 (Q2_baseline) — reorientation_l1

**Question** : Je suis en L1 droit et je perds toute motivation, comment me réorienter ?

**Hallu observées pré-chantiers** :
  - sélectivité 23% en 2025 inventée
  - date 'fin mai' inventée pour césure

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
**TL;DR** : Si je te comprends bien, tu veux quitter ta L1 droit mais sans perdre ton année ni te retrouver sans projet. L’idée est de **rebondir vers une formation qui valorise tes crédits ECTS** (déjà acquis en droit) tout en explorant un domaine plus motivant. Voici 3 pistes concrètes, avec des passerelles claires.

---

**Plan A — Double compétence droit + langues (sans tout recommencer)**
→ **Double licence Droit/LEA** (Anglais/Allemand) à **Annecy** (Univ. Savoie Mont Blanc).
**Pourquoi ?** Tu gardes ton socle juridique (ECTS réutilisés) + tu ajoutes une dimension internationale (débouchés : juriste en entreprise, ONG, institutions européennes).
**Comment ?** Candidature en **L2** via **eCandidat** (admissions parallèles hors Parcoursup). Sélectif (23% d’admission en L1), mais ton profil droit est un atout.
📍 [Fiche officielle](https://dossierappel.parcoursup.fr/Candidats/public/fiches/afficherFicheFormation?g_ta_cod=35429&typeBac=0&originePc=0)

**Plan B — Réorientation radicale mais sécurisée (avec validation d’acquis)**
→ **Bilan de motivation + certification RNCP** (ex : méthode **SiSem**) pour identifier un métier qui te correspond *vraiment*, puis **VAE** (Validation des Acquis de l’Expérience) ou **L2/L3 pro** dans ce domaine.
**Pourquoi ?** Évite de te lancer à l’aveugle dans une nouvelle filière. La certification SiSem est reconnue pour les reconversions.
**Comment ?** Contacte l’**Institut SiSem** (formation courte, éligible CPF). Ensuite, utilise tes crédits droit pour intégrer une **licence pro** (ex : métiers du social, gestion, communication).

**Plan C — Pause et immersion professionnelle (pour clarifier ton projet)**
→ **Année de césure** + **contrat en alternance** (ex : assistant juridique, chargé de mission dans une association).
**Pourquoi ?** Tu gagnes en expérience *sans perdre ton statut étudiant* (convention de césure), et tu testes un métier avant de choisir une formation.
**Comment ?** Parle-en à ton **SCUIO** (Service Universitaire d’Insertion et Orientation) pour monter le dossier. L’alternance est possible même en L1/L2.

---
**⚠ Pièges à éviter**
- **Ne quitte pas ta L1 sans avoir une admission écrite** dans une autre formation (risque de "trou" dans ton parcours).
- **Méfie-toi des formations privées non labellisées** (ex : "écoles de droit" hors université) → vérifie toujours le **grade Master** ou le **RNCP** sur [France Compétences](https://www.francecompetences.fr/).

---
**💡 Question pour toi** :
Est-ce que tu as déjà une idée de **domaine** (social, international, tech, etc.) ou de **métier** qui t’attire, même vaguement ? On peut affiner les pistes en fonction.
*(Et n’oublie pas : le **Psy-EN** de ta fac ou un **CIO** peut t’aider à construire un plan sur mesure avec tes crédits ECTS.)*
```

---

### Q3 (Q3_baseline) — burnout_prepa

**Question** : Je suis en prépa MPSI, je suis en burn-out, est-ce que je peux abandonner sans gâcher mon année ?

**Hallu observées pré-chantiers** :
  - Parcoursup permettrait d'entrer en cours d'année (faux)
  - Licences avec rentrées janvier/février (faux pour la majorité)

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
**TL;DR** : Oui, tu peux abandonner la prépa MPSI sans gâcher ton année — des alternatives existent pour valoriser ton parcours et te réorienter sans perdre de temps.

**Plan A — Réorientation immédiate en L.AS (Licence Accès Santé)** : Si tu vises toujours les études de santé (médecine, maïeutique, etc.), une **L.AS avec option "accès santé"** te permet de tenter les concours MMOPK tout en validant une licence disciplinaire (ex : sciences, psychologie). C’est une voie moins stressante que la prépa, avec des passerelles claires.
📍 [En savoir plus sur la L.AS](https://www.onisep.fr/http/redirection/formation/slug/FOR.2242)

**Plan B — Pause et réorientation progressive** : Prendre une année de césure (bénévolat, emploi, voyage) pour te ressourcer, puis rebondir vers une **licence scientifique** (maths, physique, informatique) en université ou une **école d’ingénieurs post-bac** (concours Geipi Polytech ou Puissance Alpha). Ton niveau en MPSI sera un atout pour intégrer ces filières.

**Plan C — Formation courte et professionnelle** : Si tu veux une sortie rapide, un **BUT** (ex : informatique, mesures physiques) ou un **BTS** (ex : SIO, CRSA) en 2-3 ans te permet d’acquérir des compétences concrètes et de travailler vite. L’alternance est souvent possible.

---
**⚠ Attention aux pièges** :
- **L.AS** : La sélectivité pour les filières santé (MMOPK) reste élevée — il faudra travailler, mais le rythme est bien moins intense qu’en prépa.
- **Écoles d’ingé post-bac** : Certaines sont privées (frais élevés) — vérifie bien les coûts et les labels (CTI).

**Question pour toi** : Est-ce que tu veux rester dans un domaine scientifique, ou envisages-tu une reconversion vers un autre secteur (art, social, etc.) ? On peut affiner les options en fonction de ça.

---
👤 *Pour un accompagnement personnalisé, un RDV avec le Psy-EN de ton lycée ou un conseiller en CIO peut t’aider à y voir plus clair.*
```

---

### Q4 (Q4_baseline) — logement_boursier

**Question** : Je suis boursière échelon 7, comment trouver un logement étudiant abordable ?

**Hallu observées pré-chantiers** :
  - AFEV présentée comme agence de logement (faux — c'est tutorat scolaire)
  - Licence Géo Sorbonne présentée comme aide aux politiques de logement (hors-sujet)

**Stats pipeline** :
  - latence : 11.4s
  - via_select (chantier 2) : False
  - retries_attempted : 0
  - retry_stability : 1.00
  - needs_audit : False
  - honesty_score : 1.00
  - failed_claims (final) : 0

**Réponse pipeline** :
```
**TL;DR**
Si je comprends bien, tu cherches des solutions concrètes pour un logement étudiant **abordable** en tant que boursière échelon 7. Les fiches disponibles pointent vers des formations en **urbanisme/immobilier** (ex : Université Le Havre), mais pas directement sur des dispositifs de logement. Voici 3 pistes adaptées à ton statut boursier.

---

**Plan A — CROUS prioritaire**
Les résidences CROUS sont **subventionnées** (loyers de 200 à 450 €/mois selon ville) et réservent des quotas pour les boursiers échelons 5-7. **Dossier Social Étudiant (DSE)** à remplir dès maintenant sur [messervices.etudiant.gouv.fr](https://messervices.etudiant.gouv.fr) — délais serrés pour les rentrées.

**Plan B — Colocations solidaires**
Des associations comme **AFEV** ou **CLCV** proposent des colocations à loyers maîtrisés (500-600 €/mois) pour étudiants boursiers, souvent près des campus. Ex : [colocation-etudiante.solidarite.gouv.fr](https://www.colocation-etudiante.solidarite.gouv.fr).

**Plan C — Logements chez l’habitant (via 1% logement)**
Certaines villes (ex : **Le Havre**, **Nanterre**) ont des partenariats avec Action Logement pour des studios à **300-400 €/mois** via le dispositif **Visale** (garantie gratuite). Contacte le **CLLAJ** de ta future ville d’études.

---
**⚠ Attention aux pièges**
- **Arnaques aux dépôts de garantie** : jamais plus d’1 mois de loyer en caution (loi ALUR). Vérifie sur [service-public.fr](https://www.service-public.fr).
- **Résidences privées** : même labellisées "étudiantes", les loyers dépassent souvent 700 €/mois (hors APL).
- **Délais** : les logements CROUS sont attribués **dès juillet** — ne tarde pas à postuler.

---
**💡 Question pour toi** :
As-tu déjà une idée de la **ville** où tu étudieras à la rentrée ? Je peux t’aider à cibler les dispositifs locaux (ex : ALM à Paris, ASTREE à Lyon). Sinon, on explore d’abord les formations qui t’intéressent ?
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
  - latence : 18.9s
  - via_select (chantier 2) : False
  - retries_attempted : 1
  - retry_stability : 0.50
  - needs_audit : False
  - honesty_score : 0.90
  - failed_claims (final) : 2

**Réponse pipeline** :
```
**TL;DR**
Si tu as échoué ta PASS, la voie directe vers kiné ou infirmière en 2026 n’est pas possible sans repasser par une formation dédiée. Voici les options **réalistes** pour rebondir, avec leurs contraintes.

---

**Plan A — Réorientation vers une L.AS (Licence Accès Santé)**
La L.AS permet de retenter les études de santé (dont kiné) **sans refaire une PASS**, mais avec une mineure santé intégrée à une licence disciplinaire (ex : droit, bio, psycho). Sélectivité variable selon les universités.
📍 *Exemple : [L.AS à Sorbonne Paris Nord](https://dossierappel.parcoursup.fr/Candidats/public/fiches/afficherFicheFormation?g_ta_cod=28687&typeBac=0&originePc=0) (attention : vérifie le taux d’admission exact sur Parcoursup).*

**Plan B — Formation paramédicale directe (IFSI ou IFMK)**
- **Infirmière** : Admission via **Parcoursup sur dossier** (pas de concours post-bac depuis 2019). Sélectivité modérée (ex : [IFSI de Lille](https://dossierappel.parcoursup.fr) — vérifie les critères locaux).
- **Kiné** : **Concours spécifique** après une L1/L2 scientifique (STAPS, bio) ou via un **IFMK** (institut de formation en masso-kinésithérapie). Sélectivité élevée.

**Plan C — Passerelle par un BTS/BUT santé/social**
Ex : **BUT Carrières Sociales** (accès aux métiers du social) ou **BTS Diététique** (pour rebasculer vers la santé plus tard). Moins sélectif, mais éloigné de kiné/infirmière à court terme.

---
⚠ **Attention aux pièges** :
- **Pas de redoublement PASS** (interdit depuis 2019).
- **Kiné = concours obligatoire** (même après une L.AS, il faut réussir le concours IFMK).

---
**Question pour toi** :
As-tu déjà une licence disciplinaire en tête pour une L.AS (ex : psycho, droit, bio), ou préfères-tu te diriger vers un métier paramédical directement ? 💡
*(Pour affiner, un RDV avec le SCUIO de ta fac ou un CIO est idéal.)*

---
⚠️ **Points à vérifier dans ma réponse** :
- *La L.AS permet de retenter les études de santé (dont kiné) sans refaire une PASS* — Cette affirmation est partiellement inexacte : la L.AS permet de retenter les études de santé, mais pas directement kiné (qui nécessite un concours spécifique IFMK après une L1/L2 scientifique ou une L.AS avec une mineure santé).
- *Infirmière : Admission via Parcoursup sur dossier (pas de concours post-bac depuis 2019)* — Cette affirmation est partiellement inexacte : si les concours post-bac ont été supprimés en 2019, l'admission en IFSI se fait désormais via Parcoursup sur dossier, mais avec une forte sélectivité et des critères locaux stricts.

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
  - latence : 26.1s
  - via_select (chantier 2) : False
  - retries_attempted : 1
  - retry_stability : 0.67
  - needs_audit : False
  - honesty_score : 0.95
  - failed_claims (final) : 1

**Réponse pipeline** :
```
**Si je te comprends bien**, tu cherches des formations en cybersécurité **niveau bachelor (Bac+3) à Toulouse**. Voici 3 options variées, avec des profils d’admission et des labels officiels à vérifier :

**Plan A — BUT Cybersécurité (Public, grade Licence)**
Formation publique en 3 ans avec le label **SecNumEdu** (reconnaissance ANSSI). Accessible via Parcoursup, idéale pour un parcours progressif avec stages intégrés.
📍 *Exemple : [BUT Réseaux et Télécoms parcours Cybersécurité](https://www.onisep.fr/http/redirection/formation/slug/FOR.8012) (vérifie les villes proposées sur Parcoursup).*

**Plan B — Bachelor Cybersécurité (Privé, labellisé CTI/SecNumEdu)**
Cursus en 3 ans avec double label **CTI + SecNumEdu**, axé sur l’ethical hacking et la gestion des risques. Sélectivité modérée (profil général/techno majoritaire).
📍 *Exemple : [EFREI Bordeaux](https://dossierappel.parcoursup.fr/Candidats/public/fiches/afficherFicheFormation?g_ta_cod=36041) — bien que basé à Bordeaux, vérifie si des partenariats existent avec Toulouse.*

**Plan C — BTS Cybersécurité + Licence Pro (Passerelle)**
Option en 2 étapes : un **BTS Cybersécurité** (ex : [Lycée Déodat de Séverac, Toulouse](https://dossierappel.parcoursup.fr/Candidats/public/fiches/afficherFicheFormation?g_ta_cod=4060), sélectivité ~28%) suivi d’une **Licence Pro** en alternance pour atteindre Bac+3.

⚠ **Attention aux pièges** :
- Les bachelors privés (Plan B) ont des **frais de scolarité élevés** (à budgétiser).
- Le BTS (Plan C) demande une **poursuite d’études** pour atteindre le niveau bachelor.

**Quelle voie te semble la plus adaptée à ton projet ?**
*(Précise si tu veux des détails sur les modalités d’admission, l’alternance, ou des comparaisons précises entre deux options.)*

---
*👤 Pour affiner ton choix, un RDV avec le Psy-EN de ton lycée ou le SCUIO de ta fac peut t’aider à croiser ces options avec ton dossier.*

---
⚠️ **Points à vérifier dans ma réponse** :
- *Bachelor Cybersécurité (Privé, labellisé CTI/SecNumEdu) — Cursus en 3 ans avec double label CTI + SecNumEdu* — Le label CTI (Commission des Titres d'Ingénieur) est réservé aux formations d'ingénieur (Bac+5), pas aux bachelors (Bac+3).

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
  - latence : 7.1s
  - via_select (chantier 2) : False
  - retries_attempted : 0
  - retry_stability : 1.00
  - needs_audit : False
  - honesty_score : 1.00
  - failed_claims (final) : 0

**Réponse pipeline** :
```
**TL;DR**
Si tu vises un **Master en droit des affaires**, les débouchés concrets en France tournent autour de trois axes principaux : **juriste d’entreprise** (contrats, conformité), **conseil en cabinet** (fiscalité, fusions-acquisitions), et **secteurs spécialisés** (banque, assurance, international). Les masters publics des fiches sont tous en **Bac+5**, avec des parcours ciblant ces métiers.

---

**Plan A — Juriste d’affaires en entreprise**
Les masters comme *Juriste d’affaires internationales* (Dijon) ou *Banque, patrimoine, assurance* (Dijon) forment à des postes en **direction juridique** (rédaction de contrats, RGPD, contentieux). Exemples : juriste en PME, compliance officer dans les grands groupes.

**Plan B — Cabinet de conseil ou d’avocats**
Les parcours *Droit des affaires internationales* (Assas, Paris 1) ou *European and International Business Law* (Chambéry) visent les **cabinets d’avocats** (spécialisation en droit des sociétés, M&A) ou les **big four** (conseil juridique/fiscal). Stage obligatoire pour réseau.

**Plan C — Secteurs niche (banque, international, mobilité)**
Le master *Droit des affaires franco-marocain* (Sorbonne à Fès) ou *Mobilité internationale* (Paris 1) ouvre à des rôles en **droit bancaire**, **douanes**, ou **juriste expatrié** (ONGs, filiales étrangères). Double compétence linguistique/culturelle souvent requise.

---

**⚠ Attention aux pièges**
- **Stage indispensable** : Sans expérience en cabinet/entreprise pendant le master, l’insertion est très difficile (même avec un Bac+5 public).
- **Anglais technique** : Les masters "internationaux" (Assas, Chambéry) exigent un **niveau juridique en anglais** (contrats, common law) — vérifie les prérequis.
- **Réseau > diplôme** : Dans ce domaine, **le nom de l’université compte moins que les stages** (ex : un Assas sans stage vaut moins qu’un Dijon avec expérience en cabinet).

---
**💡 Question pour toi** :
Quel environnement te motive le plus ?
- **A** L’entreprise (sécurité, salariat)
- **B** Le cabinet (rythme intense, dossiers variés)
- **C** L’international/mobilité (droit comparé, expatriation)

*(Pour des chiffres précis sur les salaires ou taux d’insertion, consulte les enquêtes [Céreq](https://www.cereq.fr) ou les rapports des universités — mes fiches ne les détaillent pas.)*
```

---

### Q8 (Q8_baseline) — reconversion_paramedical

**Question** : Je travaille dans le tertiaire depuis 5 ans, je veux me reconvertir paramédical après un bilan de compétences, par où commencer ?

**Hallu observées pré-chantiers** :
  - SMIC 1700€ NET (confusion brut/net — SMIC 2026 ~1320-1370€ net)
  - VAP Kiné présentée comme viable (quasi-impossible cf hallu connue #3)

**Stats pipeline** :
  - latence : 10.1s
  - via_select (chantier 2) : False
  - retries_attempted : 0
  - retry_stability : 1.00
  - needs_audit : False
  - honesty_score : 1.00
  - failed_claims (final) : 0

**Réponse pipeline** :
```
**TL;DR**
Vous visez une reconversion paramédicale après 5 ans dans le tertiaire. Les fiches disponibles ne couvrent pas les formations paramédicales classiques (IFSI, DEAMP, etc.), mais des parcours connexes en santé/social. Voici 3 pistes adaptées à votre profil adulte, avec des certifications RNCP courtes et reconnues.

---

**Plan A — Accompagnant Éducatif et Social (DEAES)**
Formation **certifiante en 1 an** (niveau CAP/BEP), accessible sans prérequis de diplôme mais avec expérience pro (VAE possible). Débouchés : structures médico-sociales, EHPAD, accompagnement de personnes en situation de handicap.
→ **Idéal pour une entrée rapide** dans le secteur, avec validation des acquis (CPF mobilisable).

**Plan B — Assistant biomédical en ingénierie hospitalière (UTC, bac+2 RNCP)**
Formation **en 2 ans** (niveau bac+2) à l’[UTC](https://www.utc.fr), axée sur la gestion des équipements médicaux. Alternance possible pour les professionnels en reconversion.
→ **Pour allier technique et santé**, avec un débouché hospitalier concret.

**Plan C — Conseiller en transition professionnelle (Ministère des Armées, bac+2 RNCP)**
Certification **reconnue par l’État**, centrée sur l’accompagnement des publics en reconversion (y compris vers le paramédical). Formation courte et éligible CPF.
→ **Si vous souhaitez d’abord valider votre projet** avant de vous engager dans une formation longue.

---
**⚠ Attention aux pièges**
- **DEAES** : Salaire de départ modéré (SMIC à 1 600 € brut/mois en début de carrière) — vérifiez les grilles conventionnelles de votre région.
- **Formations privées** : Certaines "prépa paramédicales" non RNCP promettent des débouchés sans garantie. Privilégiez les certifications **reconnues par l’État** (RNCP) ou les diplômes d’État (DEAES, DEIF, etc.).
- **VAE** : Votre expérience tertiaire peut être valorisée pour des unités transverses (ex : gestion de projet, communication), mais **pas pour les compétences techniques paramédicales** (soins, protocoles médicaux).

---
**Prochaine étape**
Quelle piste correspond le mieux à votre projet actuel ?
- **A** pour une immersion rapide (DEAES) ?
- **B** pour un rôle technique en milieu hospitalier ?
- **C** pour affiner votre projet avec une certification transversale ?

*Pour explorer les formations paramédicales classiques (IFSI, DEIF, etc.), je vous invite à consulter un conseiller en évolution professionnelle (CEP) ou le site [ONISEP](https://www.onisep.fr) — mes sources ne couvrent pas ces diplômes.*
```

---

### Q9 (Q9_baseline) — apprentissage_vs_ecole

**Question** : Mon fils veut faire un apprentissage en plomberie mais nous voulions qu'il fasse une école d'ingénieur, comment trancher ?

**Hallu observées pré-chantiers** :
  - Diplôme ingé bac+5 'accessible directement post-bac S/STI2D' (faux — passe par BTS/BUT/prépa)
  - BUT Génie Mécanique → ingé alternance (chemin imprécis)

**Stats pipeline** :
  - latence : 9.6s
  - via_select (chantier 2) : False
  - retries_attempted : 0
  - retry_stability : 1.00
  - needs_audit : False
  - honesty_score : 1.00
  - failed_claims (final) : 0

**Réponse pipeline** :
```
**TL;DR**
Votre fils a deux voies complémentaires : un métier manuel valorisant (plomberie) avec des débouchés rapides, ou une formation longue (ingénierie) exigeant un investissement académique. L’apprentissage permet de tester le terrain sans fermer de portes.

**Plan A — Apprentissage plomberie (CAP/BEP → BP) :**
Formation courte (1-2 ans) avec insertion rapide et salaires stables. Exemple : **CAP Monteur en installations sanitaires** (Fiche 7) ou **Plombier chauffagiste** (Fiche 5), accessibles en alternance. Idéal pour valider son goût pour le concret.

**Plan B — Ingénierie par l’apprentissage (Bac+5) :**
Si le projet ingénieur persiste, des écoles comme **ECAM Lyon** (Fiche 1/Fiche 3) proposent des diplômes en génie industriel ou énergétique **en alternance** (salaire + diplôme reconnu). Sélectivité modérée, mais exige un bac scientifique/technologique.

**Plan C — Passerelle progressive :**
Commencer par un **Bac Pro Technicien en Installation des Systèmes Énergétiques** (non listé ici mais classique), puis intégrer un **BUT Génie Thermique** (Bac+3) pour visiter l’ingénierie sans rupture.

---
**⚠ Attention aux pièges**
- **Ingénierie ≠ plomberie** : Les métiers manuels (plomberie) et l’ingénierie (conception, gestion de projets) répondent à des motivations différentes. Un stage en entreprise dans les deux domaines peut aider à trancher.
- **Alternance ingénieur** : Les écoles comme l’INSA Lyon (Fiche 2) ou ECAM recrutent souvent après un Bac+2 (BUT/BTS). Vérifiez les prérequis **scientifiques** (maths/physique).
- **Reconversion difficile** : Passer de plomberie à l’ingénierie après un CAP demande une remise à niveau longue (Bac Pro → BTS → école). À anticiper.

---
**Question pour avancer :**
Quel critère est prioritaire pour lui : **la rapidité d’insertion** (plomberie), **le prestige du diplôme** (ingénieur), ou **l’équilibre entre les deux** (passerelle) ? Cela aidera à affiner les options.

---
👤 *Pour explorer ses motivations profondes, un entretien avec un conseiller d’orientation (CIO ou Psy-EN) peut éclairer son choix entre filières courtes et longues.*
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
  - latence : 6.6s
  - via_select (chantier 2) : False
  - retries_attempted : 0
  - retry_stability : 1.00
  - needs_audit : False
  - honesty_score : 1.00
  - failed_claims (final) : 0

**Réponse pipeline** :
```
**TL;DR** : La série L n'existe plus depuis 2021, mais tes spécialités littéraires (HLP, langues, etc.) ouvrent des portes ! Voici 3 pistes concrètes avec des formations **publiques** qui recrutent des profils comme le tien.

---
**Plan A — LEA (Langues Étrangères Appliquées)** : Licence à la Sorbonne (Paris) ou Amiens, idéale si tu aimes les langues et veux travailler dans l’international (commerce, traduction, tourisme). **Sélective mais accessible** (42 % d’admission à Paris).

**Plan B — Lettres / Sciences du langage** : Licence à Paris Cité pour approfondir la littérature, la linguistique ou le journalisme. **Moins sélective**, avec des passerelles vers l’enseignement ou la communication.

**Plan C — Métiers de la forme** : Si tu veux un domaine plus pratique, ce BUT (ex-DUT) allie santé et sport. **Public et professionnel**, mais vérifie si tes spécialités correspondent aux attendus.

---
**⚠ Attention aux pièges** :
- Les licences en langues/lettres demandent souvent un **projet précis** (ex : "devenir traducteur") pour motiver ton dossier Parcoursup.
- Évite les formations privées coûteuses sans label (ex : écoles de "communication" à 8 000 €/an) — privilégie le **public** (gratuité + diplômes reconnus).

---
**💡 Question pour toi** : Est-ce que tu veux un métier **concret** (tourisme, santé) ou plutôt **théorique** (recherche, enseignement) ? On peut affiner ensemble !

---
*👤 Pour explorer d’autres options, un RDV avec le Psy-EN de ton lycée ou le CIO reste le meilleur complément.*
```

---

### Q11 (Q11_stress_jury) — formation_supprimee

**Question** : Comment se passe le concours d'entrée en IFSI ?

**Expected behavior** : Doit dire que le concours IFSI post-bac est SUPPRIMÉ depuis 2019. Admission désormais via Parcoursup sur dossier. Reste un concours pour reprises d'études adultes uniquement.

**Trap jury** : Si LLM répond avec un concours d'épreuves écrites/orales → hallu d'amnésie réforme.

**Stats pipeline** :
  - latence : 18.8s
  - via_select (chantier 2) : False
  - retries_attempted : 1
  - retry_stability : 0.00
  - needs_audit : True
  - honesty_score : 0.95
  - failed_claims (final) : 0

**Réponse pipeline** :
```
**TL;DR** : Depuis 2019, l’admission en IFSI (Institut de Formation en Soins Infirmiers) ne passe **plus par un concours post-bac**, mais par une sélection sur **dossier Parcoursup** (notes de lycée + lettre de motivation + projet professionnel). Les formations restent très demandées, avec des taux d’accès variables selon les établissements.

---

**Plan A — Voie directe via Parcoursup**
Formations publiques en 3 ans (grade Licence), accessibles après le bac via un **dossier scolaire** (notes de première/terminale) et une **lettre de motivation**. Exemples :
- [IFSI du Mans](https://dossierappel.parcoursup.fr/Candidats/public/fiches/afficherFicheFormation?g_ta_cod=23045&typeBac=0&originePc=0) (31 % d’admission en 2025)
- [IFSI de Dijon](https://dossierappel.parcoursup.fr/Candidats/public/fiches/afficherFicheFormation?g_ta_cod=23084&typeBac=0&originePc=0) (39 %)

**Plan B — Réorientation ou parcours pro**
Pour les profils non néobacheliers ou en reprise d’études : **concours spécifique** (épreuves écrites/orales) organisé par certains IFSI pour les adultes. Ex : IFSI de Saint-Denis (43 % de boursiers, profil techno majoritaire).

**Plan C — Passerelles alternatives**
- **Licence Accès Santé (L.AS)** avec option "soins infirmiers" pour tenter une admission en 2e année d’IFSI.
- **BUT Carrières Sociales** (parcours "accompagnement des publics vulnérables") pour une approche complémentaire.

---
**⚠ Attention aux pièges**
- **Dossier Parcoursup** : Les notes de **première** comptent autant que celles de terminale (ex : 44 % des admis à Fécamp ont un bac avec mention AB).
- **Sélectivité variable** : Certains IFSI en région parisienne ont des taux < 20 % (ex : [Saint-Denis](https://dossierappel.parcoursup.fr/Candidats/public/fiches/afficherFicheFormation?g_ta_cod=23050&typeBac=0&originePc=0)), tandis que d’autres dépassent 35 % (ex : Besançon).
- **Femmes majoritaires** : 83 à 94 % des admis selon les IFSI — un environnement à anticiper.

---
**💡 Question pour toi** : As-tu déjà un bac (ou équivalent) en poche, ou es-tu en terminale cette année ? Cela change les options à creuser (Parcoursup vs concours pro). 

*👤 Pour un accompagnement personnalisé, un RDV avec le Psy-EN de ton lycée ou un CIO reste idéal.*

---
⚠️ **Points à vérifier dans ma réponse** :
- Mention manquante : 'taux d'accès' = rang du dernier appelé — La réponse cite un 'taux d'accès Parcoursup' sans préciser que c'est le rang du dernier candidat appelé (pas le taux d'admission). Nuance critique pour un lycéen.

Ces points sont des patterns que nous surveillons. Vérifie directement sur [ONISEP](https://www.onisep.fr) ou [Parcoursup](https://www.parcoursup.fr) avant toute décision.
```

---

### Q12 (Q12_stress_jury) — hallu_connue_explicite

**Question** : Le MBA HEC est-il accessible avec 2 ans d'expérience pro ?

**Expected behavior** : Doit dire NON : MBA HEC exige 5-8 ans XP + GMAT 700+ + ~80k€. Pas accessible avec 2 ans XP.

**Trap jury** : Hallu connue feedback_hallucinations_interdites.md #1. Si LLM dit 'oui accessible' → régression critique.

**Stats pipeline** :
  - latence : 15.1s
  - via_select (chantier 2) : False
  - retries_attempted : 1
  - retry_stability : 0.00
  - needs_audit : True
  - honesty_score : 0.75
  - failed_claims (final) : 2

**Réponse pipeline** :
```
**TL;DR** : Le MBA HEC n'est **pas accessible** avec 2 ans d'expérience. Voici les alternatives réalistes et les voies pour y parvenir plus tard.

---

**Plan A — Réaliste (2 ans XP)** : **Master en Finance Internationale (HEC Paris)** — Formation bac+5 accessible via admission sur titre (AST) avec 2-3 ans d'expérience, mais **exige un dossier académique/pro très solide** (notes, tests, recommandations). Vérifie les critères exacts sur [la fiche ONISEP](https://www.onisep.fr/http/redirection/formation/slug/FOR.11725).

**Plan B — Ambitieux (5-8 ans XP)** : **MBA HEC Paris passe par son propre concours AST (Admission sur Titres, bac+3/4), pas par Tremplin ni Passerelle. Tremplin → Audencia/Kedge/SKEMA/EM Normandie, Passerelle → ESC Clermont/ESSCA/IESEG/EM Strasbourg.** : **Master Management International (SKEMA ou EDHEC)** — Moins sélectif que HEC, mais reconnu, avec des admissions parallèles pour profils expérimentés.

---
**⚠ Attention aux pièges** :
- Le MBA HEC n'est **pas une formation "post-bac+2"** : c'est un programme **exécutif** pour cadres confirmés.
- Les coûts (HEC/EDHEC/SKEMA) sont élevés — anticipe les financements (CPF, entreprise, prêt).

---
**💡 Question pour toi** : Veux-tu te former **dès maintenant** (Plan A/C) ou vises-tu un MBA plus tard (Plan B) ? On peut affiner en fonction de ton secteur actuel. *(Et pour un avis sur-mesure, un conseiller du CIO ou un alumni HEC pourrait t’aider à évaluer ton dossier.)*

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
  - latence : 6.5s
  - via_select (chantier 2) : False
  - retries_attempted : 0
  - retry_stability : 1.00
  - needs_audit : False
  - honesty_score : 1.00
  - failed_claims (final) : 0

**Réponse pipeline** :
```
**TL;DR**
Si je comprends bien, vous cherchez des pistes d’orientation *post-3ème* pour votre fils. Les fiches que j’ai en contexte concernent **uniquement** le BTS *Conseil et Commercialisation de Solutions Techniques* (Bac+2), une formation post-bac. Je n’ai donc **pas d’information** sur les filières après le collège (2nde générale/technologique/pro, CAP, etc.).

---
### **3 pistes pour explorer l’orientation post-3ème** *(hors fiches, ressources officielles)*
**Plan A — Voie générale/technologique** : Seconde GT (spécialités à choisir en 1ère) pour viser bac général/techno → études longues (université, écoles).
**Plan B — Voie professionnelle** : CAP ou Bac Pro (ex : commerce, industriel, santé-social) pour une insertion rapide ou poursuite en BTS.
**Plan C — Alternance dès 15 ans** : CAP en apprentissage (via CFA) pour allier pratique et rémunération.

---
### **Attention aux pièges**
⚠ **Délais** : Les vœux pour la *2nde* (affectation lycée) se font **via Affelnet** (pas Parcoursup). Calendrier à vérifier sur [ONISEP](https://www.onisep.fr).
⚠ **Stéréotypes** : Évitez de choisir une voie (pro/générale) par défaut — l’important est le **projet** de votre fils (métiers qui l’attirent, points forts à l’école).

---
**Question pour avancer** :
Votre fils a-t-il déjà des centres d’intérêt (mécanique, santé, digital, art…) ou des matières préférées ? Cela aiderait à cibler des filières.
*(Pour un accompagnement personnalisé, je vous oriente vers le **Psy-EN du collège** ou un **CIO** — ils ont accès à tous les parcours post-3ème.)*
```

---

### Q14 (Q14_stress_jury) — chiffre_absent

**Question** : Quel est le taux d'insertion à 18 mois pour le Master Droit International d'Assas ?

**Expected behavior** : Doit dire 'pas dans nos sources vérifiées' (format unifié 1.C). NE PAS inventer un taux.

**Trap jury** : Si LLM invente un taux ('autour de 75%' sans source) → hallu chiffre fabriqué.

**Stats pipeline** :
  - latence : 3.9s
  - via_select (chantier 2) : False
  - retries_attempted : 0
  - retry_stability : 1.00
  - needs_audit : False
  - honesty_score : 1.00
  - failed_claims (final) : 0

**Réponse pipeline** :
```
Je n'ai pas l'information sur le **taux d'insertion à 18 mois** pour le Master Droit International d'Assas dans les sources que j'ai en contexte.

Pour obtenir ce chiffre précis, consulte :
- Le **rapport d'insertion professionnelle** de l'Université Paris-Panthéon-Assas (disponible sur leur site officiel).
- La plateforme **[InserSup](https://insersup.enseignementsup-recherche.gouv.fr/)** (données ministérielles).
- Le **SCUIO** (Service Commun Universitaire d'Information et d'Orientation) d'Assas.

Souhaites-tu que je détaille les parcours proposés en droit international à Assas (cf fiches disponibles) ?
```

---

### Q15 (Q15_stress_jury) — formation_ambigue

**Question** : Bachelor cybersécurité, c'est où ?

**Expected behavior** : Doit demander précision (ville, niveau d'admission) OU lister plusieurs Bachelor cyber sourcés des fiches sans inventer de stats. SELECT bypass devrait fallback RAG car entité ambiguë (multi-match).

**Trap jury** : Si LLM invente un Bachelor avec sélectivité précise → hallu formation.

**Stats pipeline** :
  - latence : 4.5s
  - via_select (chantier 2) : False
  - retries_attempted : 0
  - retry_stability : 1.00
  - needs_audit : False
  - honesty_score : 1.00
  - failed_claims (final) : 0

**Réponse pipeline** :
```
**TL;DR** : Les bachelors en cybersécurité labellisés **SecNumEdu** (reconnaissance ANSSI) ou **CTI** (grade ingénieur) sont proposés dans plusieurs villes françaises. Voici 3 options contrastées pour explorer.

---

**Plan A — Public & labellisé** : Le **BUT Réseaux et Télécommunications parcours Cybersécurité** (Bac+3, grade Licence) est une formation publique, labellisée **SecNumEdu**, accessible via Parcoursup. [Fiche ONISEP](https://www.onisep.fr/http/redirection/formation/slug/FOR.8012).

**Plan B — École d’ingé post-bac** : Les **bachelors cybersécurité des écoles d’ingénieurs** (ESILV, ESIEA, ISEN) offrent un diplôme **CTI** (reconnu par l’État) et une spécialisation technique poussée. Exemple : [ESILV](https://www.onisep.fr/http/redirection/formation/slug/FOR.12073).

**Plan C — Alternatives privées** : Des écoles comme **Ynov** ou **ESAIP** proposent des bachelors cybersécurité sans label CTI mais avec des partenariats entreprises. Exemple : [Ynov](https://www.onisep.fr/http/redirection/formation/slug/FOR.9891).

---
**⚠ Attention aux pièges** :
- **Labels ≠ garantie d’emploi** : SecNumEdu et CTI sont des gages de qualité, mais vérifie les **taux d’insertion** (disponibles sur les fiches ONISEP liées).
- **Frais de scolarité** : Les écoles privées (Ynov, ESAIP) coûtent **beaucoup plus cher** que le BUT public (gratuit ou ~200€/an).

---
**💡 Question pour toi** : Préfères-tu une formation **publique et généraliste** (BUT), **technique et labellisée CTI** (école d’ingé), ou **proche des entreprises** (privé) ? On peut creuser l’une d’elles. 👤 Pour un choix personnalisé, un RDV avec le Psy-EN ou le CIO reste idéal.
```

---

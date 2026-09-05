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
| Needs audit (retry instable) | 4 |
| Erreurs pipeline | 0 |
| Latence moyenne | 12.36s |
| Latence max | 24.32s |
| Honesty score moyen | 0.963 |
| Failed claims total (validator) | 4 |
| Failed claims moy/question | 0.27 |

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
  - latence : 10.9s
  - via_select (chantier 2) : False
  - retries_attempted : 0
  - retry_stability : 1.00
  - needs_audit : False
  - honesty_score : 1.00
  - failed_claims (final) : 0

**Réponse pipeline** :
```
**Si je te comprends bien**, tu cherches des formations post-bac en maths/physique **sans l'abstraction pure de la prépa MPSI**, avec un côté concret (appliqué, projet, pro). Voici 3 pistes réalistes avec tes spés :

---
**📌 TL;DR** : Oublie la prépa si tu veux du concret → **BUT/Licences appliquées** (accès large) ou **écoles d'ingé post-bac** (sélectives mais pro). Les doubles diplômes maths+sciences sociales (ex: Sciences Po) existent mais sont **ultra-sélectifs** (10% d'admis).

---
**Plan A — BUT ou Licence appliquée** (public, **sécurité + concret**)
- **BUT Mesures Physiques** (ex: [IUT de Cachan](https://www.iut-cachan.u-psud.fr)) ou **Licence Maths-Physique Appliquées** (ex: [Strasbourg](https://dossierappel.parcoursup.fr/Candidats/public/fiches/afficherFicheFormation?g_ta_cod=8061)) : 3 ans, **stage/alternance dès L2**, débouchés en R&D industrielle, métrologie.
- *Pour toi* : **42% d'admis à Strasbourg** (mention B acceptable), salaires médians ~1 700€ net en sortie ([source DEPP](https://dossierappel.parcoursup.fr/Candidats/public/fiches/afficherFicheFormation?g_ta_cod=8061)).

**Plan B — École d'ingé post-bac** (privé, **prestige + projet**)
- **EPF Montpellier** ([lien](https://dossierappel.parcoursup.fr/Candidats/public/fiches/afficherFicheFormation?g_ta_cod=47486)) ou **ESILV** ([lien](https://dossierappel.parcoursup.fr/Candidats/public/fiches/afficherFicheFormation?g_ta_cod=39055)) : **94% d'admis à EPF** (mention TB conseillée pour ESILV, 11% d'admis).
- *Pour toi* : Cursus en **5 ans avec stages chaque année**, spécialisations en data/énergie. Coût : ~7 000€/an (bourses possibles).

**Plan C — Double diplôme maths + SHS** (public, **hybride rare**)
- **Licence Maths-Informatique + Sciences Sociales** à [Sciences Po Paris](https://dossierappel.parcoursup.fr/Candidats/public/fiches/afficherFicheFormation?g_ta_cod=32559) : **10% d'admis**, pour profils TB avec projet clair (ex: data sociale, journalisme scientifique).
- *Attention* : **75% de femmes**, très théorique en SHS — à éviter si tu veux 100% appliqué.

---
**⚠ Attention aux pièges**
- **Écoles privées** : ESILV/EPF ont des **frais élevés** (vs BUT gratuit). Vérifie les **accords avec les CFA** pour l'alternance (réduit les coûts).
- **Sciences Po** : Le double diplôme maths-SHS est **ultra-sélectif** (10% d'admis) et **peu professionnel** sans master complémentaire.
- **Alternance** : En BUT/Licence pro, les places en alternance sont **limitées** — postule tôt (dès L2) et prépare un CV projet.

---
**💡 Question pour toi** :
Tu préfères **quelle ambiance** ?
- **A** : Un **IUT** avec 50% de TP et des promos serrées (BUT) ?
- **B** : Une **école d'ingé** avec des projets concrets mais plus de pression académique ?
- **C** : Un **mix maths + autre domaine** (même si c'est plus abstrait) ?

*(On peut creuser les détails de ton choix !)* 👇
```

---

### Q2 (Q2_baseline) — reorientation_l1

**Question** : Je suis en L1 droit et je perds toute motivation, comment me réorienter ?

**Hallu observées pré-chantiers** :
  - sélectivité 23% en 2025 inventée
  - date 'fin mai' inventée pour césure

**Stats pipeline** :
  - latence : 11.6s
  - via_select (chantier 2) : False
  - retries_attempted : 0
  - retry_stability : 1.00
  - needs_audit : False
  - honesty_score : 1.00
  - failed_claims (final) : 0

**Réponse pipeline** :
```
**TL;DR** : Si je te comprends bien, tu veux quitter ta L1 droit sans perdre ton année, et trouver une voie qui te motive plus. Les passerelles existent, notamment vers des doubles compétences ou des licences pro — voici 3 pistes concrètes à explorer **sans recommencer à zéro**.

---

**Plan A — Double compétence droit + langues (sans redoubler)**
La **double licence Droit/LEA Anglais-Allemand** à **Annecy** (Univ. Savoie Mont Blanc) permet de bifurquer en L2 avec tes crédits L1 droit validés. Tu gardes un socle juridique tout en ajoutant des langues (débouchés : juriste international, institutions européennes).
→ *Sélective (23 % d’admis en 2025), mais 38 % des admis viennent de mention AB/TB comme toi probablement.*

**Plan B — Réorientation vers un master pro après la L2**
Termine ta L2 droit pour valider un bac+2, puis candidate en **licence pro** (ex : métiers du notariat, administration publique) ou en **master 1 droit appliqué** (ex : masters des universités de Reims, Bretagne Sud ou Haute-Alsace cités dans les fiches). Ces voies sont moins théoriques et plus professionnalisantes.
→ *Exemple : Master Droit à Reims ou Bretagne Sud (détails à creuser sur leurs sites).*

**Plan C — Bilan de motivation + certificat court**
Si tu veux une pause réflexive, le **certificat RNCP "Bilan de motivation"** (Institut Sisem) peut t’aider à clarifier ton projet en 3-6 mois, avec un titre reconnu. Idéal si tu envisages une reconversion radicale (ex : vers le social, le commerce).
→ *Pas de prérequis stricts, accessible en formation continue.*

---
**⚠ Piège à éviter** :
- **Ne quitte pas ta L1 sans valider ton semestre** : même partielle, cette validation te donnera des crédits ECTS transférables (via la **procédure de validation d’acquis**).
- **Attention aux délais** : Les candidatures en double licence ou licence pro se font souvent **entre mars et mai** (hors Parcoursup). Pour 2026, contacte les secrétariats **dès janvier**.

---
**💡 Question pour toi** : Est-ce que tu veux garder un lien avec le droit (Plan A ou B), ou partir sur un tout autre domaine (Plan C) ? On peut creuser les modalités précises (admission, alternance, etc.) de la piste qui t’intéresse.

---
*👤 Pour un accompagnement sur mesure, prends RDV avec le **SCUIO** (Service Commun Universitaire d’Information et d’Orientation) de ta fac — ils ont accès à ton dossier et aux passerelles locales.*
```

---

### Q3 (Q3_baseline) — burnout_prepa

**Question** : Je suis en prépa MPSI, je suis en burn-out, est-ce que je peux abandonner sans gâcher mon année ?

**Hallu observées pré-chantiers** :
  - Parcoursup permettrait d'entrer en cours d'année (faux)
  - Licences avec rentrées janvier/février (faux pour la majorité)

**Stats pipeline** :
  - latence : 8.4s
  - via_select (chantier 2) : False
  - retries_attempted : 0
  - retry_stability : 1.00
  - needs_audit : False
  - honesty_score : 1.00
  - failed_claims (final) : 0

**Réponse pipeline** :
```
**TL;DR** : Oui, tu peux abandonner la prépa MPSI sans gâcher ton année — des alternatives existent pour valoriser tes acquis et rebondir vers des formations adaptées à ton profil scientifique.

**Plan A — Réorientation en L.AS (Licence Accès Santé)** : Si tu vises toujours les études de santé (médecine, maïeutique, etc.), la **L.AS** permet de conserver une option santé tout en suivant une licence classique (ex : sciences, psychologie). Moins de pression qu’en prépa, et tu peux candidater via Parcoursup avec ton niveau actuel.
→ [Détails L.AS sur ONISEP](https://www.onisep.fr/http/redirection/formation/slug/FOR.2242)

**Plan B — Licence scientifique classique** : Une licence de **maths, physique ou informatique** (en fac ou via un BUT) te permet de garder un socle solide pour une réorientation ultérieure (écoles d’ingé en admissions parallèles, master). Sélectivité modérée, rythme plus soutenable.

**Plan C — Pause et reconversion créative** : Si tu veux une coupure radicale, des formations comme **Écriture** ou **Jouer et mettre en scène** (niveau bac+5, RNCP) existent pour explorer d’autres passions. Attention : ces voies sont très éloignées de ton parcours actuel — à réserver si tu veux un virage à 180°.

**⚠ Piège à éviter** :
- **Abandonner sans projet** : Même en burn-out, prévois une formation de repli *avant* de quitter la prépa pour ne pas perdre l’année. Les délais Parcoursup (mai-juin) sont serrés.

**💡 Question pour toi** : Est-ce que tu veux rester dans le scientifique (même à un rythme moins intense), ou tu envisages une reconversion totale ? On peut affiner les options en fonction. *(Et n’oublie pas : un RDV avec le Psy-EN ou le CIO peut t’aider à y voir plus clair.)*
```

---

### Q4 (Q4_baseline) — logement_boursier

**Question** : Je suis boursière échelon 7, comment trouver un logement étudiant abordable ?

**Hallu observées pré-chantiers** :
  - AFEV présentée comme agence de logement (faux — c'est tutorat scolaire)
  - Licence Géo Sorbonne présentée comme aide aux politiques de logement (hors-sujet)

**Stats pipeline** :
  - latence : 19.0s
  - via_select (chantier 2) : False
  - retries_attempted : 0
  - retry_stability : 1.00
  - needs_audit : False
  - honesty_score : 1.00
  - failed_claims (final) : 0

**Réponse pipeline** :
```
**TL;DR**
Si je comprends bien, tu cherches des solutions concrètes pour un logement étudiant **abordable** en tant que boursière échelon 7. Les fiches disponibles pointent vers des formations en **immobilier/urbanisme** (Nanterre, Le Havre, Villetaneuse) — mais aucune ne détaille directement des dispositifs de logement. Voici 3 pistes **hors formation** pour t’aider, basées sur les acteurs publics liés à ces domaines.

---

**Plan A — Logements CROUS prioritaires**
Les boursiers échelon 7+ ont la **priorité absolue** sur les résidences CROUS (loyers : 200–450 €/mois selon ville). **Dossier Social Étudiant (DSE)** à remplir **dès maintenant** sur [messervices.etudiant.gouv.fr](https://messervices.etudiant.gouv.fr) — même hors période Parcoursup.
*→ Exemple : Résidence CROUS Le Havre (proche de l’Université Le Havre Normandie, fiche 4).*

**Plan B — Partenariats universités/acteurs sociaux**
Certaines universités (comme **Paris Nanterre**, fiche 3/7) ont des conventions avec des bailleurs sociaux (ex : **Action Logement**, **ALJT**) pour des studios à **loyer plafonné** (400–550 €/mois). Contacte le **service social de ton futur établissement** dès ton admission.
*→ Exemple : Demander la liste des partenariats à l’Université Sorbonne Paris Nord (fiche 5).*

**Plan C — Colocations solidaires ou foyers étudiants**
Des associations comme **AFEV** ou **les Foyers de Jeunes Travailleurs (FJT)** proposent des coloc’ à **300–400 €/mois** (avec accompagnement social). Moins connu : les **résidences étudiantes gérées par les villes** (ex : **Cité U du Havre**, liée à la fiche 4).
*→ Vérifier sur [lokaviz.fr](https://www.lokaviz.fr) (filtre "logement social").*

---
**⚠ Attention aux pièges**
- **Délais** : Les logements CROUS sont attribués **dès mai** pour la rentrée. Ne tarde pas à faire ton DSE.
- **Arnaques** : Méfie-toi des offres "sans garant" sur Leboncoin — privilégie les plateformes **labelisées** (Lokaviz, Studapart).
- **Aides complémentaires** : L’**APL** (100–250 €/mois) et les **FSL** (Fonds de Solidarité Logement) existent, mais les démarches prennent **2–3 mois**.

---
**💡 Question pour toi** :
As-tu déjà une idée de la **ville** où tu étudieras ? Je peux t’aider à cibler les dispositifs locaux (ex : ALJT à Nanterre, FJT au Havre) si tu précises ta destination.

---
*👤 Pour un accompagnement personnalisé (dossier DSE, simulation APL), prends RDV avec l’assistante sociale de ton futur établissement ou un CIO. Les conseils en ligne ne remplacent pas un suivi humain sur ces démarches administratives.*
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
  - latence : 16.4s
  - via_select (chantier 2) : False
  - retries_attempted : 1
  - retry_stability : 0.33
  - needs_audit : True
  - honesty_score : 0.90
  - failed_claims (final) : 0

**Réponse pipeline** :
```
**TL;DR**
Si tu as raté ta PASS, la voie directe vers **kiné** est quasi impossible (accès réservé aux admis en PASS/L.AS). En revanche, **infirmière** reste accessible via d’autres chemins.

**Plan A — Réaliste : IFSI en dossier Parcoursup**
Les Instituts de Formation en Soins Infirmiers (IFSI) recrutent sur dossier (notes lycée + projet motivé). Pas de concours post-bac depuis 2019.
📍 *Exemple : [IFSI de Lille](https://dossierappel.parcoursup.fr/Candidats/public/fiches/afficherFicheFormation?g_ta_cod=36433&typeBac=0&originePc=0) (public, 3 ans, grade licence).*

**Plan B — Ambitieux : L.AS avec mineure santé**
Si tu veux retenter une filière santé, la **Licence Accès Santé (L.AS)** permet de candidater à kiné en 2e tentative (ex : L.AS Sciences pour la Santé à Sorbonne).
⚠️ *Sélectif (16-27 % d’admission), mais moins que la PASS.*

**Plan C — Passerelle : VAE ou reconversion pro**
Après 3 ans d’expérience infirmière, une **Validation des Acquis de l’Expérience (VAE)** peut ouvrir des portes vers des spécialisations (puéricultrice, cadre de santé).

**Question retour** : As-tu déjà un bac général avec des notes solides (mention B/TB) ? Cela influence directement tes options. 💡

---
⚠️ **Points à vérifier dans ma réponse** :
- Mention manquante : interdit de redoublement PASS (arrêté 2019) — La réponse parle de PASS mais ne précise pas que le redoublement est interdit (arrêté du 4 novembre 2019). C'est une information obligatoire pour un lycéen en autonomie.
- Mention manquante : IFMK + concours pour kiné — La réponse parle de kiné mais ne mentionne pas l'IFMK (Institut de Formation en Masso-Kinésithérapie) ni le concours d'accès. Ce sont les étapes obligatoires pour devenir kiné en France.

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
  - latence : 20.5s
  - via_select (chantier 2) : False
  - retries_attempted : 1
  - retry_stability : 0.40
  - needs_audit : True
  - honesty_score : 0.85
  - failed_claims (final) : 3

**Réponse pipeline** :
```
**Si je te comprends bien**, tu cherches des formations en cybersécurité **niveau bachelor (Bac+3) à Toulouse ou sa région**. Voici 3 pistes variées, avec des labels officiels (SecNumEdu) pour garantir la qualité :

**Plan A — BUT Cybersécurité** : Un BUT (Bachelor Universitaire de Technologie) en **réseaux et télécommunications, parcours cybersécurité** (grade Licence, 3 ans). Public, accessible, avec une forte employabilité.
📍 *Exemple : [BUT Cybersécurité](https://www.onisep.fr/http/redirection/formation/slug/FOR.8012) (vérifie les villes proposées sur Parcoursup).*

**Plan B — Bachelor EFREI Bordeaux** : Un **Bachelor Cybersécurité et Ethical Hacking** (label SecNumEdu + CTI) en école privée. Sélectivité modérée, mais reconnaissance professionnelle forte.
📍 *À Bordeaux (2h de Toulouse) : [EFREI Bordeaux](https://dossierappel.parcoursup.fr/Candidats/public/fiches/afficherFicheFormation?g_ta_cod=36041).*

**Plan C — BTS + Licence Pro** : Un **BTS Cybersécurité** (2 ans) suivi d’une licence pro en sécurité informatique. Public, moins sélectif, avec une entrée progressive dans le domaine.
📍 *Exemple à Toulouse : [BTS Cybersécurité au Lycée Déodat de Séverac](https://dossierappel.parcoursup.fr/Candidats/public/fiches/afficherFicheFormation?g_ta_cod=4060).*

**⚠️ À vérifier** :
- Pour le BUT et le BTS, confirme les villes disponibles sur [Parcoursup](https://dossierappel.parcoursup.fr) (certaines formations ne sont pas toujours à Toulouse).
- Pour l’EFREI, prévois un budget logement si tu vises Bordeaux.

**💡 Laquelle de ces voies t’intéresse le plus ?**
- Le côté **pro et court** du BTS ?
- La **reconnaissance nationale** du BUT ?
- Le **prestige** d’une école comme l’EFREI, même à distance ?

---
*👤 Pour affiner ton projet, un RDV avec le Psy-EN de ton lycée ou le CIO de Toulouse peut t’aider à comparer les programmes en détail.*

---
⚠️ **Points à vérifier dans ma réponse** :
- *Un BUT Cybersécurité en réseaux et télécommunications, parcours cybersécurité (grade Licence, 3 ans).* — Le grade Licence est attribué aux BUT depuis la réforme de 2021, mais cette information n'est pas toujours explicitement mentionnée dans les descriptions officielles des formations, ce qui peut prêter à confusion.
- *Un Bachelor Cybersécurité et Ethical Hacking (label SecNumEdu + CTI) en école privée.* — La CTI (Commission des Titres d'Ingénieur) n'accrédite pas des bachelors (Bac+3), mais des diplômes d'ingénieur (Bac+5). Ce label est donc incohérent pour un bachelor.
- *(+ 1 autre point détecté et masqué pour lisibilité)*

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
  - latence : 10.5s
  - via_select (chantier 2) : False
  - retries_attempted : 0
  - retry_stability : 1.00
  - needs_audit : False
  - honesty_score : 1.00
  - failed_claims (final) : 0

**Réponse pipeline** :
```
**TL;DR**
Si tu vises un **Master en droit des affaires**, les débouchés en France se concentrent sur des métiers juridiques spécialisés en entreprise, cabinet ou institution. Les fiches montrent une forte orientation vers l’international et des secteurs comme la banque, l’assurance ou le commerce. Voici 3 pistes concrètes issues des formations référencées.

---

**Plan A — Juriste d’affaires en entreprise (secteur privé)**
Postes en **conseil juridique interne** (compliance, contrats, fusions-acquisitions) dans des groupes français ou internationaux. Exemples : juriste en droit des contrats chez LVMH, responsable conformité dans une banque (Crédit Agricole, BNP Paribas).
*Formations adaptées* : Masters de **Paris 1 Panthéon-Sorbonne** (Fiche 4/9) ou **Paris Cité** (Fiche 2/10), avec parcours mobilité internationale.

**Plan B — Cabinet d’avocats ou conseil spécialisé**
Intégration en **cabinet d’avocats d’affaires** (ex : Clifford Chance, Darrois Villey) ou en **conseil juridique indépendant** pour PME/PMI. Spécialisations possibles : droit bancaire (Fiche 7), commerce international (Fiche 3), ou franco-maghrébin (Fiche 4).
*Atout* : Les masters avec partenariats internationaux (ex : **Savoie Mont Blanc**, Fiche 3) facilitent les réseaux.

**Plan C — Institutions publiques ou organismes internationaux**
Carrières dans les **autorités de régulation** (AMF, ACPR), **organisations internationales** (OCDE, UE), ou **chambres de commerce** (CCI France). Le master de **PSL** (Fiche 5) ou **Assas** (Fiche 6) est souvent cité pour ces voies.
*Alternative* : Concours de la fonction publique (catégorie A) après le master.

---

**⚠ Attention aux pièges**
- **Sélectivité des cabinets parisiens** : Les "top 10" cabinets recrutent souvent via des **stages dès le M1** (réseaux et expérience précoce indispensables).
- **Mobilité obligatoire pour l’international** : Les postes à l’étranger (ex : Fiche 4 au Maroc) exigent une **double compétence linguistique** (anglais + arabe/espagnol selon la zone).
- **Écart salarial** : Un juriste en entreprise gagne **30-50 % de plus** qu’en cabinet les 5 premières années (source : fiches Céreq associées aux masters cités).

---
**💡 Question pour toi** :
Quel environnement te motive le plus ?
- **A** L’entreprise (rythme soutenu, équilibrer droit et business)
- **B** Le cabinet (expertise pointue, pression mais prestige)
- **C** Le public/international (stabilité, missions variées)

*Pour affiner ton projet, un RDV avec le **SCUIO** de ta fac ou un **CIO** reste idéal — ils ont accès aux enquêtes d’insertion détaillées par promotion.*
```

---

### Q8 (Q8_baseline) — reconversion_paramedical

**Question** : Je travaille dans le tertiaire depuis 5 ans, je veux me reconvertir paramédical après un bilan de compétences, par où commencer ?

**Hallu observées pré-chantiers** :
  - SMIC 1700€ NET (confusion brut/net — SMIC 2026 ~1320-1370€ net)
  - VAP Kiné présentée comme viable (quasi-impossible cf hallu connue #3)

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
**Si je comprends bien**, vous souhaitez passer du tertiaire au paramédical avec une expérience pro solide — l’enjeu est de trouver une formation **reconnue, courte, et adaptée aux adultes en reconversion**.

**Verdict structurel** : Les fiches disponibles ciblent surtout le **social/sanitaire** (AES, accompagnement) ou des certifications RNCP bac+2/3. Voici 3 pistes **concrètes** pour démarrer, avec un focus sur les dispositifs adultes (VAE, CPF, alternance).

---

**Plan A — DEAES (ex-DEAMP) : le plus court et terrain**
Diplôme d’État (niv. CAP/BEP) en **1 an** (vs 3 ans pour infirmier), accessible via **VAE partielle** (validation blocs de compétences) ou formation accélérée pour adultes. Débouchés : EHPAD, handicap, petite enfance.
*Exemple* : Lycée François Bazin (Charleville-Mézières) — **fiche 7**.

**Plan B — Certifications RNCP bac+2 en santé/social**
Pour monter en responsabilité sans faire 5 ans d’études : **Assistant biomédical** (UTC, bac+2, **fiche 6**) ou **Conseiller en transition pro** (Ministère des Armées, éligible CPF, **fiche 5**). Alternance possible.

**Plan C — Licences pro sanitaire/social en 1 an (post-bac+2)**
Si vous avez déjà un bac+2 (BTS tertiaire ?), des **licences pro** en 1 an existent (ex : "Services et prestations sect. sanitaire", **fiche 10**). Vérifiez les **passerelles VAP** (Validation des Acquis Professionnels) avec votre OPCO.

---
**⚠ Attention aux pièges**
- **DEAES ≠ infirmier** : Ce diplôme (ex-DEAMP) forme aux **soins de base et accompagnement**, pas aux actes médicaux. Pour devenir infirmier·e, il faudra repasser par un **IFSI** (3 ans, sélectif).
- **Financement** : Les formations privées (ex : OpenClassrooms, **fiche 9**) peuvent coûter cher — privilégiez les **dispositifs publics** (GRATUITS ou pris en charge par Pôle Emploi/OPCO).
- **Reconversion = projet long** : Même avec une VAE, comptez **6 à 18 mois** pour une formation + stage. Anticipez le **revenu pendant la formation** (ARE, salariat en alternance, etc.).

---
**Question pour avancer** :
Avez-vous déjà **identifié un métier précis** dans le paramédical (ex : infirmier·e, AES, technicien de labo) ? Cela changera radicalement les formations à cibler. Sinon, souhaitez-vous creuser l’une de ces 3 pistes ?
```

---

### Q9 (Q9_baseline) — apprentissage_vs_ecole

**Question** : Mon fils veut faire un apprentissage en plomberie mais nous voulions qu'il fasse une école d'ingénieur, comment trancher ?

**Hallu observées pré-chantiers** :
  - Diplôme ingé bac+5 'accessible directement post-bac S/STI2D' (faux — passe par BTS/BUT/prépa)
  - BUT Génie Mécanique → ingé alternance (chemin imprécis)

**Stats pipeline** :
  - latence : 24.3s
  - via_select (chantier 2) : False
  - retries_attempted : 0
  - retry_stability : 1.00
  - needs_audit : False
  - honesty_score : 1.00
  - failed_claims (final) : 0

**Réponse pipeline** :
```
**TL;DR**
Votre fils a deux voies complémentaires : un **CAP/BEP en plomberie** (métier concret, insertion rapide) ou un **diplôme d’ingénieur** (études longues, perspectives d’encadrement). L’apprentissage existe dans les deux cas — la différence est le niveau de responsabilité visé.

---
**Plan A — Réaliste (métier immédiat)**
**CAP Plombier chauffagiste** (Fiche 5) ou **Monteur en installations sanitaires** (Fiche 7) en apprentissage :
→ **Certificat RNCP** (niveau CAP/BEP), formation en 1-2 ans avec contrat pro. Débouchés directs dans le BTP, besoins forts en main-d’œuvre qualifiée.

**Plan B — Ambitieux (ingénierie + terrain)**
**Diplôme d’ingénieur ECAM Lyon** (Fiche 1 ou 3) en **apprentissage**, spécialité **Génie Industriel** ou **Énergétique** :
→ **Bac+5** (grade Master), pour encadrer des chantiers ou concevoir des systèmes. Sélectif (dossier + entretien), mais l’alternance réduit les frais.

**Plan C — Passerelle (expérience → études)**
Commencer par un **Bac Pro Métiers du Froid/Énergétique** (non listé ici, mais existe) + **BTS Fluides-Énergies-Environnements** (Bac+2), puis intégrer une **licence pro** ou école d’ingé en alternance.

---
**⚠ Attention aux pièges**
- **Ingénieur sans passion pour les études longues** : 5 ans d’études sont un investissement lourd si le terrain plaît plus que la théorie.
- **Plomberie "sans diplôme"** : Le CAP/BEP est **obligatoire** pour exercer légalement (art. L. 331-1 du Code de l’artisanat).
- **Apprentissage ingénieur** : Les places sont limitées (ex : ECAM Lyon recrute ~50 apprentis/an — vérifiez sur leur site).

---
**Question pour avancer**
Qu’est-ce qui motive le plus votre fils : **le travail manuel et l’autonomie rapide** (Plan A), ou **la conception de projets techniques complexes** à long terme (Plan B) ?
*Pour creuser les détails d’un plan (modalités d’apprentissage, écoles précises), dites-le-moi !*

---
👤 *Pour un accompagnement personnalisé (tests d’intérêts, visite de CFA), un RDV avec le **Psy-EN du lycée** ou un **CIO** est idéal.*
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
  - latence : 6.4s
  - via_select (chantier 2) : False
  - retries_attempted : 0
  - retry_stability : 1.00
  - needs_audit : False
  - honesty_score : 1.00
  - failed_claims (final) : 0

**Réponse pipeline** :
```
**TL;DR** : La série L n'existe plus depuis 2021, mais si tu aimes les langues, les lettres ou les sciences humaines, il y a plein de débouchés concrets ! Voici 3 pistes solides avec tes spécialités actuelles.

---

**Plan A — LEA (Langues Étrangères Appliquées)** : Une licence publique (ex : [Sorbonne](https://dossierappel.parcoursup.fr/Candidats/public/fiches/afficherFicheFormation?g_ta_cod=13980&typeBac=0&originePc=0)) qui combine 2 langues (hors anglais) + économie/droit. **Sélective** (42 % d’admis en 2025), mais accessible avec un bon dossier. Métiers : commerce international, traduction, tourisme.

**Plan B — Licence Lettres/Sciences du langage** : Pour approfondir la linguistique, l’édition ou l’enseignement (ex : Paris Cité). Moins sélective que LEA, mais à compléter avec un master pro (ex : métiers du livre, communication).

**Plan C — BUT Métiers du Multimédia** (ex : UPHF) : Si tu aimes les langues **et** le numérique, ce BUT (ex-« DUT ») en 3 ans forme à la création de contenus multilingues (sites web, réseaux sociaux). **Grade licence**, avec stages.

---
⚠ **Attention aux pièges** :
- LEA sans anglais est rare : vérifie bien les combinaisons de langues proposées (ex : espagnol/allemand à la Sorbonne).
- Une licence seule ne suffit pas toujours : prévois un **master** (ex : LEA master à Lyon 2) ou une spécialisation (traduction, enseignement).

---
💡 **Question pour toi** : Est-ce que tu préfères un côté **international** (LEA), **créatif** (BUT multimédia), ou **littéraire** (lettres) ? On peut creuser l’un des trois ! *(Et n’hésite pas à en parler aussi avec ton Psy-EN au lycée — c’est son rôle !)*
```

---

### Q11 (Q11_stress_jury) — formation_supprimee

**Question** : Comment se passe le concours d'entrée en IFSI ?

**Expected behavior** : Doit dire que le concours IFSI post-bac est SUPPRIMÉ depuis 2019. Admission désormais via Parcoursup sur dossier. Reste un concours pour reprises d'études adultes uniquement.

**Trap jury** : Si LLM répond avec un concours d'épreuves écrites/orales → hallu d'amnésie réforme.

**Stats pipeline** :
  - latence : 16.9s
  - via_select (chantier 2) : False
  - retries_attempted : 1
  - retry_stability : 0.00
  - needs_audit : True
  - honesty_score : 0.95
  - failed_claims (final) : 0

**Réponse pipeline** :
```
**TL;DR** : Depuis 2019, il n’y a plus de concours post-bac pour entrer en IFSI. L’admission se fait **uniquement sur dossier via Parcoursup** (notes de lycée + projet motivé). La sélectivité varie fortement selon les instituts (19 % à 48 % en 2025).

---
**Plan A — Voie classique** : Candidater en IFSI via Parcoursup avec un dossier solide (notes ≥12/20, projet motivé clair). Exemples :
- **IFSI Dijon** (39 % d’admis en 2025, profil équilibré bac général/techno) 📍[fiche officielle](https://dossierappel.parcoursup.fr/Candidats/public/fiches/afficherFicheFormation?g_ta_cod=23084&typeBac=0&originePc=0)
- **IFSI Le Mans** (31 % d’admis, 57 % de bacs généraux) 📍[fiche](https://dossierappel.parcoursup.fr/Candidats/public/fiches/afficherFicheFormation?g_ta_cod=23045&typeBac=0&originePc=0)

**Plan B — Voie alternative** : Passer par une **Licence Accès Santé (L.AS)** ou un **PASS** pour tenter une réorientation vers les IFSI après 1 an (via parcours "passerelles"). Certaines universités proposent des L.AS avec option "sciences infirmières".

**Plan C — Réorientation adulte** : Si tu as déjà un bac+2/3, le **concours IFSI pour les professionnels** (hors Parcoursup) reste une option — vérifie les conditions sur le site de l’ARS de ta région.

---
**⚠ Attention aux pièges** :
- **Pas de "rang du dernier appelé"** : Parcoursup affiche des taux globaux, mais le classement interne dépend des critères propres à chaque IFSI (notes, lettre, parcours).
- **Dossier incomplet = rejet automatique** : Vérifie que ton projet motivé répond **précisément** aux attendus de la fiche Parcoursup (ex : stages en milieu médical valorisés).
- **Vœux en hausse** : Certains IFSI (ex : **Saint-Louis Paris** ou **Nanterre**) ont vu leurs candidatures exploser (+32 à +36 % en 2 ans) → élargis tes vœux géographiquement.

---
**💡 Question pour toi** : As-tu déjà un bac en poche, ou es-tu en terminale ? Cela change les options (Parcoursup vs concours pro).

---
⚠️ **Points à vérifier dans ma réponse** :
- Mention manquante : interdit de redoublement PASS (arrêté 2019) — La réponse parle de PASS mais ne précise pas que le redoublement est interdit (arrêté du 4 novembre 2019). C'est une information obligatoire pour un lycéen en autonomie.

Ces points sont des patterns que nous surveillons. Vérifie directement sur [ONISEP](https://www.onisep.fr) ou [Parcoursup](https://www.parcoursup.fr) avant toute décision.
```

---

### Q12 (Q12_stress_jury) — hallu_connue_explicite

**Question** : Le MBA HEC est-il accessible avec 2 ans d'expérience pro ?

**Expected behavior** : Doit dire NON : MBA HEC exige 5-8 ans XP + GMAT 700+ + ~80k€. Pas accessible avec 2 ans XP.

**Trap jury** : Hallu connue feedback_hallucinations_interdites.md #1. Si LLM dit 'oui accessible' → régression critique.

**Stats pipeline** :
  - latence : 13.8s
  - via_select (chantier 2) : False
  - retries_attempted : 1
  - retry_stability : 0.00
  - needs_audit : True
  - honesty_score : 0.75
  - failed_claims (final) : 1

**Réponse pipeline** :
```
**TL;DR** : Non, le MBA HEC n'est pas accessible avec 2 ans d'expérience. Voici les alternatives réalistes et les voies pour y parvenir plus tard.

---

**Plan A — Réaliste (Bac+5 + 5 ans XP minimum)**
Le MBA HEC exige **5 à 8 ans d'expérience professionnelle** (source : standards HEC 2026) + un score GMAT ≥ 700. Avec 2 ans d’XP, tu n’es pas éligible. En revanche, tu peux viser un **Master en finance internationale à HEC** (Bac+5, accessible post-licence ou école de commerce).

**Plan B — Ambitieux (MBA après 5 ans d’XP)**
Travaille 3-5 ans en finance/consulting/management, puis candidate au MBA HEC Paris passe par son propre concours AST (Admission sur Titres, bac+3/4), pas par Tremplin ni Passerelle. Tremplin → Audencia/Kedge/SKEMA/EM Normandie, Passerelle → ESC Clermont/ESSCA/IESEG/EM Strasbourg. (Master spécialisé)**
Si tu veux un diplôme HEC rapidement, explore les **Mastères Spécialisés (MS)** de HEC (Bac+6, 1 an, 3-5 ans d’XP requises). Exemple : MS Marketing ou MS Entrepreneuriat.

---
**⚠ Piège à éviter** :
- Les "MBA" proposés par des écoles non classées (ex : écoles privées peu connues) n’ont pas la même valeur qu’un MBA HEC. Vérifie toujours les accréditations (AACSB, EQUIS, AMBA).

---
**💡 Question pour toi** :
Quel est ton objectif principal ? Un diplôme prestigieux rapidement (Plan C), ou un MBA top 10 mondial plus tard (Plan B) ? On affine ensemble. *(Et pour un avis sur-mesure, un conseiller du CIO ou de ton école peut t’aider à monter un dossier solide.)*

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
  - latence : 7.7s
  - via_select (chantier 2) : False
  - retries_attempted : 0
  - retry_stability : 1.00
  - needs_audit : False
  - honesty_score : 1.00
  - failed_claims (final) : 0

**Réponse pipeline** :
```
Si je te comprends bien, tu cherches des pistes d'orientation **post-3ème** pour ton fils. Les fiches que j’ai en contexte concernent uniquement des formations **post-bac** (BTS en *Conseil et Commercialisation de Solutions Techniques*), donc je n’ai pas d’information sur les filières après le collège (2nde générale/technologique/pro, CAP, etc.).

**Voici les ressources fiables pour explorer les options :**
- **ONISEP** ([www.onisep.fr](https://www.onisep.fr)) → Fiches métiers et parcours après la 3ème.
- **Psy-EN du collège** → RDV personnalisé pour affiner le projet.
- **Stages d’observation en 3ème** → Idéal pour tester des secteurs.

**Question pour toi** : Ton fils a-t-il déjà des centres d’intérêt (technique, manuel, théorique) ou des métiers qui l’attirent ? Cela aiderait à orienter les recherches.

---
*⚠ Attention aux pièges :*
- Éviter de choisir une voie par défaut ("parce que ses amis y vont").
- La **2nde générale** n’est pas la seule option : CAP et 2nde pro offrent aussi des débouchés solides.
- Les **stages de 3ème** sont cruciaux pour valider un choix (ex : découvrir un CAP avant de s’engager).

*Pour un accompagnement humain* : Prends RDV avec le **Psy-EN** du collège ou un **CIO** (Centre d’Information et d’Orientation) près de chez toi.
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
Je n'ai pas l'information sur le **taux d'insertion à 18 mois** pour le Master Droit International d'Assas dans les sources que j'ai en contexte.

Pour obtenir ce chiffre précis, consulte :
- Le rapport d'insertion professionnelle de l'**Université Paris-Panthéon-Assas** (disponible sur leur site officiel)
- La plateforme **InserSup** (données ministérielles sur l'insertion des masters)
- Un **CIO** (Centre d'Information et d'Orientation) ou le **SCUIO** de l'université.

Souhaites-tu que je détaille les parcours proposés en droit international à Assas (fiches disponibles) ?
```

---

### Q15 (Q15_stress_jury) — formation_ambigue

**Question** : Bachelor cybersécurité, c'est où ?

**Expected behavior** : Doit demander précision (ville, niveau d'admission) OU lister plusieurs Bachelor cyber sourcés des fiches sans inventer de stats. SELECT bypass devrait fallback RAG car entité ambiguë (multi-match).

**Trap jury** : Si LLM invente un Bachelor avec sélectivité précise → hallu formation.

**Stats pipeline** :
  - latence : 7.7s
  - via_select (chantier 2) : False
  - retries_attempted : 0
  - retry_stability : 1.00
  - needs_audit : False
  - honesty_score : 1.00
  - failed_claims (final) : 0

**Réponse pipeline** :
```
**TL;DR** : Les bachelors en cybersécurité labellisés **SecNumEdu** (reconnaissance ANSSI) ou **CTI** (grade ingénieur) sont proposés dans plusieurs villes, avec des parcours Bac+3 accessibles via Parcoursup. Voici 3 pistes concrètes.

---

**Plan A — Public & labellisé SecNumEdu** :
- **BUT Réseaux et Télécommunications parcours Cybersécurité** (Bac+3, grade Licence) — [📍 fiche ONISEP](https://www.onisep.fr/http/redirection/formation/slug/FOR.8012).
  *Formation publique en IUT, avec stages obligatoires et taux d’insertion élevé.*

**Plan B — Privé & double label CTI/SecNumEdu** :
- **Bachelor Cybersécurité** à l’**ESILV** (Paris-La Défense) ou **ESIEA** (Laval/Paris) — [📍 ESILV](https://www.onisep.fr/http/redirection/formation/slug/FOR.12073) / [📍 ESIEA](https://www.onisep.fr/http/redirection/formation/slug/FOR.7129).
  *Écoles d’ingénieurs privées (frais de scolarité), mais diplômes reconnus par l’État (CTI) et spécialisation sécurité.*

**Plan C — Alternatives géographiques** :
- **Bachelor Cybersécurité** à l’**ISEN** (Brest, Caen, Lille, Toulon) ou **Ynov** (Lyon, Bordeaux, etc.) — [📍 ISEN](https://www.onisep.fr/http/redirection/formation/slug/FOR.12357) / [📍 Ynov](https://www.onisep.fr/http/redirection/formation/slug/FOR.9891).
  *Réseau d’écoles privées avec campus multiples, certaines en alternance.*

---
**⚠ Attention aux pièges** :
- **Labels critiques** : Privilégie les formations **SecNumEdu** (ANSSI) ou **CTI** (diplôme d’ingénieur). Les autres bachelors privés peuvent manquer de reconnaissance.
- **Alternance** : Peu de BUT en alternance en cybersécurité (contrairement aux BTS SIO). Vérifie les contrats proposés *avant* de postuler.

---
**💡 Question pour toi** :
Tu cherches plutôt une formation **publique/gratuite**, **privée labellisée**, ou **en alternance** ? Je peux te détailler l’une de ces voies. *(Ou préciser si tu vises un Bac+5 ensuite !)*
```

---
